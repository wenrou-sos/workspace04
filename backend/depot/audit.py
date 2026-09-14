"""操作审计：记录关键业务动作到 OperationLog。"""
from .models import OperationLog


def actor_name(user):
    if not user or not user.is_authenticated:
        return ""
    profile = getattr(user, "profile", None)
    return (profile.display_name if profile and profile.display_name else user.username)


def write_log(user, action, module, target="", detail="", request=None):
    ip = ""
    if request is not None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = xff.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "") or ""
    return OperationLog.objects.create(
        user=user if user and user.is_authenticated else None,
        actor_name=actor_name(user),
        action=action,
        module=module,
        target=str(target)[:200],
        detail=detail[:5000],
        ip=ip or None,
    )


class AuditModelMixin:
    """为 ModelViewSet 增加创建/修改审计与创建人自动写入。

    子类可设置 audit_module（模块中文名）和 target_label(instance)。
    """

    audit_module = ""

    def target_label(self, instance):
        return str(instance)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create_action(self, instance):
        """新增成功后记录的日志动作，默认“新增”，子类可覆盖（如入库/出库）。"""
        return OperationLog.Action.CREATE

    def create_detail(self, instance):
        """新增日志详情，默认空，子类可覆盖。"""
        return ""

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:
            instance = self.get_queryset().model.objects.filter(pk=response.data.get("id")).first()
            write_log(
                request.user,
                self.create_action(instance) if instance else OperationLog.Action.CREATE,
                self.audit_module,
                self.target_label(instance) if instance else "",
                self.create_detail(instance) if instance else "",
                request=request,
            )
        return response

    def update(self, request, *args, **kwargs):
        label = self.target_label(self.get_object())
        response = super().update(request, *args, **kwargs)
        if response.status_code in (200, 202):
            write_log(
                request.user, OperationLog.Action.UPDATE, self.audit_module,
                label, "", request=request,
            )
        return response

    def destroy(self, request, *args, **kwargs):
        label = self.target_label(self.get_object())
        response = super().destroy(request, *args, **kwargs)
        if response.status_code in (200, 204):
            write_log(
                request.user, OperationLog.Action.DELETE, self.audit_module,
                label, "", request=request,
            )
        return response

from django.db.models import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.response import Response

from .audit import write_log
from .models import OperationLog


class ProtectedDeleteMixin:
    """删除被外键引用的对象时返回 409 中文说明；删除成功则写审计日志。"""

    audit_module = ""

    def target_label(self, instance):
        return str(instance)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        label = self.target_label(instance)
        try:
            self.perform_destroy(instance)
        except (ProtectedError, RestrictedError) as exc:
            refs = getattr(exc, "protected_objects", None) or getattr(exc, "restricted_objects", [])
            names = sorted({type(obj)._meta.verbose_name for obj in refs})
            detail = f"「{label}」已被{'、'.join(names)}引用，不能直接删除，请先清理相关业务数据。"
            return Response({"detail": detail}, status=status.HTTP_409_CONFLICT)
        write_log(request.user, OperationLog.Action.DELETE, self.audit_module, label, "", request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

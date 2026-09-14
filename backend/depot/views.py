"""视图：认证、岗位授权、仓房范围过滤、操作审计与仪表盘聚合。"""
from datetime import timedelta

from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import AuditModelMixin, actor_name, write_log
from .filters import MonitorRecordFilter, StockRecordFilter
from .mixins import ProtectedDeleteMixin
from .models import (
    FumigationTask,
    GrainBatch,
    Granary,
    MonitorRecord,
    OperationLog,
    StockRecord,
    Stocktake,
    StocktakeItem,
    UserProfile,
)
from .permissions import DepotPermission, can_access_granary, get_profile, is_director
from .serializers import (
    FumigationTaskSerializer,
    GrainBatchSerializer,
    GranarySerializer,
    MonitorRecordSerializer,
    OperationLogSerializer,
    StockRecordSerializer,
    StocktakeItemSerializer,
    StocktakeSerializer,
    UserManageSerializer,
    UserProfileSerializer,
)

# 可写岗位集合
WRITE_ROLES = {"admin", "director", "keeper"}
MANAGE_ROLES = {"admin", "director"}


class ScopedModelViewSet(ProtectedDeleteMixin, AuditModelMixin, viewsets.ModelViewSet):
    """业务 ViewSet 基类：登录 + 岗位权限 + 仓房数据范围 + 受保护删除。

    子类通过 granary_field 指定仓房外键过滤字段（None 表示模型本身就是仓房）。
    """

    permission_classes = [IsAuthenticated, DepotPermission]
    audit_module = ""
    # 仓房关联字段（用于范围过滤），None 表示该模型本身就是仓房
    granary_field = "granary_id"

    def scope_ids(self):
        """当前用户可见仓房 ID；None 表示不限。"""
        profile = get_profile(self.request.user)
        return profile.scoped_granary_ids() if profile else set()

    def get_queryset(self):
        qs = super().get_queryset()
        ids = self.scope_ids()
        if ids is None:
            return qs
        if self.granary_field is None:
            return qs.filter(pk__in=ids)
        return qs.filter(**{f"{self.granary_field}__in": ids})

    # 供权限类校验创建目标仓房
    def extract_granary(self, data):
        if self.granary_field is None:
            pk = data.get("id")
            return Granary.objects.filter(pk=pk).first()
        gid = data.get("granary")
        return Granary.objects.filter(pk=gid).first() if gid else None

    def obj_granary(self, obj):
        if self.granary_field is None:
            return obj
        return getattr(obj, "granary", None)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:
            instance = self.get_queryset().model.objects.filter(pk=response.data.get("id")).first()
            write_log(
                request.user, self.create_action(instance), self.audit_module,
                self.target_label(instance) if instance else "",
                self.audit_detail(instance) if instance else "",
                request=request,
            )
        return response

    def create_action(self, instance):
        return OperationLog.Action.CREATE

    def audit_detail(self, instance):
        return ""


class GranaryViewSet(ScopedModelViewSet):
    queryset = Granary.objects.all()
    serializer_class = GranarySerializer
    filterset_fields = ["status", "granary_type"]
    search_fields = ["code", "name", "manager"]
    audit_module = "仓房档案"
    granary_field = None
    create_roles = MANAGE_ROLES  # 保管员不能建/删仓房档案
    delete_roles = MANAGE_ROLES
    scoped_create = False

    @action(detail=True, methods=["get"])
    def temperature_series(self, request, pk=None):
        """单仓最近 24 小时温湿度趋势。"""
        granary = self.get_object()
        since = timezone.now() - timedelta(hours=24)
        records = granary.monitor_records.filter(recorded_at__gte=since).order_by("recorded_at")
        return Response(
            [
                {
                    "time": r.recorded_at.strftime("%H:%M"),
                    "avg_temp": float(r.avg_temp),
                    "max_temp": float(r.max_temp),
                    "humidity": float(r.humidity),
                    "alert": r.alert_level,
                }
                for r in records
            ]
        )


class GrainBatchViewSet(ScopedModelViewSet):
    queryset = GrainBatch.objects.select_related("granary").all()
    serializer_class = GrainBatchSerializer
    filterset_fields = ["granary", "grain_kind", "grade"]
    search_fields = ["batch_no", "origin"]
    audit_module = "库存批次"
    scoped_create = True


class MonitorRecordViewSet(ScopedModelViewSet):
    queryset = MonitorRecord.objects.select_related("granary").all()
    serializer_class = MonitorRecordSerializer
    filterset_class = MonitorRecordFilter
    search_fields = ["granary__code", "inspector"]
    audit_module = "温湿度监测"
    scoped_create = True

    def perform_create(self, serializer):
        super().perform_create(serializer)
        # 检测人直接取登录身份
        instance = serializer.instance
        instance.inspector = actor_name(self.request.user)
        instance.save(update_fields=["inspector"])

    @action(detail=False, methods=["get"])
    def latest(self, request):
        """每仓最新一条检测记录（按当前用户仓房范围）。"""
        ids = self.scope_ids()
        granaries = Granary.objects.all()
        if ids is not None:
            granaries = granaries.filter(pk__in=ids)
        rows = []
        for gid in granaries.values_list("id", flat=True):
            rec = MonitorRecord.objects.filter(granary_id=gid).first()
            if rec:
                rows.append(self.get_serializer(rec).data)
        return Response(rows)


class StockRecordViewSet(ScopedModelViewSet):
    queryset = StockRecord.objects.select_related("granary", "batch").all()
    serializer_class = StockRecordSerializer
    filterset_class = StockRecordFilter
    search_fields = ["record_no", "counterparty", "operator"]
    audit_module = "出入库"
    scoped_create = True

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        instance.operator = actor_name(self.request.user)
        instance.save(update_fields=["operator"])

    def perform_update(self, serializer):
        serializer.validated_data["operator"] = actor_name(self.request.user)
        super().perform_update(serializer)

    def create_action(self, instance):
        return OperationLog.Action.STOCK_IN if instance.direction == "in" else OperationLog.Action.STOCK_OUT

    def audit_detail(self, instance):
        return (
            f"{instance.get_direction_display()}{instance.quantity}吨，"
            f"{instance.get_biz_type_display()}，对方：{instance.counterparty or '—'}"
        )


class FumigationTaskViewSet(ScopedModelViewSet):
    queryset = FumigationTask.objects.select_related("granary").all()
    serializer_class = FumigationTaskSerializer
    filterset_fields = ["granary", "status", "agent"]
    search_fields = ["task_no", "leader", "granary__code"]
    audit_module = "熏蒸作业"
    scoped_create = True
    create_roles = MANAGE_ROLES  # 安排熏蒸仅主任/管理员
    action_roles = {"advance": WRITE_ROLES}  # 保管员可推进自己仓的作业状态

    def obj_granary(self, obj):
        return obj.granary

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        instance.leader = actor_name(self.request.user)
        instance.save(update_fields=["leader"])

    def perform_update(self, serializer):
        # 负责人字段不允许通过编辑接口被篡改
        serializer.validated_data.pop("leader", None)
        super().perform_update(serializer)

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        """状态推进：已安排 → 施药中 → 密闭中 → 通风散气 → 已完成。"""
        task = self.get_object()
        flow = {
            FumigationTask.Status.PLANNED: (FumigationTask.Status.RUNNING, "actual_start"),
            FumigationTask.Status.RUNNING: (FumigationTask.Status.SEALED, None),
            FumigationTask.Status.SEALED: (FumigationTask.Status.VENTILATING, None),
            FumigationTask.Status.VENTILATING: (FumigationTask.Status.DONE, "actual_end"),
        }
        if task.status not in flow:
            return Response({"detail": f"当前状态 {task.get_status_display()} 不可推进"}, status=400)
        new_status, time_field = flow[task.status]
        task.status = new_status
        if time_field:
            setattr(task, time_field, timezone.now())
        task.save()
        write_log(
            request.user, OperationLog.Action.FUMIGATION_ADVANCE, "熏蒸作业",
            str(task), f"{task.granary.code} 状态推进为 {task.get_status_display()}",
            request=request,
        )
        return Response(self.get_serializer(task).data)


class StocktakeViewSet(ScopedModelViewSet):
    queryset = Stocktake.objects.prefetch_related("items").all()
    serializer_class = StocktakeSerializer
    filterset_fields = ["status"]
    search_fields = ["stocktake_no", "name", "leader"]
    audit_module = "库存盘点"
    granary_field = None  # 盘点单是全库性单据，保管员可见但只能操作自己仓的明细
    create_roles = MANAGE_ROLES
    action_roles = {
        "generate_items": WRITE_ROLES,
        "finish": MANAGE_ROLES,  # 盘点调账（审核）仅主任/管理员
    }

    def get_queryset(self):
        # 盘点单不按仓房过滤（跨仓盘点），全部登录用户可见
        return viewsets.ModelViewSet.get_queryset(self)

    def obj_granary(self, obj):
        # 盘点单是跨仓单据，对象本身不归属单一仓房；
        # 保管员的仓房范围在 generate_items / finish 内部按明细过滤
        return None

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        instance.leader = actor_name(self.request.user)
        instance.save(update_fields=["leader"])

    @action(detail=True, methods=["post"])
    def generate_items(self, request, pk=None):
        """按当前在储批次生成/补充盘点明细（保管员只覆盖自己管辖仓房）。"""
        stocktake = self.get_object()
        if stocktake.status not in (Stocktake.Status.DRAFT, Stocktake.Status.COUNTING):
            return Response({"detail": "盘点已结束，不能再生成明细"}, status=400)
        batches = GrainBatch.objects.filter(quantity__gt=0).select_related("granary")
        ids = self.scope_ids()
        if ids is not None:
            batches = batches.filter(granary_id__in=ids)
        with transaction.atomic():
            # 不清空别人已生成的明细，仅补本仓房范围缺失的
            existing_batch_ids = set(stocktake.items.values_list("batch_id", flat=True))
            items = [
                StocktakeItem(
                    stocktake=stocktake, granary=batch.granary, batch=batch,
                    book_quantity=batch.quantity,
                )
                for batch in batches
                if batch.id not in existing_batch_ids
            ]
            StocktakeItem.objects.bulk_create(items)
            stocktake.status = Stocktake.Status.COUNTING
            stocktake.save(update_fields=["status"])
        write_log(
            request.user, OperationLog.Action.STOCKTAKE_GENERATE, "库存盘点",
            str(stocktake), f"生成/补充盘点明细 {len(items)} 条", request=request,
        )
        # 重新查询以刷新 prefetch_related 的 items 缓存
        refreshed = Stocktake.objects.prefetch_related("items").get(pk=stocktake.pk)
        return Response(StocktakeSerializer(refreshed).data)

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        """完成盘点（调账审核）：汇总差异并生成盘盈/盘亏调整流水。

        批次结存由出入库流水驱动，因此盘点调账为每个差异批次生成一条
        signed 调整流水——批次结存、仓房结存（流水汇总）、盘点结果三处一致。
        """
        stocktake = self.get_object()
        items_qs = stocktake.items.select_related("batch", "granary")
        ids = self.scope_ids()
        if ids is not None:
            items_qs = items_qs.filter(granary_id__in=ids)
        items = list(items_qs)
        if not items:
            return Response({"detail": "盘点明细为空，请先生成明细"}, status=400)
        unfilled = [i for i in items if i.actual_quantity is None]
        if unfilled:
            return Response({"detail": f"还有 {len(unfilled)} 条明细未填写实盘数量"}, status=400)

        operator = actor_name(request.user)
        seq = StockRecord.objects.filter(record_no__startswith=f"{stocktake.stocktake_no}-A").count()
        detail_lines = []
        with transaction.atomic():
            for item in items:
                diff = round(float(item.actual_quantity) - float(item.book_quantity), 2)
                item.gain_quantity = diff if diff > 0 else 0
                item.loss_quantity = -diff if diff < 0 else 0
                item.save()
                if diff == 0:
                    continue
                seq += 1
                StockRecord.objects.create(
                    record_no=f"{stocktake.stocktake_no}-A{seq:02d}",
                    granary=item.granary,
                    batch=item.batch,
                    direction=StockRecord.Direction.INBOUND if diff > 0 else StockRecord.Direction.OUTBOUND,
                    biz_type=StockRecord.BizType.ADJUST_GAIN if diff > 0 else StockRecord.BizType.ADJUST_LOSS,
                    quantity=abs(diff),
                    unit_price=0,
                    counterparty="库存盘点调账",
                    operator=operator,
                    remark=f"{stocktake.name} 盘点{'盘盈' if diff > 0 else '盘亏'}：{item.reason or '账实差异'}",
                    created_by=request.user,
                )
                detail_lines.append(f"{item.granary.code}/{item.batch.batch_no} {'+' if diff > 0 else ''}{diff}吨")

            # 全部明细都已实盘才允许置为已调账
            if not stocktake.items.filter(actual_quantity__isnull=True).exists():
                stocktake.status = Stocktake.Status.ADJUSTED
                stocktake.save(update_fields=["status"])
        write_log(
            request.user, OperationLog.Action.STOCKTAKE_ADJUST, "库存盘点",
            str(stocktake), "；".join(detail_lines) or "无差异", request=request,
        )
        return Response(StocktakeSerializer(stocktake).data)


class StocktakeItemViewSet(ScopedModelViewSet):
    queryset = StocktakeItem.objects.select_related("granary", "batch").all()
    serializer_class = StocktakeItemSerializer
    filterset_fields = ["stocktake", "granary"]
    audit_module = "盘点明细"
    http_method_names = ["get", "patch", "head", "options"]  # 明细由生成动作创建，不允许手工增删

    def perform_update(self, serializer):
        # 保管员只能录入实盘数量与差异原因，账面数等字段锁定
        allowed = {}
        if "actual_quantity" in serializer.validated_data:
            allowed["actual_quantity"] = serializer.validated_data["actual_quantity"]
        if "reason" in serializer.validated_data:
            allowed["reason"] = serializer.validated_data["reason"]
        serializer.save(**allowed)


class OperationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """操作审计日志：主任/管理员看全部，保管员只看自己。"""

    serializer_class = OperationLogSerializer
    permission_classes = [IsAuthenticated, DepotPermission]
    filterset_fields = ["action", "module", "user"]
    search_fields = ["actor_name", "target"]
    read_roles = {"admin", "director", "keeper"}  # 只读用户不开放审计日志

    def get_queryset(self):
        qs = OperationLog.objects.all()
        profile = get_profile(self.request.user)
        if profile and profile.role == UserProfile.Role.KEEPER:
            qs = qs.filter(user=self.request.user)
        return qs


class UserProfileViewSet(viewsets.ModelViewSet):
    """账号岗位管理：仅主任/管理员，可分配角色与管辖仓房、重置密码。"""

    permission_classes = [IsAuthenticated, DepotPermission]
    create_roles = MANAGE_ROLES
    update_roles = MANAGE_ROLES
    delete_roles = MANAGE_ROLES
    read_roles = MANAGE_ROLES  # 仅主任/管理员可查看账号清单
    queryset = UserProfile.objects.select_related("user").prefetch_related("granaries")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return UserManageSerializer
        return UserProfileSerializer

    def perform_create(self, serializer):
        from django.contrib.auth.models import User

        data = serializer.validated_data
        password = data.get("password")
        if not password:
            from rest_framework.serializers import ValidationError
            raise ValidationError({"password": "新建账号必须设置初始密码"})
        user = User.objects.create_user(
            username=data["username"], password=password,
            first_name=data.get("display_name", ""),
            is_staff=data["role"] == UserProfile.Role.ADMIN,
        )
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={"role": data["role"], "display_name": data["display_name"],
                      "phone": data.get("phone", "")},
        )
        profile.role = data["role"]
        profile.display_name = data["display_name"]
        profile.phone = data.get("phone", "")
        profile.save()
        if data["role"] == UserProfile.Role.KEEPER:
            profile.granaries.set(Granary.objects.filter(id__in=data.get("granary_ids", [])))
        else:
            profile.granaries.clear()
        serializer.instance = profile
        write_log(self.request.user, OperationLog.Action.CREATE, "账号岗位",
                  str(profile), f"创建账号 {user.username}", request=self.request)

    def perform_update(self, serializer):
        data = serializer.validated_data
        profile = self.get_object()
        user = profile.user
        if data.get("password"):
            user.set_password(data["password"])
        if "username" in data:
            user.username = data["username"]
        user.first_name = data.get("display_name", user.first_name)
        user.is_staff = data.get("role") == UserProfile.Role.ADMIN
        user.save()
        profile.role = data["role"]
        profile.display_name = data["display_name"]
        profile.phone = data.get("phone", profile.phone)
        profile.save()
        if data["role"] == UserProfile.Role.KEEPER and "granary_ids" in data:
            profile.granaries.set(Granary.objects.filter(id__in=data["granary_ids"]))
        elif data["role"] != UserProfile.Role.KEEPER:
            profile.granaries.clear()
        write_log(self.request.user, OperationLog.Action.UPDATE, "账号岗位",
                  str(profile), f"更新账号 {user.username}", request=self.request)

    def destroy(self, request, *args, **kwargs):
        profile = self.get_object()
        if profile.user == request.user:
            return Response({"detail": "不能删除当前登录账号"}, status=status.HTTP_400_BAD_REQUEST)
        if profile.user.is_superuser:
            return Response({"detail": "不能删除超级管理员账号"}, status=status.HTTP_400_BAD_REQUEST)
        label = str(profile)
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == 204:
            write_log(request.user, OperationLog.Action.DELETE, "账号岗位", label, "", request=request)
        return response


# ---------------- 认证 ----------------

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            write_log(None, OperationLog.Action.LOGIN_FAIL, "认证", username, "用户名或密码错误", request=request)
            return Response({"detail": "用户名或密码错误"}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        profile = getattr(user, "profile", None)
        write_log(user, OperationLog.Action.LOGIN, "认证", username, "登录成功", request=request)
        return Response(
            {
                "token": token.key,
                "user": {
                    "username": user.username,
                    "name": actor_name(user),
                    "role": profile.role if profile else "viewer",
                    "role_display": profile.get_role_display() if profile else "只读用户",
                    "granary_ids": list(profile.granaries.values_list("id", flat=True)) if profile else [],
                    "granary_codes": list(profile.granaries.values_list("code", flat=True)) if profile else [],
                    "is_manager": is_director(user),
                },
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        write_log(request.user, OperationLog.Action.LOGOUT, "认证", request.user.username, "", request=request)
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "已退出登录"})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, "profile", None)
        return Response(
            {
                "username": user.username,
                "name": actor_name(user),
                "role": profile.role if profile else "viewer",
                "role_display": profile.get_role_display() if profile else "只读用户",
                "granary_ids": list(profile.granaries.values_list("id", flat=True)) if profile else [],
                "granary_codes": list(profile.granaries.values_list("code", flat=True)) if profile else [],
                "is_manager": is_director(user),
            }
        )


# ---------------- 仪表盘（只读，按仓房范围统计） ----------------

class DashboardViewSet(viewsets.ViewSet):
    """仪表盘统计：所有登录用户只读，保管员仅统计本人管辖仓房。"""

    permission_classes = [IsAuthenticated]

    def _scoped_granaries(self):
        profile = get_profile(self.request.user)
        ids = profile.scoped_granary_ids() if profile else set()
        qs = Granary.objects.all()
        if ids is not None:
            qs = qs.filter(pk__in=ids)
        return qs, ids

    def list(self, request):
        granaries, ids = self._scoped_granaries()
        total_capacity = sum(float(g.capacity) for g in granaries)
        total_stock = sum(float(g.current_stock) for g in granaries)
        status_count = {s.value: 0 for s in Granary.Status}
        for g in granaries:
            status_count[g.status] += 1

        kind_qs = GrainBatch.objects.all()
        if ids is not None:
            kind_qs = kind_qs.filter(granary_id__in=ids)
        stock_by_kind = {}
        for b in kind_qs.values("grain_kind").annotate(q=Sum("quantity")):
            stock_by_kind[dict(GrainBatch.GrainKind.choices)[b["grain_kind"]]] = round(float(b["q"] or 0), 2)

        fumigation_qs = FumigationTask.objects.filter(
            status__in=["planned", "running", "sealed", "ventilating"]
        )
        monitor_qs = MonitorRecord.objects.filter(alert_level__in=["warning", "critical"])
        if ids is not None:
            fumigation_qs = fumigation_qs.filter(granary_id__in=ids)
            monitor_qs = monitor_qs.filter(granary_id__in=ids)

        since = timezone.now() - timedelta(days=7)
        in_qs = StockRecord.objects.filter(direction="in", occurred_at__gte=since)
        out_qs = StockRecord.objects.filter(direction="out", occurred_at__gte=since)
        if ids is not None:
            in_qs = in_qs.filter(granary_id__in=ids)
            out_qs = out_qs.filter(granary_id__in=ids)
        in_q = in_qs.aggregate(q=Sum("quantity"))["q"] or 0
        out_q = out_qs.aggregate(q=Sum("quantity"))["q"] or 0

        return Response(
            {
                "granary_count": granaries.count(),
                "total_capacity": round(total_capacity, 2),
                "total_stock": round(total_stock, 2),
                "utilization": round(total_stock / total_capacity * 100, 1) if total_capacity else 0,
                "status_count": status_count,
                "stock_by_kind": stock_by_kind,
                "active_fumigations": fumigation_qs.count(),
                "warning_count": monitor_qs.count(),
                "week_inbound": round(float(in_q), 2),
                "week_outbound": round(float(out_q), 2),
            }
        )

    @action(detail=False, methods=["get"])
    def trend(self, request):
        _, ids = self._scoped_granaries()
        since = timezone.now().date() - timedelta(days=6)
        records = (
            StockRecord.objects.filter(occurred_at__date__gte=since)
        )
        if ids is not None:
            records = records.filter(granary_id__in=ids)
        records = (
            records.annotate(day=TruncDate("occurred_at"))
            .values("day", "direction")
            .annotate(q=Sum("quantity"))
            .order_by("day")
        )
        days = [(since + timedelta(days=i)).strftime("%m-%d") for i in range(7)]
        inbound = {d: 0 for d in days}
        outbound = {d: 0 for d in days}
        for r in records:
            key = r["day"].strftime("%m-%d")
            if key in inbound:
                target = inbound if r["direction"] == "in" else outbound
                target[key] = round(float(r["q"] or 0), 2)
        return Response(
            {"days": days, "inbound": list(inbound.values()), "outbound": list(outbound.values())}
        )

    @action(detail=False, methods=["get"])
    def temp_monitor(self, request):
        granaries, _ = self._scoped_granaries()
        result = []
        for granary in granaries:
            latest = granary.monitor_records.first()
            result.append(
                {
                    "granary_code": granary.code,
                    "granary_name": granary.name,
                    "manager": granary.manager,
                    "status": granary.status,
                    "avg_temp": float(latest.avg_temp) if latest else None,
                    "max_temp": float(latest.max_temp) if latest else None,
                    "humidity": float(latest.humidity) if latest else None,
                    "alert_level": latest.alert_level if latest else None,
                    "recorded_at": latest.recorded_at.strftime("%m-%d %H:%M") if latest else None,
                }
            )
        since = timezone.now() - timedelta(hours=12)
        alerts = MonitorRecord.objects.filter(
            alert_level__in=["warning", "critical"], recorded_at__gte=since
        ).select_related("granary")
        ids = self._scoped_granaries()[1]
        if ids is not None:
            alerts = alerts.filter(granary_id__in=ids)
        alerts = alerts[:20]
        alert_list = [
            {
                "granary": a.granary.code,
                "time": a.recorded_at.strftime("%m-%d %H:%M"),
                "avg_temp": float(a.avg_temp),
                "max_temp": float(a.max_temp),
                "humidity": float(a.humidity),
                "level": a.alert_level,
                "note": a.note,
            }
            for a in alerts
        ]
        return Response({"granaries": result, "alerts": alert_list})

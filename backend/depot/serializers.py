from rest_framework import serializers

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


class GranarySerializer(serializers.ModelSerializer):
    granary_type_display = serializers.CharField(source="get_granary_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    current_stock = serializers.SerializerMethodField()
    utilization = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.profile.display_name", read_only=True, default=None)

    class Meta:
        model = Granary
        fields = "__all__"
        read_only_fields = ("status", "created_by")

    def get_current_stock(self, obj):
        return round(float(obj.current_stock), 2)

    def get_utilization(self, obj):
        return obj.utilization


class GrainBatchSerializer(serializers.ModelSerializer):
    grain_kind_display = serializers.CharField(source="get_grain_kind_display", read_only=True)
    grade_display = serializers.CharField(source="get_grade_display", read_only=True)
    granary_code = serializers.CharField(source="granary.code", read_only=True)

    class Meta:
        model = GrainBatch
        fields = "__all__"
        read_only_fields = ("quantity", "created_by")


class MonitorRecordSerializer(serializers.ModelSerializer):
    alert_level_display = serializers.CharField(source="get_alert_level_display", read_only=True)
    granary_code = serializers.CharField(source="granary.code", read_only=True)

    class Meta:
        model = MonitorRecord
        fields = "__all__"
        read_only_fields = ("alert_level", "inspector", "created_by")


class StockRecordSerializer(serializers.ModelSerializer):
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    biz_type_display = serializers.CharField(source="get_biz_type_display", read_only=True)
    granary_code = serializers.CharField(source="granary.code", read_only=True)
    batch_no = serializers.CharField(source="batch.batch_no", read_only=True, allow_null=True)
    signed_quantity = serializers.FloatField(read_only=True)
    amount = serializers.SerializerMethodField()
    voided_by_name = serializers.CharField(source="voided_by.profile.display_name", read_only=True, default=None)

    class Meta:
        model = StockRecord
        fields = "__all__"
        read_only_fields = (
            "operator", "created_by", "is_void", "void_reason",
            "voided_at", "voided_by",
        )

    def get_amount(self, obj):
        return round(float(obj.quantity) * float(obj.unit_price), 2)

    def validate(self, attrs):
        from .stock_locks import (
            assert_granary_open,
            assert_non_negative,
            assert_record_mutable,
        )

        instance = self.instance  # None=新增，否则为更正
        data = attrs

        direction = data.get("direction") or (instance.direction if instance else None)
        quantity = data.get("quantity")
        if quantity is not None:
            quantity = float(quantity)
            if quantity <= 0:
                raise serializers.ValidationError("数量必须大于 0")
        batch = data.get("batch")
        granary = data.get("granary")
        occurred_at = data.get("occurred_at") or (instance.occurred_at if instance else None)

        if instance is None:
            # ---- 新增 ----
            if batch is None:
                raise serializers.ValidationError({"batch": "请选择批次"})
            if granary is None:
                granary = batch.granary
                data["granary"] = granary
            if batch.granary_id != granary.id:
                raise serializers.ValidationError({"batch": "所选批次不属于该仓房"})
            # 盘盈/盘亏只能由盘点流程生成
            if data.get("biz_type") in (StockRecord.BizType.ADJUST_GAIN, StockRecord.BizType.ADJUST_LOSS):
                raise serializers.ValidationError({"biz_type": "盘盈/盘亏调整单由盘点流程自动生成"})
            assert_granary_open(granary)
            if direction == StockRecord.Direction.OUTBOUND and quantity is not None:
                assert_non_negative(batch, -quantity)
        else:
            # ---- 更正：系统调账单与已作废单锁定 ----
            request = self.context.get("request")
            new_batch = batch if batch is not None else instance.batch
            new_granary = granary if granary is not None else instance.granary
            new_direction = direction
            new_occurred_at = occurred_at
            # 保管员不能把单据更正到自己管辖范围之外的仓房/批次
            if request is not None and not request.user.is_superuser:
                from .permissions import can_access_granary
                if not can_access_granary(request.user, new_granary):
                    raise serializers.ValidationError({"granary": "无权将单据更正到非本人管辖的仓房"})
            assert_record_mutable(instance, new_occurred_at, new_granary, new_batch)
            if new_batch.granary_id != new_granary.id:
                raise serializers.ValidationError({"batch": "所选批次不属于该仓房"})

            new_qty = float(quantity if quantity is not None else instance.quantity)
            new_signed = float(new_qty) if new_direction == "in" else -float(new_qty)
            # 扣除原单影响后，新影响下的批次结存不得为负
            assert_non_negative(new_batch, new_signed, exclude_record=instance)
            # 若换了批次，旧批次冲销原单后也不应为负（正常只会减少出库/增入库，理论非负，做防御）
            if instance.batch_id and new_batch.id != instance.batch_id:
                assert_non_negative(instance.batch, -float(instance.signed_quantity))
        return attrs


class FumigationTaskSerializer(serializers.ModelSerializer):
    agent_display = serializers.CharField(source="get_agent_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    granary_code = serializers.CharField(source="granary.code", read_only=True)

    class Meta:
        model = FumigationTask
        fields = "__all__"
        read_only_fields = ("leader", "actual_start", "actual_end", "status", "created_by")

    def validate(self, attrs):
        start = attrs.get("plan_start")
        end = attrs.get("plan_end")
        if start and end and end <= start:
            raise serializers.ValidationError("计划结束时间必须晚于开始时间。")
        return attrs


class StocktakeItemSerializer(serializers.ModelSerializer):
    batch_no = serializers.CharField(source="batch.batch_no", read_only=True)
    granary_code = serializers.CharField(source="granary.code", read_only=True)
    diff = serializers.SerializerMethodField()

    class Meta:
        model = StocktakeItem
        fields = "__all__"

    def get_diff(self, obj):
        if obj.actual_quantity is None:
            return None
        return round(float(obj.actual_quantity) - float(obj.book_quantity), 2)


class StocktakeSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = StocktakeItemSerializer(many=True, read_only=True)
    total_book = serializers.SerializerMethodField()
    total_actual = serializers.SerializerMethodField()
    total_diff = serializers.SerializerMethodField()

    class Meta:
        model = Stocktake
        fields = "__all__"
        read_only_fields = ("status", "leader", "created_by")

    def _totals(self, obj):
        book = sum(float(i.book_quantity) for i in obj.items.all())
        actual = sum(float(i.actual_quantity or 0) for i in obj.items.all())
        return book, actual

    def get_total_book(self, obj):
        return round(self._totals(obj)[0], 2)

    def get_total_actual(self, obj):
        return round(self._totals(obj)[1], 2)

    def get_total_diff(self, obj):
        book, actual = self._totals(obj)
        return round(actual - book, 2)


class OperationLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = OperationLog
        fields = "__all__"


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    granary_codes = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ["id", "username", "role", "role_display", "display_name", "phone", "granary_codes"]

    def get_granary_codes(self, obj):
        return list(obj.granaries.values_list("code", flat=True))


class UserManageSerializer(serializers.Serializer):
    """账号创建/编辑：同时维护 Django 账号、岗位与管辖仓房。"""

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, required=False, allow_blank=True,
                                     help_text="新建必填，编辑时留空表示不改密码")
    display_name = serializers.CharField(max_length=30)
    role = serializers.ChoiceField(choices=UserProfile.Role.choices)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    granary_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    def validate_username(self, value):
        from django.contrib.auth.models import User
        qs = User.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise serializers.ValidationError("用户名已存在")
        return value
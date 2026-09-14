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

    class Meta:
        model = StockRecord
        fields = "__all__"
        read_only_fields = ("operator", "created_by")

    def get_amount(self, obj):
        return round(float(obj.quantity) * float(obj.unit_price), 2)

    def validate(self, attrs):
        if attrs.get("direction") == StockRecord.Direction.OUTBOUND:
            batch = attrs.get("batch")
            qty = float(attrs.get("quantity", 0))
            if batch and qty > float(batch.quantity):
                raise serializers.ValidationError(
                    f"出库数量 {qty} 吨超过批次结存 {float(batch.quantity)} 吨"
                )
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
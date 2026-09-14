from rest_framework import serializers

from .models import (
    FumigationTask,
    GrainBatch,
    Granary,
    MonitorRecord,
    StockRecord,
    Stocktake,
    StocktakeItem,
)


class GranarySerializer(serializers.ModelSerializer):
    granary_type_display = serializers.CharField(source="get_granary_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    current_stock = serializers.SerializerMethodField()
    utilization = serializers.SerializerMethodField()

    class Meta:
        model = Granary
        fields = "__all__"

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


class MonitorRecordSerializer(serializers.ModelSerializer):
    alert_level_display = serializers.CharField(source="get_alert_level_display", read_only=True)
    granary_code = serializers.CharField(source="granary.code", read_only=True)

    class Meta:
        model = MonitorRecord
        fields = "__all__"


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

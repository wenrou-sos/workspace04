import django_filters

from .models import MonitorRecord, StockRecord


class MonitorRecordFilter(django_filters.FilterSet):
    recorded_at__gte = django_filters.IsoDateTimeFilter(field_name="recorded_at", lookup_expr="gte")
    recorded_at__lte = django_filters.IsoDateTimeFilter(field_name="recorded_at", lookup_expr="lte")

    class Meta:
        model = MonitorRecord
        fields = ["granary", "alert_level", "recorded_at__gte", "recorded_at__lte"]


class StockRecordFilter(django_filters.FilterSet):
    occurred_at__gte = django_filters.IsoDateTimeFilter(field_name="occurred_at", lookup_expr="gte")
    occurred_at__lte = django_filters.IsoDateTimeFilter(field_name="occurred_at", lookup_expr="lte")

    class Meta:
        model = StockRecord
        fields = [
            "granary", "direction", "biz_type", "batch",
            "occurred_at__gte", "occurred_at__lte",
        ]

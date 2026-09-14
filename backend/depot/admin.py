from django.contrib import admin

from .models import (
    FumigationTask,
    GrainBatch,
    Granary,
    MonitorRecord,
    StockRecord,
    Stocktake,
    StocktakeItem,
)


@admin.register(Granary)
class GranaryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "granary_type", "capacity", "status", "manager")
    list_filter = ("status", "granary_type")
    search_fields = ("code", "name", "manager")


@admin.register(GrainBatch)
class GrainBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_no", "granary", "grain_kind", "grade", "quantity", "stored_at")
    list_filter = ("grain_kind", "grade")
    search_fields = ("batch_no", "origin")


@admin.register(MonitorRecord)
class MonitorRecordAdmin(admin.ModelAdmin):
    list_display = ("granary", "recorded_at", "avg_temp", "max_temp", "humidity", "alert_level")
    list_filter = ("alert_level",)


@admin.register(StockRecord)
class StockRecordAdmin(admin.ModelAdmin):
    list_display = ("record_no", "granary", "direction", "biz_type", "quantity", "occurred_at")
    list_filter = ("direction", "biz_type")
    search_fields = ("record_no", "counterparty")


@admin.register(FumigationTask)
class FumigationTaskAdmin(admin.ModelAdmin):
    list_display = ("task_no", "granary", "agent", "status", "plan_start", "plan_end", "leader")
    list_filter = ("status", "agent")


class StocktakeItemInline(admin.TabularInline):
    model = StocktakeItem
    extra = 0


@admin.register(Stocktake)
class StocktakeAdmin(admin.ModelAdmin):
    list_display = ("stocktake_no", "name", "plan_date", "leader", "status")
    list_filter = ("status",)
    inlines = [StocktakeItemInline]

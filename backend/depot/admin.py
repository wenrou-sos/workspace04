from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

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


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    filter_horizontal = ("granaries",)
    verbose_name_plural = "岗位与管辖仓房"


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "email", "first_name", "is_staff", "is_active")


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


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
    list_display = ("granary", "recorded_at", "avg_temp", "max_temp", "humidity", "alert_level", "inspector")
    list_filter = ("alert_level",)


@admin.register(StockRecord)
class StockRecordAdmin(admin.ModelAdmin):
    list_display = ("record_no", "granary", "direction", "biz_type", "quantity", "operator", "occurred_at")
    list_filter = ("direction", "biz_type")
    search_fields = ("record_no", "counterparty", "operator")


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


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_name", "action", "module", "target", "ip")
    list_filter = ("action", "module")
    search_fields = ("actor_name", "target", "detail")
    readonly_fields = ("user", "actor_name", "action", "module", "target", "detail", "ip", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

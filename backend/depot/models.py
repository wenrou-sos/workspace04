"""粮食储备库核心数据模型。

覆盖七大业务域：
- 账号与岗位（UserProfile：管理员/主任/保管员/只读用户，保管员按仓房授权）
- 仓房管理（Granary）
- 粮情/库存批次（GrainBatch）
- 温湿度监测（MonitorRecord）
- 出入库记录（StockRecord，联动结存数量）
- 熏蒸作业（FumigationTask）
- 库存盘点（Stocktake / StocktakeItem）
- 操作审计（OperationLog，所有关键动作追到人）
"""
from django.conf import settings
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class TimeStampedModel(models.Model):
    """带创建/更新时间的基类。"""

    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        abstract = True


class UserProfile(models.Model):
    """用户岗位档案：与 Django 账号一对一。"""

    class Role(models.TextChoices):
        ADMIN = "admin", "系统管理员"
        DIRECTOR = "director", "库管主任"
        KEEPER = "keeper", "保管员"
        VIEWER = "viewer", "只读用户"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile",
        verbose_name="系统账号",
    )
    role = models.CharField("岗位角色", max_length=20, choices=Role.choices, default=Role.VIEWER)
    display_name = models.CharField("姓名", max_length=30, blank=True)
    phone = models.CharField("联系电话", max_length=20, blank=True)
    # 保管员可管辖的仓房（主任/管理员默认全部，viewer 只读全部）
    granaries = models.ManyToManyField(
        "Granary", verbose_name="管辖仓房", blank=True, related_name="keepers"
    )

    class Meta:
        verbose_name = "用户岗位"
        verbose_name_plural = "用户岗位"
        db_table = "depot_user_profile"

    def __str__(self):
        return f"{self.display_name or self.user.username}（{self.get_role_display()}）"

    @property
    def role_level(self):
        return {
            self.Role.ADMIN: 4,
            self.Role.DIRECTOR: 3,
            self.Role.KEEPER: 2,
            self.Role.VIEWER: 1,
        }.get(self.role, 0)

    def can_access_granary(self, granary):
        """判断该用户是否有权访问指定仓房。"""
        if self.role in {self.Role.ADMIN, self.Role.DIRECTOR, self.Role.VIEWER}:
            return True
        if granary is None:
            return False
        return self.granaries.filter(pk=granary.pk).exists()

    def scoped_granary_ids(self):
        """该用户可见的仓房 ID 集合；None 表示不限制（全仓）。"""
        if self.role in {self.Role.ADMIN, self.Role.DIRECTOR, self.Role.VIEWER}:
            return None
        return set(self.granaries.values_list("pk", flat=True))


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    """新建账号时自动创建岗位档案；超级用户默认管理员。"""
    if created and not hasattr(instance, "profile"):
        UserProfile.objects.create(
            user=instance,
            role=UserProfile.Role.ADMIN if instance.is_superuser else UserProfile.Role.VIEWER,
            display_name=instance.username,
        )


class OperationLog(models.Model):
    """关键业务操作审计日志，全部操作可追溯到人。"""

    class Action(models.TextChoices):
        LOGIN = "login", "登录"
        LOGIN_FAIL = "login_fail", "登录失败"
        LOGOUT = "logout", "登出"
        CREATE = "create", "新增"
        UPDATE = "update", "修改"
        DELETE = "delete", "删除"
        STOCK_IN = "stock_in", "入库"
        STOCK_OUT = "stock_out", "出库"
        FUMIGATION_ADVANCE = "fumigation_advance", "熏蒸状态推进"
        STOCKTAKE_GENERATE = "stocktake_generate", "生成盘点明细"
        STOCKTAKE_ADJUST = "stocktake_adjust", "盘点调账"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="operation_logs", verbose_name="操作人",
    )
    actor_name = models.CharField("操作人姓名", max_length=30, blank=True)
    action = models.CharField("动作", max_length=30, choices=Action.choices)
    module = models.CharField("业务模块", max_length=30)
    target = models.CharField("操作对象", max_length=200, blank=True)
    detail = models.TextField("操作详情", blank=True)
    ip = models.GenericIPAddressField("IP 地址", null=True, blank=True)
    created_at = models.DateTimeField("操作时间", auto_now_add=True)

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ["-created_at"]
        db_table = "depot_operation_log"

    def __str__(self):
        return f"{self.actor_name} {self.get_action_display()} {self.target} @ {self.created_at:%Y-%m-%d %H:%M}"


class Granary(TimeStampedModel):
    """粮仓仓房档案。"""

    class GranaryType(models.TextChoices):
        SQUARE = "square", "平房仓"
        SILO = "silo", "立筒仓"
        UNDERGROUND = "underground", "地下仓"
        SHALLOW = "shallow", "浅圆仓"

    class Status(models.TextChoices):
        EMPTY = "empty", "空仓"
        STORING = "storing", "在储"
        FUMIGATING = "fumigating", "熏蒸中"
        MAINTENANCE = "maintenance", "检修"

    code = models.CharField("仓号", max_length=20, unique=True)
    name = models.CharField("仓房名称", max_length=50)
    granary_type = models.CharField("仓型", max_length=20, choices=GranaryType.choices)
    capacity = models.DecimalField("设计仓容(吨)", max_digits=10, decimal_places=2)
    area = models.DecimalField("建筑面积(㎡)", max_digits=10, decimal_places=2, default=0)
    manager = models.CharField("保管员", max_length=30)
    location = models.CharField("库区位置", max_length=100, blank=True)
    build_year = models.PositiveIntegerField("建成年份", null=True, blank=True)
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.EMPTY)
    temperature_threshold = models.DecimalField("温度告警阈值(℃)", max_digits=5, decimal_places=1, default=25)
    humidity_threshold = models.DecimalField("湿度告警阈值(%)", max_digits=5, decimal_places=1, default=70)
    remark = models.TextField("备注", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_granaries", verbose_name="建档人",
    )

    class Meta:
        verbose_name = "仓房"
        verbose_name_plural = "仓房"
        ordering = ["code"]
        db_table = "depot_granary"

    def __str__(self):
        return f"{self.code} {self.name}"

    @property
    def current_stock(self):
        """当前结存数量（吨），由出入库流水汇总。"""
        from django.db.models import Case, DecimalField, F, Sum, When

        total = self.stock_records.aggregate(
            q=Sum(
                Case(
                    When(direction="in", then="quantity"),
                    default=-F("quantity"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )["q"]
        return total or 0

    @property
    def utilization(self):
        """仓容利用率（%）。"""
        if not self.capacity:
            return 0
        return round(float(self.current_stock) / float(self.capacity) * 100, 1)


class GrainBatch(TimeStampedModel):
    """库存粮批次（一仓可存多批次，实际多为一仓一货位）。"""

    class GrainKind(models.TextChoices):
        WHEAT = "wheat", "小麦"
        RICE = "rice", "稻谷"
        CORN = "corn", "玉米"
        SOYBEAN = "soybean", "大豆"
        PADDY = "paddy", "水稻"

    class QualityGrade(models.TextChoices):
        GRADE1 = "1", "一等"
        GRADE2 = "2", "二等"
        GRADE3 = "3", "三等"
        GRADE4 = "4", "四等"
        GRADE5 = "5", "五等"

    granary = models.ForeignKey(
        Granary, verbose_name="所在仓房", on_delete=models.PROTECT, related_name="batches"
    )
    batch_no = models.CharField("批次号", max_length=30, unique=True)
    grain_kind = models.CharField("粮食品种", max_length=20, choices=GrainKind.choices)
    grade = models.CharField("质量等级", max_length=2, choices=QualityGrade.choices, default="3")
    origin = models.CharField("产地", max_length=60, blank=True)
    quantity = models.DecimalField("结存数量(吨)", max_digits=12, decimal_places=2, default=0)
    inbound_price = models.DecimalField("入库单价(元/吨)", max_digits=10, decimal_places=2, default=0)
    production_year = models.PositiveIntegerField("生产年份", null=True, blank=True)
    stored_at = models.DateField("入库日期", default=timezone.localdate)
    moisture = models.DecimalField("水分(%)", max_digits=5, decimal_places=2, default=0)
    impurity = models.DecimalField("杂质(%)", max_digits=5, decimal_places=2, default=0)
    remark = models.TextField("备注", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_batches", verbose_name="登记人",
    )

    class Meta:
        verbose_name = "粮油库存批次"
        verbose_name_plural = "粮油库存批次"
        ordering = ["-stored_at"]
        db_table = "depot_grain_batch"

    def __str__(self):
        return f"{self.batch_no} ({self.get_grain_kind_display()})"


class MonitorRecord(TimeStampedModel):
    """粮情温湿度检测记录（测温电缆/人工巡检）。"""

    class AlertLevel(models.TextChoices):
        NORMAL = "normal", "正常"
        WARNING = "warning", "预警"
        CRITICAL = "critical", "告警"

    granary = models.ForeignKey(
        Granary, verbose_name="仓房", on_delete=models.CASCADE, related_name="monitor_records"
    )
    recorded_at = models.DateTimeField("检测时间", default=timezone.now)
    avg_temp = models.DecimalField("平均粮温(℃)", max_digits=5, decimal_places=2)
    max_temp = models.DecimalField("最高粮温(℃)", max_digits=5, decimal_places=2)
    min_temp = models.DecimalField("最低粮温(℃)", max_digits=5, decimal_places=2)
    ambient_temp = models.DecimalField("仓温(℃)", max_digits=5, decimal_places=2, default=0)
    humidity = models.DecimalField("仓内相对湿度(%)", max_digits=5, decimal_places=2)
    outside_temp = models.DecimalField("外温(℃)", max_digits=5, decimal_places=2, default=0)
    outside_humidity = models.DecimalField("外湿(%)", max_digits=5, decimal_places=2, default=0)
    sensor_layer = models.CharField("检测层点", max_length=30, blank=True, help_text="如：上层/中层/下层")
    alert_level = models.CharField("告警级别", max_length=10, choices=AlertLevel.choices, default=AlertLevel.NORMAL)
    inspector = models.CharField("检测人", max_length=30, blank=True)
    note = models.CharField("情况说明", max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_monitors", verbose_name="录入人",
    )

    class Meta:
        verbose_name = "温湿度检测记录"
        verbose_name_plural = "温湿度检测记录"
        ordering = ["-recorded_at"]
        db_table = "depot_monitor_record"

    def __str__(self):
        return f"{self.granary.code} {self.recorded_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        # 根据仓房阈值自动判定告警级别
        if not self.granary_id:
            super().save(*args, **kwargs)
            return
        t_limit = float(self.granary.temperature_threshold)
        h_limit = float(self.granary.humidity_threshold)
        temps = [float(self.avg_temp), float(self.max_temp)]
        humidity = float(self.humidity)
        if max(temps) >= t_limit + 3 or humidity >= h_limit + 10:
            self.alert_level = self.AlertLevel.CRITICAL
        elif max(temps) >= t_limit or humidity >= h_limit:
            self.alert_level = self.AlertLevel.WARNING
        else:
            self.alert_level = self.AlertLevel.NORMAL
        super().save(*args, **kwargs)


class StockRecord(TimeStampedModel):
    """出入库流水记录，写入时联动批次结存数量。"""

    class Direction(models.TextChoices):
        INBOUND = "in", "入库"
        OUTBOUND = "out", "出库"

    class BizType(models.TextChoices):
        PURCHASE = "purchase", "收购入库"
        TRANSFER_IN = "transfer_in", "调拨入仓"
        RETURN = "return", "退货入库"
        SALE = "sale", "销售出库"
        TRANSFER_OUT = "transfer_out", "调出出仓"
        LOSS = "loss", "损耗出库"
        PROCESS = "process", "加工出库"
        ADJUST_GAIN = "adjust_gain", "盘盈入库"
        ADJUST_LOSS = "adjust_loss", "盘亏出库"

    record_no = models.CharField("单据编号", max_length=30, unique=True)
    granary = models.ForeignKey(
        Granary, verbose_name="仓房", on_delete=models.PROTECT, related_name="stock_records"
    )
    batch = models.ForeignKey(
        GrainBatch, verbose_name="粮油批次", on_delete=models.PROTECT,
        related_name="stock_records", null=True, blank=True,
    )
    direction = models.CharField("出入库方向", max_length=5, choices=Direction.choices)
    biz_type = models.CharField("业务类型", max_length=20, choices=BizType.choices)
    quantity = models.DecimalField("数量(吨)", max_digits=12, decimal_places=2)
    unit_price = models.DecimalField("单价(元/吨)", max_digits=10, decimal_places=2, default=0)
    counterparty = models.CharField("对方单位/客户", max_length=100, blank=True)
    operator = models.CharField("经办人", max_length=30)
    occurred_at = models.DateTimeField("出入库时间", default=timezone.now)
    remark = models.CharField("备注", max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_stock_records", verbose_name="制单人",
    )

    class Meta:
        verbose_name = "出入库记录"
        verbose_name_plural = "出入库记录"
        ordering = ["-occurred_at"]
        db_table = "depot_stock_record"

    def __str__(self):
        return f"{self.record_no} {self.get_direction_display()}{self.quantity}吨"

    @property
    def signed_quantity(self):
        """带符号数量：入库为正、出库为负。"""
        q = float(self.quantity)
        return q if self.direction == self.Direction.INBOUND else -q

    @transaction.atomic
    def save(self, *args, **kwargs):
        creating = self._state.adding
        old = None
        if not creating:
            old = StockRecord.objects.get(pk=self.pk)
        super().save(*args, **kwargs)
        if self.batch_id:
            batch = GrainBatch.objects.select_for_update().get(pk=self.batch_id)
            delta = float(self.signed_quantity)
            if old and old.batch_id:
                old_signed = float(old.quantity)
                old_signed = old_signed if old.direction == self.Direction.INBOUND else -old_signed
                if old.batch_id == batch.id:
                    delta -= old_signed
                else:
                    old_batch = GrainBatch.objects.select_for_update().get(pk=old.batch_id)
                    old_batch.quantity = max(0, float(old_batch.quantity) - old_signed)
                    old_batch.save(update_fields=["quantity"])
            batch.quantity = float(batch.quantity) + delta
            batch.save(update_fields=["quantity"])
        self._sync_granary_status()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        batch = self.batch
        old_signed = float(self.signed_quantity)
        granary = self.granary
        super().delete(*args, **kwargs)
        if batch:
            batch.quantity = max(0, float(batch.quantity) - old_signed)
            batch.save(update_fields=["quantity"])
        # 状态重算
        if granary.stock_records.exists():
            granary.status = Granary.Status.FUMIGATING if granary.status == Granary.Status.FUMIGATING else Granary.Status.STORING
        elif granary.status != Granary.Status.MAINTENANCE:
            granary.status = Granary.Status.EMPTY
        granary.save(update_fields=["status"])

    def _sync_granary_status(self):
        granary = self.granary
        if granary.status == Granary.Status.MAINTENANCE:
            return
        if granary.current_stock > 0:
            if granary.status != Granary.Status.FUMIGATING:
                granary.status = Granary.Status.STORING
        else:
            granary.status = Granary.Status.EMPTY
        granary.save(update_fields=["status"])


class FumigationTask(TimeStampedModel):
    """熏蒸作业安排（磷化氢/环流熏蒸等）。"""

    class Agent(models.TextChoices):
        PH3 = "ph3", "磷化氢(环流熏蒸)"
        ALP = "alp", "磷化铝片剂"
        CO2 = "co2", "气调(二氧化碳)"
        OTHER = "other", "其他药剂"

    class Status(models.TextChoices):
        PLANNED = "planned", "已安排"
        RUNNING = "running", "施药中"
        SEALED = "sealed", "密闭中"
        VENTILATING = "ventilating", "通风散气"
        DONE = "done", "已完成"
        CANCELED = "canceled", "已取消"

    task_no = models.CharField("作业单号", max_length=30, unique=True)
    granary = models.ForeignKey(
        Granary, verbose_name="熏蒸仓房", on_delete=models.PROTECT, related_name="fumigations"
    )
    agent = models.CharField("熏蒸药剂", max_length=10, choices=Agent.choices)
    dose = models.DecimalField("用药量(kg)", max_digits=8, decimal_places=2)
    plan_start = models.DateTimeField("计划开始时间")
    plan_end = models.DateTimeField("计划结束时间")
    actual_start = models.DateTimeField("实际开始时间", null=True, blank=True)
    actual_end = models.DateTimeField("实际结束时间", null=True, blank=True)
    seal_days = models.PositiveIntegerField("密闭天数", default=7)
    status = models.CharField("作业状态", max_length=12, choices=Status.choices, default=Status.PLANNED)
    leader = models.CharField("作业负责人", max_length=30)
    team = models.CharField("作业人员", max_length=200, blank=True)
    target_pest = models.CharField("防治对象", max_length=100, blank=True, help_text="如：玉米象、赤拟谷盗")
    effect = models.CharField("熏蒸效果", max_length=200, blank=True)
    safety_note = models.TextField("安全措施", blank=True)
    remark = models.TextField("备注", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_fumigations", verbose_name="安排人",
    )

    class Meta:
        verbose_name = "熏蒸作业"
        verbose_name_plural = "熏蒸作业"
        ordering = ["-plan_start"]
        db_table = "depot_fumigation_task"

    def __str__(self):
        return f"{self.task_no} {self.granary.code}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # 实际作业中的熏蒸联动仓房状态（已安排/已完成不改变仓房原状态）
        active = {self.Status.RUNNING, self.Status.SEALED, self.Status.VENTILATING}
        granary = self.granary
        if self.status in active:
            granary.status = Granary.Status.FUMIGATING
            granary.save(update_fields=["status"])
        elif self.status in {self.Status.DONE, self.Status.CANCELED}:
            granary.status = Granary.Status.STORING if granary.current_stock > 0 else Granary.Status.EMPTY
            granary.save(update_fields=["status"])


class Stocktake(TimeStampedModel):
    """库存盘点单。"""

    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        COUNTING = "counting", "盘点中"
        FINISHED = "finished", "已完成"
        ADJUSTED = "adjusted", "已调账"

    stocktake_no = models.CharField("盘点单号", max_length=30, unique=True)
    name = models.CharField("盘点名称", max_length=100)
    plan_date = models.DateField("盘点日期", default=timezone.localdate)
    leader = models.CharField("盘点负责人", max_length=30)
    members = models.CharField("参加人员", max_length=200, blank=True)
    status = models.CharField("状态", max_length=12, choices=Status.choices, default=Status.DRAFT)
    remark = models.TextField("备注", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_stocktakes", verbose_name="创建人",
    )

    class Meta:
        verbose_name = "库存盘点单"
        verbose_name_plural = "库存盘点单"
        ordering = ["-plan_date"]
        db_table = "depot_stocktake"

    def __str__(self):
        return self.stocktake_no


class StocktakeItem(models.Model):
    """盘点单明细：账存 vs 实存。"""

    stocktake = models.ForeignKey(
        Stocktake, verbose_name="盘点单", on_delete=models.CASCADE, related_name="items"
    )
    granary = models.ForeignKey(Granary, verbose_name="仓房", on_delete=models.PROTECT)
    batch = models.ForeignKey(GrainBatch, verbose_name="粮油批次", on_delete=models.PROTECT)
    book_quantity = models.DecimalField("账面数量(吨)", max_digits=12, decimal_places=2)
    actual_quantity = models.DecimalField("实盘数量(吨)", max_digits=12, decimal_places=2, null=True, blank=True)
    loss_quantity = models.DecimalField("损耗(吨)", max_digits=12, decimal_places=2, default=0)
    gain_quantity = models.DecimalField("溢余(吨)", max_digits=12, decimal_places=2, default=0)
    reason = models.CharField("差异原因", max_length=200, blank=True)

    class Meta:
        verbose_name = "盘点明细"
        verbose_name_plural = "盘点明细"
        unique_together = ("stocktake", "batch")
        db_table = "depot_stocktake_item"

    def __str__(self):
        return f"{self.stocktake.stocktake_no}-{self.batch.batch_no}"

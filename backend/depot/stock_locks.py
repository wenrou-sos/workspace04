"""出入库单据的业务边界校验：熏蒸锁、盘点结账期、负库存。"""
from decimal import Decimal

from rest_framework.serializers import ValidationError

from .models import FumigationTask, StockRecord, Stocktake, StocktakeItem

# 熏蒸作业进行中（实际施药后）会锁仓，禁止出入库与单据更正/作废
FUMIGATION_LOCKED = {
    FumigationTask.Status.RUNNING,
    FumigationTask.Status.SEALED,
    FumigationTask.Status.VENTILATING,
}


def active_fumigation(granary):
    """返回仓房当前进行中的熏蒸作业，没有则 None。"""
    if granary is None:
        return None
    return FumigationTask.objects.filter(granary=granary, status__in=FUMIGATION_LOCKED).first()


def _settled_item(granary, batch, occurred_at):
    """该仓/批次在指定时间之前（含当天）是否已被一张已调账盘点覆盖。"""
    qs = StocktakeItem.objects.filter(
        stocktake__status=Stocktake.Status.ADJUSTED,
        stocktake__plan_date__lte=occurred_at.date(),
        granary=granary,
    )
    if batch is not None:
        qs = qs.filter(batch=batch)
    return qs.select_related("stocktake").first()


def assert_granary_open(granary):
    """新增单据前置：仓房不在熏蒸作业期间。"""
    task = active_fumigation(granary)
    if task:
        raise ValidationError(
            f"{granary.code} 正在进行熏蒸作业（{task.get_status_display()}），"
            f"作业结束前禁止办理出入库。"
        )


def assert_record_mutable(record, new_occurred_at=None, new_granary=None, new_batch=None):
    """更正/作废前置：单据本身可改、未被盘点结账、仓房未锁。"""
    if record.is_adjustment:
        raise ValidationError("盘点调账单由系统生成，不能更正或作废；如需修正请新建盘点单。")
    if record.is_void:
        raise ValidationError("该单据已作废，不能再次更正或作废。")

    granary = new_granary or record.granary
    batch = new_batch if new_batch is not None else record.batch
    occurred_at = new_occurred_at or record.occurred_at

    task = active_fumigation(granary)
    if task:
        raise ValidationError(
            f"{granary.code} 正在进行熏蒸作业（{task.get_status_display()}），该期间单据不能改动。"
        )

    item = _settled_item(granary, batch, occurred_at)
    if item:
        raise ValidationError(
            f"该单据时间处于已完成盘点「{item.stocktake.stocktake_no}」"
            f"（盘点日 {item.stocktake.plan_date:%Y-%m-%d}）的结账期间内，"
            f"为保证账实一致不能更正或作废；如需调整请新建盘点单。"
        )
    # 原单据所在期间也要检查（防止把已结账单据改到别处）
    if (new_granary or new_occurred_at) and record.pk:
        old_item = _settled_item(record.granary, record.batch, record.occurred_at)
        if old_item:
            raise ValidationError(
                f"原单据已被盘点「{old_item.stocktake.stocktake_no}」结账，不能更正。"
            )


def projected_batch_quantity(batch, signed_delta, exclude_record=None):
    """应用变更后批次结存；exclude_record 为正在更正的原单（先扣除其影响）。"""
    qty = float(batch.quantity)
    if exclude_record is not None and exclude_record.batch_id == batch.id:
        qty -= float(exclude_record.signed_quantity)
    return qty + signed_delta


def assert_non_negative(batch, signed_delta, exclude_record=None):
    """变更后批次结存不允许为负。"""
    result = projected_batch_quantity(batch, signed_delta, exclude_record)
    if result < -0.001:
        raise ValidationError(
            f"更正/作废后批次 {batch.batch_no} 结存将为 {round(result, 2)} 吨，"
            f"不允许出现负库存。"
        )
    return Decimal(str(round(result, 2)))

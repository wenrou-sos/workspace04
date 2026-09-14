"""视图：ModelViewSet + 仪表盘/图表聚合接口。"""
from datetime import timedelta

from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import MonitorRecordFilter, StockRecordFilter
from .models import (
    FumigationTask,
    GrainBatch,
    Granary,
    MonitorRecord,
    StockRecord,
    Stocktake,
    StocktakeItem,
)
from .serializers import (
    FumigationTaskSerializer,
    GrainBatchSerializer,
    GranarySerializer,
    MonitorRecordSerializer,
    StockRecordSerializer,
    StocktakeItemSerializer,
    StocktakeSerializer,
)


class GranaryViewSet(viewsets.ModelViewSet):
    queryset = Granary.objects.all()
    serializer_class = GranarySerializer
    filterset_fields = ["status", "granary_type"]
    search_fields = ["code", "name", "manager"]

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


class GrainBatchViewSet(viewsets.ModelViewSet):
    queryset = GrainBatch.objects.select_related("granary").all()
    serializer_class = GrainBatchSerializer
    filterset_fields = ["granary", "grain_kind", "grade"]
    search_fields = ["batch_no", "origin"]


class MonitorRecordViewSet(viewsets.ModelViewSet):
    queryset = MonitorRecord.objects.select_related("granary").all()
    serializer_class = MonitorRecordSerializer
    filterset_class = MonitorRecordFilter
    search_fields = ["granary__code", "inspector"]

    @action(detail=False, methods=["get"])
    def latest(self, request):
        """每仓最新一条检测记录，用于监控大屏。"""
        granary_ids = Granary.objects.values_list("id", flat=True)
        rows = []
        for gid in granary_ids:
            rec = MonitorRecord.objects.filter(granary_id=gid).first()
            if rec:
                rows.append(self.get_serializer(rec).data)
        return Response(rows)


class StockRecordViewSet(viewsets.ModelViewSet):
    queryset = StockRecord.objects.select_related("granary", "batch").all()
    serializer_class = StockRecordSerializer
    filterset_class = StockRecordFilter
    search_fields = ["record_no", "counterparty", "operator"]


class FumigationTaskViewSet(viewsets.ModelViewSet):
    queryset = FumigationTask.objects.select_related("granary").all()
    serializer_class = FumigationTaskSerializer
    filterset_fields = ["granary", "status", "agent"]
    search_fields = ["task_no", "leader", "granary__code"]

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
        return Response(self.get_serializer(task).data)


class StocktakeViewSet(viewsets.ModelViewSet):
    queryset = Stocktake.objects.prefetch_related("items").all()
    serializer_class = StocktakeSerializer
    filterset_fields = ["status"]
    search_fields = ["stocktake_no", "name", "leader"]

    @action(detail=True, methods=["post"])
    def generate_items(self, request, pk=None):
        """按当前所有在储批次自动生成盘点明细（账存数）。"""
        stocktake = self.get_object()
        if stocktake.status != Stocktake.Status.DRAFT:
            return Response({"detail": "只有草稿状态的盘点单可以生成明细"}, status=400)
        stocktake.items.all().delete()
        items = [
            StocktakeItem(
                stocktake=stocktake,
                granary=batch.granary,
                batch=batch,
                book_quantity=batch.quantity,
            )
            for batch in GrainBatch.objects.filter(quantity__gt=0).select_related("granary")
        ]
        StocktakeItem.objects.bulk_create(items)
        stocktake.status = Stocktake.Status.COUNTING
        stocktake.save(update_fields=["status"])
        return Response(StocktakeSerializer(stocktake).data)

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        """完成盘点：汇总差异并回写批次结存（调账）。"""
        stocktake = self.get_object()
        items = list(stocktake.items.select_related("batch"))
        if not items:
            return Response({"detail": "盘点明细为空，请先生成明细"}, status=400)
        unfilled = [i for i in items if i.actual_quantity is None]
        if unfilled:
            return Response({"detail": f"还有 {len(unfilled)} 条明细未填写实盘数量"}, status=400)

        for item in items:
            diff = float(item.actual_quantity) - float(item.book_quantity)
            item.gain_quantity = diff if diff > 0 else 0
            item.loss_quantity = -diff if diff < 0 else 0
            item.save()

        # 盘点调账：直接修正批次结存
        for item in items:
            if float(item.actual_quantity) != float(item.book_quantity):
                batch = item.batch
                batch.quantity = item.actual_quantity
                batch.save(update_fields=["quantity"])

        stocktake.status = Stocktake.Status.ADJUSTED
        stocktake.save(update_fields=["status"])
        return Response(StocktakeSerializer(stocktake).data)


class StocktakeItemViewSet(viewsets.ModelViewSet):
    queryset = StocktakeItem.objects.select_related("granary", "batch").all()
    serializer_class = StocktakeItemSerializer
    filterset_fields = ["stocktake", "granary"]


class DashboardViewSet(viewsets.ViewSet):
    """仪表盘统计接口（不需要分页）。"""

    permission_classes = []

    def list(self, request):
        granaries = Granary.objects.all()
        total_capacity = sum(float(g.capacity) for g in granaries)
        total_stock = sum(float(g.current_stock) for g in granaries)
        status_count = {s.value: 0 for s in Granary.Status}
        for g in granaries:
            status_count[g.status] += 1

        stock_by_kind = {}
        for b in GrainBatch.objects.values("grain_kind").annotate(q=Sum("quantity")):
            stock_by_kind[dict(GrainBatch.GrainKind.choices)[b["grain_kind"]]] = round(float(b["q"] or 0), 2)

        active_fumigations = FumigationTask.objects.filter(
            status__in=["planned", "running", "sealed", "ventilating"]
        ).count()
        warning_count = MonitorRecord.objects.filter(alert_level__in=["warning", "critical"]).count()

        # 近 7 天出入库量
        since = timezone.now() - timedelta(days=7)
        in_q = StockRecord.objects.filter(direction="in", occurred_at__gte=since).aggregate(
            q=Sum("quantity")
        )["q"] or 0
        out_q = StockRecord.objects.filter(direction="out", occurred_at__gte=since).aggregate(
            q=Sum("quantity")
        )["q"] or 0

        return Response(
            {
                "granary_count": granaries.count(),
                "total_capacity": round(total_capacity, 2),
                "total_stock": round(total_stock, 2),
                "utilization": round(total_stock / total_capacity * 100, 1) if total_capacity else 0,
                "status_count": status_count,
                "stock_by_kind": stock_by_kind,
                "active_fumigations": active_fumigations,
                "warning_count": warning_count,
                "week_inbound": round(float(in_q), 2),
                "week_outbound": round(float(out_q), 2),
            }
        )

    @action(detail=False, methods=["get"])
    def trend(self, request):
        """近 7 天每日出入库趋势。"""
        since = timezone.now().date() - timedelta(days=6)
        records = (
            StockRecord.objects.filter(occurred_at__date__gte=since)
            .annotate(day=TruncDate("occurred_at"))
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
        """各仓最新温湿度 + 最近 12 小时告警。"""
        result = []
        for granary in Granary.objects.all():
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
        ).select_related("granary")[:20]
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

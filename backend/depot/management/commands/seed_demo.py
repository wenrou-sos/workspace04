"""内置样例粮仓数据的初始化命令。

用法：python manage.py seed_demo
幂等：已存在样例仓号时直接清空重建。
"""
import math
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from depot.models import (
    FumigationTask,
    GrainBatch,
    Granary,
    MonitorRecord,
    StockRecord,
    Stocktake,
    StocktakeItem,
)

random.seed(20260914)

GRANARIES = [
    # 仓号, 名称, 仓型, 仓容, 面积, 保管员, 位置, 建成年, 温阈值, 湿阈值
    ("P01", "1号平房仓", "square", 5000, 720, "张建国", "东区A排01", 2009, 25, 70),
    ("P02", "2号平房仓", "square", 5000, 720, "李秀英", "东区A排02", 2009, 25, 70),
    ("P03", "3号平房仓", "square", 4000, 600, "王海涛", "东区B排01", 2012, 25, 70),
    ("P04", "4号平房仓", "square", 4000, 600, "陈丽华", "东区B排02", 2012, 25, 70),
    ("X01", "1号立筒仓", "silo", 2000, 120, "刘志强", "西区筒仓群01", 2016, 26, 68),
    ("X02", "2号立筒仓", "silo", 2000, 120, "赵敏", "西区筒仓群02", 2016, 26, 68),
    ("L01", "1号浅圆仓", "shallow", 3000, 200, "孙伟", "北区01", 2019, 25, 70),
    ("L02", "2号浅圆仓", "shallow", 3000, 200, "周芳", "北区02", 2019, 25, 70),
]

# 仓号 → (品种, 等级, 目标结存, 产地, 年份, 水分, 杂质, 单价)
BATCH_PLAN = {
    "P01": ("wheat", "2", 4300, "河南周口", 2025, 11.8, 0.8, 2980),
    "P02": ("corn", "2", 3600, "吉林公主岭", 2025, 13.5, 0.9, 2420),
    "P03": ("rice", "3", 3100, "黑龙江五常", 2024, 13.2, 0.7, 3860),
    "P04": ("soybean", "3", 1800, "内蒙古呼伦贝尔", 2025, 12.0, 0.6, 4750),
    "X01": ("wheat", "3", 1500, "山东德州", 2024, 12.2, 1.0, 2890),
    "X02": (),  # 空仓
    "L01": ("paddy", "3", 2450, "安徽合肥", 2025, 14.1, 1.1, 2760),
    "L02": (),  # 检修
}

BUYERS = ["中央储备粮直属库", "市面粉加工厂", "饲料集团华东公司", "粮油贸易有限公司", "食品股份有限公司"]
SUPPLIERS = ["金穗粮油公司", "丰收种植合作社", "东北粮贸集团", "黄淮农业开发公司", "皖江米业"]


class Command(BaseCommand):
    help = "生成粮食储备库样例数据（仓房、库存、温湿度、出入库、熏蒸、盘点）"

    def handle(self, *args, **options):
        self.stdout.write("清理旧样例数据……")
        StocktakeItem.objects.all().delete()
        Stocktake.objects.all().delete()
        FumigationTask.objects.all().delete()
        StockRecord.objects.all().delete()
        MonitorRecord.objects.all().delete()
        GrainBatch.objects.all().delete()
        Granary.objects.all().delete()

        now = timezone.now()
        granary_map = {}
        for code, name, gtype, cap, area, mgr, loc, year, t, h in GRANARIES:
            g = Granary.objects.create(
                code=code, name=name, granary_type=gtype, capacity=cap, area=area,
                manager=mgr, location=loc, build_year=year,
                temperature_threshold=t, humidity_threshold=h,
            )
            granary_map[code] = g

        self.stdout.write("生成在储批次与出入库流水……")
        seq = 1
        for code, plan in BATCH_PLAN.items():
            granary = granary_map[code]
            if not plan:
                continue
            kind, grade, target, origin, year, moisture, impurity, price = plan
            inbound_date = now - timedelta(days=random.randint(120, 200))
            batch = GrainBatch.objects.create(
                granary=granary,
                batch_no=f"PC{inbound_date:%Y%m}{code}",
                grain_kind=kind, grade=grade, origin=origin,
                inbound_price=price, production_year=year,
                stored_at=inbound_date.date(),
                moisture=moisture, impurity=impurity,
            )
            inbound_qty = float(granary.capacity) * random.uniform(0.85, 0.97)
            StockRecord.objects.create(
                record_no=f"RK{inbound_date:%Y%m%d}{seq:03d}",
                granary=granary, batch=batch, direction="in", biz_type="purchase",
                quantity=round(inbound_qty, 2), unit_price=price,
                counterparty=random.choice(SUPPLIERS),
                operator=granary.manager, occurred_at=inbound_date,
                remark="新粮收购整仓入库",
            )
            seq += 1

            out_qty = inbound_qty - target
            if out_qty > 50:
                out_date = now - timedelta(days=random.randint(20, 90))
                StockRecord.objects.create(
                    record_no=f"CK{out_date:%Y%m%d}{seq:03d}",
                    granary=granary, batch=batch, direction="out", biz_type="sale",
                    quantity=round(out_qty, 2), unit_price=round(price * 1.05, 2),
                    counterparty=random.choice(BUYERS),
                    operator=granary.manager, occurred_at=out_date,
                    remark="轮换销售出库",
                )
                seq += 1

            # 最近 60 天再补几条零星调拨/销售流水
            extra = random.randint(2, 4)
            for _ in range(extra):
                days_ago = random.randint(3, 60)
                direction = random.choice(["in", "out"])
                qty = round(random.uniform(20, 150), 2)
                batch.refresh_from_db()
                if direction == "out" and qty > float(batch.quantity):
                    continue
                d = now - timedelta(days=days_ago, hours=random.randint(0, 8))
                StockRecord.objects.create(
                    record_no=f"{'RK' if direction == 'in' else 'CK'}{d:%Y%m%d}{seq:03d}",
                    granary=granary, batch=batch, direction=direction,
                    biz_type=random.choice(["transfer_in", "sale", "loss"])
                    if direction == "out" else random.choice(["transfer_in", "return"]),
                    quantity=qty,
                    unit_price=price if direction == "in" else round(price * 1.05, 2),
                    counterparty=random.choice(SUPPLIERS + BUYERS),
                    operator=granary.manager, occurred_at=d,
                )
                seq += 1

        # 空仓/检修状态
        granary_map["X02"].status = Granary.Status.EMPTY
        granary_map["X02"].save()
        granary_map["L02"].status = Granary.Status.MAINTENANCE
        granary_map["L02"].save()

        self.stdout.write("生成近 7 天温湿度检测记录（每仓每 4 小时一条）……")
        layers = ["上层", "中层", "下层"]
        for code, granary in granary_map.items():
            if granary.status == Granary.Status.MAINTENANCE:
                continue
            for hours_ago in range(0, 24 * 7, 4):
                ts = now - timedelta(hours=hours_ago, minutes=random.randint(0, 30))
                # 白天温度高、夜间低；在储仓粮温略高
                hour = ts.hour
                diurnal = 2.5 * math.sin((hour - 9) / 24 * 2 * math.pi)
                occupied = granary.batches.exists()
                base = 20.5 if occupied else 16
                avg = base + diurnal + random.uniform(-0.8, 0.8)
                spread = random.uniform(1.0, 3.2)
                mx = avg + spread
                mn = avg - random.uniform(0.6, 1.6)
                humidity = 58 + random.uniform(-6, 8) + (diurnal * -1.2)
                # 注入一些异常：P02 在 2 天前有一次高温告警，X01 湿度偏高
                note = ""
                if code == "P02" and 46 <= hours_ago <= 50:
                    mx += 7
                    avg += 2.5
                    note = "午后仓温偏高，粮堆表层升温"
                if code == "X01" and hours_ago % 12 == 0:
                    humidity += 12
                    note = "连阴雨天气，仓内偏湿"
                MonitorRecord.objects.create(
                    granary=granary, recorded_at=ts,
                    avg_temp=round(avg, 2), max_temp=round(mx, 2), min_temp=round(mn, 2),
                    ambient_temp=round(base + 4 + diurnal + random.uniform(-1, 1), 2),
                    humidity=round(min(humidity, 96), 1),
                    outside_temp=round(22 + diurnal + random.uniform(-1.5, 1.5), 2),
                    outside_humidity=round(62 + random.uniform(-10, 12), 1),
                    sensor_layer=random.choice(layers),
                    inspector=granary.manager if random.random() > 0.4 else "值班员",
                    note=note,
                )

        self.stdout.write("生成熏蒸作业安排……")
        FumigationTask.objects.create(
            task_no="XZ20260901001", granary=granary_map["X01"],
            agent="ph3", dose=18.5,
            plan_start=now - timedelta(days=2), plan_end=now + timedelta(days=5),
            actual_start=now - timedelta(days=2, hours=3),
            seal_days=10, status="sealed", leader="刘志强",
            team="刘志强、马超、丁一", target_pest="玉米象、赤拟谷盗",
            safety_note="作业人员佩戴防毒面具；仓区 20 米内设警戒；散气后检测磷化氢浓度低于 0.3mg/m³ 方可入仓。",
            remark="秋季保粮熏蒸",
        )
        FumigationTask.objects.create(
            task_no="XZ20260920001", granary=granary_map["P03"],
            agent="alp", dose=26,
            plan_start=now + timedelta(days=6), plan_end=now + timedelta(days=16),
            seal_days=9, status="planned", leader="陈丽华",
            team="陈丽华、王芳、丁一", target_pest="麦蛾、锯谷盗",
            safety_note="施药前检查气密性；备足防毒器具与急救药品。",
            remark="计划结合秋季普查开展",
        )
        FumigationTask.objects.create(
            task_no="XZ20260615001", granary=granary_map["P01"],
            agent="ph3", dose=22,
            plan_start=now - timedelta(days=90), plan_end=now - timedelta(days=80),
            actual_start=now - timedelta(days=90), actual_end=now - timedelta(days=79),
            seal_days=9, status="done", leader="张建国",
            team="张建国、马超", target_pest="玉米象",
            effect="熏蒸后布点检测无活虫，杀虫率 100%",
            safety_note="散气 72 小时，浓度检测合格后清渣。",
        )

        self.stdout.write("生成 8 月份盘点单（已完成调账）……")
        st = Stocktake.objects.create(
            stocktake_no="PD20260831001", name="2026年8月末库存盘点",
            plan_date=now.date() - timedelta(days=14),
            leader="赵国栋", members="赵国栋、张建国、李秀英、王海涛、陈丽华、刘志强",
            status="adjusted", remark="月末例行盘点，账实基本相符，零星水分减量已调账。",
        )
        for batch in GrainBatch.objects.all():
            book = float(batch.quantity) * 1.003  # 盘点时账面略大于现在
            loss = round(book * random.uniform(0.0004, 0.0015), 2)
            actual = round(book - loss, 2)
            StocktakeItem.objects.create(
                stocktake=st, granary=batch.granary, batch=batch,
                book_quantity=round(book, 2), actual_quantity=actual,
                loss_quantity=loss, reason="保管自然损耗（水分减量）",
            )

        # 一张进行中的 9 月盘点草稿，方便前端演示生成明细
        Stocktake.objects.create(
            stocktake_no="PD20260914001", name="2026年9月中旬盘点",
            plan_date=now.date(), leader="赵国栋", members="各仓保管员",
            status="draft", remark="季度盘点",
        )

        self.stdout.write(self.style.SUCCESS(
            f"样例数据生成完毕：{Granary.objects.count()} 个仓房、"
            f"{GrainBatch.objects.count()} 个在储批次、"
            f"{StockRecord.objects.count()} 条出入库流水、"
            f"{MonitorRecord.objects.count()} 条温湿度记录、"
            f"{FumigationTask.objects.count()} 个熏蒸任务、"
            f"{Stocktake.objects.count()} 张盘点单。"
        ))

# 智慧粮库 —— 粮食储备库管理系统

基于 **Vue 3 + Django 5 (DRF) + PostgreSQL** 的粮食储备库管理系统，覆盖仓房档案、粮情库存、
温湿度监测、出入库流水、熏蒸作业安排与库存盘点全流程，内置完整样例粮仓数据。

## 功能模块

| 模块 | 说明 |
| --- | --- |
| 综合看板 | 在储总量、仓容利用率、近 7 日出入库趋势图、品种结构饼图、各仓实时粮情、温湿度预警时间线 |
| 仓房管理 | 仓房档案 CRUD、仓型/状态、温湿度告警阈值、仓容利用率进度条、单仓 24 小时温湿度曲线 |
| 库存粮情 | 在储批次（品种、等级、产地、水分/杂质、单价货值），结存数量由出入库流水自动联动 |
| 温湿度监测 | 检测记录录入（自动按仓房阈值判定 正常/预警/告警）、近 7 天多仓温湿度趋势对比、时间范围筛选 |
| 出入库记录 | 入库/出库单据，出库超结存自动拦截，保存后自动更新批次结存与仓房状态 |
| 熏蒸作业 | 作业安排、药剂/剂量/密闭天数、安全措施；一键状态推进：已安排→施药中→密闭中→通风散气→已完成 |
| 库存盘点 | 一键按在储批次生成盘点明细、录入实盘数量、自动算损溢，完成后按实盘调账回写批次结存 |

## 技术栈

- **后端**：Python 3.11 / Django 5.2 / Django REST Framework / django-filter / psycopg 3
- **前端**：Vue 3（Composition API）/ Vite 5 / Element Plus / ECharts 5 / Pinia / Vue Router / Axios
- **数据库**：PostgreSQL（本项目内置免 root 的用户态 PG 18 二进制，亦可连接任意外部 PG）

## 目录结构

```
.
├── backend/              # Django 项目
│   ├── grain_depot/      # 项目配置（settings/urls/wsgi）
│   ├── depot/            # 业务应用：models / views / serializers / filters / seed 命令
│   └── manage.py
├── frontend/             # Vue 3 + Vite 工程
│   └── src/{api,components,router,utils,views}
├── pgsql/                # 用户态 PostgreSQL 18 二进制（aarch64）
├── pgdata/               # PostgreSQL 数据目录（自动生成）
└── scripts/              # start-db.sh / init.sh
```

## 快速开始

### 1. 安装依赖

```bash
# Python 依赖
pip install -r backend/requirements.txt

# 前端依赖
cd frontend && npm install && cd ..
```

### 2. 初始化数据库与样例数据

```bash
bash scripts/init.sh
# 等价于：启动 PG → CREATE DATABASE → migrate → seed_demo
```

连接**外部 PostgreSQL** 时无需使用内置二进制，用环境变量覆盖即可：

```bash
export PGHOST=127.0.0.1 PGPORT=5432 PGUSER=postgres PGPASSWORD=xxx PGDATABASE=grain_depot
python3 backend/manage.py migrate
python3 backend/manage.py seed_demo
```

### 3. 启动服务

```bash
# 终端 A：Django API（:8000）
cd backend && python3 manage.py runserver 0.0.0.0:8000

# 终端 B：Vite 前端（:5173，/api 自动代理到 8000）
cd frontend && npm run dev
```

浏览器打开 <http://localhost:5173>

- Django Admin 后台：<http://localhost:8000/admin/> ，演示账号 `admin / admin123`
- API 根路径（可浏览调试）：<http://localhost:8000/api/>

## 内置样例数据

执行 `python3 backend/manage.py seed_demo`（幂等，可重复执行）生成：

- **8 栋仓房**：4 栋平房仓、2 栋立筒仓、2 栋浅圆仓（含 1 空仓、1 检修仓），总仓容 2.8 万吨
- **6 个在储批次**：小麦 / 玉米 / 稻谷 / 大豆 / 水稻，共约 1.69 万吨
- **294 条温湿度记录**：近 7 天每 4 小时一条，注入了午后高温、连阴雨偏湿等异常场景
- **28 条出入库流水**：收购入库、轮换销售、调拨、损耗等类型
- **3 个熏蒸作业单**：密闭中（X01 立筒仓）、已安排待执行（P03）、已完成（P01）
- **2 张盘点单**：8 月已调账单（带自然损耗）+ 9 月草稿单（可演示完整盘点流程）

## 主要 API

| 方法 & 路径 | 说明 |
| --- | --- |
| `GET /api/dashboard/` | 看板汇总指标 |
| `GET /api/dashboard/trend/` | 近 7 日出入库趋势 |
| `GET /api/dashboard/temp_monitor/` | 各仓最新粮情 + 预警列表 |
| `GET/POST/PUT/DELETE /api/granaries/` 等 7 个资源 | 仓房/批次/监测/出入库/熏蒸/盘点标准 REST |
| `GET /api/granaries/{id}/temperature_series/` | 单仓 24 小时温湿度曲线 |
| `POST /api/fumigations/{id}/advance/` | 熏蒸作业状态推进 |
| `POST /api/stocktakes/{id}/generate_items/` | 按在储批次生成盘点明细 |
| `POST /api/stocktakes/{id}/finish/` | 完成盘点并调账 |

## 业务规则说明

- 批次结存数量不允许手工直接修改，全部由出入库流水（带符号求和）驱动，保证账实可追溯
- 出库数量超过批次结存时后端校验拒绝
- 温湿度记录保存时按仓房阈值自动定级：达阈值=预警，超阈值 3℃ / 湿度超 10% = 告警
- 熏蒸进入施药/密闭/散气状态时仓房自动置为「熏蒸中」，完成后按结存恢复在储/空仓

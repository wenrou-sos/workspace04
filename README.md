# 智慧粮库 —— 粮食储备库管理系统

基于 **Vue 3 + Django 5 (DRF) + PostgreSQL** 的粮食储备库管理系统，覆盖仓房档案、粮情库存、
温湿度监测、出入库流水、熏蒸作业安排与库存盘点全流程，内置完整样例粮仓数据。

## 功能模块

| 模块 | 说明 |
| --- | --- |
| 登录鉴权 | Token 登录、前端路由守卫、请求自动带凭证、401 自动跳转、登出即失效 |
| 综合看板 | 在储总量、仓容利用率、近 7 日出入库趋势图、品种结构饼图、各仓实时粮情、温湿度预警时间线（按仓房范围统计） |
| 账号岗位 | 管理员/主任维护账号、分配角色与保管员管辖仓房；操作日志模块查看全员审计 |
| 仓房管理 | 仓房档案 CRUD、仓型/状态、温湿度告警阈值、仓容利用率进度条、单仓 24 小时温湿度曲线 |
| 库存粮情 | 在储批次（品种、等级、产地、水分/杂质、单价货值），结存数量由出入库流水自动联动 |
| 温湿度监测 | 检测记录录入（检测人自动取登录身份、按仓房阈值自动定级）、近 7 天多仓趋势对比 |
| 出入库记录 | 入库/出库单据，经办人自动取登录身份；出库超结存拦截、越仓操作拦截，保存联动结存与仓房状态 |
| 熏蒸作业 | 主任安排作业；责任保管员一键推进：已安排→施药中→密闭中→通风散气→已完成，负责人自动记录 |
| 库存盘点 | 分仓生成明细、保管员只录本仓实盘；**完成调账仅库管主任/管理员**（操作与审核分离） |
| 操作日志 | 登录、出入库、熏蒸推进、盘点生成/调账、增删改全部留痕，记录到人/IP，保管员只见本人 |

## 岗位与权限

系统采用「角色 + 仓房范围」双层授权，所有写接口在后端强制校验，前端按钮仅作体验层隐藏：

| 能力 | 系统管理员 admin | 库管主任 director | 保管员 keeper | 只读用户 viewer |
| --- | :---: | :---: | :---: | :---: |
| 看板/业务数据查看 | 全部 | 全部 | **仅本人管辖仓房** | 全部（只读） |
| 温湿度/出入库/批次录入 | ✅ | ✅ | **仅本人仓房** | ❌ |
| 熏蒸状态推进 | ✅ | ✅ | **仅本人仓房** | ❌ |
| 安排熏蒸 / 新建仓房 / 盘点单 | ✅ | ✅ | ❌ | ❌ |
| 盘点录入实盘 | ✅ | ✅ | **仅本人仓房明细** | ❌ |
| **盘点调账（审核）/ 删除** | ✅ | ✅ | ❌ | ❌ |
| 账号岗位管理 / 全员日志 | ✅ | ✅ | ❌（日志仅见本人） | ❌ |

演示账号（一键播种后可用）：

| 账号 | 密码 | 岗位 | 范围 |
| --- | --- | --- | --- |
| `admin` | `admin123` | 系统管理员 | 全部 + Django 后台 |
| `director` | `director123` | 库管主任（赵国栋） | 全仓业务、删除、盘点调账 |
| `zhangjg`…`zhouf` | `keeper123` | 8 名保管员 | 各自 1 栋仓房（张建国→P01、李秀英→P02、王海涛→P03、陈丽华→P04、刘志强→X01、赵敏→X02、孙伟→L01、周芳→L02） |
| `viewer` | `viewer123` | 只读用户 | 全仓只读、看板 |

责任字段（经办人、检测人、熏蒸负责人、盘点负责人、建档/登记人）均由登录身份自动写入，界面不可手填；
所有关键动作写入操作审计日志（含操作人、IP、时间、对象、详情），历史记录可追到人。

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

### 方式一：一键启动（推荐）

```bash
# 1) 安装依赖（首次）
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# 2) 一键启动（自动初始化内置 PG、迁移、填充样例数据、起后端和前端）
bash scripts/start.sh
```

脚本幂等，重复执行不会重复播种。之后浏览器访问 <http://localhost:5173>，用演示账号登录（如 `director / director123`）。
停止全部服务：`bash scripts/stop.sh`。

> Linux 受管 Python（PEP 668）若 `pip install` 报 externally-managed 错误，
> 请务必使用上面的 venv；或在明确风险后加 `--break-system-packages`。

### 方式二：分步启动

```bash
# 1. Python 依赖（建议 venv）
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. 前端依赖
cd frontend && npm install && cd ..

# 3. 初始化数据库（启动内置 PG → 建库 → migrate → 填充样例数据）
bash scripts/init.sh

# 4. 启动服务（两个终端）
cd backend && python3 manage.py runserver 0.0.0.0:8000
cd frontend && npm run dev
```

连接**外部 PostgreSQL** 时无需使用内置二进制，用环境变量覆盖即可（脚本检测到 `PGHOST` 会自动跳过内置 PG）：

```bash
export PGHOST=127.0.0.1 PGPORT=5432 PGUSER=postgres PGPASSWORD=xxx PGDATABASE=grain_depot
python3 backend/manage.py migrate
python3 backend/manage.py seed_demo
```

### 常见启动问题

| 现象 | 原因 / 处理 |
| --- | --- |
| 后端报 `connection refused` / 页面提示无法连接 :8000 | 内置 PostgreSQL 未启动，先执行 `bash scripts/start-db.sh` 或 `bash scripts/start.sh` |
| `pip install` 报 externally-managed | 系统 Python 受 PEP 668 保护，请使用 venv（见方式一） |
| 内置 PG 报找不到共享库 | 启动脚本已自动设置 `LD_LIBRARY_PATH`；手动执行命令时请先 `export LD_LIBRARY_PATH=$PWD/pgsql/lib` |
| 端口 8000/5173/55432 被占用 | 先 `bash scripts/stop.sh`，或修改对应配置 |

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
| `POST /api/auth/login/` | 账号密码登录，返回 Token 与岗位信息 |
| `POST /api/auth/logout/` | 登出并销毁 Token |
| `GET /api/auth/me/` | 当前登录身份、角色、管辖仓房 |
| `GET /api/dashboard/` | 看板汇总指标（保管员按仓房范围统计） |
| `GET /api/dashboard/trend/` | 近 7 日出入库趋势 |
| `GET /api/dashboard/temp_monitor/` | 各仓最新粮情 + 预警列表 |
| `GET/POST/PUT/DELETE /api/granaries/` 等资源 | 仓房/批次/监测/出入库/熏蒸/盘点标准 REST（需 Token，按岗位授权） |
| `GET /api/granaries/{id}/temperature_series/` | 单仓 24 小时温湿度曲线 |
| `POST /api/fumigations/{id}/advance/` | 熏蒸作业状态推进 |
| `POST /api/stocktakes/{id}/generate_items/` | 按在储批次生成盘点明细（保管员限本仓） |
| `POST /api/stocktakes/{id}/finish/` | 完成盘点并调账（仅主任/管理员） |
| `GET /api/operation-logs/` | 操作审计日志（保管员只见本人） |
| `/api/users/` | 账号岗位与管辖仓房管理（仅主任/管理员） |

除登录接口外，所有 API 都需要请求头 `Authorization: Token <token>`。

## 业务规则说明

- 所有接口默认必须登录；写操作按岗位授权，保管员的数据与操作严格限定在本人管辖仓房
- 责任字段（经办人/检测人/负责人/建档人）由登录身份自动注入，客户端无法手填或篡改
- 批次结存数量不允许手工直接修改，全部由出入库流水（带符号求和）驱动，保证账实可追溯
- 出库数量超过批次结存时后端校验拒绝
- 温湿度记录保存时按仓房阈值自动定级：达阈值=预警，超阈值 3℃ / 湿度超 10% = 告警
- 熏蒸进入施药/密闭/散气状态时仓房自动置为「熏蒸中」，完成后按结存恢复在储/空仓
- 盘点调账通过生成「盘盈入库 / 盘亏出库」调整流水完成（而非直接改数量），看板、仓房结存、批次结存与流水始终一致
- 盘点采用「保管员分仓录入实盘 → 库管主任统一调账」的操作与审核分离模式
- 删除已有业务引用的仓房/批次时返回 409 并列出被哪些数据引用，需先清理引用数据
- 登录、登出、增删改、出入库、熏蒸推进、盘点生成/调账等全部写入操作日志（操作人 + IP + 时间 + 对象），不可在界面修改

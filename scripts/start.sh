#!/usr/bin/env bash
# 一键启动：PostgreSQL + Django API(:8000) + Vite(:5173)
# 首次运行自动执行迁移与样例数据填充；日志见 /tmp/django.log、/tmp/vite.log
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$(cd "$(dirname "$0")" && pwd)"

PYBIN="${PYTHON:-python3}"
"$PYBIN" -c "import django" 2>/dev/null || {
  echo "错误：当前 Python 缺少依赖。请先安装：" >&2
  echo "  $PYBIN -m pip install -r $ROOT/backend/requirements.txt" >&2
  exit 1
}

api_alive() {
  # 需认证接口未登录返回 401/403，同样说明 Django 已在服务
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/dashboard/ 2>/dev/null)
  case "$code" in 200|401|403) return 0;; *) return 1;; esac
}

bash "$DIR/start-db.sh"

cd "$ROOT/backend"
echo "执行数据库迁移……"
"$PYBIN" manage.py migrate --noinput >/tmp/migrate.log 2>&1 || {
  echo "迁移失败，请查看 /tmp/migrate.log" >&2
  tail -20 /tmp/migrate.log >&2
  exit 1
}

# 全新库（没有仓房）时自动填充样例数据
COUNT=$("$PYBIN" manage.py shell -c "from depot.models import Granary; print(Granary.objects.count())" 2>/dev/null | tail -1)
if [ "$COUNT" = "0" ]; then
  echo "空数据库，自动填充样例数据……"
  "$PYBIN" manage.py seed_demo
fi

if api_alive; then
  echo "Django API 已在运行"
else
  nohup "$PYBIN" manage.py runserver 0.0.0.0:8000 >/tmp/django.log 2>&1 &
  for i in $(seq 1 15); do
    api_alive && break
    sleep 1
  done
  if api_alive; then
    echo "Django API 已启动 → http://localhost:8000 （日志 /tmp/django.log）"
  else
    echo "Django API 启动失败，最后 20 行日志：" >&2
    tail -20 /tmp/django.log >&2
    exit 1
  fi
fi

cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  echo "未发现 node_modules，安装前端依赖……"
  npm install
fi
if curl -sf http://localhost:5173/ >/dev/null 2>&1; then
  echo "前端已在运行"
else
  nohup npm run dev >/tmp/vite.log 2>&1 &
  echo "前端已启动 → http://localhost:5173 （日志 /tmp/vite.log）"
fi

sleep 1
echo ""
echo "系统就绪：浏览器访问 http://localhost:5173"
echo "Django Admin：http://localhost:8000/admin （admin / admin123）"

#!/usr/bin/env bash
# 一键启动：PostgreSQL + Django API(:8000) + Vite(:5173)
# 日志输出到 /tmp/django.log 与 /tmp/vite.log；用 stop.sh 停止
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$(cd "$(dirname "$0")" && pwd)"

bash "$DIR/start-db.sh"

cd "$ROOT/backend"
if ! curl -sf http://localhost:8000/api/ >/dev/null 2>&1; then
  nohup python3 manage.py runserver 0.0.0.0:8000 >/tmp/django.log 2>&1 &
  echo "Django API 已启动 → http://localhost:8000 （日志 /tmp/django.log）"
else
  echo "Django API 已在运行"
fi

cd "$ROOT/frontend"
if ! curl -sf http://localhost:5173/ >/dev/null 2>&1; then
  nohup npm run dev >/tmp/vite.log 2>&1 &
  echo "前端已启动 → http://localhost:5173 （日志 /tmp/vite.log）"
else
  echo "前端已在运行"
fi

sleep 2
echo ""
echo "系统就绪：浏览器访问 http://localhost:5173"
echo "Django Admin：http://localhost:8000/admin （admin / admin123）"

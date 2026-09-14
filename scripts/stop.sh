#!/usr/bin/env bash
# 停止 Django / Vite / 用户态 PostgreSQL
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

pkill -f "manage.py runserver" 2>/dev/null && echo "Django 已停止" || echo "Django 未运行"
pkill -f "vite" 2>/dev/null && echo "Vite 已停止" || echo "Vite 未运行"

export LD_LIBRARY_PATH="$ROOT/pgsql/lib:${LD_LIBRARY_PATH:-}"
if "$ROOT/pgsql/bin/pg_ctl" -D "$ROOT/pgdata" status >/dev/null 2>&1; then
  "$ROOT/pgsql/bin/pg_ctl" -D "$ROOT/pgdata" stop -m fast
else
  echo "PostgreSQL 未运行"
fi

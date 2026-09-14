#!/usr/bin/env bash
# 启动用户态 PostgreSQL（数据目录 ../pgdata，端口 55432）
# 如已通过 PGHOST/PGPORT 指定外部数据库，本脚本跳过内置 PG。
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 如果用户配置了外部 PG，直接探测连通性并退出
if [ -n "$PGHOST" ]; then
  echo "检测到 PGHOST=$PGHOST，使用外部 PostgreSQL，跳过内置实例。"
  exit 0
fi

# 选择可用的 Python 解释器（优先激活的 venv，再找带 psycopg 的解释器）
PYBIN="${PYTHON:-}"
if [ -z "$PYBIN" ]; then
  for cand in python python3 "$HOME/.venv/bin/python" "$ROOT/.venv/bin/python"; do
    if command -v "$cand" >/dev/null 2>&1 || [ -x "$cand" ]; then
      if "$cand" -c "import psycopg" >/dev/null 2>&1; then
        PYBIN="$cand"
        break
      fi
    fi
  done
fi
if [ -z "$PYBIN" ]; then
  echo "错误：未找到带有 psycopg 的 Python。请先执行：" >&2
  echo "  pip install -r $ROOT/backend/requirements.txt" >&2
  exit 1
fi

export LD_LIBRARY_PATH="$ROOT/pgsql/lib:${LD_LIBRARY_PATH:-}"
export PGDATA="$ROOT/pgdata"

if [ ! -x "$ROOT/pgsql/bin/pg_ctl" ]; then
  echo "错误：未找到内置 PostgreSQL（$ROOT/pgsql 不存在）。" >&2
  echo "请设置 PGHOST/PGPORT/PGUSER/PGPASSWORD 使用外部 PostgreSQL，或重新获取内置二进制。" >&2
  exit 1
fi

if "$ROOT/pgsql/bin/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  echo "PostgreSQL 已在运行（端口 55432）"
else
  if [ ! -f "$PGDATA/PG_VERSION" ]; then
    "$ROOT/pgsql/bin/initdb" -D "$PGDATA" -U postgres --auth=trust --encoding=UTF8 --locale=C
    printf "listen_addresses = 'localhost'\nport = 55432\nunix_socket_directories = '/tmp'\n" >> "$PGDATA/postgresql.conf"
  fi
  "$ROOT/pgsql/bin/pg_ctl" -D "$PGDATA" -l "$PGDATA/server.log" start
  echo "PostgreSQL 已启动（端口 55432）"
fi

# 确保业务数据库存在
"$PYBIN" - <<'PYEOF'
import sys
import psycopg
try:
    conn = psycopg.connect(host="localhost", port=55432, dbname="postgres", user="postgres", autocommit=True, connect_timeout=5)
except Exception as exc:
    print(f"连接 PostgreSQL 失败：{exc}", file=sys.stderr)
    sys.exit(1)
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname='grain_depot'")
if not cur.fetchone():
    cur.execute("CREATE DATABASE grain_depot ENCODING 'UTF8'")
    print("已创建数据库 grain_depot")
conn.close()
PYEOF

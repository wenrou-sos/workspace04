#!/usr/bin/env bash
# 启动用户态 PostgreSQL（数据目录 ../pgdata，端口 55432）
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export LD_LIBRARY_PATH="$ROOT/pgsql/lib:${LD_LIBRARY_PATH:-}"
export PGDATA="$ROOT/pgdata"

if "$ROOT/pgsql/bin/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  echo "PostgreSQL 已在运行"
else
  if [ ! -f "$PGDATA/PG_VERSION" ]; then
    "$ROOT/pgsql/bin/initdb" -D "$PGDATA" -U postgres --auth=trust --encoding=UTF8 --locale=C
    printf "listen_addresses = 'localhost'\nport = 55432\nunix_socket_directories = '/tmp'\n" >> "$PGDATA/postgresql.conf"
  fi
  "$ROOT/pgsql/bin/pg_ctl" -D "$PGDATA" -l "$PGDATA/server.log" start
fi

# 确保业务数据库存在
python3 - <<'PYEOF'
import psycopg
conn = psycopg.connect(host="localhost", port=55432, dbname="postgres", user="postgres", autocommit=True)
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname='grain_depot'")
if not cur.fetchone():
    cur.execute("CREATE DATABASE grain_depot ENCODING 'UTF8'")
    print("已创建数据库 grain_depot")
conn.close()
PYEOF

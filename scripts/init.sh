#!/usr/bin/env bash
# 一键初始化：建库、迁移、填充样例数据
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/start-db.sh"
cd "$DIR/../backend"
python3 manage.py migrate
python3 manage.py seed_demo
echo "初始化完成。"

#!/bin/bash
set -e

echo "=== [1/4] MySQL 서버 연결 대기 중... ==="
until python -c "
import os, pymysql
pymysql.connect(
    host=os.getenv('MYSQL_HOST', 'mysql'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
)
" 2>/dev/null; do
    echo "  MySQL 준비 중... 2초 후 재시도"
    sleep 2
done
echo "  MySQL 서버 연결 성공"

echo "=== [2/4] Database 생성 (없는 경우) ==="
python -c "
import os, pymysql
db_name = os.getenv('MYSQL_DATABASE')
conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST', 'mysql'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
)
cursor = conn.cursor()
cursor.execute(f'CREATE DATABASE IF NOT EXISTS \`{db_name}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
conn.commit()
conn.close()
print(f'  Database \"{db_name}\" 준비 완료')
"

echo "=== [3/4] Alembic migration 실행 중... ==="
HEAD_COUNT=$(alembic heads 2>/dev/null | grep -c "(head)" || echo 0)
if [ "$HEAD_COUNT" -gt 1 ]; then
    echo "  Multiple heads 감지 (${HEAD_COUNT}개) → 자동 merge 실행"
    alembic merge heads -m "auto_merge_$(date +%Y%m%d_%H%M%S)"
fi
alembic upgrade head
echo "  Migration 완료"

echo "=== [4/4] 초기 데이터 삽입 (hot_places, 중복 자동 skip) ==="
python -m app.database.insert_db
echo "  초기 데이터 삽입 완료"

echo "=== 서버 시작 ==="
exec "$@"

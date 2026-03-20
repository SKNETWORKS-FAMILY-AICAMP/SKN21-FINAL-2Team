# # -no-deps 옵션을 주면 Qdrant 충돌을 피하며 실행할 수 있습니다.
# docker compose run --rm --no-deps backend sh app/database/entrypoint.sh

#!/bin/bash
set -e

echo "[Step 1/3] Creating database tables..."
python -m app.database.create_db

echo "[Step 2/3] Inserting initial data..."
python -m app.database.insert_db

echo "[Step 3/3] Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

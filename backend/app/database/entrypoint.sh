#!/bin/sh
set -eu

echo "[Step 1/3] Ensuring MySQL database exists..."
python -m app.database.ensure_database

echo "[Step 2/3] Running Alembic migrations..."
alembic upgrade head

echo "[Step 3/3] Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_NO_CACHE=0

# 1. 필수 시스템 패키지 + uv 설치
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv

# 2. 패키지 설치 (requirements.txt가 바뀌지 않으면 캐시 레이어 재사용)
COPY requirements.txt .
RUN uv pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
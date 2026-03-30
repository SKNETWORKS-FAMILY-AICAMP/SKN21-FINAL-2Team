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
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/chromium /usr/bin/google-chrome \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv

# 2. 패키지 설치 (requirements.txt가 바뀌지 않으면 캐시 레이어 재사용)
COPY requirements.txt .
RUN uv pip install -r requirements.txt

COPY . .

# CRLF → LF 변환 + 실행 권한 부여 (Windows에서 작업한 경우 대응)
RUN sed -i 's/\r//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
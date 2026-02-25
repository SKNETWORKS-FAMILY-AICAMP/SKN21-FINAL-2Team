FROM python:3.11-slim

WORKDIR /app

# 1. 환경 변수 설정 (중요: root 경고 및 버전 체크를 꺼서 로그를 깔끔하게 함)
ENV PIP_ROOT_USER_ACTION=ignore
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONUNBUFFERED=1

# 2. 필수 시스템 패키지 설치
# 빌드에 필요한 도구(gcc, python3-dev)가 없으면 일부 AI 패키지 설치 시 에러가 날 수 있습니다.
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. 패키지 설치 최적화
COPY requirements.txt .
# --no-cache-dir은 용량을 아껴주지만, 
# 만약 빌드가 자꾸 튕긴다면 --timeout 100 옵션을 추가하는 것도 방법입니다.
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
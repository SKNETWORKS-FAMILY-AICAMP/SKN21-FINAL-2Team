# GitHub Actions 기반 AWS EC2 CI/CD 가이드

## 1. 개요

이 문서는 `release/v*` 브랜치를 스테이징, `main` 브랜치를 운영으로 사용하는 현재 저장소의 GitHub Actions CI/CD 구성을 정리한다.

- `pull_request -> release/v*`, `main`: CI 실행
- `push -> release/v*`: 스테이징 배포
- `push -> main`: 운영 배포

즉, 자동배포는 태그가 아니라 브랜치 반영 시점에 동작한다.

## 2. 워크플로우 구성

### 2.1 CI

파일: `.github/workflows/ci.yml`

- 백엔드 `pytest -q`
- 프론트엔드 `npm test -- --runInBand`
- 프론트엔드 `npm run build`
  - 현재 `frontend/package.json`의 `build` 스크립트는 `next build --webpack`이다.
  - 이유: Next 16 기본 Turbopack 빌드에서 경로 alias 해석이 불안정하게 실패한 사례가 있어 CI와 로컬 빌드 결과를 일치시키기 위해 Webpack 빌드로 고정했다.

대상 이벤트:

- `pull_request` to `release/v*`
- `pull_request` to `main`

### 2.2 스테이징 배포

파일: `.github/workflows/cd-staging.yml`

- `release/v*` 브랜치에 `push` 발생 시 실행
- `verify-backend`, `verify-frontend` 두 job이 **병렬로** 검증 수행
  - 각 job에 pip 캐시 / npm 캐시 적용
- `backend`, `frontend`, `nginx` 이미지를 GHCR에 푸시
- 스테이징 EC2에 SSH 접속 후 다음 순서로 배포
  - 배포 디렉토리 이동 후 `.env.staging`, `.env.backend.staging`, `.env.frontend.staging`, `docker-compose.ec2.yml` 존재 여부 확인
  - `.env.staging`에서 `NGINX_PORT`를 읽고, 미설정 시 기본값 `80` 사용
  - `df -h`, `docker system df`로 초기 상태 출력
  - 미사용 컨테이너/이미지/build cache 및 7일 이상 지난 미사용 이미지 정리
  - 디스크 부족 위험이 있으면 현재 compose 스택을 `down` 한 뒤 이미지 참조를 해제하고 한 번 더 정리
  - `docker compose pull && docker compose up -d`
  - 배포 후 다시 `df -h`, `docker system df` 출력
- 배포 후 `http://127.0.0.1:${NGINX_PORT}/api/healthz` 최대 30회 retry 확인
- backend 컨테이너 healthcheck는 `curl` 대신 Python one-liner로 `/api/healthz`를 검사하며, 초기 모델 로딩 시간을 고려해 `start_period=180s`를 사용한다

### 2.3 운영 배포

파일: `.github/workflows/cd-production.yml`

- `main` 브랜치에 `push` 발생 시 실행
- 동일한 2단계 병렬 검증 수행
- 운영용 이미지를 GHCR에 푸시
- 운영 EC2에 SSH 접속 후 스테이징과 동일한 정리/검사 절차를 거쳐 재배포
- 배포 후 `http://127.0.0.1:${NGINX_PORT}/api/healthz` 최대 30회 retry 확인

## 3. 자동배포 트리거

### 3.1 스테이징

다음 경우 스테이징 자동배포가 발생한다.

1. `release/v1.2.0` 브랜치에 직접 커밋 후 push
2. PR이 `release/v1.2.0`에 merge

공통점은 최종적으로 `release/v*` 브랜치에 새로운 commit이 반영된다는 점이다.

### 3.2 운영

다음 경우 운영 자동배포가 발생한다.

1. `release/v1.2.0` 브랜치를 `main`에 merge
2. `main` 브랜치에 직접 commit 후 push

운영 배포는 `main` 브랜치에 새로운 commit이 반영되는 순간 동작한다.

## 4. EC2 서버 준비

서버에는 다음이 준비되어 있어야 한다.

- Docker
- Docker Compose
- 배포 디렉토리
- 환경 파일
- 충분한 루트 디스크 여유 공간

예시 디렉토리 구조:

```text
/home/ubuntu/triver/
├── docker-compose.ec2.yml
├── .env.staging
├── .env.production
├── .env.backend.staging
├── .env.frontend.staging
├── .env.backend.production
└── .env.frontend.production
```

배포용 compose 템플릿은 `deploy/docker-compose.ec2.yml`을 사용한다.  
SCP로 EC2 배포 디렉토리에 직접 복사된다 (`deploy/` 폴더 제거, 파일만 전달).

중요:

- GitHub `Secrets` 또는 `Environments`에 저장한 값은 EC2의 `.env.*` 파일을 자동으로 생성하지 않는다.
- `${STAGING_APP_DIR}` 또는 `${PROD_APP_DIR}` 아래에 런타임용 `.env.*` 파일을 미리 배치해야 한다.
- 필수 파일이 없으면 배포 워크플로우가 즉시 실패한다.

## 5. GitHub Secrets

### 5.1 공통

- `GHCR_USERNAME`: GHCR 로그인 사용자명 (PAT 발급 계정)
- `GHCR_TOKEN`: GHCR pull 전용 PAT (`read:packages` 권한, EC2에서 이미지 pull 시 사용)

> **주의**: `GHCR_TOKEN`은 PAT(Personal Access Token)이므로 만료일을 관리해야 한다.
> 만료 시 EC2 pull 단계에서 배포가 실패한다. 정기적으로 갱신하고 팀 내 관리 정책을 수립할 것.

### 5.2 스테이징

- `STAGING_HOST`
- `STAGING_USER`
- `STAGING_SSH_KEY`
- `STAGING_PORT`
- `STAGING_APP_DIR`

### 5.3 운영

- `PROD_HOST`
- `PROD_USER`
- `PROD_SSH_KEY`
- `PROD_PORT`
- `PROD_APP_DIR`

## 6. 환경 파일

서버의 compose 실행용 파일:

- `.env.staging`
- `.env.production`

예시는 다음 파일을 참고한다.

- `deploy/.env.staging.example`
- `deploy/.env.production.example`

애플리케이션 런타임 환경변수는 별도 파일로 분리한다.

- 백엔드: `.env.backend.staging`, `.env.backend.production`
- 프론트엔드: `.env.frontend.staging`, `.env.frontend.production`

백엔드 환경변수 예시는 `backend/.env.example` 파일을 참고한다.

`docker-compose.ec2.yml`은 기본값으로 `.env.backend`, `.env.frontend`를 바라보지만, 실제 배포에서는 `.env.staging` 또는 `.env.production`의 아래 값으로 덮어쓴다.

```env
BACKEND_ENV_FILE=.env.backend.staging
FRONTEND_ENV_FILE=.env.frontend.staging
```

즉 스테이징 EC2에는 최소 아래 파일이 모두 있어야 한다.

- `.env.staging`
- `.env.backend.staging`
- `.env.frontend.staging`

운영도 동일하게 `.env.production`, `.env.backend.production`, `.env.frontend.production`이 필요하다.

### 6.1 CORS 설정

백엔드는 `CORS_ORIGINS` 환경변수로 허용 도메인을 제어한다.

```env
# 쉼표로 구분하여 복수 도메인 허용
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://triver-s.com,https://www.triver-s.com
# 필요 시 서브도메인 패턴 허용
CORS_ORIGIN_REGEX=https://.*\.triver-s\.com
```

미설정 시에도 로컬 개발 주소와 운영 기본 도메인(`triver-s.com`, `www.triver-s.com`)은 허용되도록 구성한다.

## 7. 이미지 태깅 규칙

- 스테이징
  - 브랜치명 기반 태그 예: `release-v1.2.0`
  - 최신 스테이징 태그: `staging-latest`
- 운영
  - 커밋 기반 태그 예: `main-abcdef1`
  - 최신 운영 태그: `prod-latest`

## 8. 네트워크 구성 (docker-compose.ec2.yml)

모든 서비스는 `app-network` 브리지 네트워크로 격리된다.

```
nginx (포트 80 노출)
  ↓
frontend (내부 3000)
  ↓
backend (내부 8000, healthcheck 포함)
adminer (포트 8080 노출, DB 관리용)
```

adminer 서비스는 `http://도메인:8080`을 통해 접속하여 RDS를 관리할 수 있다. 접속 시 서버(System)는 `MySQL`을 선택하고, 호스트는 서버의 `.env.backend.*`에 설정된 `MYSQL_HOST` 값을 입력한다.

backend 서비스는 `/api/healthz` 엔드포인트로 헬스체크를 수행한다.

## 9. 운영 권장 사항

- `main`은 브랜치 보호 규칙으로 직접 push를 제한하는 것을 권장한다.
- `release/v*` 브랜치는 검수 완료 후 `main` merge 뒤 삭제한다.
- 데이터베이스 마이그레이션 자동화는 현재 범위에 포함하지 않는다.
- 서버의 `.env.*` 파일은 Git에 포함하지 않는다.
- `GHCR_TOKEN` PAT는 만료 전 갱신하고 GitHub Secrets를 업데이트한다.
- 배포 전후 서버에서 `df -h`, `docker system df`, `sudo du -sh /var/lib/containerd`로 용량을 점검하는 것을 권장한다.
- 현재 자동 정리 정책은 미사용 컨테이너/이미지/build cache 및 7일 이상 지난 미사용 이미지를 정리한다.
- 다만 실행 중 컨테이너가 기존 이미지를 참조 중이면 `docker image prune`만으로는 공간이 즉시 확보되지 않는다. 이 경우 현재 배포 스크립트처럼 `docker compose down` 후 재정리를 거쳐 새 이미지를 pull한다.
- `docker volume prune`은 데이터 손실 위험 때문에 기본 배포 절차에 포함하지 않는다.
- 루트 디스크 사용률이 80%를 넘기기 시작하면 EBS 증설을 검토한다. 29GB급 루트 디스크는 이미지 누적 시 재발 가능성이 높다.

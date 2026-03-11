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
- 스테이징 EC2에 SSH 접속 후 `docker compose pull && docker compose up -d`
- 배포 후 `http://127.0.0.1/api/healthz` 최대 10회 retry 확인

### 2.3 운영 배포

파일: `.github/workflows/cd-production.yml`

- `main` 브랜치에 `push` 발생 시 실행
- 동일한 2단계 병렬 검증 수행
- 운영용 이미지를 GHCR에 푸시
- 운영 EC2에 SSH 접속 후 동일한 방식으로 재배포
- 배포 후 `http://127.0.0.1/api/healthz` 최대 10회 retry 확인

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

### 6.1 CORS 설정

백엔드는 `CORS_ORIGINS` 환경변수로 허용 도메인을 제어한다.

```env
# 쉼표로 구분하여 복수 도메인 허용
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
```

미설정 시 `http://localhost:3000` 만 허용된다.

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
```

backend 서비스는 `/api/healthz` 엔드포인트로 헬스체크를 수행한다.

## 9. 운영 권장 사항

- `main`은 브랜치 보호 규칙으로 직접 push를 제한하는 것을 권장한다.
- `release/v*` 브랜치는 검수 완료 후 `main` merge 뒤 삭제한다.
- 데이터베이스 마이그레이션 자동화는 현재 범위에 포함하지 않는다.
- 서버의 `.env.*` 파일은 Git에 포함하지 않는다.
- `GHCR_TOKEN` PAT는 만료 전 갱신하고 GitHub Secrets를 업데이트한다.

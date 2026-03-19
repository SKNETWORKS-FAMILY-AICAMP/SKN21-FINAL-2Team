# LLM 모델 교체 가이드 (gpt-4o-mini → qwen2.5:3b)

**작성일**: 2026-03-19  
**대상**: Cloud Vision + LLM 기반 OCR 서비스의 모델 교체 프로세스  
**상태**: 모든 코드 변경 완료, 서버 배포 준비 단계

---

## 📋 개요

### 배경
- **기존**: Google Cloud Vision API + OpenAI gpt-4o-mini
- **변경**: OCR 필드 추출만 → Ollama (로컬) + qwen2.5:3b
- **챗봇**: 여전히 OpenAI gpt-4o-mini 유지 ✅
- **이유**: 개인정보 보호, 비용 절감, 로컬 제어 (챗봇은 영향 없음)

### 핵심: 독립적인 LLM 설정
```
┌─────────────────────────────────────────┐
│ 🤖 일반 LLM (챗봇)                       │
│ LLM_MODEL=gpt-4o-mini (OpenAI)          │
│ LLM_TYPE=openai                         │
└─────────────────────────────────────────┘
           
┌─────────────────────────────────────────┐
│ 🖼️  OCR 전용 LLM (예약정보 추출)         │
│ OCR_LLM_MODEL=qwen2.5:3b (Ollama)       │
│ OCR_LLM_TYPE=ollama                     │
└─────────────────────────────────────────┘
```

### 테스트 결과 (보고서 기준)
| 항목 | gpt-4o-mini | qwen2.5:3b | 평가 |
|------|-------------|-----------|------|
| 응답시간 | 1.8~2.7초 | 17~30초 | qwen이 길지만 실용적 |
| JSON 파싱 성공률 | 100% | 100% | 동등 |
| 필드명 정확도 | 100% | ~90% | qwen: 필드명 변형 |
| 시간 값 정확도 | 단일값 | 범위값 | qwen: 범위 처리 필요 |
| 추가정보 혼입 | 없음 | 있음 (2~3건) | qwen: 후처리 필요 |

### 개선 사항
✅ **프롬프트 강화**: 필드명, 형식, 값 추출 규칙 더 명시적  
✅ **후처리 로직**: 필드명 정규화, 시간 범위 처리, 추가정보 제거  
✅ **모듈화 설정**: 환경변수로 모델 전환 가능 (서버 재배포 최소화)  
✅ **독립적 관리**: 챗봇과 OCR이 **완전히 분리된** LLM 설정  

---

## 🔧 변경된 코드 구조

### 1. LLMFactory 개선 (`app/core/llm_factory.py`)

**이전**: OpenAI만 지원
```python
class LLMFactory:
    @classmethod
    def get_llm(cls, model: str = LLM_MODEL, temperature: float = 0):
        return ChatOpenAI(model=model, temperature=temperature)
```

**개선**: OpenAI + Ollama 지원
```python
class LLMFactory:
    @classmethod
    def get_llm(cls, model: str = LLM_MODEL, temperature: float = 0, llm_type: str = LLM_TYPE):
        if llm_type.lower() == "ollama":
            return ChatOllama(model=model, temperature=temperature, base_url=OLLAMA_BASE_URL)
        else:
            return ChatOpenAI(model=model, temperature=temperature)
```

### 2. 환경설정 개선 (`app/utils/config.py`)

**일반 LLM (챗봇)**:
```python
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TYPE = os.getenv("LLM_TYPE", "openai")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
```

**OCR 전용 LLM** (🆕 추가):
```python
OCR_LLM_MODEL = os.getenv("OCR_LLM_MODEL", "qwen2.5:3b")
OCR_LLM_TYPE = os.getenv("OCR_LLM_TYPE", "ollama")
OCR_OLLAMA_BASE_URL = os.getenv("OCR_OLLAMA_BASE_URL", "http://localhost:11434")
```

### 3. OCR 서비스 강화 (`app/services/ocr_service.py`)

**변경**: 일반 LLM이 아닌 **OCR 전용 LLM** 사용
```python
# 이전 (문제): LLMFactory.get_llm(model=LLM_MODEL, ...)
#   → 환경변수 변경하면 챗봇도 영향

# 현재 (개선): LLMFactory.get_llm(model=OCR_LLM_MODEL, llm_type=OCR_LLM_TYPE, ...)
#   → OCR만 qwen으로, 챗봇은 여전히 gpt-4o-mini
```

**프롬프트 개선**:
- 필드명 정확성 강조 (오타/변형 금지)
- 시간 범위 처리 (첫 값만 추출)
- 값 원문 추출 강조 (추가정보 금지)
- 예상치 못한 필드 추가 금지

**후처리 함수 추가** (`_normalize_llm_output`):
- 필드명 정규화 (차량번호 → 차량 번호)
- 시간 범위 처리 (14:30~16:30 → 14:30)
- 불필요한 접미사 제거 (식당이름 + 레스토랑 → 식당이름만)

### 4. Docker 설정 (`docker-compose.yml`)

**Ollama 서비스 추가**:
```yaml
ollama:
  image: ollama/ollama:latest
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  # qwen2.5:3b 자동 다운로드
```

### 5. 패키지 의존성 (`backend/requirements.txt`)

**추가**:
```
langchain-ollama  # Ollama 통합 라이브러리
```

---

## 🚀 배포 프로세스


### ✅ **1단계: 로컬 테스트 (개발 환경)**

#### 1.1 환경 준비
```bash
# backend/.env 파일 생성 (env.example 기반)
# 🤖 챗봇: OpenAI gpt-4o-mini 유지
LLM_MODEL=gpt-4o-mini
LLM_TYPE=openai

# 🖼️ OCR: Ollama qwen2.5:3b로 변경 ← 이 부분만!
OCR_LLM_MODEL=qwen2.5:3b
OCR_LLM_TYPE=ollama
OCR_OLLAMA_BASE_URL=http://localhost:11434

# Ollama 기본 주소 (필요시)
OLLAMA_BASE_URL=http://localhost:11434
```

#### 1.2 Ollama 로컬 실행
```bash
# macOS/Linux
brew install ollama  # 또는 다운로드: https://ollama.ai
ollama serve &
ollama pull qwen2.5:3b

# Windows: Ollama Windows 앱 설치 후 자동 실행
# (포트 11434로 시작됨)
```

#### 1.3 패키지 설치
```bash
cd backend
pip install -r requirements.txt
# 또는 poetry update (pyproject.toml 사용시)
```

#### 1.4 테스트 실행
```bash
# 기존 test_llm_quick.py 실행
python test_llm_quick.py

# 또는 개별 OCR 서비스 테스트
pytest tests/test_ocr_service.py -v
```

#### 1.5 결과 검증
- [ ] 모든 카테고리에서 JSON 파싱 성공
- [ ] 필드명이 정확함 (오타/변형 없음)
- [ ] 시간 값이 단일값 (범위 아님)
- [ ] 추가정보가 제거됨 (식당명만, 레스토랑 제거)

---

### ✅ **2단계: Docker 컴포즈 테스트 (통합 테스트)**

#### 2.1 Docker 빌드 및 실행
```bash
# 프로젝트 루트에서
docker compose -f docker-compose.yml up -d --build

# 로그 확인
docker compose logs -f backend
docker compose logs -f ollama
```

#### 2.2 Ollama 서버 대기
Ollama 컨테이너가 qwen2.5:3b를 다운로드하는 동안 대기 (처음 실행 시 3~5분)  
```bash
docker compose logs ollama | grep "pulling"
```

#### 2.3 Backend 헬스체크
```bash
curl http://localhost:8000/health
```

#### 2.4 통합 테스트
```bash
# 컨테이너 내에서 테스트 실행
docker compose exec backend python test_llm_quick.py

# 또는 API 호출 테스트
curl -X POST http://localhost:8000/api/ocr/extract \
  -F "image=@test_image.jpg" \
  -F "category=transportation"
```

---

### ✅ **3단계: 프로덕션 배포 (서버)**

#### 3.1 프로덕션 환경 파일 생성
```bash
# backend/.env.production (또는 backend/.env)
# 🤖 챗봇: OpenAI gpt-4o-mini 유지 (영향 없음)
LLM_MODEL=gpt-4o-mini
LLM_TYPE=openai
OLLAMA_BASE_URL=http://localhost:11434

# 🖼️ OCR 전용: Ollama qwen2.5:3b (Docker Compose 사용)
OCR_LLM_MODEL=qwen2.5:3b
OCR_LLM_TYPE=ollama
OCR_OLLAMA_BASE_URL=http://ollama:11434  # Docker 내부 네트워크

# 기타 프로덕션 설정...
OPENAI_API_KEY=your_openai_key
GOOGLE_VISION_API_KEY=your_vision_key
# ...
```

#### 3.2 EC2/서버에 배포
```bash
# 서버에 로그인
ssh -i your_key.pem ec2-user@your_server_ip

# 코드 최신화
cd /path/to/SKN21-FINAL-2Team
git pull origin main

# Docker 빌드 및 실행
docker compose -f docker-compose.ec2.yml up -d --build

# 또는 기존 스크립트 사용
./deploy.sh  # (if exists)
```

#### 3.3 헬스체크 및 모니터링
```bash
# 서버에서 테스트
curl http://your_server/health

# 로그 모니터링
docker compose logs -f backend --tail=50
docker compose logs -f ollama --tail=50

# 메모리/CPU 사용률 확인
docker stats
```

---

## 🛠️ 트러블슈팅

### 문제 1: Ollama 연결 실패
```
Error: Failed to connect to http://localhost:11434
```
**해결책**:
1. Ollama 서버가 실행 중인지 확인: `docker compose ps | grep ollama`
2. 포트 확인: `netstat -an | grep 11434`
3. Ollama 컨테이너 로그 확인: `docker compose logs ollama`
4. 서버 재시작: `docker compose restart ollama`

### 문제 2: qwen2.5:3b 모델 다운로드 실패
```
Error: failed to pull model qwen2.5:3b
```
**해결책**:
1. 네트워크 연결 확인
2. Ollama 내 수동 다운로드: `docker compose exec ollama ollama pull qwen2.5:3b`
3. 디스크 용량 확인 (모델: ~2GB)

### 문제 3: LLM 응답이 느림 (30초+)
**원인**: CPU 리소스 부족, Ollama 병렬 처리 설정
**해결책**:
```yaml
# docker-compose.yml의 ollama 서비스에서
environment:
  OLLAMA_NUM_PARALLEL: "2"  # CPU 코어 수에 맞게 조정
  OLLAMA_NUM_THREAD: "4"
```

### 문제 4: 필드명이 정규화되지 않음
**원인**: 후처리 함수의 필드명 매핑 부족
**해결책**: `ocr_service.py`의 `field_mappings` 딕셔너리에 새로운 필드명 추가
```python
field_mappings = {
    "transportation": {
        "차량번호": "차량 번호",  # 추가
        "새로운_필드": "정규화_필드",  # 필요시 추가
    }
}
```

---

## ❓ FAQ (자주 묻는 질문)

**Q1: 챗봇이 여전히 gpt-4o-mini를 사용하는지 어떻게 확인하나요?**

A: 다음 명령으로 환경변수를 확인하세요:
```bash
grep "LLM_MODEL\|LLM_TYPE\|OCR_LLM" backend/.env
```
올바른 출력:
```
LLM_MODEL=gpt-4o-mini       # 챗봇 (영향 없음)
LLM_TYPE=openai
OCR_LLM_MODEL=qwen2.5:3b    # OCR만 변경됨
OCR_LLM_TYPE=ollama
```

---

**Q2: 실수로 일반 LLM_TYPE을 변경했어요. 빠르게 되돌릴 수 있나요?**

A: 네, 2분 안에 복구 가능합니다:
```bash
# 파일 수정
echo "LLM_TYPE=openai" >> backend/.env

# 컨테이너 재시작
docker compose restart backend

# 30초 후 자동 복구됨
```

---

**Q3: OCR 모델만 gpt-4o-mini로 바꾸고 싶어요 (비용 증가해도 ok)**

A: 다음과 같이 설정하세요:
```bash
OCR_LLM_MODEL=gpt-4o-mini
OCR_LLM_TYPE=openai
```
그러면 OCR만 OpenAI를 사용하고, 챗봇은 여전히 gpt-4o-mini (비용 중복 약간 증가).

---

**Q4: 응답이 너무 느리면 (30초+)?**

A: 여러 방법이 있습니다:
1. **Ollama CPU 리소스 증가**:
   ```yaml
   # docker-compose.yml
   environment:
     OLLAMA_NUM_PARALLEL: "4"  # CPU 코어 수에 맞게
     OLLAMA_NUM_THREAD: "8"
   ```

2. **더 빠른 모델 사용**: qwen2.5:1.5b (더 작음)
   ```bash
   OCR_LLM_MODEL=qwen2.5:1.5b
   ```

3. **Redis 캐싱 추가** (같은 이미지 재요청 시 빠름)

---

**Q5: 모델 추가 (Gemma3, llama3.2 등) 가능한가요?**

A: 네, `docker-compose.yml`의 ollama entrypoint에 추가하면 됩니다:
```yaml
entrypoint: >
  sh -c "
  ollama serve &
  sleep 10 &&
  ollama pull qwen2.5:3b &&
  ollama pull gemma3:4b &&
  wait
  "
```

그 후 환경변수로 선택:
```bash
OCR_LLM_MODEL=gemma3:4b
```

---

**Q6: 프로덕션에서 필드명 매핑을 추가하려면?**

A: `ocr_service.py`의 `field_mappings` 딕셔너리에 추가하고 재배포:
```python
field_mappings = {
    "transportation": {
        "기존_필드명": "새로운_필드명",  # 추가
    }
}
```

---

**Q7: 로컬에서 테스트했는데 서버에만 안 되는 이유?**

A: 네트워크 차이일 가능성:
- 로컬: `OLLAMA_BASE_URL=http://localhost:11434`
- Docker: `OLLAMA_BASE_URL=http://ollama:11434` ⭐ (서비스명 사용)

`.env.production` 파일을 확인하세요!

---

**Q8: OCR_OLLAMA_BASE_URL과 OLLAMA_BASE_URL의 차이는?**

A:
- `OLLAMA_BASE_URL`: 일반 LLM 사용 시 (현재 거의 사용 안 함)
- `OCR_OLLAMA_BASE_URL`: OCR 전용 LLM 사용 시 ⭐ (현재 사용 중)

둘 다 같은 주소로 설정해도 괜찮습니다.

---

**Q9: 챗봇 응답 성능이 저하됐어요**

A: Ollama가 CPU를 많이 사용 중일 가능성:
```bash
# CPU 사용률 확인
docker stats ollama

# Ollama 요청이 많으면 CPU 병렬 수 제한
docker exec ollama bash -c "echo OLLAMA_NUM_PARALLEL=2 >> /etc/ollama/config"
docker compose restart ollama
```

---

**Q10: 한꺼번에 여러 추가 필드를 추출하고 싶어요**

A: `ocr_service.py`의 `category_prompts` 딕셔너리를 수정하세요:
```python
"transportation": "교통 티켓입니다. '날짜', '출발지', '출발시간', '도착지', '도착시간', '승차홈', '차량 번호', '좌석', '승객명'을 추출해주세요.",
```

그 후 `_normalize_llm_output`에 필요시 정규화 로직 추가.

---

## 📊 성능 비교 및 예상값


### 응답 시간 (OCR + LLM)
| 상황 | gpt-4o-mini | qwen2.5:3b | 차이 |
|------|-------------|-----------|------|
| 첫 요청 | 2.3초 | 27.8초 | +25.5초 |
| 후속 요청 | 2.3초 | 18.0초 | +15.7초 |
| 배치 처리 (10개) | 23초 | 180~200초 | ~8배 |

**개선 방안**:
- Ollama 병렬 처리 증가 (OLLAMA_NUM_PARALLEL)
- 배치 처리 시 async/await 활용
- 캐싱 레이어 추가 (Redis 등)

### 비용 절감
| 항목 | gpt-4o-mini | qwen2.5:3b | 절감 |
|------|-------------|-----------|------|
| API 비용/1000req | $0.15 | $0 (로컬) | 100% |
| 월간 예상 비용 | $450 (3M req) | $0 | $450 |

---

## 🔄 모델 전환 (OpenAI ↔ Ollama)

### ⚡ OCR 모델만 즉시 전환 가능 (환경변수만 수정)
```bash
# 🖼️ OCR을 OpenAI로 바꾸기 (비용 증가, 빠름)
echo "OCR_LLM_TYPE=openai" >> backend/.env
echo "OCR_LLM_MODEL=gpt-4o-mini" >> backend/.env

# 🖼️ OCR을 Ollama로 바꾸기 (비용 절감, 느림)
echo "OCR_LLM_TYPE=ollama" >> backend/.env
echo "OCR_LLM_MODEL=qwen2.5:3b" >> backend/.env

# 서버 재시작 (챗봇은 영향 없음)
docker compose restart backend
```

### ✅ 중요: 일반 LLM (챗봇)은 변경하지 마세요!
```bash
# ❌ 이렇게 하지 마세요 (챗봇도 영향을 받음)
echo "LLM_TYPE=ollama" >> backend/.env

# ✅ 이렇게 하세요 (OCR만 변경)
echo "OCR_LLM_TYPE=ollama" >> backend/.env
```

### 점진적 롤아웃 (AB 테스트)
```python
# app/services/ocr_service.py에서 (선택적)
# 특정 사용자/요청에만 다른 모델 적용
if user_id in OPENAI_OCR_USERS:
    llm = LLMFactory.get_llm(
        model=OCR_LLM_MODEL, 
        llm_type="openai"  # 강제 로직 추가 가능
    )
else:
    llm = LLMFactory.get_llm(
        model=OCR_LLM_MODEL,
        llm_type=OCR_LLM_TYPE  # 기본값 (ollama)
    )
```

---

## ✅ 배포 체크리스트

### 로컬 개발 환경
- [ ] LLMFactory.py 수정 완료 (OpenAI + Ollama 지원)
- [ ] config.py 환경변수 추가 완료 (일반 LLM + OCR 전용)
- [ ] ocr_service.py 프롬프트/후처리 개선 완료
- [ ] ocr_service.py가 OCR_LLM_* 사용하도록 수정 완료 ✅
- [ ] requirements.txt에 langchain-ollama 추가 완료
- [ ] env.example 업데이트 완료 (일반/OCR 분리)
- [ ] 로컬 테스트 통과 (test_llm_quick.py)
- [ ] **챗봇이 여전히 gpt-4o-mini 사용하는지 확인** ✅

### Docker 컴포즈
- [ ] docker-compose.yml에 ollama 서비스 추가 완료
- [ ] 컨테이너 빌드 및 실행 성공
- [ ] Ollama 모델 다운로드 완료
- [ ] Backend ↔ Ollama 통신 확인
- [ ] Docker 컴포즈 테스트 통과

### 프로덕션 서버
- [ ] 서버에 코드 배포 완료
- [ ] .env.production 파일 설정 완료
- [ ] Docker 빌드 및 실행 성공
- [ ] 헬스체크 통과
- [ ] 동시 3~5개 요청 테스트 통과
- [ ] 모니터링 수집 시작

### 사후관리
- [ ] 초기 24시간 모니터링 강화
- [ ] 에러 로그 분석
- [ ] 응답 시간 모니터링 (SLA 확인)
- [ ] 필드 추출 정확도 검증
- [ ] 사용자 피드백 수집

---

## 📚 참고 자료

- **Ollama 공식 사이트**: https://ollama.ai
- **qwen2.5 모델 카드**: https://huggingface.co/Qwen/Qwen2.5-3B
- **LangChain Ollama**: https://python.langchain.com/docs/integrations/llms/ollama
- **프로젝트 테스트 보고서**: `backend/llm_model_test_report.md`
- **LLM 성능 분석**: `docs/LANGGRAPH_PERFORMANCE_ANALYSIS.md`

---

## 📞 문의 및 지원

- **기술 이슈**: GitHub Issues
- **성능 최적화**: LangSmith 대시보드 (LANGSMITH_PROJECT)
- **모델 선택 가이드**: 본 문서 상단 테스트 결과 参照

---

**마지막 업데이트**: 2026-03-19  
**상태**: ✅ 모든 코드 변경 완료, 배포 준비 완료

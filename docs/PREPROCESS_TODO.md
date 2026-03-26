# 전처리 스크립트 수정 계획

> 작성일: 2026-03-25
> 상태: 검토 중 (코멘트 필요 항목 있음)

---

## A. 필드명 snake_case 통일

**대상 파일**: `preprocess/popply.py`, `preprocess/seoul_culture.py`

### popply
| 현재 | 변경 |
|------|------|
| `startDate` | `start_date` |
| `endDate` | `end_date` |

### seoul_culture
| 현재 | 변경 |
|------|------|
| `STRTDATE` | `start_date` |
| `END_DATE` | `end_date` |
| `RGSTDATE` | `rgst_date` |
| `IS_FREE` | `is_free` |
| `PLAYER` | `player` |

### 연쇄 수정

> **주의**: 아래 파일들은 직접 수정할 예정이므로 건드리지 말 것.
> - `scheduler/cleanup_expired_contents.py`의 `END_DATE`/`endDate` fallback → `end_date`로 통일
> - `scheduler/sync_new_contents.py` 내 `endDate` 참조 있으면 수정

---

## B. 불필요 필드 제거

**대상 파일**: `preprocess/shopping.py`

| 필드 | 소스 | 제거 이유 |
|------|------|----------|
| `contenttypeid_code` | 다이소, 무신사 | `collect/shopping.py`에서 자체 부여한 코드(`"99"`). 서비스 미사용 |
| `updated_at` | 다이소, 무신사 | 수집 날짜(`2026.03.23`). 날짜 형식도 다른 소스와 불일치하며 다른 소스에는 없는 필드 |

---

## C. tourapi summary 제거

**대상 파일**: `preprocess/tourapi.py`

현재 `overview`(description)의 첫 문장을 `first_sentence()`로 잘라서 `summary` 필드 생성 중.

- tourapi: API에서 summary를 제공하지 않음. 우리가 만들어서 넣은 것
- visitseoul: API에서 `sumry` 필드로 원래 제공 → 유지
- 팝플리, 열린데이터광장: summary 없음
- 다이소: summary 없음
- 무신사, 올리브영: 자체 생성된 summary 있음

### 앱 런타임 영향 분석

`summary` 필드를 참조하는 런타임 코드 **2곳** 확인:

| 파일 | 라인 | 코드 | 영향 |
|------|------|------|------|
| `core/retrieval/place_score.py` | 65 | `payload.get("summary")` | 검색 점수 계산에 사용. summary 없으면 빈 문자열로 fallback → 점수에 반영 안 됨 |
| `agents/executor.py` | 147 | `payload.get("summary")` | 장소 소개 텍스트 구성에 사용. summary 없으면 `description`으로 fallback |

**결론**: 둘 다 `or` 체인 fallback이 있어서 에러는 안 나지만, **tourapi 장소들의 검색 점수가 달라질 수 있음**. 현재 tourapi의 summary는 description 첫 문장이므로, 없어지면 해당 점수 항목이 0이 됨.

> **코멘트 필요**: 검색 점수 변동을 감수하고 제거할지, 아니면 유지할지 결정 필요.

---

## D. 쇼핑 데이터 enrich 단계 통일

**대상 파일**: `preprocess/shopping.py`, `enrich/generate_llm_text.py`

### 현재 흐름 (비표준)
```
collect/shopping.py → data/{brand}_투어.json
    ↓
preprocess/shopping.py (llm_text 직접 생성, 같은 파일 덮어쓰기)
    ↓
enrich_geo()만 적용 → data/enrich/{brand}_투어_enrich.json
```

### 변경 후 흐름 (표준)
```
collect/shopping.py → data/raw/{brand}_투어.jsonl (또는 .json)
    ↓
preprocess/shopping.py (필드 정리만, llm_text 생성 제거)
    → data/preprocessed/{brand}_투어.json
    ↓
enrich/generate_llm_text.py (GPT-4o-mini로 llm_text + tags 생성)
    → data/enrich/{brand}_투어_enrich.json
```

### 수정 사항

**preprocess/shopping.py**
- `_build_llm_text()` 함수 및 호출 제거
- 입력: `data/{brand}_투어.json`
- 출력: `data/preprocessed/{brand}_투어.json` (경로 변경)
- `enrich_geo()` 추가
- `contenttypeid_code`, `updated_at` 제거 로직 추가

**enrich/generate_llm_text.py**
- `TARGETS`에 `daiso_투어`, `musinsa_투어`, `oliveyoung_투어` 추가

### 소개글 관련 상수 처리

`preprocess/shopping.py`에 하드코딩된 소개글 상수들:
- `MUSINSA_INTROS` — 무신사 매장별 전용 소개글 (15개)
- `OY_SPECIAL_INTROS` — 올리브영 특수매장 전용 소개글 (6개)
- `OY_AREA_CONTEXT` — 올리브영 지역별 컨텍스트 (16개)
- `MUSINSA_COORDS` — 무신사 매장 좌표 보정값
- `MUSINSA_FALLBACK_IMAGES` — 이미지 없는 매장 대체 이미지

이 상수들을 제거하면 llm_text 생성 시 GPT가 description + 기본 정보만 보고 생성하게 됨. 하드코딩만큼 정확한 매장 특징(예: "지하 1층부터 2층까지 운영", "무신사에서 인기 있는 수백 개 브랜드" 등)이 반영 안 될 수 있음.

> **코멘트 필요**:
> - 옵션 1: GPT-4o-mini로 전환 — 통일성 확보, 비용 발생, 품질 변동 가능
> - 옵션 2: 하드코딩 소개글 유지하되 파이프라인 경로만 통일 — 품질 유지, `preprocess/shopping.py`에서 llm_text 생성은 유지하고 출력 경로만 `data/preprocessed/`로 변경
> - 옵션 3: 하드코딩 소개글을 GPT 프롬프트의 참고 자료로 전달 — 통일성 + 품질 모두 확보, 구현 복잡도 증가

---

## E. enrich 파일 재생성

A~D 수정 완료 후 재생성이 필요한 파일:

| 파일 | 재생성 이유 | 비용 |
|------|-----------|------|
| `popply_팝업스토어_enrich.json` | 필드명 변경 (startDate→start_date) | 전처리만 (API 호출 없음) |
| `seoul_culture_문화행사_enrich.json` | 필드명 변경 (END_DATE→end_date 등) | 전처리만 |
| `daiso_투어_enrich.json` | 불필요 필드 제거 + 파이프라인 변경 | D 옵션에 따라 다름 |
| `musinsa_투어_enrich.json` | 동일 | 동일 |
| `oliveyoung_투어_enrich.json` | 동일 | 동일 |
| `tourapi_*_enrich.json` (4개) | summary 제거 (C 확정 시) | 전처리만 |
| `visitseoul_*_enrich.json` (4개) | 변경 없음 | 불필요 |

---

## F. Qdrant upsert 재실행

E 완료 후 전체 데이터를 Qdrant에 다시 업로드.

```bash
QDRANT_HOST=localhost python -m app.scripts.qdrant_upsert --snapshot
```

소요 시간: 약 2~3시간 (텍스트 임베딩 + 이미지 다운로드/임베딩)

---

## 데이터 이슈 보고

### place 없는 건
| 소스 | contentid | title | 상태 |
|------|-----------|-------|------|
| popply | 4657 | Mardi Mersrerdi 팝업 | place가 `"빈 문자열"` (LLM 추출 실패) |

### addr 없는 건
| 소스 | contentid | title | 상태 |
|------|-----------|-------|------|
| visitseoul_관광지 | KOP015109 | 고궁을 찾다 | API에서 주소 미제공 (좌표는 있음, 경복궁 근처) |

---

## 작업 순서 (제안)

```
1. 코멘트 필요 항목 확정
   - C: tourapi summary 제거 여부 (검색 점수 변동 감수 여부)
   - D: 쇼핑 llm_text 처리 방식 (옵션 1/2/3)
   - F: Qdrant 재실행 시점

2. 스크립트 수정 (A → B → C → D)

3. enrich 파일 재생성 (E)

4. Qdrant upsert 재실행 (F)
```

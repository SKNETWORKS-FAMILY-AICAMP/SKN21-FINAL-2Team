"""
LLM 모델 빠른 비교 테스트 스크립트 (복수 카테고리 지원)
=====================================================================
사용법 (CMD에서 backend 폴더 안에서 실행):
  python test_llm_quick.py
  또는
  uv run python test_llm_quick.py

✅ 테스트할 수 있는 모델:
  - gpt-4o-mini               : OpenAI API (API Key 필수)
  - Qwen/Qwen2.5-3B-Instruct  : HuggingFace Inference API (HF_TOKEN 필수)
  - Qwen/Qwen2.5-7B-Instruct  : HuggingFace Inference API (더 정확, 느림)

✨ 주요 기능:
  👉 여러 카테고리를 한 번에 테스트 가능
  👉 각 카테고리별 최적화된 OCR 샘플 포함
  👉 ocr_service.py 와 동일한 프롬프트 사용
  👉 모든 모델의 응답시간 자동 측정
  👉 JSON 파싱 성공/실패 자동 판별

📋 아래 'CATEGORIES_TO_TEST' 를 수정하여 테스트할 카테고리 선택:
  - 단일 선택: CATEGORIES_TO_TEST = ["transportation"]
  - 복수 선택: CATEGORIES_TO_TEST = ["transportation", "hotel", "activity"]
  - 모두 테스트: CATEGORIES_TO_TEST = ["transportation", "hotel", "activity", "restaurant", "etc"]
=====================================================================
"""

import asyncio
import json
import time
import os
from dotenv import load_dotenv

# .env 파일 로드 (OPENAI_API_KEY, HF_TOKEN 등)
load_dotenv()

# =====================================================================
# 👇 섹션 1. 각 카테고리별 OCR 텍스트 샘플 정의
# =====================================================================
SAMPLE_OCR_TEXTS = {
    "transportation": """
SKT 11:34 ㄱㅁ·
네이버 예매 승차권
2021.11.02 (화)
*50ill 77%
스마트티켓 1매직통
서울
대전
05:05
06:02
KTX-산천 201
열차정보 >
어른 1
타는곳 번호
호차 번호
좌석번호
승차권QR
15분 전에
표시됩니다
2호차
일반실
승차권 번호
SAMPLE
13D
83125-1101-10000-00
결제내역
승차권 환불
N
로그아웃
지도 고객센터 네이버 기차예매 이용약관
2021.11.01(월) 오전 11시 34분 39초
상입니다. 정상적인 승차권은 이 문구가 왼쪽으로 흐르고 있습니다.
N
☑
<
000
""",
    "hotel": """
KT
예약내역
퍼스트 70 호텔
95%■오후 12:45
12
상세 정보 보기
길찾기
1. 예약 정보
체크인
체크아웃
2박
2018.12.03() 15:00
2018.12.05() 11:00
객실 정보
예약 장소
퍼스트 70 호텔
객실 타입
조식|원데이초특가] Superior Twin 싱글2
위치
제주특별자치도 서귀포시 서귀동 182
예약자 정보
예약자명
연락처
이메일
이용우
+82 (0)10-2957-8072
Jvw61423@naver.com.
""",
    "activity": """
나눔티켓
[광주] 2022 어린이 직업 체험 특별전 <키자니아 Go! 광주> (객석나눔)
÷
이동
일자선택
KidZania
국립아시아문화전당 어린이문화원
2022. 7.29-8.28."
장르
기타
수량선택
광주
장소
국립아시아문화전당 어린이문화원
공연기간
2022/07/31()-2022/12/31(E)
관람자정보
예매기간
관람 1일전 17시 00분까지
등급
36개월 이상~만 14세 미만 관람가
유의사항 확인 및 동의
관람시간
최대 4시간
개인정보처리 / 개인정보 처리방침 동의
문의
1544-3405 (나눔티켓)
취소/환불 규정에 대한 동의
공연예매
예약조회
0원
*필수항목
가격정보
본 공연은 한국문화예술위원회(공연)의 객석기부로 이루어집니다.
어린이 입장권 무료 (정상가 25,900원)
회차정보
[2부] 오후 2시 30분 ~ 6시 30분
|취소수수료 : 없음
예매 유의사항에 대한 동의
예매 : 관람 1일전 오후 5시까지 가능
취소: 관람 1일전 오후 5시까지 가능
※가상계좌/무통장 결제수단의 경우 동일 공연에 대해 3회까지 미입금 취소 시 가상계좌/무
통장 예매가 제한됩니다. (예매시 유의하시기 바랍니다)
전체동의
다음단계
""",
    "restaurant": """
3
9:41
KONJIAM
RESORT
예약/구매 내역
레스토랑 예약내역을 확인하실 수 있습니다.
담하
예약완료
영업시간: 07:30~20:30
예약자 정보
예약번호
예약취소
1234567891011
예약자
휴대폰번호
이용일
예약시간
이용인원수
홍길동
010-1234-5678
2023.01.01
중식(12:30~13:30)
성인 8명
요청사항
목록
""",
    "etc": """
22
공공서비스예약
문화체험
전시/관람
넘어넘어
예약 유형 문화체험 [전시/관람]
공공서비스 서울기록원 특별전시
나의 예약 정보
사전예약관람
자치구
은평구
이용일시
2021년 03월 16일
화요일10:00~12:00
현재 예약 접수 대기중입니다. 예약을
완료하려면 반드시 아래 '예약완료
하러가기' 버튼을 눌러주세요.
예약완료 하러가기
나의 예약 정보
서울기록원 특별전시 사전예약관람
.
이용일자
2021.03.16
.
이용회차
10:00~12:00 (2시간)
.
취소기간
2021-03-15
.
취소수수료
없음
다시 선택
상세정보 확인
오호 10:40
예약 날짜 / 회차
""",
}

# =====================================================================
# 👇 섹션 2. 테스트할 카테고리 선택
# =====================================================================
# 옵션 1: 단일 카테고리 테스트
# CATEGORIES_TO_TEST = ["transportation"]

# 옵션 2: 복수 카테고리 한 번에 테스트 ✅ (권장!)
CATEGORIES_TO_TEST = ["transportation", "hotel", "activity", "restaurant", "etc"]

# =====================================================================
# 👇 섹션 3. 테스트할 모델 목록 (주석 처리로 제외 가능)
# =====================================================================
# 주의: 모델명 변경 위치 (이 MODELS 리스트) / 또는 .env의 OCR_HF_MODEL_ID
MODELS = [
    # ("gpt", "gpt-4o-mini"),                          # OpenAI (API Key 필수)
    ("huggingface", "Qwen/Qwen2.5-3B-Instruct"),      # HuggingFace Inference API <- HF_TOKEN 필수
    # ("huggingface", "Qwen/Qwen2.5-7B-Instruct"),    # 더 정확한 모델 (느림, 비활성화)
]

# =====================================================================
# 섹션 4. ocr_service.py 와 완전히 동일한 카테고리별 프롬프트
# (아래 프롬프트는 자동으로 활용됩니다 — 수정 불필요)
# =====================================================================
CATEGORY_PROMPTS = {
    "transportation": "교통 티켓입니다. '날짜', '출발지', '출발시간', '도착지', '도착시간', '승차홈', '차량 번호', '좌석'을 추출해주세요.",
    "hotel":          "호텔 예약증입니다. '날짜', '숙소 이름', '체크인 날짜', '체크인 시간', '체크아웃 날짜', '체크아웃 시간', '방 호실'을 추출해주세요.",
    "activity":       "공연/활동 티켓입니다. '날짜', '이름', '시간', '장소', '좌석'을 추출해주세요.",
    "restaurant":     "식당 예약증입니다. '날짜', '식당이름', '예약시간', '예약자명'을 추출해주세요.",
    "etc":            "기타 예약증/영수증입니다. '예약내역', '시간', '예약자명'을 추출해주세요.",
}

def build_system_prompt(category: str) -> str:
    """ocr_service.py 와 동일한 시스템 프롬프트 생성"""
    prompt_instruction = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["etc"])
    return (
        f"당신은 OCR 텍스트에서 예약 정보를 추출하는 어시스턴트입니다.\n"
        f"다음 텍스트에서 {prompt_instruction}\n"
        f"추출 규칙:\n"
        f"1. 날짜와 관련된 모든 항목(날짜, 체크인 날짜 등)은 반드시 'YYYY-MM-DD' 형식(예: 2026-03-25)으로 통일해서 반환하세요.\n"
        f"2. 시간과 관련된 모든 항목(시간, 출발시간 등)은 반드시 '24시간 표기법 HH:MM' 패턴(예: 16:30)으로 통일해서 반환하세요.\n"
        f"3. 결괏값의 Key는 위에서 요청한 한글 명칭을 그대로 사용하세요.\n"
        f"4. 결과는 반드시 JSON 형식으로만 반환하세요. JSON 외의 설명 텍스트는 포함하지 마세요.\n"
        f"5. 찾을 수 없는 항목은 빈 문자열로 두세요."
    )


async def test_gpt(model_name: str, system_prompt: str, user_text: str):
    """OpenAI GPT 계열 테스트 (현재 사용 중인 방식)"""
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model_name, temperature=0)

        start = time.time()
        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_text},
        ])
        elapsed = time.time() - start

        content = response.content.strip()
        # 마크다운 코드블록 제거 (ocr_service.py 와 동일한 처리)
        if content.startswith("```json"): content = content[7:]
        if content.startswith("```"):     content = content[3:]
        if content.endswith("```"):       content = content[:-3]
        content = content.strip()

        return elapsed, content
    except Exception as e:
        return None, f"❌ 오류: {e}"


async def test_huggingface(model_name: str, system_prompt: str, user_text: str):
    """HuggingFace Inference API 테스트 (현재 OCR에 사용 중인 방식)"""
    try:
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        # 주의: HF_TOKEN 환경변수가 로드되어 있어야 합니다
        endpoint = HuggingFaceEndpoint(
            repo_id=model_name,
            temperature=0.01,  # HuggingFace는 temperature=0 미지원
            max_new_tokens=512,
            task="text-generation"
        )
        llm = ChatHuggingFace(llm=endpoint)

        start = time.time()
        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_text},
        ])
        elapsed = time.time() - start

        content = response.content.strip()
        # 마크다운 코드블록 제거 (ocr_service.py와 동일한 처리)
        if content.startswith("```json"): content = content[7:]
        if content.startswith("```"):     content = content[3:]
        if content.endswith("```"):       content = content[:-3]
        content = content.strip()

        return elapsed, content
    except ImportError:
        return None, "❌ langchain-huggingface 미설치. 실행: pip install langchain-huggingface"
    except Exception as e:
        return None, f"❌ 오류: {e}\n   → HF_TOKEN이 설정되어 있는지 확인하세요"


def print_result(backend: str, model_name: str, elapsed, content: str):
    """결과 출력"""
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"🤖 모델: [{backend}] {model_name}")
    print(f"⏱  응답 시간: {f'{elapsed:.2f}s' if elapsed else 'N/A'}")
    print(f"{sep}")
    print(f"📝 원본 응답:\n{content}")

    # JSON 파싱 시도
    try:
        parsed = json.loads(content)
        print(f"\n✅ JSON 파싱 성공!")
        for k, v in parsed.items():
            status = "✓" if v else "○ (빈 값)"
            print(f"   {status}  {k}: {v}")
    except json.JSONDecodeError:
        print(f"\n❌ JSON 파싱 실패 — 위 원본 응답을 확인하세요")


async def main():
    print("\n" + "=" * 80)
    print("🧪 LLM 모델 비교 테스트 (복수 카테고리)")
    print(f"📊 테스트할 카테고리: {', '.join(CATEGORIES_TO_TEST)}")
    print(f"🤖 테스트할 모델: {len(MODELS)}개")
    print("=" * 80)

    # 각 카테고리별로 순회
    for category in CATEGORIES_TO_TEST:
        ocr_text = SAMPLE_OCR_TEXTS.get(category, SAMPLE_OCR_TEXTS["etc"])
        system_prompt = build_system_prompt(category)

        print(f"\n\n{'█' * 80}")
        print(f"📂 카테고리: {category.upper()}")
        print(f"{'█' * 80}")
        print(f"\n📄 OCR 입력 텍스트:\n{ocr_text.strip()}")
        print(f"\n📋 시스템 프롬프트:\n{system_prompt}")

        # 이 카테고리에 대해 모든 모델 테스트
        for backend, model_name in MODELS:
            if backend == "gpt":
                elapsed, content = await test_gpt(model_name, system_prompt, ocr_text)
            elif backend == "huggingface":
                elapsed, content = await test_huggingface(model_name, system_prompt, ocr_text)
            else:
                continue

            print_result(backend, model_name, elapsed, content)

    print(f"\n\n{'=' * 80}")
    print("✅ 모든 카테고리 테스트 완료!")
    print("💡 CATEGORIES_TO_TEST 변수를 수정하여 특정 카테고리만 선택 테스트 가능합니다.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

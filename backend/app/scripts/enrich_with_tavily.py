import os
import re
import json
import time
import unicodedata
from typing import List, Dict
from tavily import TavilyClient
from openai import OpenAI
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate

from app.utils.config import LLM_MODEL
from app.utils.llm_factory import LLMFactory
from app.scripts.preprocess_data import ingest_data

load_dotenv(override=True)

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CATEGORY_HINTS = {
    "관광지": ["인생샷", "산책로", "포토존", "경치", "입장료", "주차", "탁 트인", "나들이"],
    "음식점": ["내돈내산", "웨이팅", "재방문", "현지인", "가성비", "분위기", "친절", "맛은 있는데", "노포맛집", "느좋", "가성비"],
    "축제공연행사": ["사전예약", "라인업", "볼거리", "티켓", "이벤트", "꿀팁", "주말기준"],
    "레포츠": ["장비", "초보", "강습", "액티비티", "시설", "활동적", "난이도"],
    "숙박": ["청결", "어메니티", "조식", "호캉스", "연박", "룸컨디션", "방음", "위치"],
    "문화시설": ["전시", "박물관", "도슨트", "관람", "체험", "교육", "실내데이트", "정기휴관"]
}

# 광고 필터 예시
AD_KEYWORDS = ["소정의 원고료", "지원받아 작성", "업체로부터", "무료체험"]

NOISE_URL_HINTS = ["support.google.com"]
WEB_URL_HINTS = [
    "blog.naver.com", 
    "tistory.com", 
    "visitkorea.or.kr", 
    "korean.visitkorea.or.kr", 
    "m.blog.naver.com",
    "tripadvisor.co.kr",
    "mangoplate.com",
    "siksinhot.com"
]

def _tokenize(text: str) -> list[str]:
    """
    텍스트 토큰화 : "매칭 정확도"와 "유연성"을 높이기 위해

    Args:
        text: 토큰화할 텍스트
    
    Returns:
        토큰화된 텍스트
    """
    if not text:
        return []
    return [t for t in re.findall(r"[A-Za-z0-9가-힣]+", text) if len(t) >= 2]


def _score_tavily_result(result: dict, title: str, title_tokens: list[str], addr_tokens: list[str], category_tokens: list[str]) -> float:
    """
    Tavily 검색 결과 점수 계산

    Args:
        result: Tavily 검색 결과
        title: 장소 이름
        title_tokens: 장소 이름 토큰
        addr_tokens: 주소 토큰
        category_tokens: 카테고리 토큰
    
    Returns:
        점수
    """
    url = (result.get("url") or "").lower()
    content = (result.get("content") or "").lower()
    result_title = (result.get("title") or "").lower()
    text = f"{result_title} {content}"

    if any(hint in url for hint in NOISE_URL_HINTS):
        return 0.0

    score = 0.0
    # URL 힌트 도메인일 경우 가산점
    if any(hint in url for hint in WEB_URL_HINTS):
        score += 1.0

    for token in title_tokens:
        if title.lower() in result_title:
            # 제목이 정확히 일치할 경우 가산점
            score += 0.5
        
        if token.lower() in text:
            score += 1.2

    for token in addr_tokens:
        if token.lower() in text:
            score += 0.5
            
    for token in category_tokens:
        if token.lower() in text:
            score += 0.6
    return score


def _build_context_from_tavily_result(result: dict) -> str:
    """
    Tavily 검색 결과에서 컨텍스트를 추출합니다.

    Args:
        result: Tavily 검색 결과
    
    Returns:
        추출된 컨텍스트
    """
    title = result.get("title", "").strip()
    content = result.get("content", "")

    content = content.replace("\\", " ")
    content = content.replace("\n", " ")
    
    # 1. JSON 형태의 메타데이터 블록 제거 (가장 지저분한 부분)
    # 블로그 정보 등이 포함된 {"title": ...} 구조를 통째로 지웁니다.
    content = re.sub(r'\{"title":.*?"\}', '', content)

    # 2. 유니코드 정규화 및 유령 문자 제거
    content = unicodedata.normalize('NFC', content)
    for char in ["\u200b", "\u200c", "\u200d", "\ufeff", "\xa0"]:
        content = content.replace(char, " ")

    # 3. 파편화된 구두점 및 의미 없는 반복 기호 정리
    # . , . . , 처럼 반복되는 기호를 하나로 합치거나 제거합니다.
    content = re.sub(r'\.+', '.', content)      # 연속된 마침표 -> 하나로
    content = re.sub(r',+', ',', content)      # 연속된 콤마 -> 하나로
    content = re.sub(r'\s*([.,])\s*', r'\1 ', content) # 기호 앞 공백 제거, 뒤 공백 추가
    
    # 4. 표 형식(파이프) 데이터 처리
    content = content.replace("|", " / ")
    
    # 4. URL 및 HTML 태그 제거
    # "<a href=...>" 또는 "http://..." 형태를 제거합니다.
    content = re.sub(r'<a\s+[^>]*>', '', content) # <a> 태그 시작
    content = re.sub(r'</a>', '', content)       # </a> 태그 끝
    content = re.sub(r'https?://\S+', '', content) # URL
    content = re.sub(r'www\.\S+', '', content)    # www 주소
    
    # 5. 이미지 파일명 제거 (Raw string 사용)
    content = re.sub(r'\S+\.(jpg|png|jpeg|gif|bmp)', '', content, flags=re.IGNORECASE)
    content = re.sub(r'http\S+', '', content)
    
    # 숫자+원 뒤에 구분자(,) 삽입 (Raw string 사용)
    content = re.sub(r'(\d[,0-9]*원)(?!\s*,)', r'\1, ', content)

    # 불필요한 특수문자 제거 (안전한 패턴)
    content = re.sub(r'[#*@_>]', ' ', content)
    for char in ["\u200b", "\u200c", "\u200d", "\ufeff", "\xa0"]:
        content = content.replace(char, " ")

    noise = [
        "URL 복사", "이웃추가", "공유하기", "스마트에디터", "본문 바로가기",
        "smartEditorVersion", "logNo", "nicknameOrBlogId"
    ]
    for n in noise:
        content = content.replace(n, "")

    # 이모지 제거
    # content = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]', '', content)
    
    # 중략 (나머지 로직은 동일)
    content = re.sub(r'\s+', ' ', content)
    result = f"[{title}] {content.strip()}"
    return result
    

def search_place_reviews(item: dict) -> str:
    """Search for reviews and keep only place-relevant realtime context."""
    title = item.get("title", "")
    address = item.get("addr", "") or f"{item.get('addr1', '')} {item.get('addr2', '')}".strip()
    category_name = str(item.get("contenttypeid", "")).strip()
    category_tokens = CATEGORY_HINTS.get(category_name, [])

    title_tokens = _tokenize(title)
    addr_tokens = _tokenize(address)

    query = f"{address} {title} 분위기 리뷰 후기 특징 방문목적 반려동물 동반 규모"
    try:
        search_result = tavily.search(
            query=query, 
            search_depth="advanced", 
            max_results=5,
            include_domains=WEB_URL_HINTS
        )

        filtered = []
        for result in search_result.get("results", []):
            content = _build_context_from_tavily_result(result)
            result['content'] = content
            score = _score_tavily_result(result, title, title_tokens, addr_tokens, category_tokens)
            if score < 4.0:
                continue
            filtered.append({
                "url": result.get("url", ""),
                "content": content,
                "score": score,
            })

        if not filtered:
            return ""

        filtered.sort(key=lambda x: x["score"], reverse=True)
        context = ""
        for result in filtered[:3]:
            print(f'\n\n[Tavily] Search filtered for {title} ({result["score"]}) : \n{result["content"]}')
            context += f"{result['content']}\n\n"
        return context
    except Exception as e:
        print(f"[ERROR] Search failed for {title}: {e}")
        return ""

def general_emotional_description(item: dict) -> str:
    item = item.copy()
    """Generate emotional description for a place."""

    GENERAL_EMOTIONAL_PROMPT = """
    당신은 장소의 매력과 특징을 데이터 기반으로 분석하여 검색 최적화된 설명을 작성하는 전문가입니다.
    이 설명은 VectorDB(Qdrant)에 저장되어 사용자의 여행 관련 질문에 대한 검색 결과로 활용됩니다.

    **[핵심 규칙: 데이터 완전성]**
    입력으로 제공되는 **[장소 정보] JSON 데이터의 모든 필드(Key와 Value)를 반드시 분석**하여 결과물에 빠짐없이 포함해야 합니다. 
    단순 나열이 아닌, 설명문의 문맥 속에 자연스럽게 녹여내어 정보와 감성이 조화를 이루게 하세요.

    작성 가이드:
    1. **장소 정보 완전 반영**: 주소(addr), 전화번호(infocenter), 주차(parking), 이용시간(usetime), 휴무일(restdate) 등 모든 기술적 정보를 문장으로 풀어내어 필수적으로 포함하세요. (예: "parking: 가능" -> "주차가 편리하여 차량 방문이 용이하며", "restdate: 월요일" -> "매주 월요일은 휴무이니 방문에 참고하세요")
    2. **공간의 본질과 분위기**: 장소의 목적과 특징을 반영해 "따뜻한 채광이 드는 조용한 카페", "힙한 감성의 인더스트리얼 인테리어" 등 매력적인 문장으로 시작하세요.
    3. **실시간 맥락 통합**: [실시간 맥락] 데이터에서 장소와 관련된 최신 리뷰 정보, 현장 분위기 등을 과장 없이 반영하세요.
    4. **검색 최적화(SEO)**: 사용자가 검색할 법한 방문 목적(데이트, 아이와 함께, 작업, 휴식)과 분위기 키워드(가성비, 럭셔리, 인생샷, 조용한 등)를 풍부하게 사용하세요.
    5. **형식 및 제약**: 
       - "이곳은~", "저곳은~" 같은 진부한 시작은 지양하고 바로 특징을 설명하세요.
       - 결과는 오직 설명 문장만 출력하세요. (URL, Source, JSON 키 이름 등 메타 정보 출력 금지)
       - [장소 정보]에 있는 데이터가 하나라도 누락되면 안 됩니다.
    """

    emo_desc = item.pop("emotional_description", "")

    result = next(ingest_data([item]))
    json_str = json.dumps(result, ensure_ascii=False, indent=2)

    prompt = ChatPromptTemplate.from_messages([
        ("system", GENERAL_EMOTIONAL_PROMPT),
        ("human", "아래 데이터를 바탕으로 검색에 최적화된 정서적 설명을 작성해줘:\n\n장소 정보: {place_data}\n\n실시간 맥락: {realtime_tavily_data}")
    ])

    response = LLMFactory.get_llm().invoke(prompt.format_messages(place_data=json_str, realtime_tavily_data=emo_desc))
    description = response.content
    print(f"===================[INFO] {item.get('title')}===================")
    print(f"장소 정보: \n{json_str}\n 생성된 설명: \n{description}")
    print("===================[INFO] 끝===================")
    return description


def enrich_data_file(input_path: str, output_path: str, limit: int = None):
    """Enrich a JSONL file with emotional context."""
    print(f"[INFO] Enriching {input_path} -> {output_path}")
    
    enriched_data = []
    with open(input_path, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]
    
    # Process only a subset for demonstration/testing if needed, or all
    count = 0
    for item in data:
        if limit is not None and count >= limit:
            break

        title = item.get("title", "")
        
        print(f"[PROCESS] ({count+1}/{len(data)}) Enriching: {title}")
        
        # 1. Search
        context = search_place_reviews(item)
        
        # 2. Add to item
        item["emotional_description"] = context
        enriched_data.append(item)
        
        count += 1
        # Avoid rate limits
        time.sleep(1)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in enriched_data:
            llm_item = general_emotional_description(item)
            item['llm_text'] = llm_item
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"[DONE] Enrichment complete. Saved to {output_path}")


def enrich_data_all():
    TEST_MODE = True
    
    # Example usage for one file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(base_dir) # backend
    data_dir = os.path.join(root_dir, "data")
    
    if not os.path.exists(data_dir):
        print(f"[ERROR] Date file not found: {data_dir}")

    file_names = []
    file_data = []
        
    for filename in os.listdir(data_dir):
        if filename.endswith(".jsonl") and not filename.startswith("25_"):
            input_file = os.path.join(data_dir, filename)
            output_file = os.path.join(data_dir, "emotional", filename.replace(".jsonl", "_enriched.jsonl"))

            enrich_data_file(input_file, output_file, limit=2 if TEST_MODE else None)


# docker exec -it skn21-final-2team-backend-1 python -m app.scripts.enrich_data
if __name__ == "__main__":
    enrich_data_all()

    # base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # root_dir = os.path.dirname(base_dir) # backend
    # emotional_dir = os.path.join(root_dir, "data", "emotional")
    
    # if not os.path.exists(emotional_dir):
    #     print(f"[ERROR] Date file not found: {emotional_dir}")

    # file_data = []
        
    # output_file = os.path.join(emotional_dir, "final.json")

    # for filename in os.listdir(emotional_dir):
    #     if filename.endswith(".jsonl") and not filename.startswith("25_"):
    #         input_file = os.path.join(emotional_dir, filename)

    #         with open(input_file, 'r', encoding='utf-8') as rf:
    #             data = [json.loads(line) for line in rf]
    #             for item in data:
    #                 category = item.get("contenttypeid", "")
    #                 title = item.get("title", "")   
    #                 emotional_description = item.get("emotional_description", "")
    #                 llm_text = item.get("llm_text", "")
                    
    #                 file_data.append({'category': category, 'title': title, 'emotional_description': emotional_description, 'llm_text': llm_text})


    # with open(output_file, 'w', encoding='utf-8') as wf:
    #     json.dump(file_data, wf, ensure_ascii=False, indent=4)

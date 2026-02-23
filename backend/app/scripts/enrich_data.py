import os
import json
import time
from typing import List, Dict
from tavily import TavilyClient
from openai import OpenAI
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import LLM_MODEL
from app.utils.llm_factory import LLMFactory
from app.scripts.preprocess_data import ingest_data

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def search_place_reviews(title: str, address: str) -> str:
    """Search for reviews and atmosphere of a place."""
    query = f"{address} {title} 분위기 리뷰 후기 방문 목적 반려동물 동반 강아지 동반 장소 특징 규모 K-Pop K-drama"
    try:
        search_result = tavily.search(query=query, search_depth="advanced", max_results=3)
        context = ""
        for result in search_result.get("results", []):
            context += f"Source: {result.get('url')}\nContent: {result.get('content')}\n\n"
        return context
    except Exception as e:
        print(f"[ERROR] Search failed for {title}: {e}")
        return ""

def general_emotional_description(item: dict) -> str:
    """Generate emotional description for a place."""

    GENERAL_EMOTIONAL_PROMPT = """
    당신은 장소의 매력과 특징을 데이터 기반으로 분석하여 검색 최적화된 설명을 작성하는 전문가입니다.
    이 설명은 VectorDB(Qdrant)에 저장되어 사용자의 여행 관련 질문에 대한 검색 결과로 활용됩니다.

    작성 목표:
    제공된 [데이터]를 바탕으로 사용자가 검색창에 입력할 법한 자연스러운 문구와 핵심 키워드를 조합하여, 의미론적(Semantic) 검색에 유리한 설명을 작성하세요.

    작성 가이드:
    1. **공간의 본질과 분위기**: "따뜻한 채광이 드는 조용한 카페", "힙한 감성의 인더스트리얼 인테리어" 등 장소의 핵심 성격을 담은 자연스러운 문장으로 작성하세요.
    2. **사용자 의도 반영**: 방문 목적(데이트, 가족 즐길거리, 작업 공간, 휴식처)과 연관된 실질적인 표현을 포함하세요.
    3. **검색어 매칭 키워드**: 가성비, 럭셔리, 반려견 동반, 아이와 함께, 인생샷, 조용한, 활기찬 등 검색에 유리한 명사 위주의 형용사를 풍부하게 사용하세요.
    4. **형식**: 정제된 2~3문장의 서술형으로 작성하세요. "이곳은~"과 같은 진부한 표현은 지양하고 바로 특징을 설명하세요.
    """

    # Fix: ingest_data expects an iterable (list of dicts)
    result = next(ingest_data([item]))
    
    formatted_data = ""
    for key, value in result.items():
        formatted_data += f"{key}: {value}\n"
    
    formatted_data += f"실시간 검색 및 리뷰 내용: {item.get('emotional_description', '')}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", GENERAL_EMOTIONAL_PROMPT),
        ("human", "아래 데이터를 바탕으로 검색에 최적화된 정서적 설명을 작성해줘:\n\n{data}")
    ])

    # Invoke LLM
    response = LLMFactory.get_llm().invoke(prompt.format_messages(data=formatted_data))
    description = response.content.strip()
    print(f"[INFO] {item.get('title')} output: {description}")
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
        address = item.get("addr1", "") + " " + item.get("addr2", "")
        
        print(f"[PROCESS] ({count+1}/{len(data)}) Enriching: {title}")
        
        # 1. Search
        context = search_place_reviews(title, address)
        
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


if __name__ == "__main__":
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
            output_file = os.path.join(data_dir, filename.replace(".jsonl", "_enriched.jsonl"))

            enrich_data_file(input_file, output_file, limit=10 if TEST_MODE else None)
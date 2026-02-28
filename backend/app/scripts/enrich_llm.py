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
    2. **형식 및 제약**: 
       - "이곳은~", "저곳은~" 같은 진부한 시작은 지양하고 바로 특징을 설명하세요.
       - 결과는 오직 설명 문장만 출력하세요. (URL, Source, JSON 키 이름 등 메타 정보 출력 금지)
       - [장소 정보]에 있는 데이터가 하나라도 누락되면 안 됩니다.
    """

    result = next(ingest_data([item]))
    json_str = json.dumps(result, ensure_ascii=False, indent=2)

    prompt = ChatPromptTemplate.from_messages([
        ("system", GENERAL_EMOTIONAL_PROMPT),
        ("human", "아래 데이터를 바탕으로 검색에 최적화된 정서적 설명을 작성해줘:\n\n장소 정보: {place_data}")
    ])

    response = LLMFactory.get_llm().invoke(prompt.format_messages(place_data=json_str))
    description = response.content
    print(f"===================[INFO] {item.get('title')}===================")
    print(f"장소 정보: \n{json_str}\n 생성된 설명: \n{description}")
    print("===================[INFO] 끝===================")
    return description


def enrich_data_file(input_path: str, output_path: str, limit: int = None):
    """Enrich a JSONL file with emotional context with checkpointing."""
    print(f"[INFO] Enriching {input_path} -> {output_path}")
    
    # 1. Load existing processed IDs for checkpointing
    processed_ids = set()
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line)
                    if "contentid" in item:
                        processed_ids.add(str(item["contentid"]))
                except json.JSONDecodeError:
                    continue
    
    print(f"[INFO] Found {len(processed_ids)} already enriched items. Skipping them.")

    # 2. Read input data
    with open(input_path, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]
    
    # 3. Process each item (append mode for real-time saving)
    count = 0
    actual_processed = 0
    
    with open(output_path, 'a', encoding='utf-8') as out_f:
        for item in data:
            if limit is not None and actual_processed >= limit:
                break
                
            contentid = str(item.get("contentid", ""))
            if contentid in processed_ids:
                count += 1
                continue

            title = item.get("title", "")
            print(f"[PROCESS] ({count+1}/{len(data)}) Enriching: {title} (ID: {contentid})")
            
            try:
                # LLM Description Generation
                llm_item = general_emotional_description(item)
                item['llm_text'] = llm_item
                
                # Write immediately to file
                out_f.write(json.dumps(item, ensure_ascii=False) + "\n")
                out_f.flush() # Ensure it's written to disk
                
                actual_processed += 1
            except Exception as e:
                print(f"[ERROR] Failed to enrich {title}: {e}")
                # Optional: break or continue depending on crash severity
            
            count += 1
            # Control rate limit if needed
            time.sleep(1)
            
    print(f"[DONE] Enrichment complete. Total processed: {actual_processed}. Saved to {output_path}")


def enrich_data_all():
    TEST_MODE = False
    
    # Example usage for one file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(base_dir) # backend
    data_dir = os.path.join(root_dir, "data")
    
    if not os.path.exists(data_dir):
        print(f"[ERROR] Date file not found: {data_dir}")

    for filename in os.listdir(data_dir):
        if filename.endswith(".jsonl") and not filename.startswith("25_"):
            input_file = os.path.join(data_dir, filename)
            output_file = os.path.join(data_dir, "llm_result", filename.replace(".jsonl", "_enriched.jsonl"))

            enrich_data_file(input_file, output_file, limit=2 if TEST_MODE else None)


# docker exec -it skn21-final-2team-backend-1 python -m app.scripts.enrich_llm
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

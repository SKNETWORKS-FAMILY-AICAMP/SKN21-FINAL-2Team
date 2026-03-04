"""
Ragas TestsetGenerator를 활용한 RAG 평가용 합성 테스트 데이터셋 자동 생성 스크립트.

Qdrant places 컬렉션의 문서를 기반으로 TestsetGenerator가 다양한 유형의
질문-답변 쌍을 자동 생성합니다.

사용법:
    docker compose run --rm backend python evaluation/create_dataset.py --num-samples 20 --limit 200
"""

import os
import sys
import json
import random
import argparse
import asyncio
import pandas as pd
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ── 경로 설정 ──────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent
RESULT_DIR = EVAL_DIR / "result"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

# 로컬 실행을 위한 환경 변수 오버라이드
os.environ["MYSQL_HOST"] = os.getenv("MYSQL_HOST", "localhost")
os.environ["MYSQL_PORT"] = os.getenv("MYSQL_PORT", "3306")
os.environ["QDRANT_HOST"] = os.getenv("QDRANT_HOST", "localhost")
os.environ["QDRANT_PORT"] = os.getenv("QDRANT_PORT", "6333")

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document
from qdrant_client import QdrantClient

from ragas import EvaluationDataset, evaluate
from ragas.testset import TestsetGenerator
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import LLMContextRecall, LLMContextPrecisionWithReference, Faithfulness, AnswerRelevancy

from app.agents.graph import workflow
from app.utils.config import LLM_MODEL, TEXT_MODEL, PLACES_COLLECTION
from app.scripts.preprocess_data import ingest_data

# ── EXECUTOR_PROMPT 참고 llm_text 생성 프롬프트 ────────────────────────────
# app/services/prompts.py의 EXECUTOR_PROMPT 스타일을 따르는 문서 설명 생성 프롬프트
DOCUMENT_DESCRIPTION_PROMPT = """\
당신은 한국 여행 추천 에이전트입니다.
아래 Context Information을 바탕으로, 이 장소를 추천하는 서술형 설명을 작성하세요.

# 중요 규칙
1. Context Information을 최우선 사용하고, 추측은 최소화하세요.
2. 답변은 불렛포인트 형식이 아닌, 편안한 대화체와 서술형 문장으로 작성하세요.
   - 장소의 분위기와 특징을 생생하게 설명하고, 왜 추천하는지 자연스럽게 전달하세요.
3. 한국어 존댓말로 작성하고, 친절하고 전문적인 가이드 느낌을 유지하세요.
4. 장소의 위치, 카테고리, 이용시간, 휴무일 등 실용 정보를 포함하세요.

# Context Information
{context_block}
"""


# ── JSONL 파일에서 문서 로드 ──────────────────────────────────────────────
def load_documents_from_jsonl(
    source_dir: str = "data/llm_result",
    limit: int = 200,
    seed: int = 42,
) -> list[Document]:
    """
    data/llm_result/*.jsonl 파일에서 llm_text를 포함한 Document를 직접 로드합니다.

    Qdrant에는 llm_text가 저장되지 않으므로(qdrant_setup.py에서 pop),
    원본 jsonl 파일에서 풍부한 텍스트를 가져옵니다.
    """
    source_path = ROOT_DIR / source_dir
    files = sorted(source_path.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(f"jsonl 파일을 찾을 수 없습니다: {source_path}")

    print(f"[INFO] JSONL 소스 디렉토리: {source_path}")
    print(f"[INFO] 발견된 jsonl 파일 수: {len(files)}")

    all_items = []
    for file_path in files:
        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                title = (item.get("title") or "").strip()
                llm_text = (item.get("llm_text") or "").strip()
                if title and llm_text:
                    all_items.append(item)

    if not all_items:
        raise ValueError("유효한 레코드가 없습니다. jsonl 파일을 확인하세요.")

    print(f"[INFO] 전체 유효 레코드 수: {len(all_items)}")

    # 랜덤 샘플링
    rng = random.Random(seed)
    if len(all_items) > limit:
        all_items = rng.sample(all_items, limit)

    documents = []
    for data in ingest_data(all_items):
        llm_text = data.pop('llm_text', '')
        doc = Document(
            page_content=llm_text,
            metadata=data,
        )
        documents.append(doc)

    print(f"[INFO] 총 {len(documents)}개 Document 생성 완료")
    return documents


# ── TestsetGenerator 생성 ─────────────────────────────────────────────────
def create_testset_generator() -> TestsetGenerator:
    """
    Ragas TestsetGenerator 인스턴스를 생성합니다.

    - LLM: config.py의 LLM_MODEL (gpt-4o-mini)
    - 임베딩: config.py의 TEXT_MODEL (BAAI/bge-m3)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

    # NOTE: TEXT_MODEL(BAAI/bge-m3)은 HuggingFace 로컬 모델이라 OpenAI API에서 사용 불가.
    #       TestsetGenerator는 OpenAI API를 호출하므로 OpenAI 임베딩 모델을 사용.
    EVAL_EMBEDDING_MODEL = "text-embedding-3-small"

    print(f"[INFO] LLM 모델: {LLM_MODEL}")
    print(f"[INFO] 임베딩 모델: {EVAL_EMBEDDING_MODEL} (TestsetGenerator용)")

    llm = LangchainLLMWrapper(ChatOpenAI(model=LLM_MODEL))
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model=EVAL_EMBEDDING_MODEL))

    generator = TestsetGenerator(
        llm=llm, 
        embedding_model=embeddings,
        llm_context=DOCUMENT_DESCRIPTION_PROMPT,
        )

    print("[INFO] TestsetGenerator 생성 완료")
    return generator


async def _invoke_graph(question: str):
    """실제 RAG 시스템을 통해 답변과 컨텍스트 추출"""
    try:
        print(f"  [DEBUG] Workflow generating for: {question}")
        graph = workflow().compile()

        # 초기 상태 설정
        inputs = {
            "user_input": question,
            "user_id": 1, # 샘플 유저 ID (기본 데이터가 있다고 가정)
            "room_id": 1,
            "messages": []
        }

        # 그래프 실행
        print("  [DEBUG] Invoking graph...")
        result = await graph.ainvoke(inputs)
        print("  [DEBUG] Graph invocation completed.")
        
        answer = result.get("answer", "")
        # candidates 정보를 context 리스트로 변환
        candidates = result.get("candidates", [])
        contexts = []
        for c in candidates:
            payload = c.get("payload") if isinstance(c, dict) else {}
            if not isinstance(payload, dict):
                payload = {}

            # payload = ingest_data(payload)
            name = (
                payload.get("title")
                or payload.get("name")
                or c.get("title")
                or c.get("name")
                or "이름 없음"
            )
            category = payload.get("contenttypeid") or payload.get("contenttypeid_code") or ""
            addr = payload.get("addr") or payload.get("address") or ""

            # description이 없으면 llm_text를 우선 사용
            desc = (
                payload.get("description")
                or payload.get("llm_text")
                or c.get("description")
                or ""
            )
            usetime = payload.get("usetime") or ""
            restdate = payload.get("restdate") or ""

            context = (
                f"이름:{name} | 분류:{category} | 주소:{addr} | 이용시간:{usetime} | 휴무:{restdate} | 설명:{desc}"
            )
            contexts.append(context)
        
        return answer, contexts
    except Exception as e:
        # 제한 환경(의존성/DB/Qdrant 미구성)에서도 평가 파이프라인 자체는 실행 가능하도록 fallback
        print(f"  [WARN] Graph execution failed: {e}")
        return f"질문: {question}\n현재 환경 제약으로 에이전트 워크플로우를 실행하지 못했습니다.", [question]


def eval_ragas(path: Path):
    import ast
    print("Start EVAL!")
    eval_df = pd.read_csv(path)

    # CSV에서 읽으면 list가 문자열로 변환되므로 다시 파싱
    eval_df["retrieved_contexts"] = eval_df["retrieved_contexts"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )

    # from_xxxx() xxxx 타입의 객체를 EvaluationDataset객체로 변환.
    eval_dataset = EvaluationDataset.from_pandas(
        eval_df[["user_input", "retrieved_contexts", "response", "reference"]]
    )

    eval_llm = LangchainLLMWrapper(ChatOpenAI(model=LLM_MODEL))
    eval_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))

    # 평가할 함수들을 List로 묶어준다.
    metrics = [
        LLMContextRecall(llm=eval_llm),
        LLMContextPrecisionWithReference(llm=eval_llm),
        Faithfulness(llm=eval_llm),
        AnswerRelevancy(llm=eval_llm, embeddings=eval_embeddings)
    ]

    # Run Evaluation
    eval_results = evaluate(dataset=eval_dataset, metrics=metrics)

    # Convert to Pandas DataFrame for easier viewing
    df_results = eval_results.to_pandas()
    print(df_results.head(10))

    print("\n📊 Evaluation Results:")
    print(eval_results)


# ── 메인 파이프라인 ──────────────────────────────────────────────────────
def generate_dataset(
    num_samples: int = 20,
    limit: int = 200,
    output: Path = Path("rag_eval_data_synthetic.json"),
    seed: int = 42,
    source: str = "data/llm_result",
) -> list[dict]:
    """
    TestsetGenerator를 사용하여 합성 테스트 데이터셋을 생성합니다.

    Args:
        num_samples: 생성할 테스트 샘플 수
        limit: 소스에서 가져올 문서 수
        output: 출력 파일 경로
        seed: 재현성을 위한 시드 값
        source: 문서 소스 ('qdrant' 또는 jsonl 디렉토리 경로, 기본: 'data/llm_result')

    Returns:
        생성된 테스트 데이터 리스트
    """
    print("=" * 60)
    print("  Ragas TestsetGenerator 기반 합성 데이터셋 생성")
    print("=" * 60)

    # 1. 문서 로드 (jsonl 기본, qdrant 옵션)
    print(f"\n[Step 1/4] 문서 로드... (소스: {source})")
    documents = load_documents_from_jsonl(source_dir=source, limit=limit, seed=seed)
    if not documents:
        raise ValueError("변환된 Document가 없습니다. 소스 데이터를 확인하세요.")

    # 2. TestsetGenerator 초기화
    print("\n[Step 2/4] TestsetGenerator 초기화...")
    generator = create_testset_generator()

    # 3. 테스트셋 생성
    print(f"\n[Step 3/4] {num_samples}개 합성 테스트 데이터 생성 중...")
    print(f"  - 소스 문서 수: {len(documents)}")
    print(f"  - 요청 샘플 수: {num_samples}")

    testset = generator.generate_with_langchain_docs(
        documents=documents,
        testset_size=num_samples,
    )

    eval_df = testset.to_pandas()
    print(eval_df.head())

    # >>>> RAG 파이프라인으로 응답 생성
    response_list = []
    retrieved_context_list = []

    for user_input in eval_df['user_input']:
        print(f"  [RAG] 질의: {user_input[:60]}...")
        answer, contexts = asyncio.run(_invoke_graph(user_input))
        response_list.append(answer)
        retrieved_context_list.append(contexts)

    # >>>> eval_df에 응답과 context 추가
    eval_df['response'] = response_list
    eval_df['retrieved_contexts'] = retrieved_context_list
    print(eval_df.head())

    # eval_df 파일 저장
    eval_df.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"[Step 4/4] 테스트셋 생성 완료: {output}")

    eval_ragas(output)


if __name__ == "__main__":
    output = Path("rag_eval_data_synthetic.json")
    if not output.is_absolute():
        output = EVAL_DIR / output
    output.parent.mkdir(parents=True, exist_ok=True)


    # generate_dataset(
    #     num_samples=20,
    #     limit=200,
    #     output=output,
    #     seed=42,
    #     source="data/llm_result",
    # )

    eval_ragas(output)

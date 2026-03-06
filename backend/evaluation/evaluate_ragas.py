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
from app.utils.config import LLM_MODEL, TEXT_MODEL, PLACES_COLLECTION, get_retrieval_params
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


# context에서 제외할 키 (좌표/이미지 등 LLM/평가에 불필요한 대용량 필드)
_EXCLUDE_KEYS = {"image", "image_urls", "mapx", "mapy", "map_url"}


def _payload_to_context(candidates: list[dict]) -> list[str]:
    """candidates의 payload를 빈값/불필요 키 제거 후 JSON string context 리스트로 변환"""
    contexts = []
    for i, c in enumerate(candidates, 1):
        payload = c.get("payload") if isinstance(c, dict) else {}
        if not isinstance(payload, dict):
            payload = {}
        filtered = {
            k: v for k, v in payload.items()
            if k not in _EXCLUDE_KEYS and v not in (None, "", [], {})
        }
        payload_str = json.dumps(filtered, ensure_ascii=False)
        contexts.append(f"{i}. {payload_str}")
    return contexts


def _infer_relevant_ids(reference: str, reference_contexts: list, candidates: list[dict]) -> list[str]:
    """reference 내 장소명이 candidates에 포함되면 relevant_id로 추정"""
    import re
    if not candidates:
        return []
    corpus_parts = [str(reference or "")]
    corpus_parts.extend([str(x) for x in (reference_contexts or [])])
    corpus = re.sub(r"\s+", "", " ".join(corpus_parts)).lower()

    relevant = []
    for c in candidates:
        payload = c.get("payload", {}) if isinstance(c, dict) else {}
        title = str(payload.get("title") or "")
        title_key = re.sub(r"\s+", "", title).lower()
        if title_key and title_key in corpus:
            cid = str(payload.get("contentid") or c.get("id") or "").strip()
            if cid and cid not in relevant:
                relevant.append(cid)
    return relevant


async def _invoke_graph(
    question: str,
    candidate_k: int,
    final_k: int,
    rerank_max_k: int,
):
    """
    실제 RAG 시스템을 통해 답변, 컨텍스트, candidates, selected_ids를 추출.
    evaluate_prepare_enriched.py 없이 enriched 데이터를 한 번에 생성하기 위해
    그래프 결과의 모든 필요 정보를 반환합니다.
    """
    try:
        print(f"  [DEBUG] Workflow generating for: {question}")
        graph = workflow().compile()

        inputs = {
            "user_input": question,
            "user_id": 1,
            "room_id": 1,
            "messages": [],
            "candidate_k": candidate_k,
            "final_k": final_k,
            "rerank_max_k": rerank_max_k,
        }

        print("  [DEBUG] Invoking graph...")
        result = await graph.ainvoke(inputs)
        print("  [DEBUG] Graph invocation completed.")

        answer = result.get("answer", "")
        candidates = result.get("candidates", [])
        selected_ids = result.get("selected_ids", [])
        contexts = _payload_to_context(candidates)

        return answer, contexts, candidates, selected_ids
    except Exception as e:
        print(f"  [WARN] Graph execution failed: {e}")
        return (
            f"질문: {question}\n현재 환경 제약으로 에이전트 워크플로우를 실행하지 못했습니다.",
            [question],
            [],
            [],
        )


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
    output: Path = Path("evaluate_testdata.csv"),
    seed: int = 42,
    source: str = "data/llm_result",
    retriever_candidate_k: int = 60,
    retriever_top_k: int = 10,
    retriever_rerank_max_k: int = 30,
) -> None:
    """
    TestsetGenerator로 합성 데이터셋 생성 + RAG 파이프라인 실행 +
    enriched 컬럼(retrieved_candidates, selected_ids, relevant_ids) 포함하여
    evaluate_testdata.csv에 저장합니다.

    evaluate_prepare_enriched.py 없이 한 번에 완성된 평가 데이터를 만듭니다.
    """
    print("=" * 60)
    print("  Ragas TestsetGenerator 기반 Enriched 데이터셋 생성")
    print("=" * 60)

    # 1. 문서 로드
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

    # 4. RAG 파이프라인 실행 → enriched 컬럼 생성
    print(f"\n[Step 4/4] RAG 파이프라인 실행 + enriched 데이터 생성...")
    response_list = []
    retrieved_context_list = []
    retrieved_candidates_list = []
    selected_ids_list = []
    relevant_ids_list = []

    for idx, row in eval_df.iterrows():
        user_input = row['user_input']
        reference = str(row.get('reference', '') or '')
        reference_contexts = row.get('reference_contexts', []) or []

        print(f"  [{idx+1}/{len(eval_df)}] 질의: {user_input[:60]}...")
        answer, contexts, candidates, selected_ids = asyncio.run(
            _invoke_graph(
                user_input,
                candidate_k=max(int(retriever_candidate_k), 1),
                final_k=max(int(retriever_top_k), 1),
                rerank_max_k=max(int(retriever_rerank_max_k), 1),
            )
        )

        # relevant_ids: reference에 포함된 장소명 기반 추정
        relevant_ids = _infer_relevant_ids(reference, reference_contexts, candidates)

        response_list.append(answer)
        retrieved_context_list.append(contexts)
        # candidates를 JSON serializable하게 정리
        retrieved_candidates_list.append(json.dumps(candidates, ensure_ascii=False, default=str))
        selected_ids_list.append(json.dumps(selected_ids, ensure_ascii=False))
        relevant_ids_list.append(json.dumps(relevant_ids, ensure_ascii=False))

    # eval_df에 모든 컬럼 추가
    eval_df['response'] = response_list
    eval_df['retrieved_contexts'] = retrieved_context_list
    eval_df['retrieved_candidates'] = retrieved_candidates_list
    eval_df['selected_ids'] = selected_ids_list
    eval_df['relevant_ids'] = relevant_ids_list

    # 컬럼명 통일 (question 컬럼 추가)
    if 'question' not in eval_df.columns and 'user_input' in eval_df.columns:
        eval_df['question'] = eval_df['user_input']

    print(eval_df.head())
    print(f"\n[컬럼 목록] {list(eval_df.columns)}")

    # CSV 저장
    eval_df.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"\n✅ Enriched 데이터셋 저장 완료: {output}")
    print(f"   - 샘플 수: {len(eval_df)}")
    print(f"   - evaluate_all.py --input-csv {output} 로 바로 평가 가능")


if __name__ == "__main__":
    eval_defaults = get_retrieval_params("evaluation")
    parser = argparse.ArgumentParser(description="RAGAS 평가용 enriched 데이터 생성")
    parser.add_argument("--num-samples", type=int, default=20)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", default="evaluate_testdata.csv")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--source", default="data/llm_result")
    parser.add_argument("--retriever-candidate-k", type=int, default=eval_defaults["candidate_k"])
    parser.add_argument("--retriever-top-k", type=int, default=eval_defaults["top_k"])
    parser.add_argument("--retriever-rerank-max-k", type=int, default=eval_defaults["rerank_max_k"])
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = EVAL_DIR / output
    output.parent.mkdir(parents=True, exist_ok=True)

    generate_dataset(
        num_samples=args.num_samples,
        limit=args.limit,
        output=output,
        seed=args.seed,
        source=args.source,
        retriever_candidate_k=args.retriever_candidate_k,
        retriever_top_k=args.retriever_top_k,
        retriever_rerank_max_k=args.retriever_rerank_max_k,
    )

    # eval_ragas(output)

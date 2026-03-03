import os
import asyncio
import json
import argparse
import random
import sys
import re
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

# 로컬 실행을 위한 환경 변수 오버라이드 (임포트 전에 반드시 수행!)
os.environ["MYSQL_HOST"] = os.getenv("MYSQL_HOST")
os.environ["MYSQL_PORT"] = os.getenv("MYSQL_PORT")
os.environ["QDRANT_HOST"] = os.getenv("QDRANT_HOST")
os.environ["QDRANT_PORT"] = os.getenv("QDRANT_PORT")

import pandas as pd
from datasets import Dataset


def _resolve_eval_path(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (EVAL_DIR / p)


def _save_summary_files(mode: str, summary: dict):
    txt_path = EVAL_DIR / f"evaluation_{mode}_summary.txt"
    json_path = EVAL_DIR / f"evaluation_{mode}_summary.json"

    lines = ["--- Summary ---"]
    for k, v in summary.items():
        if isinstance(v, float):
            lines.append(f"{k}: {v:.4f}")
        else:
            lines.append(f"{k}: {v}")
    content = "\n".join(lines)

    with txt_path.open("w", encoding="utf-8") as f:
        f.write(content + "\n")
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Summary saved to {txt_path}")
    print(f"Summary saved to {json_path}")

def _load_test_data(data_file: str = "rag_eval_data.json", limit: Optional[int] = None):
    data_path = _resolve_eval_path(data_file)
    if not data_path.exists():
        raise FileNotFoundError(f"Test data file not found: {data_path}")
    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if limit is not None and limit > 0:
        data = data[:limit]
    return data


def _extract_gold_title(ground_truth: str) -> str:
    if not ground_truth:
        return ""
    # "<title> (<addr>) - <desc>" 형식에서 title 추출
    left = ground_truth.split(" - ", 1)[0].strip()
    title = left.split(" (", 1)[0].strip()
    return title


def _extract_gold_location(question: str) -> str:
    if not question:
        return ""
    m = re.search(r"(서울특별시\s+[가-힣]+구)", question)
    return m.group(1) if m else ""


def _extract_gold_category(question: str) -> str:
    if not question:
        return ""
    categories = ["관광지", "문화시설", "축제공연행사", "레포츠", "숙박", "음식점"]
    for c in categories:
        if c in question:
            return c
    return ""


async def _invoke_graph(question: str):
    from app.agents.graph import workflow

    graph = workflow().compile()
    inputs = {
        "user_input": question,
        "user_id": 1,
        "room_id": 1,
        "messages": [],
    }
    return await graph.ainvoke(inputs)


def _to_slot_dict(slots):
    if not slots:
        return {}
    if hasattr(slots, "model_dump"):
        return slots.model_dump()
    if hasattr(slots, "dict"):
        return slots.dict()
    if isinstance(slots, dict):
        return slots
    return {}

def generate_test_data_from_llm_results(
    source_dir: str = "data/llm_result",
    output_file: str = "rag_eval_data.json",
    sample_size: int = 20,
    seed: int = 42,
):
    """
    llm_result 폴더 내 jsonl 파일을 읽어 RAGAS 평가용 테스트 데이터(question/ground_truth)를 생성한다.
    """
    source_path = Path(source_dir)
    files = sorted(source_path.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No jsonl files found in {source_dir}")

    rng = random.Random(seed)
    records = []
    companion_opts = ["혼자", "친구와", "연인과", "부모님과", "아이와"]
    time_opts = ["평일 저녁", "주말 오전", "주말 오후", "비 오는 날", "늦은 밤"]
    purpose_opts = ["사진 찍기 좋은", "조용히 쉬기 좋은", "가성비 좋은", "분위기 좋은", "동선이 편한"]
    budget_opts = ["예산은 넉넉해", "예산은 보통이야", "예산은 아끼고 싶어"]
    transport_opts = ["대중교통으로 이동할 거야", "차로 이동할 거야", "도보 이동이 편하면 좋겠어"]
    constraint_opts = [
        "너무 붐비는 곳은 피하고 싶어",
        "초행자도 찾기 쉬운 곳이면 좋겠어",
        "너무 시끄럽지 않았으면 좋겠어",
        "1~2곳만 간단히 추천해줘",
    ]

    type_templates = {
        "관광지": [
            "{district}에서 {companion} 갈 만한 관광지 추천해줘. {time} 기준으로 {constraint}.",
            "{district} 기준으로 {purpose} 관광지 알려줘. {transport}, {budget}.",
            "{district}에서 '{title}' 느낌의 관광지 더 추천해줘. {companion} 갈 거고 {constraint}.",
        ],
        "문화시설": [
            "{district}에서 전시/관람하기 좋은 문화시설 추천해줘. {time}, {purpose} 위주로.",
            "{district} 문화시설 중에 {companion} 가기 좋은 곳 알려줘. {transport}, {constraint}.",
            "{district}에서 '{title}' 같은 무드의 문화시설 추천해줘. {budget}.",
        ],
        "축제공연행사": [
            "{district} 근처에서 이번에 갈 만한 축제나 공연행사 추천해줘. {companion} 갈 거야.",
            "{district}에서 {time}에 즐기기 좋은 행사 추천해줘. {purpose}, {constraint}.",
            "{district} 기준으로 공연/행사 2개만 추천해줘. {transport}, {budget}.",
        ],
        "레포츠": [
            "{district}에서 {companion} 즐길 만한 레포츠 장소 추천해줘. {time}에 가려고 해.",
            "{district} 레포츠 중에 {purpose} 장소 알려줘. {transport}, {constraint}.",
            "{district}에서 '{title}' 같은 활동적인 장소 추천해줘. {budget}.",
        ],
        "숙박": [
            "{district}에서 {companion} 머물 숙소 추천해줘. {purpose} 숙소면 좋아.",
            "{district} 숙소 추천 부탁해. {transport}, {budget}, {constraint}.",
            "{district}에서 '{title}' 느낌의 숙소 더 알려줘. {time} 체크인 예정이야.",
        ],
        "음식점": [
            "{district}에서 {companion} 가기 좋은 음식점 추천해줘. {time} 방문 예정이야.",
            "{district} 음식점 중 {purpose} 곳 알려줘. {budget}, {constraint}.",
            "{district}에서 '{title}' 같은 분위기의 맛집 추천해줘. {transport}.",
        ],
        "기본": [
            "{district}에서 {companion} 가기 좋은 {content_type} 추천해줘.",
            "{district} 기준으로 {purpose} {content_type} 알려줘. {constraint}.",
            "{district}에서 {content_type} 2곳만 추천해줘. {transport}, {budget}.",
        ],
    }
    type_focus = {
        "관광지": "볼거리와 동선",
        "문화시설": "전시/관람 포인트",
        "축제공연행사": "행사 성격과 방문 타이밍",
        "레포츠": "활동 강도와 준비사항",
        "숙박": "접근성과 숙소 편의",
        "음식점": "대표 메뉴와 분위기",
    }

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
                content_type = (item.get("contenttypeid") or "장소").strip()
                addr = (item.get("addr") or "서울").strip()
                llm_text = (item.get("llm_text") or "").strip()
                contentid = str(item.get("contentid") or "")

                if not title or not llm_text:
                    continue

                district = "서울"
                addr_parts = addr.split()
                if len(addr_parts) >= 2:
                    district = f"{addr_parts[0]} {addr_parts[1]}"
                elif addr_parts:
                    district = addr_parts[0]

                templates = type_templates.get(content_type, type_templates["기본"])
                question = rng.choice(templates).format(
                    district=district,
                    title=title,
                    content_type=content_type,
                    companion=rng.choice(companion_opts),
                    time=rng.choice(time_opts),
                    purpose=rng.choice(purpose_opts),
                    budget=rng.choice(budget_opts),
                    transport=rng.choice(transport_opts),
                    constraint=rng.choice(constraint_opts),
                )

                gt_core = llm_text.replace("\n", " ").strip()
                focus = type_focus.get(content_type, "핵심 특징")
                # 추천형 태스크에 맞춘 reference로 변환
                ground_truth = (
                    f"{district} {content_type} 추천 답변. "
                    f"{title}을 포함해 유사한 장소 2~3곳을 제안하고, "
                    f"{focus} 기준 추천 이유와 짧은 방문 팁을 제공. "
                    f"대표 근거: {title}({addr}). {gt_core}"
                )

                records.append(
                    {
                        "contentid": contentid,
                        "contenttype": content_type,
                        "question": question,
                        "ground_truth": ground_truth,
                    }
                )

    # contentid 기준 중복 제거
    unique = {}
    for r in records:
        key = r["contentid"] or f"{r['question']}|{r['ground_truth']}"
        if key not in unique:
            unique[key] = {
                "contenttype": r["contenttype"],
                "question": r["question"],
                "ground_truth": r["ground_truth"],
            }
    candidates = list(unique.values())

    if not candidates:
        raise ValueError("No valid records for generating test data")

    take_n = min(sample_size, len(candidates))

    # contenttype별 균형 샘플링으로 질문 다양성 확보
    by_type = {}
    for c in candidates:
        by_type.setdefault(c["contenttype"], []).append(c)

    sampled = []
    type_names = sorted(by_type.keys())
    if type_names:
        # 1차: 각 타입 최소 1개씩
        for t in type_names:
            if len(sampled) >= take_n:
                break
            sampled.append(rng.choice(by_type[t]))

        # 2차: 남은 개수는 라운드로빈 + 랜덤
        while len(sampled) < take_n:
            progressed = False
            for t in type_names:
                if len(sampled) >= take_n:
                    break
                pool = by_type[t]
                candidates_left = [x for x in pool if x not in sampled]
                if candidates_left:
                    sampled.append(rng.choice(candidates_left))
                    progressed = True
            if not progressed:
                break

    # 최종 안전장치
    if len(sampled) < take_n:
        remain = [x for x in candidates if x not in sampled]
        need = take_n - len(sampled)
        sampled.extend(rng.sample(remain, need) if len(remain) > need else remain)

    # 출력 포맷은 기존 rag_eval_data.json과 동일하게 유지
    sampled = [{"question": s["question"], "ground_truth": s["ground_truth"]} for s in sampled]

    out_path = _resolve_eval_path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(sampled, f, ensure_ascii=False, indent=4)

    print(f"[INFO] Generated {len(sampled)} test samples -> {output_file}")
    return sampled

async def get_rag_response(question: str):
    """실제 RAG 시스템을 통해 답변과 컨텍스트 추출"""
    try:
        from app.agents.graph import workflow

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
            contexts.append(context[:700])
        
        return answer, contexts
    except Exception as e:
        # 제한 환경(의존성/DB/Qdrant 미구성)에서도 평가 파이프라인 자체는 실행 가능하도록 fallback
        print(f"  [WARN] Graph execution failed: {e}")
        return f"질문: {question}\n현재 환경 제약으로 에이전트 워크플로우를 실행하지 못했습니다.", [question]


async def run_intent_evaluation(limit: Optional[int] = None):
    from app.agents.models.output import IntentType

    test_data = _load_test_data(limit=limit)
    rows = []
    total = len(test_data)
    primary_match = 0
    loc_match = 0
    cat_match = 0
    loc_total = 0
    cat_total = 0

    print(f"--- Running Intent Node Evaluation for {total} samples ---")
    for item in test_data:
        q = item.get("question", "")
        gold_location = _extract_gold_location(q)
        gold_category = _extract_gold_category(q)

        try:
            result = await _invoke_graph(q)
            pred_primary = str(result.get("primary_intent", ""))
            pred_slots = _to_slot_dict(result.get("slots"))
        except Exception as e:
            pred_primary = f"ERROR:{e}"
            pred_slots = {}

        expected_primary = str(IntentType.PLACE_INQUIRY)
        is_primary_match = pred_primary.endswith(expected_primary)
        primary_match += 1 if is_primary_match else 0

        pred_location = str(pred_slots.get("location") or "")
        pred_category = str(pred_slots.get("category") or "")

        is_loc_match = None
        if gold_location:
            is_loc_match = (gold_location in pred_location) or (pred_location in gold_location)
            loc_total += 1
            loc_match += 1 if is_loc_match else 0

        is_cat_match = None
        if gold_category:
            is_cat_match = pred_category == gold_category
            cat_total += 1
            cat_match += 1 if is_cat_match else 0

        rows.append(
            {
                "question": q,
                "gold_primary_intent(proxy)": expected_primary,
                "pred_primary_intent": pred_primary,
                "primary_match": is_primary_match,
                "gold_location(proxy)": gold_location,
                "pred_location": pred_location,
                "location_match": is_loc_match,
                "gold_category(proxy)": gold_category,
                "pred_category": pred_category,
                "category_match": is_cat_match,
            }
        )

    df = pd.DataFrame(rows)
    report_file = str(EVAL_DIR / "evaluation_intent_report.csv")
    df.to_csv(report_file, index=False)

    summary = {
        "mode": "intent",
        "limit": limit if limit is not None else "all",
        "sample_count": total,
        "samples": total,
        "primary_accuracy": (primary_match / total) if total else 0.0,
        "location_slot_accuracy": (loc_match / loc_total) if loc_total else 0.0,
        "category_slot_accuracy": (cat_match / cat_total) if cat_total else 0.0,
        "location_evaluable_count": loc_total,
        "category_evaluable_count": cat_total,
    }
    print("\n--- Intent Node Summary ---")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")
    print(f"Report saved to {report_file}")
    _save_summary_files("intent", summary)
    return summary


async def run_retriever_evaluation(limit: Optional[int] = None):
    test_data = _load_test_data(limit=limit)
    rows = []
    total = len(test_data)
    hit1 = 0
    hit3 = 0
    hit5 = 0
    mrr_sum = 0.0

    print(f"--- Running Retriever Node Evaluation for {total} samples ---")
    for item in test_data:
        q = item.get("question", "")
        gold_title = _extract_gold_title(item.get("ground_truth", ""))
        try:
            result = await _invoke_graph(q)
            candidates = result.get("candidates", []) or []
        except Exception as e:
            print(f"[WARN] Retriever eval invoke failed: {e}")
            candidates = []

        names = []
        for c in candidates:
            payload = c.get("payload") if isinstance(c, dict) else {}
            if not isinstance(payload, dict):
                payload = {}
            name = (payload.get("title") or payload.get("name") or c.get("title") or c.get("name") or "").strip()
            names.append(name)

        rank = 0
        if gold_title:
            for i, n in enumerate(names, start=1):
                if n and (gold_title in n or n in gold_title):
                    rank = i
                    break

        if rank == 1:
            hit1 += 1
        if 1 <= rank <= 3:
            hit3 += 1
        if 1 <= rank <= 5:
            hit5 += 1
        if rank > 0:
            mrr_sum += 1.0 / rank

        rows.append(
            {
                "question": q,
                "gold_title(proxy)": gold_title,
                "retrieved_titles_top5": names[:5],
                "gold_rank_in_top5": rank if rank > 0 else None,
                "hit@1": rank == 1,
                "hit@3": 1 <= rank <= 3,
                "hit@5": 1 <= rank <= 5,
                "reciprocal_rank": (1.0 / rank) if rank > 0 else 0.0,
            }
        )

    df = pd.DataFrame(rows)
    report_file = str(EVAL_DIR / "evaluation_retriever_report.csv")
    df.to_csv(report_file, index=False)

    summary = {
        "mode": "retriever",
        "limit": limit if limit is not None else "all",
        "sample_count": total,
        "samples": total,
        "hit@1": (hit1 / total) if total else 0.0,
        "hit@3": (hit3 / total) if total else 0.0,
        "hit@5": (hit5 / total) if total else 0.0,
        "mrr@5": (mrr_sum / total) if total else 0.0,
    }
    print("\n--- Retriever Node Summary ---")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")
    print(f"Report saved to {report_file}")
    _save_summary_files("retriever", summary)
    return summary


async def run_executor_evaluation(limit: Optional[int] = None):
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy
    from ragas.llms import llm_factory
    from ragas.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
    from openai import OpenAI
    from app.utils.config import LLM_MODEL, TEXT_MODEL

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    openai_client = OpenAI(api_key=api_key)
    eval_llm = llm_factory(model=LLM_MODEL, client=openai_client)

    embedding_model = TEXT_MODEL
    if embedding_model.startswith("openai/"):
        eval_embeddings = OpenAIEmbeddings(
            model=embedding_model.replace("openai/", ""),
            client=openai_client,
        )
    elif "/" in embedding_model:
        hf_embeddings = HuggingFaceEmbeddings(model=embedding_model)

        class _EmbeddingAdapter:
            def __init__(self, base):
                self.base = base

            def embed_query(self, text):
                return self.base.embed_text(text)

            def embed_documents(self, texts):
                return self.base.embed_texts(texts)

            async def aembed_query(self, text):
                return await self.base.aembed_text(text)

            async def aembed_documents(self, texts):
                return await self.base.aembed_texts(texts)

        eval_embeddings = _EmbeddingAdapter(hf_embeddings)
    else:
        eval_embeddings = OpenAIEmbeddings(model=embedding_model, client=openai_client)

    faithfulness.llm = eval_llm
    answer_relevancy.llm = eval_llm
    answer_relevancy.embeddings = eval_embeddings

    test_data = _load_test_data(limit=limit)
    questions = [d["question"] for d in test_data]
    ground_truths = [d["ground_truth"] for d in test_data]
    answers = []
    all_contexts = []

    print(f"--- Running Executor Node Evaluation for {len(questions)} samples ---")
    for q in questions:
        ans, ctx = await get_rag_response(q)
        answers.append((ans or "")[:700])
        all_contexts.append([(c or "")[:220] for c in (ctx or [])[:4]])

    dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": all_contexts,
            "ground_truth": ground_truths,
        }
    )

    result = evaluate(dataset, metrics=[faithfulness, answer_relevancy])
    df = result.to_pandas()
    report_file = str(EVAL_DIR / "evaluation_executor_report.csv")
    df.to_csv(report_file, index=False)
    summary = {
        "mode": "executor",
        "limit": limit if limit is not None else "all",
        "sample_count": len(df),
        "samples": len(df),
        "faithfulness": float(df["faithfulness"].mean()) if "faithfulness" in df else 0.0,
        "answer_relevancy": float(df["answer_relevancy"].mean()) if "answer_relevancy" in df else 0.0,
    }
    print("\n--- Executor Node Summary ---")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")
    print(f"Report saved to {report_file}")
    _save_summary_files("executor", summary)
    return summary


async def run_all_evaluations(limit: Optional[int] = None):
    await run_intent_evaluation(limit=limit)
    await run_retriever_evaluation(limit=limit)
    await run_executor_evaluation(limit=limit)
    await run_evaluation(limit=limit, mode="all")

async def run_evaluation(limit: Optional[int] = None, mode: str = "e2e"):
    from ragas import evaluate
    from ragas.run_config import RunConfig
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from ragas.llms import llm_factory
    from ragas.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
    from openai import OpenAI
    from app.utils.config import LLM_MODEL, TEXT_MODEL

    # OpenAI API Key 설정
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    # OpenAI 클라이언트 생성
    openai_client = OpenAI(api_key=api_key)

    # 프로젝트 설정(config.py)과 동일한 모델을 사용
    eval_llm = llm_factory(model=LLM_MODEL, client=openai_client)

    embedding_model = TEXT_MODEL
    try:
        if embedding_model.startswith("openai/"):
            eval_embeddings = OpenAIEmbeddings(
                model=embedding_model.replace("openai/", ""),
                client=openai_client,
            )
        elif "/" in embedding_model:
            hf_embeddings = HuggingFaceEmbeddings(model=embedding_model)

            class _EmbeddingAdapter:
                # ragas metric이 embed_query/embed_documents 시그니처를 요구하므로 어댑터 제공
                def __init__(self, base):
                    self.base = base

                def embed_query(self, text):
                    return self.base.embed_text(text)

                def embed_documents(self, texts):
                    return self.base.embed_texts(texts)

                async def aembed_query(self, text):
                    return await self.base.aembed_text(text)

                async def aembed_documents(self, texts):
                    return await self.base.aembed_texts(texts)

            eval_embeddings = _EmbeddingAdapter(hf_embeddings)
        else:
            eval_embeddings = OpenAIEmbeddings(model=embedding_model, client=openai_client)
    except Exception as e:
        fallback_embedding_model = "BAAI/bge-m3"
        print(f"[WARN] Failed to initialize embedding '{embedding_model}': {e}")
        print(f"[WARN] Falling back to OpenAI '{fallback_embedding_model}' for evaluation runtime.")
        eval_embeddings = OpenAIEmbeddings(model=fallback_embedding_model, client=openai_client)
        embedding_model = f"openai/{fallback_embedding_model}"

    print(f"[INFO] Eval LLM model: {LLM_MODEL}")
    print(f"[INFO] Eval embedding model: {embedding_model} (from config TEXT_MODEL={TEXT_MODEL})")

    # 메트릭 객체 설정 (v0.4.3+ 환경 호환성을 위해 ragas.metrics 객체 사용)
    faithfulness.llm = eval_llm
    answer_relevancy.llm = eval_llm
    answer_relevancy.embeddings = eval_embeddings
    context_precision.llm = eval_llm
    context_recall.llm = eval_llm

    # 1. 테스트 데이터 로드
    data_file = _resolve_eval_path("rag_eval_data.json")
    if not data_file.exists():
        print(f"[ERROR] Test data file not found: {data_file}")
        return

    with data_file.open("r", encoding="utf-8") as f:
        test_data = json.load(f)

    if limit is not None and limit > 0:
        test_data = test_data[:limit]
    
    questions = [d["question"] for d in test_data]
    ground_truths = [d["ground_truth"] for d in test_data]
    
    answers = []
    all_contexts = []
    
    print(f"--- Starting RAG Response Generation for {len(questions)} samples ---")
    for q in questions:
        print(f"Querying: {q}")
        ans, ctx = await get_rag_response(q)
        # Faithfulness judge max token 초과 방지를 위해 답변/컨텍스트를 더 짧게 제한
        answers.append((ans or "")[:380])
        all_contexts.append([(c or "")[:140] for c in (ctx or [])[:3]])
    
    # 2. Ragas 데이터셋 구성
    data_dict = {
        "question": questions,
        "answer": answers,
        "contexts": all_contexts,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(data_dict)
    
    # 3. 평가 실행
    print("--- Running Ragas Evaluation ---")
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    
    try:
        # 장시간 정체를 피하기 위해 RAGAS 실행 타임아웃/재시도 상한을 명시
        run_config = RunConfig(timeout=90, max_retries=2, max_wait=10, max_workers=1)
        result = evaluate(
            dataset,
            metrics=metrics,
            run_config=run_config,
            raise_exceptions=False,
            batch_size=1,
        )
        
        # 4. 결과 출력 및 저장
        df = result.to_pandas()
        print("\n--- Evaluation Results ---")
        print(df)
        
        # 5. 전체 평균 점수 및 요약 기록 (유저 요청 사항)
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 수치형 필드만 평균 계산 (ID, 질문 등을 제외한 메트릭 점수만)
        metric_cols = [col for col in df.columns if col in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall', 'ragas_score']]
        averages = df[metric_cols].mean() if not df[metric_cols].empty else df.select_dtypes(include=['number']).mean()
        
        sample_count = len(questions)
        summary_lines = [
            f"Evaluation Time: {timestamp}",
            f"mode: {mode}",
            f"limit: {limit if limit is not None else 'all'}",
            f"sample_count: {sample_count}",
            "--- Average Scores ---"
        ]
        for metric_name, avg in averages.items():
            summary_lines.append(f"{metric_name}: {avg:.4f}")
        
        summary_content = "\n".join(summary_lines)
        
        # CSV 보고서 저장
        output_file = str(EVAL_DIR / "evaluation_report.csv")
        df.to_csv(output_file, index=False)
        print(f"\nReport saved to {output_file}")
        
        # 요약 파일 저장
        summary_file = EVAL_DIR / "evaluation_summary.txt"
        with summary_file.open("a", encoding="utf-8") as f:
            f.write("\n\n------------------\n")
            f.write(summary_content)
        print(f"Summary saved to {summary_file}")
        
    except Exception as e:
        print(f"[ERROR] Evaluation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-test-data", action="store_true")
    parser.add_argument(
        "--mode",
        default="e2e",
        choices=["e2e", "intent", "retriever", "executor", "all"],
        help="평가 모드 선택",
    )
    parser.add_argument("--source-dir", default="data/llm_result")
    parser.add_argument("--output-file", default="rag_eval_data.json")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.generate_test_data:
        generate_test_data_from_llm_results(
            source_dir=args.source_dir,
            output_file=args.output_file,
            sample_size=args.sample_size,
            seed=args.seed,
        )
    else:
        if args.mode == "intent":
            asyncio.run(run_intent_evaluation(limit=args.limit))
        elif args.mode == "retriever":
            asyncio.run(run_retriever_evaluation(limit=args.limit))
        elif args.mode == "executor":
            asyncio.run(run_executor_evaluation(limit=args.limit))
        elif args.mode == "all":
            asyncio.run(run_all_evaluations(limit=args.limit))
        else:
            asyncio.run(run_evaluation(limit=args.limit))

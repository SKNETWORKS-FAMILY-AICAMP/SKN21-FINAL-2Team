"""
LLM 모델 비교 벤치마크 스크립트

각 파이프라인 노드(Intent, Planner, Executor)별로 모델 레이턴시와 구조화 출력 품질을 측정합니다.

사용법:
    cd backend
    python -m evaluation.benchmark_models
    python -m evaluation.benchmark_models --dry-run       # API 연결만 확인
    python -m evaluation.benchmark_models --n 5          # 쿼리 5개만 사용
    python -m evaluation.benchmark_models --models openai,anthropic  # 특정 모델만
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# backend 루트를 PYTHONPATH에 추가 (python -m 없이 실행 시에도 동작)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(_BACKEND_ROOT / ".env", override=True)

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_openai import ChatOpenAI
from app.core.llm_factory import LLMFactory
from app.agents.models.output import IntentCoreOutput, SummaryOutput, PlannerOutput, CategoryType
from app.agents.prompts.prompts import INTENT_PROMPT, SUMMARY_PROMPT, PLANNER_PROMPT, get_language_instruction
from app.models.enums import LanguageType

# ── 모델 매트릭스 ──────────────────────────────────────────────────────────────
ALL_MODELS = [
    {"name": "gpt-4o-mini",       "llm_type": "openai",    "model": "gpt-4o-mini"},
    {"name": "gpt-5.4",           "llm_type": "openai",    "model": "gpt-5.4"},
    {"name": "gpt-5.4-mini",      "llm_type": "openai",    "model": "gpt-5.4-mini"},
    {"name": "gpt-5.4-nano",      "llm_type": "openai",    "model": "gpt-5.4-nano"},
    {"name": "claude-haiku-4-5",  "llm_type": "anthropic", "model": "claude-haiku-4-5-20251001"},
    {"name": "ollama-llama3.2",   "llm_type": "ollama",    "model": "llama3.2"},
    # ollama-qwen3.5-4b: 메모리 부족(~3.5GB 필요, 가용 ~3.7GB)으로 OOM 크래시 → 제외
    # GPU 환경 또는 16GB+ 여유 메모리에서 재시도 권장
    # {"name": "ollama-qwen3.5-4b", "llm_type": "ollama", "model": "qwen3.5:4b"},
]


def _get_llm(llm_type: str, model: str, temperature: float, num_ctx: int | None = None):
    """LLM 인스턴스 반환. ollama 전용 num_ctx 옵션 지원."""
    if llm_type == "ollama" and num_ctx is not None:
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return ChatOpenAI(
            model=model,
            base_url=ollama_base_url,
            api_key="ollama",
            temperature=temperature,
            model_kwargs={"options": {"num_ctx": num_ctx}},
        )
    return LLMFactory.get_llm(model=model, temperature=temperature, llm_type=llm_type)

# ── TRIP_PLANNING 쿼리 (testdata.csv에는 없으므로 직접 추가) ────────────────────
_TRIP_PLANNING_QUERIES = [
    "2박3일 서울 여행 계획 짜줘. 혼자 가고 카페랑 맛집 위주로 돌고 싶어.",
    "친구들이랑 주말에 서울 당일치기 코스 추천해줘. 젊은 분위기 좋아해.",
]


def _load_test_queries(n: int = 8) -> list[dict]:
    """evaluate_testdata.csv에서 place inquiry 쿼리를 로드하고 trip planning 쿼리를 추가합니다."""
    csv_path = _BACKEND_ROOT / "evaluation" / "evaluate_testdata.csv"
    df = pd.read_csv(csv_path)

    # question 컬럼 사용 (모델 생성 질문)
    place_queries = (
        df["question"]
        .dropna()
        .drop_duplicates()
        .sample(min(n, len(df)), random_state=42)
        .tolist()
    )
    queries = [{"query": q, "intent": "PLACE_INQUIRY"} for q in place_queries]
    queries += [{"query": q, "intent": "TRIP_PLANNING"} for q in _TRIP_PLANNING_QUERIES]
    return queries


# ── 노드별 벤치마크 함수 ──────────────────────────────────────────────────────

async def _bench_intent(llm_type: str, model: str, query: str, num_ctx: int | None = None) -> dict:
    """Intent 노드: intent_chain + summary_chain 병렬 실행 레이턴시 측정."""
    try:
        llm = _get_llm(llm_type=llm_type, model=model, temperature=0, num_ctx=num_ctx)
        intent_llm = llm.with_structured_output(IntentCoreOutput)
        summary_llm = llm.with_structured_output(SummaryOutput)

        intent_prompt = ChatPromptTemplate.from_messages([
            ("system", INTENT_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "{user_input}")
        ])
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", SUMMARY_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "{user_input}")
        ])

        intent_chain = intent_prompt | intent_llm
        summary_chain = summary_prompt | summary_llm

        inputs = {
            "messages": [],
            "user_input": query,
            "category_desc": CategoryType.description(),
            "summary_message": "없음",
            "summary_title": "제목 없음",
            "summary_language_instruction": get_language_instruction(LanguageType.ko),
            "image_intent_type": "",
            "gps_location_context": "",
        }

        t0 = time.perf_counter()
        if llm_type == "ollama":
            # ollama는 병렬 실행 시 메모리 부족(OOM)으로 프로세스 크래시 → 순차 실행
            intent_result = await intent_chain.ainvoke(inputs)
            _ = await summary_chain.ainvoke(inputs)
        else:
            intent_result, _ = await asyncio.gather(
                intent_chain.ainvoke(inputs),
                summary_chain.ainvoke(inputs),
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        detected_intent = intent_result.primary_intent.value if hasattr(intent_result, "primary_intent") else "unknown"
        return {
            "latency_ms": round(elapsed_ms, 1),
            "detected_intent": detected_intent,
            "error": None,
        }
    except Exception as e:
        return {"latency_ms": None, "detected_intent": None, "error": str(e)}


async def _bench_planner(llm_type: str, model: str, query: str, num_ctx: int | None = None) -> dict:
    """Planner 노드: structured output 레이턴시 측정. TRIP_PLANNING 쿼리에만 의미 있음."""
    try:
        llm = _get_llm(llm_type=llm_type, model=model, temperature=0.7, num_ctx=num_ctx)
        structured_llm = llm.with_structured_output(PlannerOutput)

        prompt = ChatPromptTemplate.from_messages([
            ("system", PLANNER_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "{user_input}")
        ])
        chain = prompt | structured_llm

        t0 = time.perf_counter()
        result = await chain.ainvoke({
            "messages": [],
            "user_input": query,
            "summary_message": "없음",
            "user_geo": "없음",
            "slots_info": "없음",
            "prefs_info": "",
            "current_itinerary": "없음",
            "pinned_places_info": "없음",
            "weather_info": "없음",
        })
        elapsed_ms = (time.perf_counter() - t0) * 1000

        itinerary_count = len(result.itinerary) if hasattr(result, "itinerary") else 0
        return {
            "latency_ms": round(elapsed_ms, 1),
            "itinerary_count": itinerary_count,
            "error": None,
        }
    except Exception as e:
        return {"latency_ms": None, "itinerary_count": None, "error": str(e)}


async def _bench_executor(llm_type: str, model: str, query: str, num_ctx: int | None = None) -> dict:
    """Executor 노드: 스트리밍 응답 생성 레이턴시 측정 (TTFT + 전체)."""
    _SIMPLE_PROMPT = (
        "당신은 서울 여행 추천 AI입니다. 아래 질문에 한국어로 간결하게 3문장 이내로 답하세요.\n\n질문: {query}"
    )
    try:
        llm = _get_llm(llm_type=llm_type, model=model, temperature=0.5, num_ctx=num_ctx)
        prompt = ChatPromptTemplate.from_messages([("human", _SIMPLE_PROMPT)])
        chain = prompt | llm

        ttft_ms: float | None = None
        output_chars = 0
        t0 = time.perf_counter()

        async for chunk in chain.astream({"query": query}):
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - t0) * 1000
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            output_chars += len(content)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "latency_ms": round(elapsed_ms, 1),
            "ttft_ms": round(ttft_ms, 1) if ttft_ms else None,
            "output_chars": output_chars,
            "error": None,
        }
    except Exception as e:
        return {"latency_ms": None, "ttft_ms": None, "output_chars": 0, "error": str(e)}


# ── 단일 (모델, 쿼리) 벤치마크 실행 ───────────────────────────────────────────

async def _bench_one(model_cfg: dict, query_cfg: dict) -> dict:
    llm_type = model_cfg["llm_type"]
    model = model_cfg["model"]
    query = query_cfg["query"]
    intent = query_cfg["intent"]
    num_ctx = model_cfg.get("num_ctx")

    print(f"  [{model_cfg['name']}] {query[:40]}...", flush=True)

    intent_res, executor_res = await asyncio.gather(
        _bench_intent(llm_type, model, query, num_ctx=num_ctx),
        _bench_executor(llm_type, model, query, num_ctx=num_ctx),
    )

    # Planner는 TRIP_PLANNING 쿼리에만 실행
    if intent == "TRIP_PLANNING":
        planner_res = await _bench_planner(llm_type, model, query, num_ctx=num_ctx)
    else:
        planner_res = {"latency_ms": None, "itinerary_count": None, "error": "skipped (not TRIP_PLANNING)"}

    return {
        "model": model_cfg["name"],
        "query": query,
        "expected_intent": intent,
        "intent": intent_res,
        "planner": planner_res,
        "executor": executor_res,
    }


# ── 요약 통계 계산 ──────────────────────────────────────────────────────────────

def _compute_summary(results: list[dict]) -> dict:
    from collections import defaultdict
    import statistics

    per_model: dict[str, dict[str, list]] = defaultdict(lambda: {
        "intent_ms": [], "executor_ms": [], "ttft_ms": [], "planner_ms": [],
        "intent_correct": [], "errors": [],
    })

    for r in results:
        name = r["model"]
        m = per_model[name]

        if r["intent"]["latency_ms"] is not None:
            m["intent_ms"].append(r["intent"]["latency_ms"])
        if r["executor"]["latency_ms"] is not None:
            m["executor_ms"].append(r["executor"]["latency_ms"])
        if r["executor"]["ttft_ms"] is not None:
            m["ttft_ms"].append(r["executor"]["ttft_ms"])
        if r["planner"]["latency_ms"] is not None:
            m["planner_ms"].append(r["planner"]["latency_ms"])

        # intent 정확도: detected intent가 expected intent와 일치하는지
        detected = r["intent"].get("detected_intent")
        expected = r["expected_intent"]
        if detected is not None:
            m["intent_correct"].append(detected == expected)

        for node in ("intent", "planner", "executor"):
            if r[node].get("error") and r[node]["error"] not in ("skipped (not TRIP_PLANNING)",):
                m["errors"].append(f"{node}: {r[node]['error'][:80]}")

    def _avg(lst):
        return round(statistics.mean(lst), 1) if lst else None

    summary = {}
    for name, m in per_model.items():
        total_list = [
            (i + e)
            for i, e in zip(m["intent_ms"], m["executor_ms"])
            if i is not None and e is not None
        ]
        summary[name] = {
            "avg_intent_ms":   _avg(m["intent_ms"]),
            "avg_executor_ms": _avg(m["executor_ms"]),
            "avg_ttft_ms":     _avg(m["ttft_ms"]),
            "avg_planner_ms":  _avg(m["planner_ms"]),
            "avg_total_ms":    _avg(total_list),
            "intent_accuracy": round(sum(m["intent_correct"]) / len(m["intent_correct"]), 3) if m["intent_correct"] else None,
            "error_count":     len(m["errors"]),
            "sample_errors":   m["errors"][:3],
        }

    return summary


# ── CLI 엔트리포인트 ────────────────────────────────────────────────────────────

async def _main(args: argparse.Namespace):
    # 모델 필터링
    selected_names = set(args.models.split(",")) if args.models else None
    models = [m for m in ALL_MODELS if selected_names is None or m["name"] in selected_names]

    queries = _load_test_queries(n=args.n)
    print(f"\n벤치마크 시작: {len(models)}개 모델 × {len(queries)}개 쿼리")

    if args.dry_run:
        print("\n[dry-run] API 연결 테스트 중...")
        for m in models:
            res = await _bench_executor(m["llm_type"], m["model"], "안녕하세요")
            status = "OK" if res["error"] is None else f"FAIL: {res['error'][:60]}"
            print(f"  {m['name']:25s} → {status}")
        return

    all_results = []
    for q_cfg in queries:
        print(f"\n쿼리: {q_cfg['query'][:60]}")
        for m_cfg in models:
            result = await _bench_one(m_cfg, q_cfg)
            all_results.append(result)

    summary = _compute_summary(all_results)

    output = {
        "timestamp": datetime.now().isoformat(),
        "models": [m["name"] for m in models],
        "query_count": len(queries),
        "summary": summary,
        "results": all_results,
    }

    # 결과 저장
    out_dir = _BACKEND_ROOT / "evaluation"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"benchmark_results_{ts}.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n결과 저장: {out_path}")

    # 요약 출력
    print("\n" + "=" * 65)
    print(f"{'모델':<25} {'Intent(ms)':>11} {'Executor(ms)':>13} {'TTFT(ms)':>9} {'Intent정확도':>12}")
    print("-" * 65)
    for name, s in summary.items():
        intent_ms   = f"{s['avg_intent_ms']:.0f}"   if s["avg_intent_ms"]   else "  ERR"
        exec_ms     = f"{s['avg_executor_ms']:.0f}"  if s["avg_executor_ms"]  else "  ERR"
        ttft_ms     = f"{s['avg_ttft_ms']:.0f}"      if s["avg_ttft_ms"]      else "  ERR"
        accuracy    = f"{s['intent_accuracy']:.1%}"  if s["intent_accuracy"] is not None else "  N/A"
        print(f"{name:<25} {intent_ms:>11} {exec_ms:>13} {ttft_ms:>9} {accuracy:>12}")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="LLM 모델 비교 벤치마크")
    parser.add_argument("--dry-run", action="store_true", help="API 연결 확인만 수행")
    parser.add_argument("--n", type=int, default=8, help="테스트 쿼리 수 (기본: 8)")
    parser.add_argument("--models", type=str, default="", help="쉼표로 구분한 모델명 (기본: 전체)")
    args = parser.parse_args()
    asyncio.run(_main(args))


if __name__ == "__main__":
    main()

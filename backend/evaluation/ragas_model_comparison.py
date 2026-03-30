"""
RAG 파이프라인 생성(Generation) 품질 모델별 비교 평가
- evaluate_testdata.csv의 user_input + retrieved_contexts 고정 사용
- 6개 모델별 응답 생성 후 LLM-as-Judge(gpt-4o-mini)로 품질 평가
"""
import sys, json, asyncio, time, ast, re
from pathlib import Path

sys.path.insert(0, '/Users/kim/SKN/SKN21-FINAL-2Team/backend')

import os
from dotenv import load_dotenv
load_dotenv('/Users/kim/SKN/SKN21-FINAL-2Team/backend/.env', override=True)

# Claude 인증을 위한 명시적 환경변수 확인
_anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not _anthropic_key:
    raise RuntimeError("ANTHROPIC_API_KEY가 환경변수에 없습니다. .env 파일을 확인하세요.")

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm_factory import LLMFactory
from evaluation.common.judge_normalization import normalize_judge_score

# EXECUTOR_PROMPT 인라인 (langgraph 의존성 없이 사용)
_EXECUTOR_PROMPT = """당신은 한국 서울 여행 추천 에이전트입니다.
아래 정보만 사용해 간결하고 실행 가능한 답변을 작성하세요.

# 추천 가능한 장소 목록
반드시 아래 목록에 있는 장소명만 그대로 사용하세요. 목록에 없는 장소는 절대 언급하지 마세요.
{candidate_names}

# 중요 규칙
1. 위 "추천 가능한 장소 목록"에 있는 장소만 추천하세요.
2. 검색 결과에 없는 정보는 지어내지 마세요.
3. 친절하고 자연스러운 서술형 문장으로 답변하세요.

# 장소 정보 리스트
{place_context}
"""

# ─── 설정 ───────────────────────────────────────────────────────────────────
MODELS = [
    {"name": "gpt-4o-mini",       "llm_type": "openai",    "model": "gpt-4o-mini"},
    {"name": "gpt-5.4",           "llm_type": "openai",    "model": "gpt-5.4"},
    {"name": "gpt-5.4-mini",      "llm_type": "openai",    "model": "gpt-5.4-mini"},
    {"name": "gpt-5.4-nano",      "llm_type": "openai",    "model": "gpt-5.4-nano"},
    {"name": "claude-haiku-4-5",  "llm_type": "anthropic", "model": "claude-haiku-4-5-20251001"},
    {"name": "ollama-llama3.2",   "llm_type": "ollama",    "model": "llama3.2"},
]

CSV_PATH = Path('/Users/kim/SKN/SKN21-FINAL-2Team/backend/evaluation/evaluate_testdata.csv')
OUTPUT_PATH = Path('/Users/kim/SKN/SKN21-FINAL-2Team/backend/evaluation/ragas_model_comparison.json')
MAX_ROWS = 21


def build_executor_prompt(contexts: list[str], user_input: str) -> str:
    """실제 executor와 동일한 조건으로 시스템 프롬프트 생성."""
    place_context = "\n".join(contexts) if contexts else "없음"
    # retrieved_contexts에서 장소명 추출 (JSON payload의 title 필드)
    candidate_names_list = []
    for ctx in contexts:
        m = re.search(r'"title"\s*:\s*"([^"]+)"', ctx)
        if m:
            candidate_names_list.append(m.group(1))
    candidate_names = "\n".join(f"- {n}" for n in candidate_names_list) if candidate_names_list else "없음"

    return _EXECUTOR_PROMPT.format(
        candidate_names=candidate_names,
        place_context=place_context,
    )

JUDGE_PROMPT = """당신은 RAG 시스템의 응답 품질을 평가하는 전문가입니다.
아래 정보를 바탕으로 4가지 항목을 각각 0~1 사이의 실수로 평가하세요.

[사용자 질문]
{user_input}

[검색된 컨텍스트]
{contexts}

[모델 응답]
{response}

[참고 정답]
{reference}

평가 항목 (각 0.0~1.0 사이의 실수):
1. relevance(답변 관련성): 질문 대비 응답이 얼마나 관련 있는가 (0=전혀 무관, 1=완전 관련)
2. faithfulness(문서 근거성): 응답이 검색 컨텍스트에 근거하는가 (0=전혀 근거 없음, 1=완전히 근거함)
3. hallucination(환각 방지): 0=심각한 환각, 1=환각 없음
4. usefulness(추천 유용성): 실제 여행/장소 추천으로 유용한가 (0=전혀 유용하지 않음, 1=매우 유용함)

반드시 아래 JSON 형식으로만 응답하세요:
{{"relevance": X.XX, "faithfulness": X.XX, "hallucination": X.XX, "usefulness": X.XX}}
"""

# ─── CSV 로드 ────────────────────────────────────────────────────────────────
def load_csv():
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    print(f"[CSV] 로드 완료: {len(df)} 행, 컬럼: {list(df.columns)}")

    # user_input 컬럼 확인
    if 'user_input' not in df.columns and 'question' in df.columns:
        df['user_input'] = df['question']
    assert 'user_input' in df.columns, "user_input 또는 question 컬럼 필요"

    # retrieved_contexts 파싱
    def parse_col(val):
        if isinstance(val, list):
            return val
        if isinstance(val, str) and val.strip():
            try:
                parsed = ast.literal_eval(val)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [val]
        return []

    df['retrieved_contexts'] = df['retrieved_contexts'].apply(parse_col)
    df['reference'] = df['reference'].apply(lambda v: str(v) if pd.notna(v) else "")

    # retrieved_contexts 비어있는 행 스킵
    df = df[df['retrieved_contexts'].apply(lambda x: len(x) > 0)].reset_index(drop=True)
    print(f"[CSV] retrieved_contexts 있는 행: {len(df)}개")

    # 최대 21개
    df = df.head(MAX_ROWS)
    print(f"[CSV] 평가 대상: {len(df)}개 행")
    return df


# ─── 응답 생성 ───────────────────────────────────────────────────────────────
async def generate_response_async(llm, system_prompt: str, user_input: str, timeout: float = 60.0) -> str:
    """실제 executor 프롬프트 구조로 ainvoke 호출 (claude 포함 모든 모델 지원)."""
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_input)]
    try:
        result = await asyncio.wait_for(
            llm.ainvoke(messages),
            timeout=timeout
        )
        return result.content if hasattr(result, 'content') else str(result)
    except asyncio.TimeoutError:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR: {e}]"


async def generate_all_responses(df: pd.DataFrame) -> dict:
    """모든 모델에 대해 모든 쿼리 응답 생성 (실제 EXECUTOR_PROMPT 사용)"""
    results = {}

    for model_cfg in MODELS:
        name = model_cfg["name"]
        llm_type = model_cfg["llm_type"]
        model_id = model_cfg["model"]
        timeout = 120.0 if name == "ollama-llama3.2" else 60.0

        print(f"\n{'='*60}")
        print(f"[모델] {name} ({llm_type}/{model_id}) 응답 생성 시작")
        print(f"{'='*60}")

        try:
            llm = LLMFactory.get_llm(model=model_id, llm_type=llm_type, temperature=0)
        except Exception as e:
            print(f"  [ERROR] LLM 초기화 실패: {e}")
            results[name] = ["[LLM_INIT_ERROR]"] * len(df)
            continue

        responses = []
        for i, row in df.iterrows():
            user_input = str(row['user_input'])
            contexts = row['retrieved_contexts']
            system_prompt = build_executor_prompt(contexts, user_input)

            print(f"  [{name}] 쿼리 {i+1}/{len(df)}: {user_input[:50]}...")
            t0 = time.time()
            response = await generate_response_async(llm, system_prompt, user_input, timeout=timeout)
            elapsed = time.time() - t0
            print(f"    -> {elapsed:.1f}s | {response[:80].replace(chr(10), ' ')}...")
            responses.append(response)

        results[name] = responses
        print(f"[모델] {name} 완료 ({len(responses)}개 응답)")

    return results


# ─── Judge 평가 ───────────────────────────────────────────────────────────────
def parse_judge_json(text: str) -> dict | None:
    """Judge 응답에서 JSON 파싱"""
    # JSON 블록 추출 시도
    match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            required = {"relevance", "faithfulness", "hallucination", "usefulness"}
            if required.issubset(data.keys()):
                return {k: normalize_judge_score(data[k]) for k in required}
        except Exception:
            pass
    return None


def judge_response(judge_llm, user_input: str, contexts: str, response: str, reference: str) -> dict | None:
    """단일 응답에 대한 Judge 평가 (실패 시 1회 재시도)"""
    prompt = JUDGE_PROMPT.format(
        user_input=user_input,
        contexts=contexts,
        response=response,
        reference=reference
    )

    for attempt in range(2):
        try:
            result = judge_llm.invoke([HumanMessage(content=prompt)])
            text = result.content if hasattr(result, 'content') else str(result)
            scores = parse_judge_json(text)
            if scores:
                return scores
            if attempt == 0:
                print(f"    [Judge] JSON 파싱 실패, 재시도... (응답: {text[:100]})")
        except Exception as e:
            if attempt == 0:
                print(f"    [Judge] 오류 발생, 재시도: {e}")
    return None


def run_judge_evaluation(df: pd.DataFrame, all_responses: dict) -> dict:
    """모든 모델에 대해 Judge 평가 실행"""
    print(f"\n{'='*60}")
    print("[Judge] LLM-as-Judge 평가 시작 (gpt-4o-mini)")
    print(f"{'='*60}")

    judge_llm = LLMFactory.get_llm(model="gpt-4o-mini", llm_type="openai", temperature=0)

    model_results = {}

    for model_cfg in MODELS:
        name = model_cfg["name"]
        responses = all_responses.get(name, [])

        print(f"\n[Judge] {name} 평가 중...")
        per_query = []
        total_scores = {"relevance": [], "faithfulness": [], "hallucination": [], "usefulness": []}

        for i, row in df.iterrows():
            if i >= len(responses):
                print(f"  [{name}] 쿼리 {i+1}: 응답 없음, 스킵")
                continue

            response = responses[i]
            if response.startswith("[ERROR") or response.startswith("[TIMEOUT") or response.startswith("[LLM_INIT"):
                print(f"  [{name}] 쿼리 {i+1}: 응답 오류({response[:30]}), 스킵")
                continue

            user_input = str(row['user_input'])
            contexts = "\n".join(row['retrieved_contexts'])
            reference = str(row['reference'])

            print(f"  [{name}] 쿼리 {i+1}/{len(df)} Judge 평가 중...")
            scores = judge_response(judge_llm, user_input, contexts, response, reference)

            if scores is None:
                print(f"    [Judge] 평가 실패, 스킵")
                continue

            print(f"    -> relevance={scores['relevance']}, faithfulness={scores['faithfulness']}, "
                  f"hallucination={scores['hallucination']}, usefulness={scores['usefulness']}")

            per_query.append({
                "idx": i,
                "user_input": user_input,
                "response": response[:200],
                **scores
            })

            for k in total_scores:
                total_scores[k].append(scores[k])

        n = len(per_query)
        if n > 0:
            avg_rel = sum(total_scores["relevance"]) / n
            avg_fai = sum(total_scores["faithfulness"]) / n
            avg_hal = sum(total_scores["hallucination"]) / n
            avg_use = sum(total_scores["usefulness"]) / n
            overall = (avg_rel + avg_fai + avg_hal + avg_use) / 4
        else:
            avg_rel = avg_fai = avg_hal = avg_use = overall = 0.0

        model_results[name] = {
            "avg_relevance": round(avg_rel, 2),
            "avg_faithfulness": round(avg_fai, 2),
            "avg_hallucination": round(avg_hal, 2),
            "avg_usefulness": round(avg_use, 2),
            "overall_avg": round(overall, 2),
            "n_evaluated": n,
            "per_query": per_query,
        }

        print(f"  [{name}] 완료: n={n}, 종합평균={overall:.2f}")

    return model_results


# ─── 결과 출력 ───────────────────────────────────────────────────────────────
def print_comparison_table(model_results: dict):
    BASELINE = {
        "name": "기존(baseline)",
        "avg_relevance": 1.00,
        "avg_faithfulness": 0.96,
        "avg_hallucination": 1.00,
        "avg_usefulness": 1.00,
        "overall_avg": 0.99,
    }

    # 종합평균 기준 내림차순 정렬
    sorted_models = sorted(
        model_results.items(),
        key=lambda x: x[1]["overall_avg"],
        reverse=True
    )

    print("\n" + "━" * 67)
    print("  모델별 RAG 생성 품질 비교 (LLM-as-Judge, 0~1점)")
    print("━" * 67)
    print(f"  {'모델':<20} {'관련성':>6} {'근거성':>6} {'환각방지':>8} {'유용성':>6} {'종합평균':>8}")
    print("  " + "─" * 63)

    for name, res in sorted_models:
        print(f"  {name:<20} {res['avg_relevance']:>6.2f} {res['avg_faithfulness']:>6.2f} "
              f"{res['avg_hallucination']:>8.2f} {res['avg_usefulness']:>6.2f} {res['overall_avg']:>8.2f}")

    print("  " + "─" * 63)
    print(f"  {BASELINE['name']:<20} {BASELINE['avg_relevance']:>6.2f} "
          f"{BASELINE['avg_faithfulness']:>6.2f} {BASELINE['avg_hallucination']:>8.2f} "
          f"{BASELINE['avg_usefulness']:>6.2f} {BASELINE['overall_avg']:>8.2f}")
    print("━" * 67)

    # 최종 추천
    if sorted_models:
        best_name, best_res = sorted_models[0]
        print(f"\n[최종 추천] 품질 기준 최고 모델: {best_name} (종합평균 {best_res['overall_avg']:.3f})")
        # 레이턴시도 고려한 추천
        # gpt-4o-mini는 빠르고 저렴, claude-haiku도 빠름
        fast_models = ["gpt-4o-mini", "gpt-5.4-nano", "gpt-5.4-mini", "claude-haiku-4-5"]
        fast_quality = [(n, r) for n, r in sorted_models if n in fast_models]
        if fast_quality:
            fn, fr = fast_quality[0]
            print(f"[레이턴시+품질 균형 추천] {fn} — 빠른 응답 속도와 높은 품질(종합평균 {fr['overall_avg']:.3f})을 동시에 제공하여 서울 여행 RAG 서비스에 적합합니다.")


# ─── 메인 ─────────────────────────────────────────────────────────────────────
async def main():
    print("=" * 67)
    print("  RAG 생성 품질 모델 비교 평가 시작")
    print("=" * 67)

    # Step 2: CSV 로드
    df = load_csv()

    # Step 3: 모델별 응답 생성
    all_responses = await generate_all_responses(df)

    # Step 4: Judge 평가
    model_results = run_judge_evaluation(df, all_responses)

    # Step 5: 결과 저장
    output = {"models": model_results}
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n[저장] {OUTPUT_PATH}")

    # Step 6: 비교 테이블 출력
    print_comparison_table(model_results)


if __name__ == "__main__":
    asyncio.run(main())

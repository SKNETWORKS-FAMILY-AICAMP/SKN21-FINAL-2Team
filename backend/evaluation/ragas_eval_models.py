"""
모델별 RAGAS 평가 (B단계)
- 각 모델의 응답을 생성 후 RAGAS faithfulness, answer_relevancy 측정
- 평가 LLM: gpt-4o-mini (비용 절감)
- 출력: ragas_eval_models.json
"""
import sys, json, asyncio, time, ast, re, os
from pathlib import Path
sys.path.insert(0, '/Users/kim/SKN/SKN21-FINAL-2Team/backend')

from dotenv import load_dotenv
load_dotenv('/Users/kim/SKN/SKN21-FINAL-2Team/backend/.env', override=True)

_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not _key:
    raise RuntimeError("ANTHROPIC_API_KEY 없음")

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from app.core.llm_factory import LLMFactory

# RAGAS imports (0.4.x)
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import OpenAIEmbeddings

# ─── 설정 ─────────────────────────────────────────────────────────────────────
MODELS = [
    {"name": "gpt-4o-mini",      "llm_type": "openai",    "model": "gpt-4o-mini"},
    {"name": "gpt-5.4",          "llm_type": "openai",    "model": "gpt-5.4"},
    {"name": "gpt-5.4-mini",     "llm_type": "openai",    "model": "gpt-5.4-mini"},
    {"name": "gpt-5.4-nano",     "llm_type": "openai",    "model": "gpt-5.4-nano"},
    {"name": "claude-haiku-4-5", "llm_type": "anthropic", "model": "claude-haiku-4-5-20251001"},
    {"name": "ollama-llama3.2",  "llm_type": "ollama",    "model": "llama3.2"},
]

CSV_PATH       = Path('/Users/kim/SKN/SKN21-FINAL-2Team/backend/evaluation/evaluate_testdata.csv')
OUTPUT_PATH    = Path('/Users/kim/SKN/SKN21-FINAL-2Team/backend/evaluation/ragas_eval_models.json')
RESPONSES_PATH = Path('/Users/kim/SKN/SKN21-FINAL-2Team/backend/evaluation/ragas_eval_responses_cache.json')
MAX_ROWS       = 21

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


def build_prompt(contexts: list[str], user_input: str) -> str:
    place_context = "\n".join(contexts) if contexts else "없음"
    names = []
    for ctx in contexts:
        m = re.search(r'"title"\s*:\s*"([^"]+)"', ctx)
        if m:
            names.append(m.group(1))
    candidate_names = "\n".join(f"- {n}" for n in names) or "없음"
    return _EXECUTOR_PROMPT.format(candidate_names=candidate_names, place_context=place_context)


async def generate_response(llm, sys_prompt: str, user_input: str, timeout: float = 60.0) -> str:
    msgs = [SystemMessage(content=sys_prompt), HumanMessage(content=user_input)]
    try:
        result = await asyncio.wait_for(llm.ainvoke(msgs), timeout=timeout)
        return result.content if hasattr(result, 'content') else str(result)
    except asyncio.TimeoutError:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR: {e}]"


async def generate_all(df: pd.DataFrame) -> dict:
    """모든 모델 응답 생성"""
    all_responses = {}
    for cfg in MODELS:
        name     = cfg["name"]
        llm_type = cfg["llm_type"]
        model_id = cfg["model"]
        timeout  = 120.0 if name == "ollama-llama3.2" else 60.0

        print(f"\n{'='*55}")
        print(f"[생성] {name}")
        print(f"{'='*55}")

        try:
            llm = LLMFactory.get_llm(model=model_id, llm_type=llm_type, temperature=0)
        except Exception as e:
            print(f"  LLM 초기화 실패: {e}")
            all_responses[name] = ["[LLM_INIT_ERROR]"] * len(df)
            continue

        responses = []
        for i, row in df.iterrows():
            user_input = str(row['user_input'])
            contexts   = row['retrieved_contexts']
            sys_prompt = build_prompt(contexts, user_input)
            t0 = time.time()
            resp = await generate_response(llm, sys_prompt, user_input, timeout=timeout)
            elapsed = time.time() - t0
            status = "OK" if not resp.startswith("[") else resp[:15]
            print(f"  Q{i+1:02d}: {elapsed:.1f}s [{status}] {resp[:50].replace(chr(10),' ')}...")
            responses.append(resp)

        all_responses[name] = responses
        print(f"  → {sum(1 for r in responses if not r.startswith('['))} / {len(responses)} 성공")
    return all_responses


def run_ragas(df: pd.DataFrame, all_responses: dict) -> dict:
    """RAGAS faithfulness + answer_relevancy 평가"""
    # 평가용 LLM / Embedding 설정 (gpt-4o-mini 사용)
    eval_llm   = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    eval_embed = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))

    metrics = [Faithfulness(llm=eval_llm), AnswerRelevancy(llm=eval_llm, embeddings=eval_embed)]

    results = {}
    for cfg in MODELS:
        name      = cfg["name"]
        responses = all_responses.get(name, [])

        print(f"\n[RAGAS] {name} 평가 중...")

        # 유효 응답 필터링 → SingleTurnSample 구성
        samples = []
        for i, row in df.iterrows():
            if i >= len(responses):
                continue
            resp = responses[i]
            if resp.startswith("[ERROR") or resp.startswith("[TIMEOUT") or resp.startswith("[LLM_INIT"):
                continue
            samples.append(SingleTurnSample(
                user_input=str(row['user_input']),
                retrieved_contexts=row['retrieved_contexts'],
                response=resp,
                reference=str(row['reference']),
            ))

        n = len(samples)
        print(f"  유효 샘플: {n}개")

        if n == 0:
            results[name] = {"faithfulness": 0.0, "answer_relevancy": 0.0, "n": 0}
            continue

        # RAGAS evaluate
        dataset = EvaluationDataset(samples=samples)
        try:
            scores = evaluate(
                dataset=dataset,
                metrics=metrics,
                llm=eval_llm,
                embeddings=eval_embed,
                show_progress=False,
            )
            score_df = scores.to_pandas()
            faith_avg = float(score_df['faithfulness'].mean()) if 'faithfulness' in score_df else 0.0
            ans_rel_avg = float(score_df['answer_relevancy'].mean()) if 'answer_relevancy' in score_df else 0.0
            print(f"  faithfulness={faith_avg:.3f}, answer_relevancy={ans_rel_avg:.3f}")
            results[name] = {
                "faithfulness":     round(faith_avg, 3),
                "answer_relevancy": round(ans_rel_avg, 3),
                "overall":          round((faith_avg + ans_rel_avg) / 2, 3),
                "n": n,
                "per_query": score_df[['faithfulness','answer_relevancy']].to_dict(orient='records'),
            }
        except Exception as e:
            print(f"  RAGAS 오류: {e}")
            results[name] = {"faithfulness": 0.0, "answer_relevancy": 0.0, "overall": 0.0, "n": n, "error": str(e)}

    return results


async def main():
    print("=" * 55)
    print("  모델별 RAGAS 평가 (B단계)")
    print("  메트릭: faithfulness, answer_relevancy (0~1)")
    print("=" * 55)

    # CSV 로드
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    def parse_col(val):
        if isinstance(val, list): return val
        if isinstance(val, str) and val.strip():
            try:
                p = ast.literal_eval(val)
                if isinstance(p, list): return p
            except: pass
            return [val]
        return []
    df['retrieved_contexts'] = df['retrieved_contexts'].apply(parse_col)
    df['reference'] = df['reference'].apply(lambda v: str(v) if pd.notna(v) else "")
    df = df[df['retrieved_contexts'].apply(lambda x: len(x) > 0)].reset_index(drop=True)
    df = df.head(MAX_ROWS)
    print(f"[CSV] {len(df)}개 쿼리 로드")

    # 1) 응답 생성 (캐시 활용)
    if RESPONSES_PATH.exists():
        print(f"[캐시] 기존 응답 로드: {RESPONSES_PATH}")
        all_responses = json.loads(RESPONSES_PATH.read_text(encoding='utf-8'))
    else:
        all_responses = await generate_all(df)
        RESPONSES_PATH.write_text(json.dumps(all_responses, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"[캐시 저장] {RESPONSES_PATH}")

    # 2) RAGAS 평가
    ragas_results = run_ragas(df, all_responses)

    # 3) 저장
    output = {"ragas_metrics": ragas_results}
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n[저장] {OUTPUT_PATH}")

    # 4) 결과 테이블 출력
    print("\n" + "━"*62)
    print("  모델별 RAGAS 평가 결과 (0~1점)")
    print("━"*62)
    print(f"  {'모델':<22} {'faithfulness':>13} {'ans_relevancy':>14} {'overall':>9} {'n':>4}")
    print("  " + "─"*58)

    sorted_results = sorted(ragas_results.items(), key=lambda x: x[1].get('overall', 0), reverse=True)
    for name, res in sorted_results:
        print(f"  {name:<22} {res['faithfulness']:>13.3f} {res['answer_relevancy']:>14.3f} "
              f"{res.get('overall',0):>9.3f} {res['n']:>4}")
    print("━"*62)


if __name__ == "__main__":
    asyncio.run(main())

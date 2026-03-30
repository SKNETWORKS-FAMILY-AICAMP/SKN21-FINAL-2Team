"""
모델별 RAGAS 평가 (B단계) - 클라우드 모델 전용 빠른 버전
- ollama 제외, 5개 클라우드 모델만 평가
- 응답 캐시 활용으로 재실행 시 즉시 평가 가능
- 출력: ragas_eval_models.json (ollama는 기존 4샘플 데이터 병합)
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

# RAGAS imports (0.4.x - legacy Metric API for evaluate() compatibility)
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import OpenAIEmbeddings

# ─── 설정 ─────────────────────────────────────────────────────────────────────
# 클라우드 모델만 (ollama 제외)
MODELS = [
    {"name": "gpt-4o-mini",      "llm_type": "openai",    "model": "gpt-4o-mini"},
    {"name": "gpt-5.4",          "llm_type": "openai",    "model": "gpt-5.4"},
    {"name": "gpt-5.4-mini",     "llm_type": "openai",    "model": "gpt-5.4-mini"},
    {"name": "gpt-5.4-nano",     "llm_type": "openai",    "model": "gpt-5.4-nano"},
    {"name": "claude-haiku-4-5", "llm_type": "anthropic", "model": "claude-haiku-4-5-20251001"},
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
            resp = await generate_response(llm, sys_prompt, user_input, timeout=60.0)
            elapsed = time.time() - t0
            status = "OK" if not resp.startswith("[") else resp[:15]
            print(f"  Q{i+1:02d}: {elapsed:.1f}s [{status}] {resp[:50].replace(chr(10),' ')}...")
            responses.append(resp)

        all_responses[name] = responses
        print(f"  → {sum(1 for r in responses if not r.startswith('['))} / {len(responses)} 성공")
    return all_responses


def run_ragas(df: pd.DataFrame, all_responses: dict) -> dict:
    """RAGAS faithfulness + answer_relevancy 평가"""
    eval_llm   = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    eval_embed = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))

    metrics = [Faithfulness(), AnswerRelevancy()]

    results = {}
    for cfg in MODELS:
        name      = cfg["name"]
        responses = all_responses.get(name, [])

        print(f"\n[RAGAS] {name} 평가 중...")

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

        dataset = EvaluationDataset(samples=samples)
        try:
            scores = evaluate(
                dataset=dataset,
                metrics=metrics,
                llm=eval_llm,
                embeddings=eval_embed,
                show_progress=True,
            )
            score_df = scores.to_pandas()
            faith_avg   = float(score_df['faithfulness'].mean())   if 'faithfulness'    in score_df else 0.0
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
            import traceback; traceback.print_exc()
            results[name] = {"faithfulness": 0.0, "answer_relevancy": 0.0, "overall": 0.0, "n": n, "error": str(e)}

    return results


async def main():
    print("=" * 55)
    print("  모델별 RAGAS 평가 (B단계) - 클라우드 전용")
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
        # 캐시에 없는 모델만 추가 생성
        missing = [cfg for cfg in MODELS if cfg["name"] not in all_responses]
        if missing:
            print(f"[캐시 미스] {[c['name'] for c in missing]} 추가 생성")
            extra = await generate_all_specific(df, missing)
            all_responses.update(extra)
            RESPONSES_PATH.write_text(json.dumps(all_responses, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        all_responses = await generate_all(df)
        RESPONSES_PATH.write_text(json.dumps(all_responses, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"[캐시 저장] {RESPONSES_PATH}")

    # 2) RAGAS 평가
    ragas_results = run_ragas(df, all_responses)

    # 3) 기존 ollama 결과 병합 (있는 경우)
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text(encoding='utf-8'))
            existing_metrics = existing.get("ragas_metrics", {})
            if "ollama-llama3.2" in existing_metrics and existing_metrics["ollama-llama3.2"].get("n", 0) > 0:
                ragas_results["ollama-llama3.2"] = existing_metrics["ollama-llama3.2"]
                print(f"\n[병합] 기존 ollama 결과 유지 (n={existing_metrics['ollama-llama3.2']['n']})")
        except Exception:
            pass

    # 4) 저장
    output = {"ragas_metrics": ragas_results}
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n[저장] {OUTPUT_PATH}")

    # 5) 결과 테이블 출력
    print("\n" + "━"*62)
    print("  모델별 RAGAS 평가 결과 (0~1점)")
    print("━"*62)
    print(f"  {'모델':<22} {'faithfulness':>13} {'ans_relevancy':>14} {'overall':>9} {'n':>4}")
    print("  " + "─"*58)

    sorted_results = sorted(ragas_results.items(), key=lambda x: x[1].get('overall', 0), reverse=True)
    for name, res in sorted_results:
        print(f"  {name:<22} {res.get('faithfulness',0):>13.3f} {res.get('answer_relevancy',0):>14.3f} "
              f"{res.get('overall',0):>9.3f} {res.get('n',0):>4}")
    print("━"*62)


async def generate_all_specific(df, models_cfg):
    """지정된 모델만 응답 생성"""
    all_responses = {}
    for cfg in models_cfg:
        name     = cfg["name"]
        llm_type = cfg["llm_type"]
        model_id = cfg["model"]
        print(f"\n{'='*55}\n[생성] {name}\n{'='*55}")
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
            resp = await generate_response(llm, sys_prompt, user_input, timeout=60.0)
            elapsed = time.time() - t0
            status = "OK" if not resp.startswith("[") else resp[:15]
            print(f"  Q{i+1:02d}: {elapsed:.1f}s [{status}]")
            responses.append(resp)
        all_responses[name] = responses
    return all_responses


if __name__ == "__main__":
    asyncio.run(main())

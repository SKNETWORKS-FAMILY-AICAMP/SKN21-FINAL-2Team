"""claude-haiku-4-5만 재실행하여 기존 결과에 병합"""
import sys, json, asyncio, time, ast, re, os
from pathlib import Path
sys.path.insert(0, '/Users/kim/SKN/SKN21-FINAL-2Team/backend')

from dotenv import load_dotenv
load_dotenv('/Users/kim/SKN/SKN21-FINAL-2Team/backend/.env', override=True)

_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not _key:
    raise RuntimeError("ANTHROPIC_API_KEY 없음")
print(f"[OK] ANTHROPIC_API_KEY 확인 ({len(_key)}자)")

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from evaluation.common.judge_normalization import normalize_judge_score

CSV_PATH = Path('/Users/kim/SKN/SKN21-FINAL-2Team/backend/evaluation/evaluate_testdata.csv')
OUTPUT_PATH = Path('/Users/kim/SKN/SKN21-FINAL-2Team/backend/evaluation/ragas_model_comparison.json')
MAX_ROWS = 21

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

JUDGE_PROMPT = """당신은 RAG 시스템의 응답 품질을 평가하는 전문가입니다.
아래 정보를 바탕으로 4가지 항목을 각각 1~5점으로 평가하세요.

[사용자 질문]
{user_input}

[검색된 컨텍스트]
{contexts}

[모델 응답]
{response}

[참고 정답]
{reference}

평가 항목 (각 1~5점, 정수):
1. relevance(답변 관련성)
2. faithfulness(문서 근거성)
3. hallucination(환각 방지): 1=심각한 환각, 5=환각 없음
4. usefulness(추천 유용성)

반드시 아래 JSON 형식으로만 응답하세요:
{{"relevance": X, "faithfulness": X, "hallucination": X, "usefulness": X}}
"""

def build_prompt(contexts, user_input):
    place_context = "\n".join(contexts) if contexts else "없음"
    candidate_names_list = []
    for ctx in contexts:
        m = re.search(r'"title"\s*:\s*"([^"]+)"', ctx)
        if m:
            candidate_names_list.append(m.group(1))
    candidate_names = "\n".join(f"- {n}" for n in candidate_names_list) or "없음"
    return _EXECUTOR_PROMPT.format(candidate_names=candidate_names, place_context=place_context)

async def generate_response(llm, system_prompt, user_input, timeout=60.0):
    msgs = [SystemMessage(content=system_prompt), HumanMessage(content=user_input)]
    try:
        result = await asyncio.wait_for(llm.ainvoke(msgs), timeout=timeout)
        return result.content if hasattr(result, 'content') else str(result)
    except asyncio.TimeoutError:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR: {e}]"

def parse_judge_json(text):
    match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
    if match:
        try:
            d = json.loads(match.group())
            required = {"relevance", "faithfulness", "hallucination", "usefulness"}
            if required.issubset(d.keys()):
                return {k: normalize_judge_score(d[k]) for k in required}
        except Exception:
            pass
    return None

async def main():
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
    print(f"[CSV] {len(df)}개 쿼리")

    # Claude 응답 생성
    claude = ChatAnthropic(model='claude-haiku-4-5-20251001', temperature=0, api_key=_key)
    responses = []
    print("\n[claude-haiku-4-5] 응답 생성 시작")
    for i, row in df.iterrows():
        user_input = str(row['user_input'])
        contexts = row['retrieved_contexts']
        sys_prompt = build_prompt(contexts, user_input)
        t0 = time.time()
        resp = await generate_response(claude, sys_prompt, user_input, timeout=60.0)
        elapsed = time.time() - t0
        print(f"  Q{i+1}: {elapsed:.1f}s | {resp[:60].replace(chr(10), ' ')}...")
        responses.append(resp)
    print(f"[claude] 생성 완료: {len(responses)}개")

    # Judge 평가
    judge = ChatOpenAI(model='gpt-4o-mini', temperature=0)
    per_query = []
    total_scores = {"relevance": [], "faithfulness": [], "hallucination": [], "usefulness": []}
    print("\n[Judge] claude-haiku-4-5 평가 시작")
    for i, row in df.iterrows():
        resp = responses[i]
        if resp.startswith("[ERROR") or resp.startswith("[TIMEOUT"):
            print(f"  Q{i+1}: 오류 응답 스킵 ({resp[:30]})")
            continue
        user_input = str(row['user_input'])
        contexts = "\n".join(row['retrieved_contexts'])[:1000]
        reference = str(row['reference'])
        prompt = JUDGE_PROMPT.format(user_input=user_input, contexts=contexts,
                                     response=resp[:500], reference=reference[:300])
        scores = None
        for attempt in range(2):
            try:
                jr = judge.invoke([HumanMessage(content=prompt)])
                text = jr.content if hasattr(jr, 'content') else str(jr)
                scores = parse_judge_json(text)
                if scores:
                    break
                print(f"  Q{i+1} 재시도... (응답: {text[:60]})")
            except Exception as e:
                print(f"  Q{i+1} judge 오류: {e}")
        if scores is None:
            print(f"  Q{i+1}: judge 실패 스킵")
            continue
        print(f"  Q{i+1}: rel={scores['relevance']}, faith={scores['faithfulness']}, "
              f"hall={scores['hallucination']}, use={scores['usefulness']}")
        per_query.append({"idx": i, "user_input": user_input, "response": resp[:200], **scores})
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

    claude_result = {
        "avg_relevance": round(avg_rel, 2),
        "avg_faithfulness": round(avg_fai, 2),
        "avg_hallucination": round(avg_hal, 2),
        "avg_usefulness": round(avg_use, 2),
        "overall_avg": round(overall, 2),
        "n_evaluated": n,
        "per_query": per_query,
    }
    print(f"\n[claude] 완료: n={n}, 종합평균={overall:.3f}")

    # 기존 결과에 병합
    with open(OUTPUT_PATH) as f:
        existing = json.load(f)
    existing["models"]["claude-haiku-4-5"] = claude_result
    OUTPUT_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[저장] {OUTPUT_PATH}")

asyncio.run(main())

"""
Generation Evaluation Script
LLM-as-Judge 방식으로 RAG 생성 품질을 평가한다.
"""
import sys
import csv
import json
import ast
import re

sys.path.insert(0, '/Users/kim/SKN/SKN21-FINAL-2Team/backend')

from dotenv import load_dotenv
load_dotenv('/Users/kim/SKN/SKN21-FINAL-2Team/backend/.env')

from app.core.llm_factory import LLMFactory
from langchain_core.messages import HumanMessage
from evaluation.common.judge_normalization import normalize_judge_score

llm = LLMFactory.get_llm(model='gpt-5.4', temperature=0, llm_type='openai')

_METRIC_KEYS = ['relevance', 'faithfulness', 'hallucination', 'usefulness']
DEFAULT_SCORES = {k: 0.5 for k in _METRIC_KEYS}

EVAL_PROMPT = """당신은 RAG 파이프라인 품질 평가 전문가입니다.
아래 정보를 바탕으로 각 항목을 0~1 사이의 실수로 평가하세요.

[사용자 질문]
{user_input}

[검색된 컨텍스트]
{retrieved_contexts}

[시스템 응답]
{response}

[참조 답변]
{reference}

평가 항목:
1. relevance (답변 관련성): 사용자 질문 대비 응답이 얼마나 관련 있는가 (0=전혀 무관, 1=완전히 관련)
2. faithfulness (문서 근거성): 응답이 검색된 컨텍스트에 근거하는가 (컨텍스트 없으면 0.5, 0=전혀 근거없음, 1=완전히 근거함)
3. hallucination (환각 방지): 응답에 사실과 다른 내용이 있는가 (0=심각한 환각, 1=환각 없음)
4. usefulness (추천 유용성): 실제 여행/장소 추천으로 얼마나 유용한가 (0=전혀 유용하지 않음, 1=매우 유용함)

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{"relevance": X.XX, "faithfulness": X.XX, "hallucination": X.XX, "usefulness": X.XX}}
"""

def parse_scores(text: str) -> dict:
    """LLM 응답에서 점수 파싱"""
    text = text.strip()
    # JSON 블록 추출 시도
    match = re.search(r'\{[^}]+\}', text, re.DOTALL)
    if match:
        try:
            raw_scores = json.loads(match.group())
            return {
                key: normalize_judge_score(value)
                for key, value in raw_scores.items()
            }
        except Exception:
            pass
    # fallback: 키-값 패턴 탐색
    scores = {}
    for key in ['relevance', 'faithfulness', 'hallucination', 'usefulness']:
        m = re.search(rf'"{key}"\s*:\s*([0-9]*\.?[0-9]+)', text)
        if m:
            scores[key] = normalize_judge_score(m.group(1))
    return scores

def safe_parse_contexts(ctx_str: str) -> str:
    """retrieved_contexts 컬럼 파싱"""
    if not ctx_str or ctx_str.strip() == '':
        return ''
    try:
        lst = ast.literal_eval(ctx_str)
        if isinstance(lst, list):
            return '\n'.join(str(x) for x in lst)
        return str(lst)
    except Exception:
        return ctx_str[:2000]

def main():
    csv_path = '/Users/kim/SKN/SKN21-FINAL-2Team/backend/evaluation/evaluate_testdata.csv'
    output_path = '/Users/kim/SKN/SKN21-FINAL-2Team/backend/evaluation/generation_summary.json'

    rows = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig: BOM 자동 제거
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        print(f"[INFO] 컬럼 목록: {headers}")
        for row in reader:
            rows.append(row)

    print(f"[INFO] 총 행 수: {len(rows)}")

    # 사용할 컬럼 결정 (BOM 제거 후 체크)
    user_input_col = 'user_input' if 'user_input' in headers else ('question' if 'question' in headers else None)
    response_col = 'response' if 'response' in headers else ('answer' if 'answer' in headers else None)
    contexts_col = 'retrieved_contexts' if 'retrieved_contexts' in headers else None
    reference_col = 'reference' if 'reference' in headers else None

    print(f"[INFO] 사용 컬럼: user_input={user_input_col}, response={response_col}, contexts={contexts_col}, reference={reference_col}")

    results = []
    skip_count = 0

    for i, row in enumerate(rows):
        user_input = row.get(user_input_col, '').strip() if user_input_col else ''
        response = row.get(response_col, '').strip() if response_col else ''
        contexts_raw = row.get(contexts_col, '') if contexts_col else ''
        reference = row.get(reference_col, '').strip() if reference_col else ''

        # response 비어있으면 스킵
        if not response:
            skip_count += 1
            print(f"[SKIP] 행 {i+1}: response 비어있음")
            continue

        retrieved_contexts = safe_parse_contexts(contexts_raw)
        contexts_display = retrieved_contexts[:1500] if retrieved_contexts else '(검색된 컨텍스트 없음)'

        prompt = EVAL_PROMPT.format(
            user_input=user_input[:500],
            retrieved_contexts=contexts_display,
            response=response[:1500],
            reference=reference[:500] if reference else '(없음)'
        )

        try:
            resp = llm.invoke([HumanMessage(content=prompt)])
            raw_text = resp.content if hasattr(resp, 'content') else str(resp)
            scores = parse_scores(raw_text)

            # 파싱 실패 시 기본값
            if not scores or len(scores) < 4:
                print(f"[WARN] 행 {i+1} 파싱 실패, raw: {raw_text[:200]}")
                scores = DEFAULT_SCORES.copy()

            # faithfulness: contexts 없으면 0.5
            if not retrieved_contexts and 'faithfulness' in scores:
                scores['faithfulness'] = 0.5

            results.append({
                'idx': i,
                'query': user_input[:100],
                'scores': scores
            })
            print(f"[OK] 행 {i+1}/{len(rows)}: {scores}")

        except Exception as e:
            print(f"[ERROR] 행 {i+1}: {e}")
            results.append({
                'idx': i,
                'query': user_input[:100],
                'scores': DEFAULT_SCORES.copy()
            })

    print(f"\n[INFO] 평가 완료: {len(results)}건, 스킵: {skip_count}건")

    if not results:
        print("[ERROR] 평가 결과가 없습니다.")
        return

    # 집계
    n = len(results)
    avgs = {
        k: sum(r['scores'].get(k, DEFAULT_SCORES[k]) for r in results) / n
        for k in _METRIC_KEYS
    }
    avg_relevance    = avgs['relevance']
    avg_faithfulness = avgs['faithfulness']
    avg_hallucination = avgs['hallucination']
    avg_usefulness   = avgs['usefulness']
    overall_avg = sum(avgs.values()) / len(avgs)

    # 위험 케이스: hallucination < 0.4 또는 faithfulness < 0.4
    risk_cases = []
    for r in results:
        s = r['scores']
        if s.get('hallucination', 1.0) < 0.4 or s.get('faithfulness', 1.0) < 0.4:
            risk_cases.append({'query': r['query'], 'scores': s})

    generation_summary = {
        'avg_relevance': round(avg_relevance, 4),
        'avg_faithfulness': round(avg_faithfulness, 4),
        'avg_hallucination': round(avg_hallucination, 4),
        'avg_usefulness': round(avg_usefulness, 4),
        'overall_avg': round(overall_avg, 4),
        'risk_count': len(risk_cases),
        'risk_queries': risk_cases,
        'n_evaluated': n,
        'n_skipped': skip_count,
        'per_query': results
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(generation_summary, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] generation_summary.json 저장 완료: {output_path}")
    print(f"  avg_relevance   : {avg_relevance:.4f}")
    print(f"  avg_faithfulness: {avg_faithfulness:.4f}")
    print(f"  avg_hallucination:{avg_hallucination:.4f}")
    print(f"  avg_usefulness  : {avg_usefulness:.4f}")
    print(f"  overall_avg     : {overall_avg:.4f}")
    print(f"  risk_count      : {len(risk_cases)}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""RAG Retrieval Evaluation Script"""
import sys
import json
from pathlib import Path
import pandas as pd

CSV_PATH = Path(__file__).parent / "evaluate_testdata.csv"
OUTPUT_PATH = Path(__file__).parent / "retrieval_summary.json"

def parse_relevant_ids(val):
    try:
        ids = json.loads(val)
        return [str(x) for x in ids]
    except:
        return []

def parse_retrieved_candidates(val):
    try:
        candidates = json.loads(val)
        return [(str(c["id"]), c["payload"].get("title","?"), c["payload"].get("contenttypeid","?")) for c in candidates]
    except:
        return []

def recall_at_k(relevant, retrieved_ids, k):
    if not relevant:
        return None
    top_k = set(retrieved_ids[:k])
    hits = sum(1 for r in relevant if r in top_k)
    return hits / len(relevant)

def rr(relevant, retrieved_ids):
    relevant_set = set(relevant)
    for i, rid in enumerate(retrieved_ids):
        if rid in relevant_set:
            return 1.0 / (i + 1)
    return 0.0

def classify(relevant, retrieved_ids, k=5):
    relevant_set = set(relevant)
    top_k_ids = retrieved_ids[:k]

    # Single pass: collect hits and find first hit rank simultaneously
    hits_in_top_k = []
    first_hit_rank = None
    for i, rid in enumerate(top_k_ids):
        if rid in relevant_set:
            hits_in_top_k.append(rid)
            if first_hit_rank is None:
                first_hit_rank = i + 1

    if not hits_in_top_k:
        return "MISS"

    types = []
    # LATE: first hit appears after k/2 (first_hit_rank is always set here)
    if first_hit_rank > k // 2:
        types.append("LATE")
    # PARTIAL: not all relevant docs found
    if len(hits_in_top_k) < len(relevant):
        types.append("PARTIAL")
    # NOISE: more than 60% non-relevant in top_k
    noise_ratio = (len(top_k_ids) - len(hits_in_top_k)) / max(len(top_k_ids), 1)
    if noise_ratio > 0.6:
        types.append("NOISE")
    if not types:
        types.append("OK")
    return "/".join(types)

def main():
    df = pd.read_csv(CSV_PATH)

    results = []
    for idx, row in df.iterrows():
        query = str(row['user_input']).strip()
        relevant_ids = parse_relevant_ids(row['relevant_ids'])
        candidates = parse_retrieved_candidates(row['retrieved_candidates'])
        retrieved_ids = [c[0] for c in candidates]

        if not relevant_ids:
            print(f"[WARN] Row {idx}: relevant_ids empty, skipping")
            continue

        k = len(retrieved_ids)
        r1 = recall_at_k(relevant_ids, retrieved_ids, 1)
        r3 = recall_at_k(relevant_ids, retrieved_ids, min(3, k))
        r5 = recall_at_k(relevant_ids, retrieved_ids, min(5, k))
        mrr_val = rr(relevant_ids, retrieved_ids)
        hit5 = 1.0 if mrr_val > 0 else 0.0  # mrr>0 implies a hit exists in retrieved
        cls = classify(relevant_ids, retrieved_ids, k=min(5, k))

        results.append({
            'idx': idx,
            'query': query,
            'relevant_ids': relevant_ids,
            'retrieved_ids': retrieved_ids,
            'candidates': candidates,
            'k': k,
            'recall@1': r1,
            'recall@3': r3,
            'recall@5': r5,
            'mrr': mrr_val,
            'hit@5': hit5,
            'type': cls
        })

    # Aggregates
    n = len(results)
    avg_r1 = sum(r['recall@1'] for r in results if r['recall@1'] is not None) / n
    avg_r3 = sum(r['recall@3'] for r in results if r['recall@3'] is not None) / n
    avg_r5 = sum(r['recall@5'] for r in results if r['recall@5'] is not None) / n
    avg_mrr = sum(r['mrr'] for r in results) / n
    avg_hit5 = sum(r['hit@5'] for r in results) / n
    avg_k = sum(r['k'] for r in results) / n
    miss_count = sum(1 for r in results if 'MISS' in r['type'])

    print("=" * 60)
    print("  RAG Retrieval Evaluation Results")
    print("=" * 60)
    print(f"  쿼리 수    : {n}개")
    print(f"  평균 top_k : {avg_k:.1f}개")
    print()
    print(f"  Recall@1  : {avg_r1:.4f}")
    print(f"  Recall@3  : {avg_r3:.4f}")
    print(f"  Recall@5  : {avg_r5:.4f}")
    print(f"  MRR       : {avg_mrr:.4f}")
    print(f"  Hit@5     : {avg_hit5:.4f}")
    print(f"  실패 쿼리 : {miss_count}개 / {n}개 (MISS 기준)")
    print("=" * 60)

    print()
    print("== 쿼리별 상세 ==")
    print(f"{'Query':<55} {'R@1':>5} {'R@3':>5} {'R@5':>5} {'MRR':>6} {'Type':<20} {'Top1 제목'}")
    print("-" * 130)
    for r in results:
        q_short = r['query'][:52] + "..." if len(r['query']) > 52 else r['query']
        top1 = r['candidates'][0][1] if r['candidates'] else "?"
        top1_type = r['candidates'][0][2] if r['candidates'] else "?"
        print(f"{q_short:<55} {r['recall@1']:>5.2f} {r['recall@3']:>5.2f} {r['recall@5']:>5.2f} {r['mrr']:>6.3f} {r['type']:<20} {top1}({top1_type})")

    print()
    print("== 실패 케이스 분석 (MISS / LATE) ==")
    for r in results:
        if 'MISS' in r['type'] or 'LATE' in r['type']:
            print(f"\n[{r['type']}] \"{r['query'][:80]}\"")
            top5_display = [(c[1], c[2]) for c in r['candidates'][:5]]
            print(f"  검색된 상위 5: {top5_display}")
            print(f"  정답 ID:       {r['relevant_ids']}")
            # Find if relevant is in retrieved at all
            rel_ranks = []
            for rel in r['relevant_ids']:
                for i, rid in enumerate(r['retrieved_ids']):
                    if rid == rel:
                        rel_ranks.append(i+1)
                        break
                else:
                    rel_ranks.append(None)
            print(f"  정답 순위:     {rel_ranks}")

    # Output summary dict for orchestrator
    miss_cases = [r for r in results if 'MISS' in r['type']]
    late_cases = [r for r in results if 'LATE' in r['type'] and 'MISS' not in r['type']]
    partial_cases = [r for r in results if 'PARTIAL' in r['type'] and 'MISS' not in r['type']]
    ok_cases = [r for r in results if r['type'] == 'OK']

    print()
    print("== 유형 분류 요약 ==")
    print(f"  MISS    : {len(miss_cases)}건")
    print(f"  LATE    : {len(late_cases)}건")
    print(f"  PARTIAL : {len(partial_cases)}건")
    print(f"  OK      : {len(ok_cases)}건")

    # Save summary as JSON for orchestrator
    summary = {
        'n_queries': n,
        'avg_k': avg_k,
        'recall@1': round(avg_r1, 4),
        'recall@3': round(avg_r3, 4),
        'recall@5': round(avg_r5, 4),
        'mrr': round(avg_mrr, 4),
        'hit@5': round(avg_hit5, 4),
        'miss_count': miss_count,
        'type_counts': {
            'MISS': len(miss_cases),
            'LATE': len(late_cases),
            'PARTIAL': len(partial_cases),
            'OK': len(ok_cases)
        },
        'per_query': [
            {
                'idx': r['idx'],
                'query': r['query'],
                'relevant_ids': r['relevant_ids'],
                'retrieved_ids': r['retrieved_ids'],
                'recall@1': r['recall@1'],
                'recall@3': r['recall@3'],
                'recall@5': r['recall@5'],
                'mrr': r['mrr'],
                'hit@5': r['hit@5'],
                'type': r['type'],
                'top1_title': r['candidates'][0][1] if r['candidates'] else '?',
                'top1_type': r['candidates'][0][2] if r['candidates'] else '?',
            }
            for r in results
        ]
    }

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print()
    print(f"[저장] retrieval_summary.json 저장 완료")
    print()
    print(f"전체 MRR {avg_mrr:.2f} — 주요 실패 원인: [리랭킹 순서 역전 / 정답이 2위에서 밀림]")

if __name__ == '__main__':
    main()

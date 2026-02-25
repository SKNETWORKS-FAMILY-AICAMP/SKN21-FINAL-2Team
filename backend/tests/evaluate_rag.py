import os
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

# 로컬 실행을 위한 환경 변수 오버라이드 (임포트 전에 반드시 수행!)
os.environ["MYSQL_HOST"] = os.getenv("MYSQL_HOST")
os.environ["MYSQL_PORT"] = os.getenv("MYSQL_PORT")
os.environ["QDRANT_HOST"] = os.getenv("QDRANT_HOST")
os.environ["QDRANT_PORT"] = os.getenv("QDRANT_PORT")

import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory
from openai import OpenAI

# 앱 모델 및 워크플로우 임포트
from app.models.user import User
from app.models.chat import ChatRoom, ChatMessage
from app.agents.graph import workflow

# OpenAI API Key 설정
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set")

# OpenAI 클라이언트 생성
openai_client = OpenAI(api_key=api_key)

# Ragas용 LLM 및 임베딩 모델 설정 (v0.4.3+ 방식)
eval_llm = llm_factory(model="gpt-4o-mini", client=openai_client)
eval_embeddings = embedding_factory(model="openai/text-embedding-3-small", client=openai_client)

# 메트릭 객체 설정 (v0.4.3+ 환경 호환성을 위해 ragas.metrics 객체 사용)
# 이 객체들은 이미 Metric 클래스를 상속받은 상태로 로드됩니다.
faithfulness.llm = eval_llm
answer_relevancy.llm = eval_llm
answer_relevancy.embeddings = eval_embeddings
context_precision.llm = eval_llm
context_recall.llm = eval_llm

async def get_rag_response(question: str):
    """실제 RAG 시스템을 통해 답변과 컨텍스트 추출"""
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
    try:
        result = await graph.ainvoke(inputs)
        print("  [DEBUG] Graph invocation completed.")
        
        answer = result.get("answer", "")
        # candidates 정보를 context 리스트로 변환
        candidates = result.get("candidates", [])
        contexts = []
        for c in candidates:
            name = c.get("name") or c.get("title") or "이름 없음"
            desc = c.get("description") or ""
            contexts.append(f"{name}: {desc[:200]}")
        
        return answer, contexts
    except Exception as e:
        print(f"  [ERROR] Graph execution failed: {e}")
        return "Error in response", []

async def run_evaluation():
    # 1. 테스트 데이터 로드
    data_file = "tests/rag_eval_data.json"
    if not os.path.exists(data_file):
        print(f"[ERROR] Test data file not found: {data_file}")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        test_data = json.load(f)
    
    questions = [d["question"] for d in test_data]
    ground_truths = [d["ground_truth"] for d in test_data]
    
    answers = []
    all_contexts = []
    
    print(f"--- Starting RAG Response Generation for {len(questions)} samples ---")
    for q in questions:
        print(f"Querying: {q}")
        ans, ctx = await get_rag_response(q)
        answers.append(ans)
        all_contexts.append(ctx)
    
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
        result = evaluate(
            dataset,
            metrics=metrics,
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
        
        summary_lines = [
            f"Evaluation Time: {timestamp}",
            "--- Average Scores ---"
        ]
        for metric_name, avg in averages.items():
            summary_lines.append(f"{metric_name}: {avg:.4f}")
        
        summary_content = "\n".join(summary_lines)
        
        # CSV 보고서 저장
        output_file = "tests/evaluation_report.csv"
        df.to_csv(output_file, index=False)
        print(f"\nReport saved to {output_file}")
        
        # 요약 파일 저장
        summary_file = "tests/evaluation_summary.txt"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary_content)
        print(f"Summary saved to {summary_file}")
        
    except Exception as e:
        print(f"[ERROR] Evaluation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_evaluation())

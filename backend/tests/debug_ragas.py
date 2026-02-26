import os
from ragas import evaluate
from ragas.metrics.collections import Faithfulness
from ragas.llms import llm_factory
from openai import OpenAI
from datasets import Dataset

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY not found")
    exit(1)

client = OpenAI(api_key=api_key)
llm = llm_factory("gpt-4o-mini", client=client)

# Minimal dataset
data = {
    "question": ["What is the capital of France?"],
    "answer": ["Paris is the capital of France."],
    "contexts": [["France is a country in Europe. Its capital is Paris."]],
    "ground_truth": ["Paris"]
}
dataset = Dataset.from_dict(data)

metric = Faithfulness(llm)
print(f"Metric type: {type(metric)}")
from ragas.metrics.base import Metric
print(f"Is instance of ragas.metrics.base.Metric: {isinstance(metric, Metric)}")

try:
    print("Starting evaluation...")
    result = evaluate(dataset, metrics=[metric])
    print("Evaluation success!")
    print(result)
except Exception as e:
    print(f"Evaluation failed: {e}")
    import traceback
    traceback.print_exc()

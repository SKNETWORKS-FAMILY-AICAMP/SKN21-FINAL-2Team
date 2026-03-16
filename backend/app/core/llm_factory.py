from langchain_openai import ChatOpenAI
from app.utils.config import LLM_MODEL

class LLMFactory:
    _llm_instances: dict[tuple[str, float], ChatOpenAI] = {}

    @classmethod
    def get_llm(cls, model: str = LLM_MODEL, temperature: float = 0):
        key = (model, float(temperature))
        if key not in cls._llm_instances:
            cls._llm_instances[key] = ChatOpenAI(model=model, temperature=temperature)
        return cls._llm_instances[key]

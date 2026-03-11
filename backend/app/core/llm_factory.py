from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from app.utils.config import LLM_MODEL

class LLMFactory:
    _llm_instances: dict[tuple[str, float], ChatOpenAI] = {}
    _tavily_instances: dict[int, TavilySearchResults] = {}

    @classmethod
    def get_llm(cls, model: str = LLM_MODEL, temperature: float = 0):
        key = (model, float(temperature))
        if key not in cls._llm_instances:
            cls._llm_instances[key] = ChatOpenAI(model=model, temperature=temperature)
        return cls._llm_instances[key]

    @classmethod
    def get_tavily(cls, max_result = 3):
        key = int(max_result)
        if key not in cls._tavily_instances:
            cls._tavily_instances[key] = TavilySearchResults(max_results=max_result)
        return cls._tavily_instances[key]

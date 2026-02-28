from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from app.utils.config import LLM_MODEL

class LLMFactory:
    _llm_instance = None
    _tavily_instance = None

    @classmethod
    def get_llm(cls, model: str = LLM_MODEL, temperature: float = 0):
        if cls._llm_instance is None:
            cls._llm_instance = ChatOpenAI(model=model, temperature=temperature)
        return cls._llm_instance

    @classmethod
    def get_tavily(cls, max_result = 3):
        if cls._tavily_instance is None:
            cls._tavily_instance = TavilySearchResults(max_results=max_result)
        return cls._tavily_instance

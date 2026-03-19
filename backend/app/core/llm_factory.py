from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain.base_language import BaseLanguageModel
from app.utils.config import LLM_MODEL, LLM_TYPE, OLLAMA_BASE_URL

class LLMFactory:
    """
    LLM 인스턴스 팩토리 (싱글톤 패턴)
    - OpenAI API (gpt-4o-mini 등)
    - Ollama 로컬 모델 (qwen2.5:3b 등)
    """
    _llm_instances: dict[tuple[str, float, str, str], BaseLanguageModel] = {}

    @classmethod
    def get_llm(
        cls, 
        model: str = LLM_MODEL, 
        temperature: float = 0,
        llm_type: str = LLM_TYPE,
        base_url: str = OLLAMA_BASE_URL
    ) -> BaseLanguageModel:
        """
        LLM 인스턴스 반환 (캐시됨)
        
        Args:
            model: 모델명 (e.g., "gpt-4o-mini", "qwen2.5:3b")
            temperature: 창의성 (0=결정론적, 1=창의적)
            llm_type: "openai" 또는 "ollama"
            base_url: Ollama 서버 주소 (llm_type="ollama"일 때만 사용)
        
        Returns:
            ChatOpenAI 또는 ChatOllama 인스턴스
        """
        key = (model, float(temperature), llm_type, base_url)
        
        if key not in cls._llm_instances:
            if llm_type.lower() == "ollama":
                cls._llm_instances[key] = ChatOllama(
                    model=model,
                    temperature=temperature,
                    base_url=base_url
                )
            else:  # openai
                cls._llm_instances[key] = ChatOpenAI(
                    model=model,
                    temperature=temperature
                )
        
        return cls._llm_instances[key]

import os
from langchain_openai import ChatOpenAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.language_models import BaseLanguageModel
from app.utils.config import LLM_MODEL, LLM_TYPE, OLLAMA_BASE_URL

class LLMFactory:
    """
    LLM 인스턴스 팩토리 (싱글톤 패턴)
    - OpenAI API (gpt-4o-mini 등)
    - Anthropic Claude API (claude-haiku-4-5 등)
    - Ollama 로컬 LLM (llama3.2, qwen2.5 등)
    - HuggingFace Inference API (Qwen/Qwen2.5-3B-Instruct 등)
    """
    _llm_instances: dict[tuple[str, float, str, str], BaseLanguageModel] = {}

    @classmethod
    def get_llm(
        cls,
        model: str = LLM_MODEL,
        temperature: float = 0,
        llm_type: str = LLM_TYPE,
        # 주의: base_url 파라미터는 하위 호환성을 위해 남겨두되, huggingface 방식에서는 사용하지 않음
        base_url: str = ""
    ) -> BaseLanguageModel:
        """
        LLM 인스턴스 반환 (캐시됨)

        Args:
            model: 모델명 (e.g., "gpt-4o-mini", "claude-haiku-4-5-20251001", "llama3.2")
            temperature: 창의성 (0=결정론적, 1=창의적)
            llm_type: "openai" | "anthropic" | "ollama" | "huggingface"
            base_url: (미사용, 하위 호환용)

        Returns:
            ChatOpenAI, ChatAnthropic, 또는 ChatHuggingFace 인스턴스
        """
        key = (model, float(temperature), llm_type, base_url)

        if key not in cls._llm_instances:
            _llm_type = llm_type.lower()
            if _llm_type == "anthropic":
                from langchain_anthropic import ChatAnthropic
                anthropic_key = os.getenv("ANTHROPIC_API_KEY")
                if not anthropic_key:
                    raise ValueError(
                        "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다. "
                        "llm_type='anthropic' 사용 전 .env 파일을 확인하세요."
                    )
                cls._llm_instances[key] = ChatAnthropic(
                    model=model,
                    temperature=temperature,
                    api_key=anthropic_key,
                )
            elif _llm_type == "ollama":
                cls._llm_instances[key] = ChatOpenAI(
                    model=model,
                    base_url=OLLAMA_BASE_URL,
                    api_key="ollama",
                    temperature=temperature,
                )
            elif _llm_type == "huggingface":
                # HuggingFace Inference API 사용 (HF_TOKEN 환경변수 자동 적용)
                # 모델명 변경: backend/.env 의 OCR_HF_MODEL_ID 또는
                #              backend/app/utils/config.py 의 OCR_LLM_MODEL 기본값 수정
                endpoint = HuggingFaceEndpoint(
                    repo_id=model,
                    temperature=temperature if temperature > 0 else 0.01,  # HF는 0 미지원
                    max_new_tokens=512,
                    task="text-generation"
                )
                cls._llm_instances[key] = ChatHuggingFace(llm=endpoint)
            else:  # openai (기본값, _llm_type == "openai")
                cls._llm_instances[key] = ChatOpenAI(
                    model=model,
                    temperature=temperature
                )

        return cls._llm_instances[key]

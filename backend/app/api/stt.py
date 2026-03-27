from fastapi import APIRouter
from pydantic import BaseModel
from app.core.llm_factory import LLMFactory

router = APIRouter(prefix="/api/stt", tags=["stt"])

LANG_NAMES = {
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "zh-TW": "Chinese (Traditional)",
    "en": "English",
}


class SttCorrectRequest(BaseModel):
    text: str
    language: str  # e.g. "ja", "zh", "en"


class SttCorrectResponse(BaseModel):
    corrected: str


@router.post("/correct", response_model=SttCorrectResponse)
async def correct_stt_text(payload: SttCorrectRequest) -> SttCorrectResponse:
    """
    K-Culture 여행 앱 STT 결과에서 잘못 인식된 한국 지명을 LLM으로 보정한다.
    예) Japanese STT: "コーナン周辺のグルメ" → "江南周辺のグルメ"
    """
    text = payload.text.strip()
    if not text:
        return SttCorrectResponse(corrected=text)

    lang_name = LANG_NAMES.get(payload.language, payload.language)

    prompt = (
        f"You are a text correction assistant for a K-Culture travel app.\n"
        f"The following text was transcribed by a {lang_name} speech-to-text engine. "
        f"Korean place names are often misrecognized as phonetically similar {lang_name} words.\n\n"
        f"Known misrecognitions ({lang_name} STT output → correct Korean place name):\n"
        f"- コーナン / 江南 → 江南(강남)\n"
        f"- 弘大 / ホンデ → 弘大(홍대)\n"
        f"- 梨泰院 / イテウォン → 梨泰院(이태원)\n"
        f"- 明洞 / ミョンドン → 明洞(명동)\n"
        f"- 新村 / シンチョン → 新村(신촌)\n"
        f"- 東大門 / トンデムン → 東大門(동대문)\n"
        f"- 仁寺洞 / インサドン → 仁寺洞(인사동)\n"
        f"- 北村 / ブクチョン → 北村(북촌)\n\n"
        f"Rules:\n"
        f"- Correct ONLY misrecognized Korean place names using the examples above as a guide.\n"
        f"- Do NOT change any other part of the text.\n"
        f"- Return the corrected sentence only, with no explanation.\n\n"
        f"Input: {text}"
    )

    llm = LLMFactory.get_llm(temperature=0.0)
    result = await llm.ainvoke(prompt)
    corrected = result.content.strip() if hasattr(result, "content") else str(result).strip()

    return SttCorrectResponse(corrected=corrected or text)

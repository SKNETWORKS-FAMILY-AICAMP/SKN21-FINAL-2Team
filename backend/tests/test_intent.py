import pytest
from unittest.mock import AsyncMock, patch

from app.agents.intent import intent_node
from app.agents.models.output import IntentOutput, IntentSlots, IntentType, InputType


@pytest.mark.asyncio
async def test_intent_node_uses_update_user_input_from_structured_output():
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = IntentOutput(
        update_user_input="제주도에서 2박 3일 여행 코스를 추천해줘",
        intents=[IntentType.TRIP_PLANNING],
        primary_intent=IntentType.TRIP_PLANNING,
        slots=IntentSlots(input_type=InputType.TEXT),
        summary_title="제주 여행",
        summary_message="제주도 여행 코스 추천 요청",
        input_tags=["제주도", "여행 코스"],
    )

    mock_llm = AsyncMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm

    with patch("app.agents.intent.LLMFactory.get_llm", return_value=mock_llm):
        with patch("app.agents.intent.ChatPromptTemplate.from_messages") as prompt_factory:
            prompt_factory.return_value.__or__.return_value = mock_structured_llm

            result = await intent_node(
                {
                    "user_input": "추천해줘",
                    "messages": [],
                    "prefs_info": "선호 없음",
                    "summary_title": "새 채팅",
                    "summary_message": "",
                }
            )

    assert result["update_user_input"] == "제주도에서 2박 3일 여행 코스를 추천해줘"
    assert result["primary_intent"] == IntentType.TRIP_PLANNING
    assert result["input_tags"] == ["제주도", "여행 코스"]

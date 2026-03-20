import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from app.agents.intent import intent_node
from app.agents.models.output import IntentCoreOutput, IntentSlots, IntentType, InputType, SummaryOutput


@pytest.mark.asyncio
async def test_intent_node_uses_update_user_input_from_structured_output():
    mock_intent_output = IntentCoreOutput(
        update_user_input="서울에서 2박 3일 여행 코스를 추천해줘",
        intents=[IntentType.TRIP_PLANNING],
        primary_intent=IntentType.TRIP_PLANNING,
        slots=IntentSlots(input_type=InputType.TEXT),
        input_tags=["서울", "여행 코스"],
    )
    mock_summary_output = SummaryOutput(
        summary_title="서울 여행",
        summary_message="서울 여행 코스 추천 요청",
    )

    mock_llm = MagicMock()
    
    # We patch ChatPromptTemplate.from_messages to return a mock prompt
    # The __or__ operator on the mock prompt will return an AsyncMock chain
    # We differentiate the chains by returning different AsyncMocks
    mock_intent_chain = AsyncMock()
    mock_intent_chain.ainvoke.return_value = mock_intent_output
    
    mock_summary_chain = AsyncMock()
    mock_summary_chain.ainvoke.return_value = mock_summary_output

    class MockPrompt:
        def __init__(self, is_summary):
            self.is_summary = is_summary
        def __or__(self, other):
            return mock_summary_chain if self.is_summary else mock_intent_chain

    with patch("app.agents.intent.LLMFactory.get_llm", return_value=mock_llm):
        with patch("app.agents.intent.ChatPromptTemplate.from_messages", side_effect=[MockPrompt(is_summary=False), MockPrompt(is_summary=True)]):
            result = await intent_node(
                {
                    "user_input": "추천해줘",
                    "messages": [],
                    "prefs_info": "선호 없음",
                    "summary_title": "explore.newTripPlan",
                    "summary_message": "",
                }
            )

    assert result["update_user_input"] == "서울에서 2박 3일 여행 코스를 추천해줘"
    assert result["primary_intent"] == IntentType.TRIP_PLANNING
    assert result["input_tags"] == ["서울", "여행 코스"]
    assert result["summary_title"] == "서울 여행"
    assert result["summary_message"] == "서울 여행 코스 추천 요청"

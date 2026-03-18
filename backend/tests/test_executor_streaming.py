from unittest.mock import AsyncMock, patch

import pytest

from app.agents.executor import executor_general_node, executor_missing_node, executor_node
from app.agents.models.output import IntentType


@pytest.mark.asyncio
async def test_executor_node_passes_runnable_config_to_streaming():
    state = {
        "candidates": [],
        "candidate_pool": [],
        "user_input": "성수에서 갈만한 곳 추천해줘",
        "messages": [],
        "prefs_info": "",
        "primary_intent": IntentType.PLACE_INQUIRY,
        "slots": None,
        "input_tags": [],
        "follow_up_questions": [],
    }
    config = {"tags": ["stream-test"]}

    with patch("app.agents.executor._build_location_context", new=AsyncMock(return_value="")), \
         patch("app.agents.executor.collect_streamed_text", new=AsyncMock(return_value="추천 답변입니다.")) as mock_collect:
        await executor_node(state, config=config)

    assert mock_collect.await_count == 1
    assert mock_collect.await_args.kwargs["config"] == config


@pytest.mark.asyncio
async def test_executor_missing_node_passes_runnable_config_to_streaming():
    state = {
        "missing_slots": ["duration"],
        "user_input": "여행 계획 짜줘",
        "messages": [],
        "prefs_info": "",
        "slots": None,
        "follow_up_questions": [],
    }
    config = {"tags": ["missing-test"]}

    with patch("app.agents.executor.collect_streamed_text", new=AsyncMock(return_value="추가 정보가 필요합니다.")) as mock_collect:
        await executor_missing_node(state, config=config)

    assert mock_collect.await_args.kwargs["config"] == config


@pytest.mark.asyncio
async def test_executor_general_node_passes_runnable_config_to_streaming():
    state = {
        "user_input": "안녕",
        "messages": [],
        "prefs_info": "",
        "slots": None,
        "follow_up_questions": [],
        "input_lat": None,
        "input_long": None,
    }
    config = {"tags": ["general-test"]}

    with patch("app.agents.executor._build_location_context", new=AsyncMock(return_value="")), \
         patch("app.agents.executor.collect_streamed_text", new=AsyncMock(return_value="안녕하세요.")) as mock_collect:
        await executor_general_node(state, config=config)

    assert mock_collect.await_args.kwargs["config"] == config

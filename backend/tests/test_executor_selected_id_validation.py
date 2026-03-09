import pytest

from app.agents.executor import executor_node


class _Chunk:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    async def astream(self, _prompt_value):
        yield _Chunk("추천 문장입니다. [IDs: invalid, 1]")


@pytest.mark.asyncio
async def test_executor_filters_invalid_selected_ids(monkeypatch):
    from app.utils.llm_factory import LLMFactory

    monkeypatch.setattr(LLMFactory, "get_llm", staticmethod(lambda temperature=0.2, model=None: _FakeLLM()))

    state = {
        "user_input": "추천해줘",
        "messages": [],
        "prefs_info": {},
        "slots": {},
        "candidates": [
            {"id": "1", "payload": {"title": "가게1", "contentid": "1", "addr": "서울"}},
            {"id": "2", "payload": {"title": "가게2", "contentid": "2", "addr": "서울"}},
        ],
        "candidate_pool": [
            {"id": "1", "payload": {"title": "가게1", "contentid": "1", "addr": "서울"}},
            {"id": "2", "payload": {"title": "가게2", "contentid": "2", "addr": "서울"}},
        ],
    }

    result = await executor_node(state)

    assert result["selected_ids"] == ["1"]


@pytest.mark.asyncio
async def test_executor_dispatches_stream_tokens(monkeypatch):
    from app.utils.llm_factory import LLMFactory
    import app.utils.llm_streaming as llm_streaming_module

    emitted = []

    async def _fake_dispatch(name, data, *, config=None):
        emitted.append((name, data, config))

    monkeypatch.setattr(LLMFactory, "get_llm", staticmethod(lambda temperature=0.2, model=None: _FakeLLM()))
    monkeypatch.setattr(llm_streaming_module, "adispatch_custom_event", _fake_dispatch)

    state = {
        "user_input": "추천해줘",
        "messages": [],
        "prefs_info": {},
        "slots": {},
        "candidates": [
            {"id": "1", "payload": {"title": "가게1", "contentid": "1", "addr": "서울"}},
        ],
        "candidate_pool": [
            {"id": "1", "payload": {"title": "가게1", "contentid": "1", "addr": "서울"}},
        ],
    }

    await executor_node(state, config={"callbacks": []})

    assert emitted
    assert emitted[0][0] == "token"
    assert emitted[0][1]["token"].startswith("추천 문장입니다.")


@pytest.mark.asyncio
async def test_executor_passes_plain_human_text_for_text_only(monkeypatch):
    from app.utils.llm_factory import LLMFactory
    from langchain_core.messages import HumanMessage

    captured = {"prompt_value": None}

    class _CaptureLLM:
        async def astream(self, prompt_value):
            captured["prompt_value"] = prompt_value
            yield _Chunk("추천 문장입니다. [IDs: 1]")

    monkeypatch.setattr(LLMFactory, "get_llm", staticmethod(lambda temperature=0.2, model=None: _CaptureLLM()))

    state = {
        "user_input": "강남 데이트 추천",
        "messages": [],
        "prefs_info": {},
        "slots": {},
        "candidates": [
            {"id": "1", "payload": {"title": "가게1", "contentid": "1", "addr": "서울"}},
        ],
        "candidate_pool": [
            {"id": "1", "payload": {"title": "가게1", "contentid": "1", "addr": "서울"}},
        ],
    }

    await executor_node(state)

    prompt_value = captured["prompt_value"]
    assert isinstance(prompt_value, list)
    assert isinstance(prompt_value[-1], HumanMessage)
    assert prompt_value[-1].content == "강남 데이트 추천"

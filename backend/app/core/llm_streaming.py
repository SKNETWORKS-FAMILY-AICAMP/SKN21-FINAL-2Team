import re
from typing import Any

from langchain_core.callbacks.manager import adispatch_custom_event


def extract_text_from_chunk(chunk: Any) -> str:
    if chunk is None:
        return ""

    if isinstance(chunk, dict):
        text = chunk.get("text")
        if isinstance(text, str):
            return text

        content = chunk.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    nested_text = part.get("text")
                    if nested_text:
                        texts.append(str(nested_text))
                elif isinstance(part, str):
                    texts.append(part)
            return "".join(texts)

    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                nested_text = part.get("text")
                if nested_text:
                    texts.append(str(nested_text))
            elif isinstance(part, str):
                texts.append(part)
        return "".join(texts)

    text = getattr(chunk, "text", None)
    if isinstance(text, str):
        return text

    if isinstance(chunk, str):
        return chunk

    return ""


async def collect_streamed_text(llm: Any, prompt_value: Any, config: Any = None) -> str:
    full_content = ""

    async for chunk in llm.astream(prompt_value):
        token_text = extract_text_from_chunk(chunk)
        if not token_text:
            continue

        full_content += token_text
        try:
            await adispatch_custom_event("token", {"token": token_text}, config=config)
        except RuntimeError:
            # runnable context 밖의 직접 호출 테스트에서는 custom event 전파를 건너뛴다.
            pass

    return full_content


def _build_stable_visible_text(full_text: str) -> tuple[str, str | None]:
    visible_text = re.sub(r"\[IDs:\s*.*?\]", "", full_text, flags=re.DOTALL)
    buffering_reason: str | None = None

    partial_id_tag_start = visible_text.rfind("[IDs:")
    if partial_id_tag_start != -1:
        visible_text = visible_text[:partial_id_tag_start]

    # Markdown 링크가 완성되기 전에는 전체 링크 구간을 보류한다.
    markdown_link_start = visible_text.rfind("[")
    if markdown_link_start != -1:
        trailing_text = visible_text[markdown_link_start:]
        if re.match(r"^\[[^\]]*\]\([^)]*$", trailing_text) or re.match(r"^\[[^\]]*$", trailing_text):
            visible_text = visible_text[:markdown_link_start]
            buffering_reason = "link"

    # raw URL은 공백/닫힘 문자로 끝나기 전까지 보류한다.
    raw_url_match = None
    for match in re.finditer(r"https?://[^\s<>\])\"\u201d\u2019]*", visible_text):
        raw_url_match = match

    if raw_url_match and raw_url_match.end() == len(visible_text):
        visible_text = visible_text[:raw_url_match.start()]
        buffering_reason = "link"

    return visible_text, buffering_reason


def compute_visible_delta(full_text: str, previous_visible_text: str) -> tuple[str, str, str | None]:
    visible_text, buffering_reason = _build_stable_visible_text(full_text)

    if len(visible_text) > len(previous_visible_text):
        return visible_text, visible_text[len(previous_visible_text):], buffering_reason
    return visible_text, "", buffering_reason

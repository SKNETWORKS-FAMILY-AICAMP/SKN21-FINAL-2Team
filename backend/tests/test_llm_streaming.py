from app.utils.llm_streaming import compute_visible_delta


def test_compute_visible_delta_buffers_trailing_raw_url() -> None:
    visible_text, delta, buffering_reason = compute_visible_delta(
        "추천 링크는 https://example.com/travel",
        "추천 링크는 ",
    )

    assert visible_text == "추천 링크는 "
    assert delta == ""
    assert buffering_reason == "link"


def test_compute_visible_delta_emits_raw_url_when_followed_by_whitespace() -> None:
    visible_text, delta, buffering_reason = compute_visible_delta(
        "추천 링크는 https://example.com/travel 입니다",
        "추천 링크는 ",
    )

    assert visible_text == "추천 링크는 https://example.com/travel 입니다"
    assert delta == "https://example.com/travel 입니다"
    assert buffering_reason is None


def test_compute_visible_delta_buffers_incomplete_markdown_link() -> None:
    visible_text, delta, buffering_reason = compute_visible_delta(
        "여기 참고하세요 [서울숲](https://example.com/seoul",
        "여기 참고하세요 ",
    )

    assert visible_text == "여기 참고하세요 "
    assert delta == ""
    assert buffering_reason == "link"


def test_compute_visible_delta_emits_completed_markdown_link_once_closed() -> None:
    visible_text, delta, buffering_reason = compute_visible_delta(
        "여기 참고하세요 [서울숲](https://example.com/seoul) 입니다",
        "여기 참고하세요 ",
    )

    assert visible_text == "여기 참고하세요 [서울숲](https://example.com/seoul) 입니다"
    assert delta == "[서울숲](https://example.com/seoul) 입니다"
    assert buffering_reason is None

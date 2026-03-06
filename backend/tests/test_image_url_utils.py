from app.utils.common import is_remote_image_url, to_client_image_url


def test_is_remote_image_url():
    assert is_remote_image_url("http://example.com/a.jpg") is True
    assert is_remote_image_url("https://cdn.visitkorea.or.kr/img/call?cmd=VIEW&id=abc") is True
    assert is_remote_image_url("data:image/jpeg;base64,aaa") is True
    assert is_remote_image_url("/api/static/a.jpg") is False
    assert is_remote_image_url("hot_places/a.jpg") is False


def test_to_client_image_url_with_remote_url():
    cdn_url = "https://cdn.visitkorea.or.kr/img/call?cmd=VIEW&id=4e579ae0-3a02-4938-93a2-5c825928c8a0"
    assert to_client_image_url(cdn_url) == cdn_url


def test_to_client_image_url_with_relative_path():
    assert to_client_image_url("hot_places/seongsu.png") == "/api/static/hot_places/seongsu.png"
    assert to_client_image_url("/hot_places/seongsu.png") == "/api/static/hot_places/seongsu.png"


def test_to_client_image_url_with_static_path():
    assert to_client_image_url("/api/static/hot_places/seongsu.png") == "/api/static/hot_places/seongsu.png"


def test_to_client_image_url_with_empty_value():
    assert to_client_image_url("") == ""
    assert to_client_image_url(None) == ""

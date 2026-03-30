"""Tests for app.utils.db_utils.get_owned_resource_or_404"""
import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

from app.utils.db_utils import get_owned_resource_or_404
from app.utils.error_handler import AppException, ErrorCode


# ── 테스트용 인메모리 모델 정의 ────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class FakeResource(Base):
    __tablename__ = "fake_resource"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String(50))


@pytest.fixture(autouse=True)
def setup_tables(db):
    """conftest의 db 픽스처를 활용해 FakeResource 테이블을 생성/삭제."""
    Base.metadata.create_all(bind=db.get_bind())
    yield
    Base.metadata.drop_all(bind=db.get_bind())


# ── 정상 케이스 ────────────────────────────────────────────────────────────────

def test_returns_resource_when_owner_matches(db):
    """소유자가 일치하면 리소스를 반환해야 한다."""
    resource = FakeResource(id=1, user_id=10, name="서울 타워")
    db.add(resource)
    db.commit()

    result = get_owned_resource_or_404(db, FakeResource, resource_id=1, user_id=10)

    assert result.id == 1
    assert result.name == "서울 타워"


# ── 404 케이스 ─────────────────────────────────────────────────────────────────

def test_raises_404_when_resource_not_found(db):
    """존재하지 않는 ID이면 AppException(404)를 발생시켜야 한다."""
    with pytest.raises(AppException) as exc_info:
        get_owned_resource_or_404(db, FakeResource, resource_id=999, user_id=10)

    assert exc_info.value.status_code == 404


def test_raises_404_when_wrong_owner(db):
    """다른 유저의 리소스이면 AppException(404)를 발생시켜야 한다."""
    resource = FakeResource(id=2, user_id=10, name="경복궁")
    db.add(resource)
    db.commit()

    with pytest.raises(AppException) as exc_info:
        get_owned_resource_or_404(db, FakeResource, resource_id=2, user_id=99)  # 다른 유저

    assert exc_info.value.status_code == 404


# ── 에러 코드 커스터마이징 ────────────────────────────────────────────────────────

def test_uses_custom_error_code(db):
    """error_code 파라미터가 AppException에 그대로 반영돼야 한다."""
    with pytest.raises(AppException) as exc_info:
        get_owned_resource_or_404(
            db, FakeResource, resource_id=999, user_id=1,
            error_code=ErrorCode.CHAT_ROOM_NOT_FOUND,
            message="Room not found",
        )

    assert exc_info.value.error_code == ErrorCode.CHAT_ROOM_NOT_FOUND
    assert exc_info.value.message == "Room not found"


def test_uses_custom_message(db):
    """message 파라미터가 AppException에 그대로 반영돼야 한다."""
    with pytest.raises(AppException) as exc_info:
        get_owned_resource_or_404(
            db, FakeResource, resource_id=999, user_id=1,
            message="Moment not found",
        )

    assert "Moment not found" in exc_info.value.message

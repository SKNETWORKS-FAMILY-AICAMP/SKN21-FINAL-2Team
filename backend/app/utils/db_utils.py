from typing import Type, TypeVar

from sqlalchemy.orm import Session

from app.utils.error_handler import AppException, ErrorCode

T = TypeVar("T")


def get_owned_resource_or_404(
    db: Session,
    model_class: Type[T],
    resource_id: int,
    user_id: int,
    error_code: ErrorCode = ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED,
    message: str = "Resource not found",
) -> T:
    """소유권 확인 + 조회. 없거나 다른 유저의 리소스이면 404 AppException 발생."""
    item = (
        db.query(model_class)
        .filter(model_class.id == resource_id, model_class.user_id == user_id)
        .first()
    )
    if not item:
        raise AppException(error_code, message, 404)
    return item

from app.models.user import User
from app.models.chat import ChatRoom, ChatMessage, ChatPlace
from app.models.reservation import Reservation
from app.utils.security import create_access_token


def _auth_headers(email: str) -> dict:
    token = create_access_token(email)
    return {"Authorization": f"Bearer {token}"}


def test_deactivate_deletes_user_and_owned_data(client, db):
    user = User(email="deactivate@test.com", name="Deact")
    db.add(user)
    db.commit()
    db.refresh(user)

    room = ChatRoom(user_id=user.id, title="r1")
    db.add(room)
    db.commit()
    db.refresh(room)

    msg = ChatMessage(room_id=room.id, message="hi", role="human")
    db.add(msg)
    db.commit()
    db.refresh(msg)

    place = ChatPlace(messages_id=msg.id, place_id=123, name="p")
    db.add(place)

    reservation = Reservation(user_id=user.id, category="etc", name="res")
    db.add(reservation)
    db.commit()

    response = client.post("/api/users/me/deactivate", headers=_auth_headers(user.email))
    assert response.status_code == 200
    assert response.json().get("ok") is True

    assert db.query(User).filter(User.id == user.id).first() is None
    assert db.query(ChatRoom).filter(ChatRoom.user_id == user.id).count() == 0
    assert db.query(ChatMessage).filter(ChatMessage.room_id == room.id).count() == 0
    assert db.query(ChatPlace).filter(ChatPlace.messages_id == msg.id).count() == 0
    assert db.query(Reservation).filter(Reservation.user_id == user.id).count() == 0

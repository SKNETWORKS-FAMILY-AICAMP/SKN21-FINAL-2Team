from app.models.chat import ChatRoom
from app.models.diary import DiaryEntryPlace
from app.models.user import User
from app.utils.security import create_access_token


def _auth_headers(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(email)}"}


def _create_user(db, email: str, name: str) -> User:
    user = User(email=email, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_room(db, user_id: int, title: str):
    room = ChatRoom(user_id=user_id, title=title)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def test_create_diary_saves_user_and_place_snapshots(client, db):
    user = _create_user(db, "diary-owner@example.com", "Owner")
    _create_room(db, user.id, "서울 여행")

    response = client.post(
        "/api/diaries",
        headers=_auth_headers(user.email),
        json={
            "title": "첫 일기",
            "content": "북촌 골목을 천천히 걸었다.",
            "entry_date": "2026-03-09",
            "cover_image_path": "/api/static/diary/cover.jpg",
            "linked_places": [
                {
                    "name": "북촌 한옥마을",
                    "adress": "서울 종로구 계동길 37",
                    "longitude": 126.9861,
                    "latitude": 37.5826,
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user.id
    assert data["linked_chat_room"] is None
    assert len(data["linked_places"]) == 1
    assert data["linked_places"][0]["chat_place_id"] is None
    assert data["linked_places"][0]["name"] == "북촌 한옥마을"
    assert data["linked_places"][0]["adress"] == "서울 종로구 계동길 37"

    snapshots = db.query(DiaryEntryPlace).all()
    assert len(snapshots) == 1
    assert snapshots[0].entry_id == data["id"]
    assert snapshots[0].chat_place_id is None


def test_list_diaries_supports_search_and_latest_sort(client, db):
    user = _create_user(db, "diary-list@example.com", "List User")

    client.post(
        "/api/diaries",
        headers=_auth_headers(user.email),
        json={
            "title": "한강 산책",
            "content": "노을이 예뻤다.",
            "entry_date": "2026-03-08",
        },
    )
    client.post(
        "/api/diaries",
        headers=_auth_headers(user.email),
        json={
            "title": "성수 카페",
            "content": "커피 향이 좋았다.",
            "entry_date": "2026-03-09",
        },
    )

    response = client.get("/api/diaries", headers=_auth_headers(user.email))
    assert response.status_code == 200
    data = response.json()
    assert [item["title"] for item in data] == ["성수 카페", "한강 산책"]

    search_response = client.get(
        "/api/diaries?query=커피",
        headers=_auth_headers(user.email),
    )
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert len(search_data) == 1
    assert search_data[0]["title"] == "성수 카페"


def test_diary_detail_update_delete_are_owner_only(client, db):
    owner = _create_user(db, "diary-owner2@example.com", "Owner 2")
    other = _create_user(db, "diary-other@example.com", "Other")

    create_response = client.post(
        "/api/diaries",
        headers=_auth_headers(owner.email),
        json={
            "title": "비밀 일기",
            "content": "혼자만 보고 싶다.",
            "entry_date": "2026-03-09",
        },
    )
    diary_id = create_response.json()["id"]

    get_response = client.get(
        f"/api/diaries/{diary_id}",
        headers=_auth_headers(other.email),
    )
    assert get_response.status_code == 404

    patch_response = client.patch(
        f"/api/diaries/{diary_id}",
        headers=_auth_headers(other.email),
        json={"title": "수정 시도"},
    )
    assert patch_response.status_code == 404

    delete_response = client.delete(
        f"/api/diaries/{diary_id}",
        headers=_auth_headers(other.email),
    )
    assert delete_response.status_code == 404

    update_response = client.patch(
        f"/api/diaries/{diary_id}",
        headers=_auth_headers(owner.email),
        json={"title": "수정된 일기", "linked_places": []},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "수정된 일기"

    delete_response = client.delete(
        f"/api/diaries/{diary_id}",
        headers=_auth_headers(owner.email),
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["ok"] is True


def test_update_diary_replaces_manual_place_snapshots(client, db):
    user = _create_user(db, "diary-main@example.com", "Main")

    create_response = client.post(
        "/api/diaries",
        headers=_auth_headers(user.email),
        json={
            "title": "장소 있는 일기",
            "content": "처음 위치",
            "entry_date": "2026-03-09",
            "linked_places": [
                {
                    "name": "서울역",
                    "adress": "서울 중구 한강대로 405",
                    "longitude": 126.9707,
                    "latitude": 37.5547,
                }
            ],
        },
    )
    diary_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/diaries/{diary_id}",
        headers=_auth_headers(user.email),
        json={
            "linked_places": [
                {
                    "name": "남산서울타워",
                    "adress": "서울 용산구 남산공원길 105",
                    "longitude": 126.9882,
                    "latitude": 37.5512,
                }
            ]
        },
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert len(data["linked_places"]) == 1
    assert data["linked_places"][0]["name"] == "남산서울타워"
    assert data["linked_places"][0]["adress"] == "서울 용산구 남산공원길 105"

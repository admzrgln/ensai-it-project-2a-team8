from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.RoomController import room_router
from backend.src.Model.Room import Room
from backend.src.Service.JWTService import JwtService

app = FastAPI()
app.include_router(room_router)

client = TestClient(app)

BASE_URL = "/rooms"

jwt = JwtService()
ADMIN = {"Authorization": f"Bearer {jwt.encode_jwt(1, 'admin').access_token}"}
CUSTOMER = {"Authorization": f"Bearer {jwt.encode_jwt(10, 'customer').access_token}"}

room = Room(number="A1", capacity=150, id_room=1)


@patch("backend.src.Controller.RoomController.room_service")
def test_find_all_rooms(mock_service):
    mock_service.find_all.return_value = [room, Room(number="A2", capacity=80, id_room=2)]

    response = client.get(f"{BASE_URL}/")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0] == {"id_room": 1, "number": "A1", "capacity": 150}
    mock_service.find_all.assert_called_once()


@patch("backend.src.Controller.RoomController.room_service")
def test_find_all_rooms_empty(mock_service):
    mock_service.find_all.return_value = []

    response = client.get(f"{BASE_URL}/")

    assert response.status_code == 200
    assert response.json() == []


@patch("backend.src.Controller.RoomController.room_service")
def test_room_by_id(mock_service):
    mock_service.find_by_id.return_value = room

    response = client.get(f"{BASE_URL}/1")

    assert response.status_code == 200
    assert response.json()["number"] == "A1"
    assert response.json()["capacity"] == 150
    mock_service.find_by_id.assert_called_once_with(1)


@patch("backend.src.Controller.RoomController.room_service")
def test_room_not_found(mock_service):
    mock_service.find_by_id.return_value = None

    response = client.get(f"{BASE_URL}/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"


@patch("backend.src.Controller.RoomController.room_service")
def test_room_by_id_invalid_id(mock_service):
    response = client.get(f"{BASE_URL}/abc")

    assert response.status_code == 422
    mock_service.find_by_id.assert_not_called()


@pytest.mark.parametrize(
    ("method", "url"),
    [
        pytest.param("post", f"{BASE_URL}/", id="create"),
        pytest.param("delete", f"{BASE_URL}/1", id="delete"),
    ],
)
def test_rooms_cannot_be_created_or_deleted(method, url):
    response = client.request(method.upper(), url, json={"number": "Z9", "capacity": 10})

    assert response.status_code == 405


@patch("backend.src.Controller.RoomController.room_service")
def test_update_room(mock_service):
    mock_service.update_room.return_value = True

    response = client.put(f"{BASE_URL}/1", json={"number": "B2", "capacity": 90}, headers=ADMIN)

    assert response.status_code == 200
    assert response.json() == {"id_room": 1, "number": "B2", "capacity": 90}
    updated = mock_service.update_room.call_args.args[0]
    assert (updated.id_room, updated.number, updated.capacity) == (1, "B2", 90)


@patch("backend.src.Controller.RoomController.room_service")
def test_update_room_not_found(mock_service):
    mock_service.update_room.return_value = False

    response = client.put(f"{BASE_URL}/999", json={"number": "B2", "capacity": 90}, headers=ADMIN)

    assert response.status_code == 404


@pytest.mark.parametrize("body", [{"number": "B2", "capacity": 0}, {"number": " ", "capacity": 90}])
@patch("backend.src.Controller.RoomController.room_service")
def test_update_room_invalid_values(mock_service, body):
    assert client.put(f"{BASE_URL}/1", json=body, headers=ADMIN).status_code == 422
    mock_service.update_room.assert_not_called()


@patch("backend.src.Controller.RoomController.room_service")
def test_update_room_refused_for_customer(mock_service):
    response = client.put(f"{BASE_URL}/1", json={"number": "B2", "capacity": 90}, headers=CUSTOMER)

    assert response.status_code == 403
    mock_service.update_room.assert_not_called()


@patch("backend.src.Controller.RoomController.room_service")
def test_update_room_refused_without_token(mock_service):
    assert client.put(f"{BASE_URL}/1", json={"number": "B2", "capacity": 90}).status_code in (401, 403)
    mock_service.update_room.assert_not_called()

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.RoomController import room_router
from backend.src.Model.Room import Room

app = FastAPI()
app.include_router(room_router)

client = TestClient(app)

BASE_URL = "/rooms"

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
        pytest.param("put", f"{BASE_URL}/1", id="update"),
        pytest.param("delete", f"{BASE_URL}/1", id="delete"),
    ],
)
def test_rooms_cannot_be_modified(method, url):
    response = client.request(method.upper(), url, json={"number": "Z9", "capacity": 10})

    assert response.status_code == 405

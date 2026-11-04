
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.RoomController import room_router

app = FastAPI()
app.include_router(room_router)

client = TestClient(app)

BASE_URL = "/rooms"

room_data = {
    "room_type": "IMAX",
    "number": "A1",
    "capacity": 150
}


# 1. GET /rooms/ : récupérer toutes les salles
@patch("backend.src.Controller.RoomController.room_service")
def test_find_all_rooms(mock_service):
    mock_service.find_all.return_value = [room_data]

    response = client.get(f"{BASE_URL}/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["room_type"] == "IMAX"
    mock_service.find_all.assert_called_once()


# 2. GET /rooms/type/{room_type} : rechercher par type
@patch("backend.src.Controller.RoomController.room_service")
def test_rooms_by_type(mock_service):
    mock_service.find_by_type.return_value = [room_data]

    response = client.get(f"{BASE_URL}/type/IMAX")

    assert response.status_code == 200
    assert response.json()[0]["room_type"] == "IMAX"
    mock_service.find_by_type.assert_called_once_with("IMAX")


# 3. GET /rooms/{id_room} : rechercher par ID
@patch("backend.src.Controller.RoomController.room_service")
def test_room_by_id(mock_service):
    mock_service.find_by_id.return_value = room_data

    response = client.get(f"{BASE_URL}/1")

    assert response.status_code == 200
    assert response.json()["number"] == "A1"
    mock_service.find_by_id.assert_called_once_with(1)


# 4. POST /rooms/ : créer une salle
@patch("backend.src.Controller.RoomController.room_service")
def test_create_room(mock_service):
    mock_service.create_room.return_value = True

    response = client.post(f"{BASE_URL}/", json=room_data)

    assert response.status_code == 201
    assert response.json()["room_type"] == "IMAX"
    assert response.json()["capacity"] == 150
    mock_service.create_room.assert_called_once()


# 5. PUT /rooms/{id_room} : modifier une salle
@patch("backend.src.Controller.RoomController.room_service")
def test_update_room(mock_service):
    mock_service.update_room.return_value = True

    updated_data = room_data.copy()
    updated_data["capacity"] = 200

    response = client.put(f"{BASE_URL}/1", json=updated_data)

    assert response.status_code == 200
    assert response.json()["message"] == "Room updated successfully"
    assert response.json()["room"]["capacity"] == 200
    mock_service.update_room.assert_called_once()


# 6. DELETE /rooms/{id_room} : supprimer une salle
@patch("backend.src.Controller.RoomController.room_service")
def test_delete_room(mock_service):
    mock_service.delete_room.return_value = True

    response = client.delete(f"{BASE_URL}/1")

    assert response.status_code == 200
    assert response.json()["message"] == "Room 1 deleted successfully"
    mock_service.delete_room.assert_called_once_with(1)


# 7. GET : salle inexistante
@patch("backend.src.Controller.RoomController.room_service")
def test_room_not_found(mock_service):
    mock_service.find_by_id.return_value = None

    response = client.get(f"{BASE_URL}/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"


# 8. POST : capacité invalide (texte)
@patch("backend.src.Controller.RoomController.room_service")
def test_create_room_invalid_capacity(mock_service):
    invalid_data = room_data.copy()
    invalid_data["capacity"] = "invalid"

    response = client.post(f"{BASE_URL}/", json=invalid_data)

    assert response.status_code == 422
    mock_service.create_room.assert_not_called()


# 9. PUT : salle inexistante
@patch("backend.src.Controller.RoomController.room_service")
def test_update_room_not_found(mock_service):
    mock_service.update_room.return_value = False

    response = client.put(f"{BASE_URL}/999", json=room_data)

    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found or update failed"


# 10. DELETE : salle inexistante
@patch("backend.src.Controller.RoomController.room_service")
def test_delete_room_not_found(mock_service):
    mock_service.delete_room.return_value = False

    response = client.delete(f"{BASE_URL}/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"


# 11. POST : la création échoue côté service (coverage 100 %)
@patch("backend.src.Controller.RoomController.room_service")
def test_create_room_failure(mock_service):
    mock_service.create_room.return_value = False

    response = client.post(f"{BASE_URL}/", json=room_data)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid data or creation failed"

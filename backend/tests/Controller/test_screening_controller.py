from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.ScreeningController import screening_router
from backend.src.Service.JWTService import JwtService
from backend.src.Service.ScreeningService import ScreeningError, ScreeningNotFoundError

app = FastAPI()
app.include_router(screening_router)

client = TestClient(app)

BASE_URL = "/screenings"

# Création / modification / suppression de séances : réservées aux administrateurs (F1)
jwt = JwtService()
ADMIN = {"Authorization": f"Bearer {jwt.encode_jwt(3, 'admin').access_token}"}
CUSTOMER = {"Authorization": f"Bearer {jwt.encode_jwt(10, 'customer').access_token}"}

# Plus d'id_admin (lu dans le JWT), ni de prix (grille /tariffs), ni de places (calculées)
screening_data = {
    "id_room": 1,
    "id_movie": 2,
    "date_time": "2026-12-15T20:30:00",
}


# 1. GET /screenings/ : récupérer toutes les séances
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_find_all_screenings(mock_service):
    mock_service.find_all.return_value = [screening_data]

    response = client.get(f"{BASE_URL}/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id_movie"] == 2
    mock_service.find_all.assert_called_once()


# 2. GET /screenings/movie/{id_movie} : chercher par film
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_screenings_by_movie(mock_service):
    mock_service.find_by_movie.return_value = [screening_data]

    response = client.get(f"{BASE_URL}/movie/2")

    assert response.status_code == 200
    assert response.json()[0]["id_movie"] == 2
    mock_service.find_by_movie.assert_called_once_with(2)


# 3. GET /screenings/{id_screening} : chercher par ID
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_screening_by_id(mock_service):
    mock_service.find_by_id.return_value = screening_data

    response = client.get(f"{BASE_URL}/1")

    assert response.status_code == 200
    assert response.json()["id_room"] == 1
    mock_service.find_by_id.assert_called_once_with(1)


# 4. POST /screenings/ : créer une séance
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_create_screening(mock_service):
    mock_service.create_screening.return_value = True

    response = client.post(f"{BASE_URL}/", json=screening_data, headers=ADMIN)

    assert response.status_code == 201
    assert response.json()["id_movie"] == 2
    assert response.json()["id_admin"] == 3  # vient du token, pas du body
    mock_service.create_screening.assert_called_once()


# 5. PUT /screenings/{id_screening} : modifier une séance
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_update_screening(mock_service):
    mock_service.update_screening.return_value = True

    updated_data = screening_data.copy()
    updated_data["id_room"] = 4

    response = client.put(f"{BASE_URL}/1", json=updated_data, headers=ADMIN)

    assert response.status_code == 200
    assert response.json()["message"] == "Screening updated successfully"
    assert response.json()["screening"]["id_room"] == 4
    assert response.json()["screening"]["id_admin"] == 3
    mock_service.update_screening.assert_called_once()


# 6. DELETE /screenings/{id_screening} : supprimer une séance
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_delete_screening(mock_service):
    mock_service.delete_screening.return_value = True

    response = client.delete(f"{BASE_URL}/1", headers=ADMIN)

    assert response.status_code == 200
    assert response.json()["message"] == "Screening 1 deleted successfully"
    mock_service.delete_screening.assert_called_once_with(1)


# 7. GET : séance inexistante
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_screening_not_found(mock_service):
    mock_service.find_by_id.return_value = None

    response = client.get(f"{BASE_URL}/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Screening not found"


# 8. POST : date invalide
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_create_screening_invalid_date(mock_service):
    invalid_data = screening_data.copy()
    invalid_data["date_time"] = "invalid"

    response = client.post(f"{BASE_URL}/", json=invalid_data, headers=ADMIN)

    assert response.status_code == 422
    mock_service.create_screening.assert_not_called()


# 9. PUT : séance inexistante
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_update_screening_not_found(mock_service):
    mock_service.update_screening.side_effect = ScreeningNotFoundError("Screening 999 not found")

    response = client.put(f"{BASE_URL}/999", json=screening_data, headers=ADMIN)

    assert response.status_code == 404
    assert response.json()["detail"] == "Screening 999 not found"


# 10. DELETE : séance inexistante
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_delete_screening_not_found(mock_service):
    mock_service.delete_screening.return_value = False

    response = client.delete(f"{BASE_URL}/999", headers=ADMIN)

    assert response.status_code == 404
    assert response.json()["detail"] == "Screening not found"


# 11. POST : une règle métier n'est pas respectée -> 400 avec le message du service
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_create_screening_business_error(mock_service):
    mock_service.create_screening.side_effect = ScreeningError("User 3 is not an administrator")

    response = client.post(f"{BASE_URL}/", json=screening_data, headers=ADMIN)

    assert response.status_code == 400
    assert response.json()["detail"] == "User 3 is not an administrator"


# 12. PUT : une règle métier n'est pas respectée -> 400 avec le message du service
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_update_screening_business_error(mock_service):
    mock_service.update_screening.side_effect = ScreeningError("Room 1 has only 50 seats (100 requested)")

    response = client.put(f"{BASE_URL}/1", json=screening_data, headers=ADMIN)

    assert response.status_code == 400
    assert response.json()["detail"] == "Room 1 has only 50 seats (100 requested)"


# --- Routes protégées : seuls les administrateurs planifient les séances (F1) ---
@patch("backend.src.Controller.ScreeningController.screening_service")
def test_create_screening_without_token_is_refused(mock_service):
    response = client.post(f"{BASE_URL}/", json=screening_data)
    assert response.status_code in (401, 403)
    mock_service.create_screening.assert_not_called()


@patch("backend.src.Controller.ScreeningController.screening_service")
def test_customer_cannot_create_screening(mock_service):
    response = client.post(f"{BASE_URL}/", json=screening_data, headers=CUSTOMER)
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin only"
    mock_service.create_screening.assert_not_called()


@patch("backend.src.Controller.ScreeningController.screening_service")
def test_customer_cannot_update_screening(mock_service):
    assert client.put(f"{BASE_URL}/1", json=screening_data, headers=CUSTOMER).status_code == 403
    mock_service.update_screening.assert_not_called()


@patch("backend.src.Controller.ScreeningController.screening_service")
def test_customer_cannot_delete_screening(mock_service):
    assert client.delete(f"{BASE_URL}/1", headers=CUSTOMER).status_code == 403
    mock_service.delete_screening.assert_not_called()


@patch("backend.src.Controller.ScreeningController.screening_service")
def test_id_admin_in_body_is_ignored(mock_service):
    """Un admin ne peut pas planifier une séance au nom d'un autre : l'id vient du token."""
    mock_service.create_screening.return_value = True

    response = client.post(f"{BASE_URL}/", json={**screening_data, "id_admin": 99}, headers=ADMIN)

    assert response.status_code == 201
    sent = mock_service.create_screening.call_args.args[0]
    assert sent.id_admin == 3


@patch("backend.src.Controller.ScreeningController.screening_service")
def test_schedule_is_public(mock_service):
    """Consulter le programme ne demande pas de compte (le client parcourt avant de réserver)."""
    mock_service.find_all.return_value = []
    assert client.get(f"{BASE_URL}/").status_code == 200

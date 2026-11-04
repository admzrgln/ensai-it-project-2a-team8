
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.MovieController import movie_router
from backend.src.Service.JWTService import JwtService
from backend.src.Service.OmdbClient import OmdbError

app = FastAPI()
app.include_router(movie_router)

client = TestClient(app)

BASE_URL = "/movies"

# Création / modification / suppression de films : réservées aux administrateurs
jwt = JwtService()
ADMIN = {"Authorization": f"Bearer {jwt.encode_jwt(1, 'admin').access_token}"}
CUSTOMER = {"Authorization": f"Bearer {jwt.encode_jwt(10, 'customer').access_token}"}

movie_data = {
    "title": "Inception",
    "duration": 148,
    "genre": "Sci-Fi",
    "external_id": "tt1375666",
    "poster_url": "https://example.com/inception.jpg"
}


# 1. GET /movies/ : récupérer tous les films
@patch("backend.src.Controller.MovieController.movie_service")
def test_find_all_movies(mock_service):
    mock_service.find_all.return_value = [movie_data]

    response = client.get(f"{BASE_URL}/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Inception"
    mock_service.find_all.assert_called_once()


# 2. GET /movies/search/{title} : rechercher par titre
@patch("backend.src.Controller.MovieController.movie_service")
def test_movie_by_title(mock_service):
    mock_service.find_by_title.return_value = movie_data

    response = client.get(f"{BASE_URL}/search/Inception")

    assert response.status_code == 200
    assert response.json()["title"] == "Inception"
    mock_service.find_by_title.assert_called_once_with("Inception")


# 3. GET /movies/{id_movie} : rechercher par ID
@patch("backend.src.Controller.MovieController.movie_service")
def test_movie_by_id(mock_service):
    mock_service.find_by_id.return_value = movie_data

    response = client.get(f"{BASE_URL}/1")

    assert response.status_code == 200
    assert response.json()["title"] == "Inception"
    mock_service.find_by_id.assert_called_once_with(1)


# 4. POST /movies/ : créer un film
@patch("backend.src.Controller.MovieController.movie_service")
def test_create_movie(mock_service):
    mock_service.create_movie.return_value = True

    response = client.post(f"{BASE_URL}/", json=movie_data, headers=ADMIN)

    assert response.status_code == 201
    assert response.json()["title"] == "Inception"
    mock_service.create_movie.assert_called_once()


# 5. PUT /movies/{id_movie} : modifier un film
@patch("backend.src.Controller.MovieController.movie_service")
def test_update_movie(mock_service):
    mock_service.update_movie.return_value = True

    updated_data = movie_data.copy()
    updated_data["title"] = "Inception Updated"

    response = client.put(f"{BASE_URL}/1", json=updated_data, headers=ADMIN)

    assert response.status_code == 200
    assert response.json()["message"] == "Movie updated successfully"
    mock_service.update_movie.assert_called_once()


# 6. DELETE /movies/{id_movie} : supprimer un film
@patch("backend.src.Controller.MovieController.movie_service")
def test_delete_movie(mock_service):
    mock_service.delete_movie.return_value = True

    response = client.delete(f"{BASE_URL}/1", headers=ADMIN)

    assert response.status_code == 200
    assert response.json()["message"] == "Movie 1 deleted successfully"
    mock_service.delete_movie.assert_called_once_with(1)


# 7. GET : film inexistant
@patch("backend.src.Controller.MovieController.movie_service")
def test_movie_not_found(mock_service):
    mock_service.find_by_id.return_value = None

    response = client.get(f"{BASE_URL}/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


# 8. POST : durée invalide (texte au lieu d'un entier)
@patch("backend.src.Controller.MovieController.movie_service")
def test_create_movie_invalid_duration(mock_service):
    invalid_data = movie_data.copy()
    invalid_data["duration"] = "invalid"

    response = client.post(f"{BASE_URL}/", json=invalid_data, headers=ADMIN)

    assert response.status_code == 422
    mock_service.create_movie.assert_not_called()


# 9. PUT : film inexistant
@patch("backend.src.Controller.MovieController.movie_service")
def test_update_movie_not_found(mock_service):
    mock_service.update_movie.return_value = False

    response = client.put(f"{BASE_URL}/999", json=movie_data, headers=ADMIN)

    assert response.status_code == 404


# 10. DELETE : film inexistant
@patch("backend.src.Controller.MovieController.movie_service")
def test_delete_movie_not_found(mock_service):
    mock_service.delete_movie.return_value = False

    response = client.delete(f"{BASE_URL}/999", headers=ADMIN)

    assert response.status_code == 404


# --- Cas supplémentaires (coverage 100 %) ---------------------------------------
# 11. GET /movies/search/{title} : titre inconnu
@patch("backend.src.Controller.MovieController.movie_service")
def test_movie_by_title_not_found(mock_service):
    mock_service.find_by_title.return_value = None

    response = client.get(f"{BASE_URL}/search/Inconnu")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


# 12. POST : la création échoue côté service
@patch("backend.src.Controller.MovieController.movie_service")
def test_create_movie_failure(mock_service):
    mock_service.create_movie.return_value = False

    response = client.post(f"{BASE_URL}/", json=movie_data, headers=ADMIN)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid data or creation failed"


# 13. GET /movies/omdb/search/{title}
@patch("backend.src.Controller.MovieController.movie_service")
def test_search_omdb(mock_service):
    mock_service.search_omdb.return_value = [{"imdb_id": "tt1375666", "title": "Inception"}]

    response = client.get(f"{BASE_URL}/omdb/search/Inception")

    assert response.status_code == 200
    assert response.json()[0]["imdb_id"] == "tt1375666"
    mock_service.search_omdb.assert_called_once_with("Inception")


@patch("backend.src.Controller.MovieController.movie_service")
def test_search_omdb_service_error(mock_service):
    mock_service.search_omdb.side_effect = OmdbError("timeout")

    response = client.get(f"{BASE_URL}/omdb/search/Inception")

    assert response.status_code == 502
    assert response.json()["detail"] == "OMDb service error"


# 14. POST /movies/omdb/import/{imdb_id}
@patch("backend.src.Controller.MovieController.movie_service")
def test_import_from_omdb(mock_service):
    mock_service.import_from_omdb.return_value = {"id_movie": 1, **movie_data}

    response = client.post(f"{BASE_URL}/omdb/import/tt1375666")

    assert response.status_code == 201
    assert response.json()["title"] == "Inception"
    mock_service.import_from_omdb.assert_called_once_with("tt1375666")


@patch("backend.src.Controller.MovieController.movie_service")
def test_import_from_omdb_not_found(mock_service):
    mock_service.import_from_omdb.side_effect = LookupError("not found")
    response = client.post(f"{BASE_URL}/omdb/import/tt0000000")
    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found on OMDb"


@patch("backend.src.Controller.MovieController.movie_service")
def test_import_from_omdb_service_error(mock_service):
    mock_service.import_from_omdb.side_effect = OmdbError("timeout")
    response = client.post(f"{BASE_URL}/omdb/import/tt1375666")
    assert response.status_code == 502


@patch("backend.src.Controller.MovieController.movie_service")
def test_import_from_omdb_failure(mock_service):
    mock_service.import_from_omdb.side_effect = RuntimeError("insert failed")
    response = client.post(f"{BASE_URL}/omdb/import/tt1375666")
    assert response.status_code == 400
    assert response.json()["detail"] == "Import failed"


# --- Routes protégées : seuls les administrateurs peuvent modifier le catalogue ---
@patch("backend.src.Controller.MovieController.movie_service")
def test_create_movie_without_token_is_refused(mock_service):
    response = client.post(f"{BASE_URL}/", json=movie_data)
    assert response.status_code in (401, 403)
    mock_service.create_movie.assert_not_called()


@patch("backend.src.Controller.MovieController.movie_service")
def test_customer_cannot_create_movie(mock_service):
    response = client.post(f"{BASE_URL}/", json=movie_data, headers=CUSTOMER)
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin only"
    mock_service.create_movie.assert_not_called()


@patch("backend.src.Controller.MovieController.movie_service")
def test_customer_cannot_update_movie(mock_service):
    assert client.put(f"{BASE_URL}/1", json=movie_data, headers=CUSTOMER).status_code == 403
    mock_service.update_movie.assert_not_called()


@patch("backend.src.Controller.MovieController.movie_service")
def test_customer_cannot_delete_movie(mock_service):
    assert client.delete(f"{BASE_URL}/1", headers=CUSTOMER).status_code == 403
    mock_service.delete_movie.assert_not_called()

from unittest.mock import MagicMock, patch

import pytest
import requests

from backend.src.Service.OmdbClient import OmdbClient, OmdbError

REQUESTS_GET = "backend.src.Service.OmdbClient.requests.get"


def fake_response(json_data: dict, raise_error: Exception | None = None) -> MagicMock:
    """Fausse réponse HTTP de requests."""
    response = MagicMock()
    response.json.return_value = json_data
    if raise_error is not None:
        response.raise_for_status.side_effect = raise_error
    return response


@pytest.fixture
def client():
    return OmdbClient(api_key="test-key")


def test_init_uses_explicit_api_key():
    assert OmdbClient(api_key="abc").api_key == "abc"


def test_init_reads_api_key_from_environment(monkeypatch):
    monkeypatch.setenv("OMDB_API_KEY", "from-env")

    assert OmdbClient().api_key == "from-env"


def test_init_without_key_raises_key_error(monkeypatch):
    monkeypatch.delenv("OMDB_API_KEY", raising=False)

    with pytest.raises(KeyError):
        OmdbClient()


def test_search_returns_list_of_results(client):
    results = [
        {"Title": "Inception", "Year": "2010", "imdbID": "tt1375666", "Poster": "url1"},
        {"Title": "Inception: The Cobol Job", "Year": "2010", "imdbID": "tt5295894", "Poster": "url2"},
    ]
    with patch(REQUESTS_GET, return_value=fake_response({"Response": "True", "Search": results})):
        assert client.search("Inception") == results


def test_search_sends_expected_request(client):
    with patch(REQUESTS_GET, return_value=fake_response({"Response": "True", "Search": []})) as mock_get:
        client.search("Inception")

    mock_get.assert_called_once_with(
        "https://www.omdbapi.com/",
        params={"apikey": "test-key", "s": "Inception", "type": "movie"},
        timeout=5,
    )


def test_search_no_result_returns_empty_list(client):
    response = fake_response({"Response": "False", "Error": "Movie not found!"})
    with patch(REQUESTS_GET, return_value=response):
        assert client.search("zzzzzzzz") == []


def test_get_by_imdb_id_returns_details(client):
    details = {
        "Response": "True",
        "Title": "Inception",
        "Runtime": "148 min",
        "Genre": "Action, Sci-Fi, Thriller",
        "imdbID": "tt1375666",
    }
    with patch(REQUESTS_GET, return_value=fake_response(details)):
        assert client.get_by_imdb_id("tt1375666") == details


def test_get_by_imdb_id_sends_expected_request(client):
    with patch(REQUESTS_GET, return_value=fake_response({"Response": "True"})) as mock_get:
        client.get_by_imdb_id("tt1375666")

    mock_get.assert_called_once_with(
        "https://www.omdbapi.com/",
        params={"apikey": "test-key", "i": "tt1375666", "plot": "short"},
        timeout=5,
    )


def test_get_by_imdb_id_not_found_returns_none(client):
    response = fake_response({"Response": "False", "Error": "Incorrect IMDb ID, movie not found!"})
    with patch(REQUESTS_GET, return_value=response):
        assert client.get_by_imdb_id("tt0000000") is None


def test_not_found_detection_is_case_insensitive(client):
    response = fake_response({"Response": "False", "Error": "MOVIE NOT FOUND!"})
    with patch(REQUESTS_GET, return_value=response):
        assert client.get_by_imdb_id("tt0000000") is None


# ---------------------------------------------------------------------------
# Erreurs
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "network_error",
    [
        requests.ConnectionError("no network"),
        requests.Timeout("too slow"),
    ],
)
def test_network_error_raises_omdb_error(client, network_error):
    with patch(REQUESTS_GET, side_effect=network_error):
        with pytest.raises(OmdbError, match="OMDb unreachable") as exc_info:
            client.search("Inception")

    # l'erreur d'origine est conservée (raise ... from error)
    assert exc_info.value.__cause__ is network_error


def test_http_error_raises_omdb_error(client):
    http_error = requests.HTTPError("500 Server Error")
    with patch(REQUESTS_GET, return_value=fake_response({}, raise_error=http_error)):
        with pytest.raises(OmdbError, match="OMDb unreachable"):
            client.get_by_imdb_id("tt1375666")


def test_invalid_api_key_raises_omdb_error(client):
    response = fake_response({"Response": "False", "Error": "Invalid API key!"})
    with patch(REQUESTS_GET, return_value=response):
        with pytest.raises(OmdbError, match="Invalid API key"):
            client.search("Inception")


def test_quota_exceeded_raises_omdb_error(client):
    response = fake_response({"Response": "False", "Error": "Request limit reached!"})
    with patch(REQUESTS_GET, return_value=response):
        with pytest.raises(OmdbError, match="Request limit reached"):
            client.get_by_imdb_id("tt1375666")


def test_too_many_results_raises_omdb_error(client):
    """Une erreur OMDb qui ne contient pas 'not found' n'est pas un cas normal."""
    response = fake_response({"Response": "False", "Error": "Too many results."})
    with patch(REQUESTS_GET, return_value=response):
        with pytest.raises(OmdbError, match="Too many results"):
            client.search("a")

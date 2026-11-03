from unittest.mock import MagicMock

import pytest

from backend.src.Model.Movie import Movie
from backend.src.Service.MovieService import MovieService, _parse_runtime
from backend.src.Service.OmdbClient import OmdbError


@pytest.fixture
def service(monkeypatch):
    """MovieService dont le DAO et le client OMDb sont remplacés par des mocks."""
    # OmdbClient() lit cette variable à la création
    monkeypatch.setenv("OMDB_API_KEY", "fake-key")

    s = MovieService()
    s.movie_dao = MagicMock()
    s.omdb_client = MagicMock()
    return s


def make_movie(**overrides) -> Movie:
    data = dict(
        title="Inception",
        duration=148,
        genre="Sci-Fi",
        external_id="tt1375666",
        poster_url="https://example.com/inception.jpg",
        id_movie=1,
    )
    data.update(overrides)
    return Movie(**data)


def make_omdb_data(**overrides) -> dict:
    """Réponse type de OMDb pour get_by_imdb_id."""
    data = {
        "Title": "Inception",
        "Runtime": "148 min",
        "Genre": "Action, Sci-Fi, Thriller",
        "imdbID": "tt1375666",
        "Poster": "https://example.com/inception.jpg",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    "runtime, expected",
    [
        ("136 min", 136),
        ("90", 90),
        ("N/A", 0),
        ("", 0),
        ("abc min", 0),
        (None, 0),
    ],
)
def test_parse_runtime(runtime, expected):
    assert _parse_runtime(runtime) == expected


def test_find_all_delegates_to_dao(service):
    movies = [make_movie(id_movie=1), make_movie(id_movie=2, title="Dune")]
    service.movie_dao.find_all.return_value = movies

    result = service.find_all()

    assert result == movies
    service.movie_dao.find_all.assert_called_once()


def test_find_by_id_found(service):
    movie = make_movie()
    service.movie_dao.find_by_id.return_value = movie

    assert service.find_by_id(1) is movie
    service.movie_dao.find_by_id.assert_called_once_with(1)


def test_find_by_id_not_found(service):
    service.movie_dao.find_by_id.return_value = None

    assert service.find_by_id(999) is None


def test_find_by_title_adds_wildcards(service):
    """Le service doit entourer le titre de % pour que le ILIKE du DAO fasse une recherche partielle."""
    movie = make_movie()
    service.movie_dao.find_by_title.return_value = movie

    result = service.find_by_title("Incep")

    assert result is movie
    service.movie_dao.find_by_title.assert_called_once_with("%Incep%")


def test_find_by_title_not_found(service):
    service.movie_dao.find_by_title.return_value = None

    assert service.find_by_title("Inconnu") is None


# CRUD

def test_create_movie_success(service):
    movie = make_movie(id_movie=None)
    service.movie_dao.insert_movie.return_value = True

    assert service.create_movie(movie) is True
    service.movie_dao.insert_movie.assert_called_once_with(movie)


def test_create_movie_failure(service):
    service.movie_dao.insert_movie.return_value = False

    assert service.create_movie(make_movie(id_movie=None)) is False


def test_update_movie_without_id_is_refused(service):
    """Clause de garde : sans id, le DAO ne doit même pas être appelé."""
    movie = make_movie(id_movie=None)

    assert service.update_movie(movie) is False
    service.movie_dao.update_movie.assert_not_called()


def test_update_movie_success(service):
    movie = make_movie(id_movie=8)
    service.movie_dao.update_movie.return_value = True

    assert service.update_movie(movie) is True
    service.movie_dao.update_movie.assert_called_once_with(movie)


def test_update_movie_dao_failure(service):
    service.movie_dao.update_movie.return_value = False

    assert service.update_movie(make_movie(id_movie=8)) is False


def test_delete_movie_success(service):
    service.movie_dao.movie_delete.return_value = True

    assert service.delete_movie(7) is True
    service.movie_dao.movie_delete.assert_called_once_with(7)


def test_delete_movie_not_found(service):
    service.movie_dao.movie_delete.return_value = False

    assert service.delete_movie(999) is False


# OMdb

def test_search_omdb_delegates_to_client(service):
    results = [{"Title": "Inception", "imdbID": "tt1375666"}]
    service.omdb_client.search.return_value = results

    assert service.search_omdb("Inception") == results
    service.omdb_client.search.assert_called_once_with("Inception")


def test_search_omdb_propagates_omdb_error(service):
    service.omdb_client.search.side_effect = OmdbError("OMDb unreachable")

    with pytest.raises(OmdbError):
        service.search_omdb("Inception")


def test_import_from_omdb_returns_existing_movie(service):
    """Si le film est déjà en base, on le renvoie sans appeler OMDb ni insérer."""
    existing = make_movie()
    service.movie_dao.find_by_external_id.return_value = existing

    result = service.import_from_omdb("tt1375666")

    assert result is existing
    service.omdb_client.get_by_imdb_id.assert_not_called()
    service.movie_dao.insert_movie.assert_not_called()


def test_import_from_omdb_creates_movie(service):
    service.movie_dao.find_by_external_id.return_value = None
    service.omdb_client.get_by_imdb_id.return_value = make_omdb_data()
    service.movie_dao.insert_movie.return_value = True

    movie = service.import_from_omdb("tt1375666")

    assert movie.title == "Inception"
    assert movie.duration == 148
    assert movie.genre == "Action"
    assert movie.external_id == "tt1375666"
    assert movie.poster_url == "https://example.com/inception.jpg"
    service.omdb_client.get_by_imdb_id.assert_called_once_with("tt1375666")
    service.movie_dao.insert_movie.assert_called_once_with(movie)


def test_import_from_omdb_poster_na_becomes_empty_string(service):
    service.movie_dao.find_by_external_id.return_value = None
    service.omdb_client.get_by_imdb_id.return_value = make_omdb_data(Poster="N/A")
    service.movie_dao.insert_movie.return_value = True

    movie = service.import_from_omdb("tt1375666")

    assert movie.poster_url == ""


def test_import_from_omdb_unknown_runtime_gives_zero_duration(service):
    service.movie_dao.find_by_external_id.return_value = None
    service.omdb_client.get_by_imdb_id.return_value = make_omdb_data(Runtime="N/A")
    service.movie_dao.insert_movie.return_value = True

    movie = service.import_from_omdb("tt1375666")

    assert movie.duration == 0


def test_import_from_omdb_movie_not_found_on_omdb(service):
    service.movie_dao.find_by_external_id.return_value = None
    service.omdb_client.get_by_imdb_id.return_value = None

    with pytest.raises(LookupError):
        service.import_from_omdb("tt0000000")

    service.movie_dao.insert_movie.assert_not_called()


def test_import_from_omdb_insertion_failure(service):
    service.movie_dao.find_by_external_id.return_value = None
    service.omdb_client.get_by_imdb_id.return_value = make_omdb_data()
    service.movie_dao.insert_movie.return_value = False

    with pytest.raises(RuntimeError):
        service.import_from_omdb("tt1375666")


def test_import_from_omdb_propagates_omdb_error(service):
    service.movie_dao.find_by_external_id.return_value = None
    service.omdb_client.get_by_imdb_id.side_effect = OmdbError("OMDb unreachable")

    with pytest.raises(OmdbError):
        service.import_from_omdb("tt1375666")

    service.movie_dao.insert_movie.assert_not_called()
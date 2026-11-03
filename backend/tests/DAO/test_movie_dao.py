from unittest.mock import patch

import pytest

from backend.src.DAO.MovieDAO import MovieDao
from backend.src.Model.Movie import Movie


@pytest.fixture
def sql_query():
    """Remplace DBConnector dans MovieDAO : renvoie le mock de sql_query."""
    with patch("backend.src.DAO.MovieDAO.DBConnector") as connector_cls:
        yield connector_cls.return_value.sql_query


@pytest.fixture
def dao():
    return MovieDao()


def movie_row(**overrides) -> dict:
    """Ligne SQL telle que renvoyée par RealDictCursor."""
    row = {
        "id_movie": 1,
        "title": "Inception",
        "duration": 148,
        "genre": "Sci-Fi",
        "external_id": "tt1375666",
        "poster_url": "https://example.com/inception.jpg",
    }
    row.update(overrides)
    return row


def make_movie(**overrides) -> Movie:
    data = dict(
        title="Inception",
        duration=148,
        genre="Sci-Fi",
        external_id="tt1375666",
        poster_url="https://example.com/inception.jpg",
        id_movie=None,
    )
    data.update(overrides)
    return Movie(**data)


def test_find_all_maps_rows_to_movies(dao, sql_query):
    sql_query.return_value = [movie_row(id_movie=1), movie_row(id_movie=2, title="Dune")]

    movies = dao.find_all()

    assert [m.id_movie for m in movies] == [1, 2]
    assert [m.title for m in movies] == ["Inception", "Dune"]
    assert all(isinstance(m, Movie) for m in movies)
    assert sql_query.call_args.kwargs["return_type"] == "all"


@pytest.mark.parametrize("empty", [[], None])
def test_find_all_empty_returns_empty_list(dao, sql_query, empty):
    sql_query.return_value = empty

    assert dao.find_all() == []


def test_find_all_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_all()


def test_find_by_id_found(dao, sql_query):
    sql_query.return_value = movie_row(id_movie=5, title="Dune")

    movie = dao.find_by_id(5)

    assert isinstance(movie, Movie)
    assert movie.id_movie == 5
    assert movie.title == "Dune"
    assert sql_query.call_args.kwargs["data"] == {"id_movie": 5}
    assert sql_query.call_args.kwargs["return_type"] == "one"


def test_find_by_id_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.find_by_id(999) is None


def test_find_by_id_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_by_id(1)


def test_find_by_title_found(dao, sql_query):
    sql_query.return_value = movie_row()

    movie = dao.find_by_title("%Incep%")

    assert movie.title == "Inception"
    assert sql_query.call_args.kwargs["data"] == {"title": "%Incep%"}
    assert "ILIKE" in sql_query.call_args.args[0]


def test_find_by_title_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.find_by_title("%zzz%") is None


def test_find_by_title_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_by_title("%x%")


def test_find_by_external_id_found(dao, sql_query):
    sql_query.return_value = movie_row()

    movie = dao.find_by_external_id("tt1375666")

    assert movie.external_id == "tt1375666"
    assert sql_query.call_args.kwargs["data"] == {"external_id": "tt1375666"}


def test_find_by_external_id_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.find_by_external_id("tt0000000") is None


def test_find_by_external_id_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_by_external_id("tt1375666")


def test_insert_movie_success_sets_generated_id(dao, sql_query):
    sql_query.return_value = {"id_movie": 42}
    movie = make_movie()

    assert dao.insert_movie(movie) is True
    assert movie.id_movie == 42
    assert sql_query.call_args.kwargs["data"] == {
        "title": "Inception",
        "duration": 148,
        "genre": "Sci-Fi",
        "external_id": "tt1375666",
        "poster_url": "https://example.com/inception.jpg",
    }


def test_insert_movie_no_row_returned(dao, sql_query):
    sql_query.return_value = None
    movie = make_movie()

    assert dao.insert_movie(movie) is False
    assert movie.id_movie is None


def test_insert_movie_database_error_returns_false(dao, sql_query):
    """Contrairement aux find_*, l'insertion avale l'erreur et renvoie False."""
    sql_query.side_effect = Exception("duplicate key")
    movie = make_movie()

    assert dao.insert_movie(movie) is False
    assert movie.id_movie is None


def test_update_movie_success(dao, sql_query):
    sql_query.return_value = {"id_movie": 8}
    movie = make_movie(id_movie=8, title="B")

    assert dao.update_movie(movie) is True
    assert sql_query.call_args.kwargs["data"]["id_movie"] == 8
    assert sql_query.call_args.kwargs["data"]["title"] == "B"


def test_update_movie_without_id_does_not_query(dao, sql_query):
    assert dao.update_movie(make_movie(id_movie=None)) is False
    sql_query.assert_not_called()


def test_update_movie_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.update_movie(make_movie(id_movie=999)) is False


def test_update_movie_database_error_returns_false(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    assert dao.update_movie(make_movie(id_movie=8)) is False


def test_movie_delete_success(dao, sql_query):
    sql_query.return_value = {"id_movie": 7}

    assert dao.movie_delete(7) is True
    assert sql_query.call_args.kwargs["data"] == {"id_movie": 7}


def test_movie_delete_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.movie_delete(999) is False


def test_movie_delete_database_error_returns_false(dao, sql_query):
    """Par exemple : film encore référencé par une séance (clé étrangère)."""
    sql_query.side_effect = Exception("foreign key violation")

    assert dao.movie_delete(7) is False
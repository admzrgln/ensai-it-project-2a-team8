from unittest.mock import MagicMock, patch

import pytest

from backend.src.DAO.DBConnector import DBConnector

CONFIG = {"host": "db.example", "port": "5432", "database": "cinema", "user": "louise",
          "password": "secret", "schema": "public"}


@pytest.fixture
def connect():
    """Remplace psycopg2.connect : aucune vraie connexion n'est ouverte."""
    with patch("backend.src.DAO.DBConnector.psycopg2.connect") as connect:
        yield connect


@pytest.fixture
def cursor(connect):
    """Faux curseur renvoyé par `with psycopg2.connect(...) as conn: with conn.cursor() as cur`."""
    cur = MagicMock()
    conn = connect.return_value.__enter__.return_value
    conn.cursor.return_value.__enter__.return_value = cur
    return cur


# --- Constructeur -------------------------------------------------------------------
def test_config_from_dict():
    db = DBConnector(CONFIG)
    assert (db.host, db.port, db.database, db.user, db.password, db.schema) == (
        "db.example", "5432", "cinema", "louise", "secret", "public")


def test_config_from_environment(monkeypatch):
    for key, value in {"POSTGRES_HOST": "h", "POSTGRES_PORT": "1", "POSTGRES_DATABASE": "d",
                       "POSTGRES_USER": "u", "POSTGRES_PASSWORD": "p", "POSTGRES_SCHEMA": "s"}.items():
        monkeypatch.setenv(key, value)
    db = DBConnector()
    assert (db.host, db.port, db.database, db.user, db.password, db.schema) == ("h", "1", "d", "u", "p", "s")


def test_missing_environment_variable_raises(monkeypatch):
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    with pytest.raises(KeyError):
        DBConnector()


# --- get_connection -------------------------------------------------------------------
def test_get_connection_uses_config_and_schema(connect):
    conn = DBConnector(CONFIG).get_connection()

    assert conn is connect.return_value
    kwargs = connect.call_args.kwargs
    assert (kwargs["host"], kwargs["port"], kwargs["database"]) == ("db.example", "5432", "cinema")
    assert (kwargs["user"], kwargs["password"]) == ("louise", "secret")
    assert kwargs["options"] == "-c search_path=public"


# --- sql_query -----------------------------------------------------------------------
def test_sql_query_one(connect, cursor):
    cursor.fetchone.return_value = {"id_movie": 1}

    res = DBConnector(CONFIG).sql_query("SELECT * FROM movie WHERE id_movie = %(id)s", {"id": 1})

    assert res == {"id_movie": 1}
    cursor.execute.assert_called_once_with("SELECT * FROM movie WHERE id_movie = %(id)s", {"id": 1})
    cursor.fetchall.assert_not_called()
    assert connect.call_args.kwargs["options"] == "-c search_path=public"


def test_sql_query_all(cursor):
    cursor.fetchall.return_value = [{"id_movie": 1}, {"id_movie": 2}]

    res = DBConnector(CONFIG).sql_query("SELECT * FROM movie", return_type="all")

    assert res == [{"id_movie": 1}, {"id_movie": 2}]
    cursor.execute.assert_called_once_with("SELECT * FROM movie", None)
    cursor.fetchone.assert_not_called()


def test_sql_query_unknown_return_type_returns_none(cursor):
    assert DBConnector(CONFIG).sql_query("DELETE FROM movie", return_type="none") is None
    cursor.fetchone.assert_not_called()
    cursor.fetchall.assert_not_called()


def test_sql_query_error_is_printed_and_raised(cursor, capsys):
    cursor.execute.side_effect = Exception("syntax error")

    with pytest.raises(Exception, match="syntax error"):
        DBConnector(CONFIG).sql_query("SELEC * FROM movie")

    assert "syntax error" in capsys.readouterr().out

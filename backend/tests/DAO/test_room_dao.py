from unittest.mock import patch

import pytest

from backend.src.DAO.RoomDAO import RoomDao
from backend.src.Model.Room import Room


@pytest.fixture
def sql_query():
    """Remplace DBConnector dans RoomDAO : renvoie le mock de sql_query."""
    with patch("backend.src.DAO.RoomDAO.DBConnector") as connector_cls:
        yield connector_cls.return_value.sql_query


@pytest.fixture
def dao():
    return RoomDao()


def room_row(**overrides) -> dict:
    """Ligne SQL telle que renvoyée par RealDictCursor (colonne 'type', pas 'room_type')."""
    row = {"id_room": 1, "type": "IMAX", "number": "1", "capacity": 130}
    row.update(overrides)
    return row


def make_room(**overrides) -> Room:
    data = dict(room_type="IMAX", number="1", capacity=130, id_room=None)
    data.update(overrides)
    return Room(**data)


def test_to_room_maps_sql_columns_to_attributes():
    room = RoomDao._to_room(room_row(id_room=4, type="3D", number="B2", capacity=80))

    assert room.id_room == 4
    assert room.room_type == "3D"  # colonne SQL "type" -> attribut room_type
    assert room.number == "B2"
    assert room.capacity == 80


def test_find_all_maps_rows_to_rooms(dao, sql_query):
    sql_query.return_value = [room_row(id_room=1), room_row(id_room=2, number="2")]

    rooms = dao.find_all()

    assert [r.id_room for r in rooms] == [1, 2]
    assert all(isinstance(r, Room) for r in rooms)
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
    sql_query.return_value = room_row(id_room=3, number="3")

    room = dao.find_by_id(3)

    assert isinstance(room, Room)
    assert room.id_room == 3
    assert sql_query.call_args.kwargs["data"] == {"id_room": 3}
    assert sql_query.call_args.kwargs["return_type"] == "one"


def test_find_by_id_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.find_by_id(999) is None


def test_find_by_id_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_by_id(1)


def test_find_by_type_maps_rows_to_rooms(dao, sql_query):
    sql_query.return_value = [room_row(id_room=1), room_row(id_room=5, number="5")]

    rooms = dao.find_by_type("%IMAX%")

    assert [r.id_room for r in rooms] == [1, 5]
    assert sql_query.call_args.kwargs["data"] == {"type": "%IMAX%"}
    assert sql_query.call_args.kwargs["return_type"] == "all"
    assert "ILIKE" in sql_query.call_args.args[0]


@pytest.mark.parametrize("empty", [[], None])
def test_find_by_type_no_result(dao, sql_query, empty):
    sql_query.return_value = empty

    assert dao.find_by_type("%zzz%") == []


def test_find_by_type_reraises_database_error(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    with pytest.raises(Exception, match="db down"):
        dao.find_by_type("%x%")


def test_insert_room_success_sets_generated_id(dao, sql_query):
    sql_query.return_value = {"id_room": 12}
    room = make_room()

    assert dao.insert_room(room) is True
    assert room.id_room == 12
    assert sql_query.call_args.kwargs["data"] == {"type": "IMAX", "number": "1", "capacity": 130}


def test_insert_room_no_row_returned(dao, sql_query):
    sql_query.return_value = None
    room = make_room()

    assert dao.insert_room(room) is False
    assert room.id_room is None


def test_insert_room_database_error_returns_false(dao, sql_query):
    sql_query.side_effect = Exception("db down")
    room = make_room()

    assert dao.insert_room(room) is False
    assert room.id_room is None


def test_update_room_success(dao, sql_query):
    sql_query.return_value = {"id_room": 3}
    room = make_room(id_room=3, capacity=250)

    assert dao.update_room(room) is True
    assert sql_query.call_args.kwargs["data"] == {
        "id_room": 3,
        "type": "IMAX",
        "number": "1",
        "capacity": 250,
    }


def test_update_room_without_id_does_not_query(dao, sql_query):
    assert dao.update_room(make_room(id_room=None)) is False
    sql_query.assert_not_called()


def test_update_room_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.update_room(make_room(id_room=999)) is False


def test_update_room_database_error_returns_false(dao, sql_query):
    sql_query.side_effect = Exception("db down")

    assert dao.update_room(make_room(id_room=3)) is False


def test_delete_room_success(dao, sql_query):
    sql_query.return_value = {"id_room": 3}

    assert dao.delete_room(3) is True
    assert sql_query.call_args.kwargs["data"] == {"id_room": 3}


def test_delete_room_not_found(dao, sql_query):
    sql_query.return_value = None

    assert dao.delete_room(999) is False


def test_delete_room_database_error_returns_false(dao, sql_query):
    """Par exemple : salle encore référencée par une séance (clé étrangère)."""
    sql_query.side_effect = Exception("foreign key violation")

    assert dao.delete_room(3) is False

from unittest.mock import MagicMock

import pytest

from backend.src.Model.Room import Room
from backend.src.Service.RoomService import RoomService


@pytest.fixture
def service():
    """RoomService dont le DAO est remplacé par un mock (aucune base nécessaire)."""
    s = RoomService()
    s.room_dao = MagicMock()
    return s


def make_room(**overrides) -> Room:
    data = dict(room_type="IMAX", number="1", capacity=130, id_room=1)
    data.update(overrides)
    return Room(**data)


# Cas invalides communs à la création et à la modification
INVALID_ROOMS = [
    pytest.param({"room_type": ""}, id="type-vide"),
    pytest.param({"room_type": "   "}, id="type-espaces"),
    pytest.param({"room_type": None}, id="type-none"),
    pytest.param({"number": ""}, id="numero-vide"),
    pytest.param({"number": "   "}, id="numero-espaces"),
    pytest.param({"number": None}, id="numero-none"),
    pytest.param({"capacity": 0}, id="capacite-zero"),
    pytest.param({"capacity": -10}, id="capacite-negative"),
]


def test_find_all_delegates_to_dao(service):
    rooms = [make_room(id_room=1), make_room(id_room=2, number="2")]
    service.room_dao.find_all.return_value = rooms

    assert service.find_all() == rooms
    service.room_dao.find_all.assert_called_once()


def test_find_by_id_found(service):
    room = make_room()
    service.room_dao.find_by_id.return_value = room

    assert service.find_by_id(1) is room
    service.room_dao.find_by_id.assert_called_once_with(1)


def test_find_by_id_not_found(service):
    service.room_dao.find_by_id.return_value = None

    assert service.find_by_id(999) is None


def test_find_by_type_adds_wildcards(service):
    """Le service entoure le type de % pour une recherche partielle (ILIKE côté DAO)."""
    rooms = [make_room()]
    service.room_dao.find_by_type.return_value = rooms

    result = service.find_by_type("IMA")

    assert result == rooms
    service.room_dao.find_by_type.assert_called_once_with("%IMA%")


def test_find_by_type_no_result(service):
    service.room_dao.find_by_type.return_value = []

    assert service.find_by_type("inconnu") == []


def test_create_room_success(service):
    room = make_room(id_room=None)
    service.room_dao.insert_room.return_value = True

    assert service.create_room(room) is True
    service.room_dao.insert_room.assert_called_once_with(room)


def test_create_room_minimum_capacity_is_valid(service):
    """Limite : une capacité de 1 est acceptée."""
    service.room_dao.insert_room.return_value = True

    assert service.create_room(make_room(id_room=None, capacity=1)) is True


def test_create_room_dao_failure(service):
    service.room_dao.insert_room.return_value = False

    assert service.create_room(make_room(id_room=None)) is False


@pytest.mark.parametrize("overrides", INVALID_ROOMS)
def test_create_room_invalid_data_is_refused(service, overrides):
    room = make_room(id_room=None, **overrides)

    assert service.create_room(room) is False
    service.room_dao.insert_room.assert_not_called()


def test_update_room_success(service):
    room = make_room(id_room=3, capacity=250)
    service.room_dao.update_room.return_value = True

    assert service.update_room(room) is True
    service.room_dao.update_room.assert_called_once_with(room)


def test_update_room_without_id_is_refused(service):
    room = make_room(id_room=None)

    assert service.update_room(room) is False
    service.room_dao.update_room.assert_not_called()


@pytest.mark.parametrize("overrides", INVALID_ROOMS)
def test_update_room_invalid_data_is_refused(service, overrides):
    room = make_room(id_room=3, **overrides)

    assert service.update_room(room) is False
    service.room_dao.update_room.assert_not_called()


def test_update_room_dao_failure(service):
    """Par exemple : salle introuvable côté base."""
    service.room_dao.update_room.return_value = False

    assert service.update_room(make_room(id_room=999)) is False


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------
def test_delete_room_success(service):
    service.room_dao.delete_room.return_value = True

    assert service.delete_room(1) is True
    service.room_dao.delete_room.assert_called_once_with(1)


def test_delete_room_not_found(service):
    service.room_dao.delete_room.return_value = False

    assert service.delete_room(999) is False

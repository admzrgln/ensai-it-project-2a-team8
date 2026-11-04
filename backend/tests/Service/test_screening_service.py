from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from backend.src.Model.Screening import Screening
from backend.src.Service.ScreeningService import ScreeningError, ScreeningNotFoundError, ScreeningService

MOVIE_DURATION = 120  # minutes
ROOM_CAPACITY = 200


@pytest.fixture
def service():
    """ScreeningService avec tous les DAO remplacés par des mocks.

    Par défaut, on se place dans le cas "tout est valide" ; chaque test
    modifie uniquement l'élément qu'il veut faire échouer.
    """
    s = ScreeningService()
    s.screening_dao = MagicMock()
    s.room_dao = MagicMock()
    s.movie_dao = MagicMock()
    s.user_dao = MagicMock()

    s.room_dao.find_by_id.return_value = MagicMock(capacity=ROOM_CAPACITY)
    s.movie_dao.find_by_id.return_value = MagicMock(duration=MOVIE_DURATION)
    s.user_dao.find_by_id.return_value = MagicMock(role="admin")
    s.screening_dao.find_overlapping.return_value = []
    s.screening_dao.insert_screening.return_value = True
    s.screening_dao.update_screening.return_value = True
    return s


def make_screening(**overrides) -> Screening:
    data = dict(
        id_room=1,
        id_movie=1,
        id_admin=1,
        date_time=datetime.now() + timedelta(days=7),
        base_price=8.5,
        available_seats=100,
        id_screening=None,
    )
    data.update(overrides)
    return Screening(**data)


def test_find_all_delegates_to_dao(service):
    screenings = [make_screening(id_screening=1), make_screening(id_screening=2)]
    service.screening_dao.find_all.return_value = screenings

    assert service.find_all() == screenings
    service.screening_dao.find_all.assert_called_once()


def test_find_by_id_found(service):
    screening = make_screening(id_screening=1)
    service.screening_dao.find_by_id.return_value = screening

    assert service.find_by_id(1) is screening
    service.screening_dao.find_by_id.assert_called_once_with(1)


def test_find_by_id_not_found(service):
    service.screening_dao.find_by_id.return_value = None

    assert service.find_by_id(999) is None


def test_find_by_movie_delegates_to_dao(service):
    screenings = [make_screening(id_screening=1)]
    service.screening_dao.find_by_movie.return_value = screenings

    assert service.find_by_movie(5) == screenings
    service.screening_dao.find_by_movie.assert_called_once_with(5)


def test_create_screening_success(service):
    screening = make_screening()

    assert service.create_screening(screening) is True
    service.screening_dao.insert_screening.assert_called_once_with(screening)


def test_create_screening_dao_failure(service):
    service.screening_dao.insert_screening.return_value = False

    with pytest.raises(ScreeningError, match="Creation failed"):
        service.create_screening(make_screening())


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"base_price": 0}, id="prix-zero"),
        pytest.param({"available_seats": 0}, id="zero-place"),
        pytest.param({"available_seats": ROOM_CAPACITY}, id="salle-pleine"),
    ],
)
def test_create_screening_boundary_values_are_valid(service, overrides):
    """Valeurs limites acceptées par les règles métier."""
    assert service.create_screening(make_screening(**overrides)) is True


def test_create_refused_negative_price(service):
    with pytest.raises(ScreeningError, match="price can't be negative"):
        service.create_screening(make_screening(base_price=-1))
    service.screening_dao.insert_screening.assert_not_called()


def test_create_refused_negative_available_seats(service):
    with pytest.raises(ScreeningError, match="available seats can't be negative"):
        service.create_screening(make_screening(available_seats=-1))
    service.screening_dao.insert_screening.assert_not_called()


def test_create_refused_date_in_the_past(service):
    past = datetime.now() - timedelta(days=1)

    with pytest.raises(ScreeningError, match="must be in the future"):
        service.create_screening(make_screening(date_time=past))
    service.screening_dao.insert_screening.assert_not_called()


def test_create_refused_unknown_room(service):
    service.room_dao.find_by_id.return_value = None

    with pytest.raises(ScreeningError, match="Room 1 not found"):
        service.create_screening(make_screening())
    service.screening_dao.insert_screening.assert_not_called()


def test_create_refused_room_too_small(service):
    screening = make_screening(available_seats=ROOM_CAPACITY + 1)

    with pytest.raises(ScreeningError, match=f"Room 1 has only {ROOM_CAPACITY} seats"):
        service.create_screening(screening)
    service.screening_dao.insert_screening.assert_not_called()


def test_create_refused_unknown_movie(service):
    service.movie_dao.find_by_id.return_value = None

    with pytest.raises(ScreeningError, match="Movie 1 not found"):
        service.create_screening(make_screening())
    service.screening_dao.insert_screening.assert_not_called()


def test_create_refused_movie_without_duration(service):
    service.movie_dao.find_by_id.return_value = MagicMock(duration=0)

    with pytest.raises(ScreeningError, match="Movie 1 has no duration"):
        service.create_screening(make_screening())
    service.screening_dao.insert_screening.assert_not_called()


def test_create_refused_unknown_organizer(service):
    service.user_dao.find_by_id.return_value = None

    with pytest.raises(ScreeningError, match="User 1 not found"):
        service.create_screening(make_screening())
    service.screening_dao.insert_screening.assert_not_called()


def test_create_refused_organizer_is_not_admin(service):
    """Un customer ne peut pas créer de séance."""
    service.user_dao.find_by_id.return_value = MagicMock(role="customer")

    with pytest.raises(ScreeningError, match="User 1 is not an administrator"):
        service.create_screening(make_screening())
    service.screening_dao.insert_screening.assert_not_called()


def test_create_refused_overlapping_screening(service):
    service.screening_dao.find_overlapping.return_value = [make_screening(id_screening=42)]

    with pytest.raises(ScreeningError, match=r"Room 1 is already used at this time \(screening 42\)"):
        service.create_screening(make_screening())
    service.screening_dao.insert_screening.assert_not_called()


def test_overlap_check_uses_room_start_and_computed_end(service):
    """La fin de séance = début + durée du film ; à la création, aucun id n'est exclu."""
    start = datetime.now() + timedelta(days=3)
    screening = make_screening(id_room=7, date_time=start)

    service.create_screening(screening)

    service.screening_dao.find_overlapping.assert_called_once_with(
        id_room=7,
        start=start,
        end=start + timedelta(minutes=MOVIE_DURATION),
        exclude_id=None,
    )


def test_update_screening_success(service):
    screening = make_screening(id_screening=3)

    assert service.update_screening(screening) is True
    service.screening_dao.update_screening.assert_called_once_with(screening)


def test_update_screening_without_id_is_refused(service):
    with pytest.raises(ScreeningError, match="id_screening is required"):
        service.update_screening(make_screening(id_screening=None))
    service.screening_dao.update_screening.assert_not_called()


def test_update_screening_invalid_data_is_refused(service):
    screening = make_screening(id_screening=3, base_price=-5)

    with pytest.raises(ScreeningError, match="price can't be negative"):
        service.update_screening(screening)
    service.screening_dao.update_screening.assert_not_called()


def test_update_screening_not_admin_is_refused(service):
    service.user_dao.find_by_id.return_value = MagicMock(role="customer")

    with pytest.raises(ScreeningError, match="not an administrator"):
        service.update_screening(make_screening(id_screening=3))
    service.screening_dao.update_screening.assert_not_called()


def test_update_excludes_itself_from_overlap_check(service):
    """Sinon la séance serait en conflit avec elle-même lors de la modification."""
    start = datetime.now() + timedelta(days=3)
    screening = make_screening(id_screening=3, id_room=2, date_time=start)

    service.update_screening(screening)

    service.screening_dao.find_overlapping.assert_called_once_with(
        id_room=2,
        start=start,
        end=start + timedelta(minutes=MOVIE_DURATION),
        exclude_id=3,
    )


def test_update_refused_when_overlapping_another_screening(service):
    service.screening_dao.find_overlapping.return_value = [make_screening(id_screening=99)]

    with pytest.raises(ScreeningError, match="already used at this time"):
        service.update_screening(make_screening(id_screening=3))
    service.screening_dao.update_screening.assert_not_called()


def test_update_screening_dao_failure(service):
    """Par exemple : séance introuvable côté base."""
    service.screening_dao.update_screening.return_value = False

    with pytest.raises(ScreeningNotFoundError, match="Screening 999 not found"):
        service.update_screening(make_screening(id_screening=999))


def test_delete_screening_success(service):
    service.screening_dao.screening_delete.return_value = True

    assert service.delete_screening(1) is True
    service.screening_dao.screening_delete.assert_called_once_with(1)


def test_delete_screening_not_found(service):
    service.screening_dao.screening_delete.return_value = False

    assert service.delete_screening(999) is False


def test_overlap_message_lists_all_conflicting_screenings(service):
    service.screening_dao.find_overlapping.return_value = [
        make_screening(id_screening=4),
        make_screening(id_screening=7),
    ]

    with pytest.raises(ScreeningError, match=r"\(screening 4, 7\)"):
        service.create_screening(make_screening())


def test_past_date_message_shows_server_time(service):
    """L'heure du serveur peut être en UTC : on l'affiche pour éviter les surprises."""
    with pytest.raises(ScreeningError, match=r"server time: \d{4}-\d{2}-\d{2} \d{2}:\d{2}"):
        service.create_screening(make_screening(date_time=datetime.now() - timedelta(minutes=1)))

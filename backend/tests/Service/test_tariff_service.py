from datetime import date
from unittest.mock import MagicMock

import pytest

from backend.src.Model.Tariff import Tariff
from backend.src.Model.Ticket import Ticket
from backend.src.Service.TariffService import TariffError, TariffService, compute_age

SCREENING_DAY = date(2026, 12, 15)
BASE_PRICE = 9.0

GRID = [
    Tariff("child", "Moins de 14 ans", 4.50, max_age=13),
    Tariff("ensai", "Élève ENSAI", 4.00, requires_ensai=True),
    Tariff("student", "Étudiant·e", 6.00, requires_student=True),
    Tariff("full", "Plein tarif", None),
]


@pytest.fixture
def service():
    s = TariffService()
    s.tariff_dao = MagicMock()
    s.tariff_dao.find_all.return_value = GRID
    s.tariff_dao.find_by_code.return_value = None
    s.tariff_dao.insert_tariff.return_value = True
    s.tariff_dao.update_tariff.return_value = True
    s.tariff_dao.deactivate_tariff.return_value = True
    return s


def make_ticket(**overrides) -> Ticket:
    data = dict(first_name="A", last_name="B", date_of_birth=date(1990, 1, 1))
    data.update(overrides)
    return Ticket(**data)


def test_compute_age_before_and_after_birthday():
    assert compute_age(date(2000, 12, 16), SCREENING_DAY) == 25
    assert compute_age(date(2000, 12, 15), SCREENING_DAY) == 26


def test_adult_pays_full_price(service):
    t = service.price_ticket(make_ticket(), BASE_PRICE, SCREENING_DAY)
    assert (t.tariff_code, t.price) == ("full", BASE_PRICE)


def test_child_tariff(service):
    t = service.price_ticket(make_ticket(date_of_birth=date(2016, 5, 1)), BASE_PRICE, SCREENING_DAY)
    assert t.tariff_code == "child"


def test_max_age_is_inclusive(service):
    """13 ans le jour de la séance -> tarif enfant ; 14 ans -> plus le droit."""
    assert service.price_ticket(make_ticket(date_of_birth=date(2013, 1, 1)), BASE_PRICE, SCREENING_DAY).tariff_code == "child"
    assert service.price_ticket(make_ticket(date_of_birth=date(2012, 1, 1)), BASE_PRICE, SCREENING_DAY).tariff_code == "full"


def test_student_tariff(service):
    t = service.price_ticket(make_ticket(is_student=True), BASE_PRICE, SCREENING_DAY)
    assert t.tariff_code == "student"


def test_ensai_student_gets_cheapest_tariff(service):
    t = service.price_ticket(make_ticket(is_ensai_student=True), BASE_PRICE, SCREENING_DAY)
    assert t.tariff_code == "ensai"


def test_never_more_than_base_price(service):
    t = service.price_ticket(make_ticket(is_student=True), 3.0, SCREENING_DAY)
    assert t.price == 3.0


def test_grid_changed_by_admin_is_used(service):
    service.tariff_dao.find_all.return_value = [
        Tariff("senior", "65 ans et +", 5.0, min_age=65),
        Tariff("full", "Plein tarif", None),
    ]
    t = service.price_ticket(make_ticket(date_of_birth=date(1950, 1, 1)), BASE_PRICE, SCREENING_DAY)
    assert (t.tariff_code, t.price) == ("senior", 5.0)


def test_empty_grid_falls_back_to_base_price(service):
    service.tariff_dao.find_all.return_value = []
    t = service.price_ticket(make_ticket(), BASE_PRICE, SCREENING_DAY)
    assert (t.tariff_code, t.price) == ("full", BASE_PRICE)


def test_create_tariff(service):
    tariff = Tariff("senior", "65 ans et +", 5.0, min_age=65)
    assert service.create_tariff(tariff) is tariff
    service.tariff_dao.insert_tariff.assert_called_once_with(tariff)


def test_create_existing_code_refused(service):
    service.tariff_dao.find_by_code.return_value = GRID[0]
    with pytest.raises(TariffError):
        service.create_tariff(Tariff("child", "Enfant", 3.0))


@pytest.mark.parametrize("tariff", [
    Tariff("x", "X", -1.0),
    Tariff("x", "X", 5.0, min_age=20, max_age=10),
    Tariff("x", "X", 5.0, min_age=-3),
    Tariff("", "X", 5.0),
])
def test_invalid_tariff_refused(service, tariff):
    with pytest.raises(TariffError):
        service.create_tariff(tariff)
    service.tariff_dao.insert_tariff.assert_not_called()


def test_update_tariff(service):
    service.tariff_dao.find_by_code.return_value = GRID[0]
    new = Tariff("child", "Moins de 14 ans", 3.50, max_age=13)
    assert service.update_tariff(new) is new
    service.tariff_dao.update_tariff.assert_called_once_with(new)


def test_update_unknown_tariff_refused(service):
    with pytest.raises(TariffError):
        service.update_tariff(Tariff("nope", "Nope", 1.0))


def test_full_tariff_cannot_be_deactivated(service):
    with pytest.raises(TariffError):
        service.deactivate_tariff("full")
    with pytest.raises(TariffError):
        service.update_tariff(Tariff("full", "Plein tarif", None, is_active=False))


def test_deactivate_tariff(service):
    assert service.deactivate_tariff("child") is True

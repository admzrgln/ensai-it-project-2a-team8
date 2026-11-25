from datetime import date, datetime, time
from unittest.mock import MagicMock

import pytest

from backend.src.Model.Tariff import Tariff
from backend.src.Model.Ticket import Ticket
from backend.src.Service.TariffService import TariffError, TariffService, compute_age

SCREENING_DAY = date(2026, 12, 15)
SCREENING_DT = datetime(2026, 12, 15, 20, 30)
FULL_PRICE = 9.0

GRID = [
    Tariff("child", "Moins de 14 ans", 4.50, max_age=13),
    Tariff("ensai", "Élève ENSAI", 4.00, requires_ensai=True),
    Tariff("student", "Étudiant·e", 6.00, requires_student=True),
    Tariff("full", "Plein tarif", FULL_PRICE),
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
    t = service.price_ticket(make_ticket(), SCREENING_DT)
    assert (t.tariff_code, t.price) == ("full", FULL_PRICE)


def test_child_tariff(service):
    t = service.price_ticket(make_ticket(date_of_birth=date(2016, 5, 1)), SCREENING_DT)
    assert t.tariff_code == "child"


def test_max_age_is_inclusive(service):
    """13 ans le jour de la séance -> tarif enfant ; 14 ans -> plus le droit."""
    aged_13 = service.price_ticket(make_ticket(date_of_birth=date(2013, 1, 1)), SCREENING_DT)
    aged_14 = service.price_ticket(make_ticket(date_of_birth=date(2012, 1, 1)), SCREENING_DT)
    assert aged_13.tariff_code == "child"
    assert aged_14.tariff_code == "full"


def test_student_tariff(service):
    t = service.price_ticket(make_ticket(is_student=True), SCREENING_DT)
    assert t.tariff_code == "student"


def test_ensai_student_gets_cheapest_tariff(service):
    t = service.price_ticket(make_ticket(is_ensai_student=True), SCREENING_DT)
    assert t.tariff_code == "ensai"


def test_cheapest_eligible_tariff_wins(service):
    """Un élève ENSAI de 10 ans a droit à 3 tarifs : on prend le moins cher (ENSAI, 4 €)."""
    t = service.price_ticket(make_ticket(date_of_birth=date(2016, 5, 1), is_ensai_student=True), SCREENING_DT)
    assert (t.tariff_code, t.price) == ("ensai", 4.0)


def test_age_is_computed_on_screening_day(service):
    t = service.price_ticket(make_ticket(date_of_birth=date(2012, 12, 16)), SCREENING_DT)
    assert t.tariff_code == "child"


def test_price_is_rounded_to_cents(service):
    service.tariff_dao.find_all.return_value = [Tariff("full", "Plein tarif", 9.333)]
    t = service.price_ticket(make_ticket(), SCREENING_DT)
    assert t.price == 9.33


def test_grid_passed_as_argument_does_not_read_database(service):
    grid = [Tariff("full", "Plein tarif", 7.0)]
    t = service.price_ticket(make_ticket(), SCREENING_DT, grid)
    assert t.price == 7.0
    service.tariff_dao.find_all.assert_not_called()


def test_schedule_tariff_applies_only_at_the_right_time(service):
    wednesday = Tariff("wed", "Mercredi après-midi", 6.5, weekday=2, time_from=time(12, 0), time_until=time(18, 0))
    grid = [wednesday, Tariff("full", "Plein tarif", FULL_PRICE)]

    on_wednesday = service.price_ticket(make_ticket(), datetime(2026, 12, 16, 14, 0), grid)
    on_tuesday = service.price_ticket(make_ticket(), SCREENING_DT, grid)

    assert on_wednesday.tariff_code == "wed"
    assert on_tuesday.tariff_code == "full"


def test_grid_changed_by_admin_is_used(service):
    service.tariff_dao.find_all.return_value = [
        Tariff("senior", "65 ans et +", 5.0, min_age=65),
        Tariff("full", "Plein tarif", FULL_PRICE),
    ]
    t = service.price_ticket(make_ticket(date_of_birth=date(1950, 1, 1)), SCREENING_DT)
    assert (t.tariff_code, t.price) == ("senior", 5.0)


def test_empty_grid_raises_error(service):
    """Sans tarif applicable (pas de plein tarif), on ne peut pas fixer de prix."""
    service.tariff_dao.find_all.return_value = []
    with pytest.raises(TariffError, match="'full' tariff is missing"):
        service.price_ticket(make_ticket(), SCREENING_DT)


def test_create_tariff(service):
    tariff = Tariff("senior", "65 ans et +", 5.0, min_age=65)
    assert service.create_tariff(tariff) is tariff
    service.tariff_dao.insert_tariff.assert_called_once_with(tariff)


def test_create_existing_code_refused(service):
    service.tariff_dao.find_by_code.return_value = GRID[0]
    with pytest.raises(TariffError):
        service.create_tariff(Tariff("child", "Enfant", 3.0))


def test_free_tariff_is_valid(service):
    """Valeur limite : un prix de 0 € (invitation) est accepté."""
    tariff = Tariff("free", "Invitation", 0.0)
    assert service.create_tariff(tariff) is tariff


@pytest.mark.parametrize(
    "tariff",
    [
        pytest.param(Tariff("x", "X", -1.0), id="prix-negatif"),
        pytest.param(Tariff("x", "X", None), id="sans-prix"),
        pytest.param(Tariff("x", "X", 5.0, min_age=20, max_age=10), id="min-sup-max"),
        pytest.param(Tariff("x", "X", 5.0, min_age=-3), id="age-negatif"),
        pytest.param(Tariff("", "X", 5.0), id="code-vide"),
        pytest.param(Tariff("x", "", 5.0), id="libelle-vide"),
        pytest.param(Tariff("x", "X", 5.0, weekday=7), id="jour-invalide"),
        pytest.param(Tariff("x", "X", 5.0, time_from=time(18, 0), time_until=time(12, 0)), id="horaires-inverses"),
        pytest.param(Tariff("full", "Plein tarif", 9.0, max_age=13), id="plein-tarif-avec-condition"),
    ],
)
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
        service.update_tariff(Tariff("full", "Plein tarif", FULL_PRICE, is_active=False))


def test_deactivate_tariff(service):
    assert service.deactivate_tariff("child") is True


def test_find_all_delegates_to_dao(service):
    assert service.find_all(only_active=False) == GRID
    service.tariff_dao.find_all.assert_called_once_with(False)


def test_find_by_code_delegates_to_dao(service):
    service.tariff_dao.find_by_code.return_value = GRID[0]
    assert service.find_by_code("child") is GRID[0]
    service.tariff_dao.find_by_code.assert_called_once_with("child")


def test_create_tariff_db_failure(service):
    service.tariff_dao.insert_tariff.return_value = False
    with pytest.raises(TariffError, match="Creation failed"):
        service.create_tariff(Tariff("senior", "65 ans et +", 5.0, min_age=65))


def test_update_tariff_db_failure(service):
    service.tariff_dao.find_by_code.return_value = GRID[0]
    service.tariff_dao.update_tariff.return_value = False
    with pytest.raises(TariffError, match="Update failed"):
        service.update_tariff(Tariff("child", "Moins de 14 ans", 3.5, max_age=13))


def test_deactivate_unknown_or_inactive_tariff(service):
    service.tariff_dao.deactivate_tariff.return_value = False
    with pytest.raises(TariffError, match="not found or already inactive"):
        service.deactivate_tariff("nope")

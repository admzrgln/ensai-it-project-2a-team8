from datetime import datetime, time

import pytest

from backend.src.Model.Tariff import Tariff


def test_tariff_constructor_defaults():
    t = Tariff("full", "Plein tarif", 9.0)
    assert (t.code, t.label, t.price) == ("full", "Plein tarif", 9.0)
    assert t.min_age is None and t.max_age is None
    assert t.requires_ensai is False and t.requires_student is False
    assert t.is_active is True
    assert t.weekday is None and t.time_from is None and t.time_until is None


def test_tariff_without_condition_has_no_conditions():
    t = Tariff("full", "Plein tarif", 9.0)
    assert t.has_conditions is False
    assert t.has_schedule_condition is False


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"min_age": 65}, id="min_age"),
        pytest.param({"max_age": 13}, id="max_age"),
        pytest.param({"requires_ensai": True}, id="ensai"),
        pytest.param({"requires_student": True}, id="student"),
        pytest.param({"weekday": 2}, id="weekday"),
    ],
)
def test_any_condition_makes_has_conditions_true(overrides):
    assert Tariff("x", "x", 5.0, **overrides).has_conditions is True


def test_tariff_without_condition_is_for_everyone():
    t = Tariff("full", "Plein tarif", 9.0)
    assert t.is_eligible(age=40, is_ensai_student=False, is_student=False)
    assert t.is_eligible(age=0, is_ensai_student=True, is_student=True)


@pytest.mark.parametrize("age, expected", [(12, False), (13, True), (64, True), (65, True), (66, False)])
def test_age_bounds_are_inclusive(age, expected):
    t = Tariff("x", "13-65 ans", 5.0, min_age=13, max_age=65)
    assert t.is_eligible(age, False, False) is expected


def test_only_min_age():
    t = Tariff("senior", "65 ans et +", 5.0, min_age=65)
    assert t.is_eligible(90, False, False)
    assert not t.is_eligible(64, False, False)


def test_only_max_age():
    t = Tariff("child", "Moins de 14 ans", 4.5, max_age=13)
    assert t.is_eligible(0, False, False)
    assert not t.is_eligible(14, False, False)


def test_requires_ensai():
    t = Tariff("ensai", "Élève ENSAI", 4.0, requires_ensai=True)
    assert t.is_eligible(20, is_ensai_student=True, is_student=False)
    assert not t.is_eligible(20, is_ensai_student=False, is_student=True)


def test_requires_student_accepts_ensai_students():
    t = Tariff("student", "Étudiant·e", 6.0, requires_student=True)
    assert t.is_eligible(20, is_ensai_student=False, is_student=True)
    assert t.is_eligible(20, is_ensai_student=True, is_student=False)
    assert not t.is_eligible(20, is_ensai_student=False, is_student=False)


def test_all_conditions_must_be_met():
    t = Tariff("young_student", "Étudiant·e de moins de 26 ans", 5.0, max_age=25, requires_student=True)
    assert t.is_eligible(22, False, True)
    assert not t.is_eligible(30, False, True)
    assert not t.is_eligible(22, False, False)


WEDNESDAY_2PM = datetime(2026, 12, 16, 14, 0)
WEDNESDAY_6PM = datetime(2026, 12, 16, 18, 0)
THURSDAY_2PM = datetime(2026, 12, 17, 14, 0)


def wednesday_afternoon() -> Tariff:
    return Tariff("wed", "Mercredi après-midi", 6.5, weekday=2, time_from=time(12, 0), time_until=time(18, 0))


def test_schedule_tariff_has_schedule_condition():
    assert wednesday_afternoon().has_schedule_condition is True
    assert Tariff("x", "x", 5.0, time_from=time(10, 0)).has_schedule_condition is True
    assert Tariff("x", "x", 5.0, time_until=time(10, 0)).has_schedule_condition is True


def test_matches_schedule_right_day_and_time():
    assert wednesday_afternoon().matches_schedule(WEDNESDAY_2PM) is True


def test_matches_schedule_wrong_day():
    assert wednesday_afternoon().matches_schedule(THURSDAY_2PM) is False


def test_matches_schedule_time_from_is_inclusive():
    assert wednesday_afternoon().matches_schedule(datetime(2026, 12, 16, 12, 0)) is True
    assert wednesday_afternoon().matches_schedule(datetime(2026, 12, 16, 11, 59)) is False


def test_matches_schedule_time_until_is_exclusive():
    assert wednesday_afternoon().matches_schedule(datetime(2026, 12, 16, 17, 59)) is True
    assert wednesday_afternoon().matches_schedule(WEDNESDAY_6PM) is False


def test_matches_schedule_without_date_is_false():
    assert wednesday_afternoon().matches_schedule(None) is False


def test_is_eligible_with_schedule():
    t = wednesday_afternoon()
    assert t.is_eligible(30, False, False, WEDNESDAY_2PM) is True
    assert t.is_eligible(30, False, False, THURSDAY_2PM) is False
    assert t.is_eligible(30, False, False) is False


def test_tariff_without_schedule_ignores_screening_date():
    t = Tariff("full", "Plein tarif", 9.0)
    assert t.is_eligible(30, False, False, THURSDAY_2PM) is True


def test_tariff_str():
    assert str(Tariff("student", "Étudiant·e", 6.0)) == "Tariff student : Étudiant·e (6.00€)"


def test_tariff_str_without_price():
    assert str(Tariff("full", "Plein tarif", None)) == "Tariff full : Plein tarif (no price)"

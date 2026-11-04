import pytest

from backend.src.Model.Tariff import Tariff


def test_tariff_constructor_defaults():
    t = Tariff("full", "Plein tarif")
    assert (t.code, t.label) == ("full", "Plein tarif")
    assert t.price is None
    assert t.min_age is None and t.max_age is None
    assert t.requires_ensai is False and t.requires_student is False
    assert t.is_active is True


# --- is_eligible ----------------------------------------------------------
def test_tariff_without_condition_is_for_everyone():
    t = Tariff("full", "Plein tarif")
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
    assert not t.is_eligible(20, is_ensai_student=False, is_student=True)  # étudiant ailleurs : non


def test_requires_student_accepts_ensai_students():
    t = Tariff("student", "Étudiant·e", 6.0, requires_student=True)
    assert t.is_eligible(20, is_ensai_student=False, is_student=True)
    assert t.is_eligible(20, is_ensai_student=True, is_student=False)  # ENSAI = étudiant·e
    assert not t.is_eligible(20, is_ensai_student=False, is_student=False)


def test_all_conditions_must_be_met():
    t = Tariff("young_student", "Étudiant·e de moins de 26 ans", 5.0, max_age=25, requires_student=True)
    assert t.is_eligible(22, False, True)
    assert not t.is_eligible(30, False, True)  # trop âgé·e
    assert not t.is_eligible(22, False, False)  # pas étudiant·e


# --- price_for ------------------------------------------------------------
def test_price_none_means_base_price():
    assert Tariff("full", "Plein tarif").price_for(9.0) == 9.0


def test_fixed_price_below_base_price():
    assert Tariff("student", "Étudiant·e", 6.0).price_for(9.0) == 6.0


def test_price_never_above_base_price():
    assert Tariff("student", "Étudiant·e", 6.0).price_for(4.0) == 4.0


def test_free_tariff():
    assert Tariff("free", "Invitation", 0.0).price_for(9.0) == 0.0


def test_tariff_str():
    assert str(Tariff("student", "Étudiant·e", 6.0)) == "Tariff student : Étudiant·e (6.0)"
    assert str(Tariff("full", "Plein tarif")) == "Tariff full : Plein tarif (prix de base)"

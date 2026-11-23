from datetime import date
from unittest.mock import MagicMock

import pytest

from backend.src.Model.PriceRevision import PriceRevision
from backend.src.Service.PriceRevisionService import (
    MAX_RATE_PERCENT,
    PriceRevisionError,
    PriceRevisionService,
)

TODAY = date(2026, 11, 23)


@pytest.fixture
def dao():
    d = MagicMock()
    d.upsert_planned.return_value = True
    d.delete_planned.return_value = True
    d.apply_due.return_value = []
    return d


@pytest.fixture
def service(dao):
    return PriceRevisionService(revision_dao=dao)


# --- find_all ---------------------------------------------------------------------
def test_find_all_delegates_to_dao(service, dao):
    revisions = [PriceRevision(2027, 2.0), PriceRevision(2028, 3.0)]
    dao.find_all.return_value = revisions

    assert service.find_all() == revisions
    dao.find_all.assert_called_once()


# --- plan_revision ----------------------------------------------------------------
def test_plan_revision_for_next_year(service, dao):
    revision = service.plan_revision(2027, 2.5, today=TODAY)

    assert (revision.year, revision.rate_percent, revision.applied_at) == (2027, 2.5, None)
    sent = dao.upsert_planned.call_args.args[0]
    assert (sent.year, sent.rate_percent) == (2027, 2.5)


def test_plan_revision_several_years_ahead(service):
    assert service.plan_revision(2030, 1.0, today=TODAY).year == 2030


@pytest.mark.parametrize(
    "year",
    [pytest.param(2026, id="annee-en-cours"), pytest.param(2020, id="annee-passee")],
)
def test_plan_revision_refused_for_current_or_past_year(service, dao, year):
    with pytest.raises(PriceRevisionError, match="future year.*current year: 2026"):
        service.plan_revision(year, 2.0, today=TODAY)
    dao.upsert_planned.assert_not_called()


@pytest.mark.parametrize(
    "rate",
    [pytest.param(0.0, id="zero"), pytest.param(MAX_RATE_PERCENT, id="maximum")],
)
def test_plan_revision_rate_bounds_are_accepted(service, rate):
    """Valeurs limites : 0 % (gel des prix) et le maximum autorisé."""
    assert service.plan_revision(2027, rate, today=TODAY).rate_percent == rate


@pytest.mark.parametrize(
    "rate",
    [pytest.param(-1.0, id="negatif"), pytest.param(MAX_RATE_PERCENT + 0.01, id="trop-grand")],
)
def test_plan_revision_refused_for_invalid_rate(service, dao, rate):
    with pytest.raises(PriceRevisionError, match="between 0 and 10 %"):
        service.plan_revision(2027, rate, today=TODAY)
    dao.upsert_planned.assert_not_called()


def test_plan_revision_rate_is_rounded_to_two_decimals(service):
    assert service.plan_revision(2027, 2.3456, today=TODAY).rate_percent == 2.35


def test_plan_revision_already_applied(service, dao):
    dao.upsert_planned.return_value = False

    with pytest.raises(PriceRevisionError, match="2027 revision has already been applied"):
        service.plan_revision(2027, 2.0, today=TODAY)


def test_plan_revision_uses_real_date_by_default(service, monkeypatch):
    """Sans `today`, le service prend la date du jour à Bruz (Europe/Paris)."""
    monkeypatch.setattr(PriceRevisionService, "today", staticmethod(lambda: date(2030, 6, 1)))

    with pytest.raises(PriceRevisionError, match="current year: 2030"):
        service.plan_revision(2030, 2.0)


def test_today_returns_a_date():
    assert isinstance(PriceRevisionService.today(), date)


# --- cancel_revision --------------------------------------------------------------
def test_cancel_revision(service, dao):
    assert service.cancel_revision(2027) is True
    dao.delete_planned.assert_called_once_with(2027)


def test_cancel_revision_not_found_or_already_applied(service, dao):
    dao.delete_planned.return_value = False

    with pytest.raises(PriceRevisionError, match="Revision 2027 not found or already applied"):
        service.cancel_revision(2027)


# --- apply_due_revisions ----------------------------------------------------------
def test_apply_due_revisions_uses_current_year(service, dao):
    dao.apply_due.return_value = [2027]

    assert service.apply_due_revisions(today=date(2027, 1, 1)) == [2027]
    dao.apply_due.assert_called_once_with(2027)


def test_apply_due_revisions_catches_up_missed_years(service, dao):
    """Si l'appli n'a pas tourné pendant 2 ans, les deux révisions sont appliquées d'un coup."""
    dao.apply_due.return_value = [2027, 2028]

    assert service.apply_due_revisions(today=date(2028, 3, 15)) == [2027, 2028]


def test_apply_due_revisions_nothing_to_do(service, dao):
    assert service.apply_due_revisions(today=TODAY) == []
    dao.apply_due.assert_called_once_with(2026)


def test_apply_due_revisions_uses_real_date_by_default(service, dao, monkeypatch):
    monkeypatch.setattr(PriceRevisionService, "today", staticmethod(lambda: date(2029, 1, 1)))

    service.apply_due_revisions()

    dao.apply_due.assert_called_once_with(2029)

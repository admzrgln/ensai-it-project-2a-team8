from datetime import datetime

from backend.src.Model.PriceRevision import PriceRevision


def test_price_revision_constructor():
    revision = PriceRevision(year=2028, rate_percent=2.5)

    assert revision.year == 2028
    assert revision.rate_percent == 2.5
    assert revision.applied_at is None  # planifiée par défaut


def test_price_revision_constructor_applied():
    applied_at = datetime(2028, 1, 1, 0, 0, 5)
    revision = PriceRevision(year=2028, rate_percent=2.5, applied_at=applied_at)

    assert revision.applied_at == applied_at


def test_price_revision_str_planned():
    assert str(PriceRevision(2028, 2.5)) == "Révision 2028 : +2.50 % (planifiée)"


def test_price_revision_str_applied():
    revision = PriceRevision(2027, 3, applied_at=datetime(2027, 1, 1))

    assert str(revision) == "Révision 2027 : +3.00 % (appliquée)"

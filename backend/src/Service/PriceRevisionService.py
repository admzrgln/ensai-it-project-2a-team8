from datetime import date, datetime
from zoneinfo import ZoneInfo

from backend.src.DAO.PriceRevisionDAO import PriceRevisionDao
from backend.src.Model.PriceRevision import PriceRevision
from utils.log_utils import log

# Le serveur peut tourner en UTC : "minuit le 1er janvier" est celui du cinéma (Bruz).
# Sous Windows, ZoneInfo demande le paquet `tzdata` (pdm add tzdata).
CINEMA_TZ = ZoneInfo("Europe/Paris")

MAX_RATE_PERCENT = 10.0  


class PriceRevisionError(Exception):
    """Règle métier non respectée sur les révisions de prix."""


class PriceRevisionService:
    """Yearly price increase: the admin plans a rate, it is applied on January 1st at midnight."""

    def __init__(self, revision_dao=None):
        self.revision_dao = revision_dao or PriceRevisionDao()

    @staticmethod
    def today() -> date:
        return datetime.now(CINEMA_TZ).date()

    @log
    def find_all(self) -> list[PriceRevision]:
        return self.revision_dao.find_all()

    @log
    def plan_revision(self, year: int, rate_percent: float, today: date | None = None) -> PriceRevision:
        """Plan (or change) the increase of a FUTURE year. Raises PriceRevisionError if invalid."""
        today = today or self.today()
        if year <= today.year:
            raise PriceRevisionError(
                f"A revision can only be planned for a future year (current year: {today.year})"
            )
        if not 0 <= rate_percent <= MAX_RATE_PERCENT:
            raise PriceRevisionError(f"The rate must be between 0 and {MAX_RATE_PERCENT:g} %")
        revision = PriceRevision(year, round(rate_percent, 2))
        if not self.revision_dao.upsert_planned(revision):
            raise PriceRevisionError(f"The {year} revision has already been applied")
        return revision

    @log
    def cancel_revision(self, year: int) -> bool:
        if not self.revision_dao.delete_planned(year):
            raise PriceRevisionError(f"Revision {year} not found or already applied")
        return True

    @log
    def apply_due_revisions(self, today: date | None = None) -> list[int]:
        """Apply every planned revision whose year has started. Safe to call as often as wanted:
        an applied revision is never applied again, and a missed January 1st is caught up."""
        today = today or self.today()
        return self.revision_dao.apply_due(today.year)
from datetime import datetime


class PriceRevision:
    """Augmentation annuelle des tarifs, appliquée le 1er janvier de `year`.

    applied_at vaut None tant que la révision est seulement planifiée.
    """

    def __init__(self, year: int, rate_percent: float, applied_at: datetime | None = None):
        self.year = year
        self.rate_percent = rate_percent
        self.applied_at = applied_at

    def __str__(self):
        state = "appliquée" if self.applied_at else "planifiée"
        return f"Révision {self.year} : +{self.rate_percent:.2f} % ({state})"

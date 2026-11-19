from datetime import date

from backend.src.Model.MovieOccupancy import MovieOccupancy
from backend.src.Model.MovieRevenue import MovieRevenue


class AccountingReport:
    """Class representing the accounting report of a period.

    Totals are derived from the lines in the constructor.
    Revenue lines are counted on the sale date; occupancy lines on the screening date
    (only screenings already started).
    """

    def __init__(
        self,
        period_start: date,
        period_end: date,
        movie_revenues: list[MovieRevenue],
        id_admin: int | None = None,
        id_report: int | None = None,
        movie_occupancies: list[MovieOccupancy] | None = None,
    ):
        self.id_report = id_report
        self.id_admin = id_admin
        self.period_start = period_start
        self.period_end = period_end
        self.movie_revenues = movie_revenues
        self.movie_occupancies = movie_occupancies or []

        # Computed values
        self.total_amount = sum(m.revenue for m in movie_revenues)
        self.tickets_sold = sum(m.tickets_sold for m in movie_revenues)
        if self.tickets_sold:
            self.average_ticket_price = self.total_amount / self.tickets_sold
        else:
            self.average_ticket_price = 0.0

        # Global occupancy: weighted by seats (not the mean of the per-movie rates)
        self.seats_offered = sum(o.seats_offered for o in self.movie_occupancies)
        self.seats_sold = sum(o.seats_sold for o in self.movie_occupancies)
        if self.seats_offered:
            self.occupancy_rate = round(100 * self.seats_sold / self.seats_offered, 1)
        else:
            self.occupancy_rate = 0.0

    def __str__(self):
        return f"""
            Accounting report from {self.period_start} to {self.period_end},
            Total amount : {self.total_amount:.2f} euros
            Total tickets_sold : {self.tickets_sold} tickets
            Average {self.average_ticket_price:.2f} euros
            Occupancy rate : {self.occupancy_rate:.1f} %
            """
from datetime import date

from backend.src.Model.MovieRevenue import MovieRevenue


class AccountingReport:
    """Class representing the accounting report of a period.

    Totals are derived from those lines in the constructor.
    """

    def __init__(
        self,
        period_start: date,
        period_end: date,
        movie_revenues: list[MovieRevenue],
        id_admin: int | None = None,
        id_report: int | None = None,
    ):
        self.id_report = id_report
        self.id_admin = id_admin
        self.period_start = period_start
        self.period_end = period_end
        self.movie_revenues = movie_revenues

        #Computed values
        self.total_amount = sum(m.revenue for m in movie_revenues)
        self.tickets_sold = sum(m.tickets_sold for m in movie_revenues)
        if self.tickets_sold:
            self.average_ticket_price = self.total_amount / self.tickets_sold
        else:
            self.average_ticket_price = 0.0

    def __str__(self):
        return f"""
            Accounting report from {self.period_start} to {self.period_end},
            Total amount : {self.total_amount:.2f} euros
            Total tickets_sold : {self.tickets_sold} tickets
            Average {self.average_ticket_price:.2f} euros
            """

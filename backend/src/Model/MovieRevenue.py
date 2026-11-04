class MovieRevenue:
    """Revenue and tickets sold for one movie over a period"""

    def __init__(
        self,
        id_movie: int,
        title: str,
        revenue: float,
        tickets_sold: int,
    ):
        self.id_movie = id_movie
        self.title = title
        self.revenue = revenue
        self.tickets_sold = tickets_sold

    def __str__(self):
        return f"{self.title} : {self.revenue:.2f}€ ({self.tickets_sold} tickets)"

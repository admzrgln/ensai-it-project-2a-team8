class MovieRevenue:
    """Revenue and tickets sold for one movie over a period.

    Parameters
    ----------
    id_movie : int
        Identifier of the movie.
    title : str
        Title of the movie.
    revenue : float
        Amount of the tickets sold, in euros.
    tickets_sold : int
        Number of tickets sold.
    """

    def __init__(self, id_movie: int, title: str, revenue: float, tickets_sold: int) -> None:
        self.id_movie = id_movie
        self.title = title
        self.revenue = revenue
        self.tickets_sold = tickets_sold

    def __str__(self) -> str:
        return f"{self.title} : {self.revenue:.2f}€ ({self.tickets_sold} tickets)"

class MovieOccupancy:
    """Occupancy of the screenings of one movie over a period.

    Parameters
    ----------
    id_movie : int
        Identifier of the movie.
    title : str
        Title of the movie.
    screenings : int
        Number of screenings of the movie in the period.
    seats_offered : int
        Total capacity of the rooms of these screenings.
    seats_sold : int
        Number of seats sold for these screenings.
    """

    def __init__(self, id_movie: int, title: str, screenings: int, seats_offered: int, seats_sold: int) -> None:
        self.id_movie = id_movie
        self.title = title
        self.screenings = screenings
        self.seats_offered = seats_offered
        self.seats_sold = seats_sold

    @property
    def occupancy_rate(self) -> float:
        """Occupancy rate of the movie.

        Returns
        -------
        float
            Percentage of the seats offered that were sold (0 to 100, one decimal).
        """
        if not self.seats_offered:
            return 0.0
        return round(100 * self.seats_sold / self.seats_offered, 1)

    def __str__(self) -> str:
        return f"{self.title} : {self.occupancy_rate:.1f} % ({self.seats_sold}/{self.seats_offered} places)"

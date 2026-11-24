class MovieOccupancy:
    """Occupancy of the screenings of one movie over a period."""

    def __init__(self, id_movie: int, title: str, screenings: int, seats_offered: int, seats_sold: int):
        self.id_movie = id_movie
        self.title = title
        self.screenings = screenings
        self.seats_offered = seats_offered
        self.seats_sold = seats_sold

    @property
    def occupancy_rate(self) -> float:
        """Taux de remplissage en pourcentage (0 à 100, une décimale)."""
        if not self.seats_offered:
            return 0.0
        return round(100 * self.seats_sold / self.seats_offered, 1)

    def __str__(self):
        return f"{self.title} : {self.occupancy_rate:.1f} % ({self.seats_sold}/{self.seats_offered} places)"

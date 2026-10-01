class Movie:  # noqa: N999
    """Class representing a Movie."""

    def __init__(
        self,
        title: str,
        duration: int,
        genre: str,
        external_id: str,
        poster_url: str,
        id_movie: int | None = None,
    ):
        """Constructor"""
        self.id_movie = id_movie
        self.title = title
        self.duration = duration
        self.genre = genre
        self.external_id = external_id
        self.poster_url = poster_url

    def __str__(self):
        """Définit le comportement de l'objet lorsqu'il est passé à print()"""
        return f"Movie {self.id_movie} : {self.title} ({self.duration} min) [{self.genre}]"
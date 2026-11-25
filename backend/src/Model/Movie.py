class Movie:
    """Movie that can be scheduled in screenings.

    Parameters
    ----------
    title : str
        Title of the movie.
    duration : int
        Duration in minutes.
    genre : str or None
        Main genre (first genre given by OMDb; None if OMDb does not know it,
        which the database refuses).
    external_id : str
        IMDb identifier, e.g. "tt1375666".
    poster_url : str
        URL of the poster ("" if unknown).
    id_movie : int or None, optional
        Identifier in the database (None before insertion).
    """

    def __init__(
        self,
        title: str,
        duration: int,
        genre: str | None,
        external_id: str,
        poster_url: str,
        id_movie: int | None = None,
    ) -> None:
        self.id_movie = id_movie
        self.title = title
        self.duration = duration
        self.genre = genre
        self.external_id = external_id
        self.poster_url = poster_url

    def __str__(self) -> str:
        return f"Movie {self.id_movie} : {self.title} ({self.duration} min) [{self.genre}]"

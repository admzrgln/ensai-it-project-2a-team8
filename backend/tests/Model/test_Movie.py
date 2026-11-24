from backend.src.Model.Movie import Movie


def make_movie(**overrides) -> Movie:
    data = dict(
        title="Inception",
        duration=148,
        genre="Sci-Fi",
        external_id="tt1375666",
        poster_url="https://example.com/inception.jpg",
    )
    data.update(overrides)
    return Movie(**data)


def test_movie_constructor_stores_all_attributes():
    movie = make_movie(id_movie=12)

    assert movie.id_movie == 12
    assert movie.title == "Inception"
    assert movie.duration == 148
    assert movie.genre == "Sci-Fi"
    assert movie.external_id == "tt1375666"
    assert movie.poster_url == "https://example.com/inception.jpg"


def test_movie_id_is_none_before_insertion():
    """Un film pas encore enregistré en base n'a pas d'identifiant."""
    movie = make_movie()

    assert movie.id_movie is None


def test_movie_str():
    movie = make_movie(id_movie=12)

    assert str(movie) == "Movie 12 : Inception (148 min) [Sci-Fi]"

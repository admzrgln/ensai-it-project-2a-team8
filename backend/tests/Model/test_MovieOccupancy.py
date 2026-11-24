import pytest

from backend.src.Model.MovieOccupancy import MovieOccupancy


def make_occupancy(**overrides) -> MovieOccupancy:
    data = dict(id_movie=1, title="Dune: Part Two", screenings=2, seats_offered=200, seats_sold=50)
    data.update(overrides)
    return MovieOccupancy(**data)


def test_movie_occupancy_constructor():
    line = make_occupancy()

    assert (line.id_movie, line.title, line.screenings) == (1, "Dune: Part Two", 2)
    assert (line.seats_offered, line.seats_sold) == (200, 50)


@pytest.mark.parametrize(
    ("seats_sold", "expected"),
    [
        pytest.param(50, 25.0, id="quart"),
        pytest.param(0, 0.0, id="salle-vide"),
        pytest.param(200, 100.0, id="salle-pleine"),
        pytest.param(1, 0.5, id="arrondi"),
    ],
)
def test_occupancy_rate(seats_sold, expected):
    assert make_occupancy(seats_sold=seats_sold).occupancy_rate == expected


def test_occupancy_rate_is_rounded_to_one_decimal():
    """1 place sur 3 = 33,333... % -> 33,3 %."""
    assert make_occupancy(seats_offered=3, seats_sold=1).occupancy_rate == 33.3


def test_occupancy_rate_without_seats_offered_is_zero():
    """Pas de division par zéro si aucune place n'a été proposée."""
    assert make_occupancy(screenings=0, seats_offered=0, seats_sold=0).occupancy_rate == 0.0


def test_movie_occupancy_str():
    assert str(make_occupancy()) == "Dune: Part Two : 25.0 % (50/200 places)"

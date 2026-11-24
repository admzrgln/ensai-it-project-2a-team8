from datetime import date
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.AccountingReportController import accounting_router
from backend.src.Model.AccountingReport import AccountingReport
from backend.src.Model.MovieOccupancy import MovieOccupancy
from backend.src.Model.MovieRevenue import MovieRevenue
from backend.src.Service.JWTService import JwtService

app = FastAPI()
app.include_router(accounting_router)

client = TestClient(app)

URL = "/accounting-reports/"
OCT_START, OCT_END = date(2026, 10, 1), date(2026, 10, 31)
PARAMS = {"period_start": "2026-10-01", "period_end": "2026-10-31"}

jwt = JwtService()
ADMIN = {"Authorization": f"Bearer {jwt.encode_jwt(1, 'admin').access_token}"}
CUSTOMER = {"Authorization": f"Bearer {jwt.encode_jwt(10, 'customer').access_token}"}


@pytest.fixture
def service():
    """Mock of the service used by the route."""
    with patch(
            "backend.src.Controller.AccountingReportController.accounting_service") as mock_service:
        yield mock_service


def october_report() -> AccountingReport:
    return AccountingReport(
        OCT_START,
        OCT_END,
        [
            MovieRevenue(id_movie=2, title="Oppenheimer", revenue=44.40, tickets_sold=4),
            MovieRevenue(id_movie=1, title="Dune: Part Two", revenue=36.00, tickets_sold=4),
        ],
        id_admin=1,
        movie_occupancies=[
            MovieOccupancy(id_movie=1,
                           title="Dune: Part Two",
                           screenings=2,
                           seats_offered=200,
                           seats_sold=50),
        ],
    )


def test_get_report_returns_200_and_the_json_report(service):
    service.generate_report.return_value = october_report()

    response = client.get(URL, params=PARAMS, headers=ADMIN)

    assert response.status_code == 200
    body = response.json()
    assert body["period_start"] == "2026-10-01"
    assert body["period_end"] == "2026-10-31"
    assert body["total_amount"] == pytest.approx(80.40)
    assert body["tickets_sold"] == 8
    assert body["average_ticket_price"] == pytest.approx(10.05)
    assert body["movie_revenues"] == [
        {"id_movie": 2, "title": "Oppenheimer", "revenue": 44.40, "tickets_sold": 4},
        {"id_movie": 1, "title": "Dune: Part Two", "revenue": 36.00, "tickets_sold": 4},
    ]
    assert body["occupancy_rate"] == 25.0
    assert body["movie_occupancies"][0]["title"] == "Dune: Part Two"


def test_json_only_contains_the_fields_of_the_model(service):
    """id_admin / id_report are internal: they must not appear in the API response."""
    service.generate_report.return_value = october_report()

    body = client.get(URL, params=PARAMS, headers=ADMIN).json()

    assert set(body) == {
        "period_start",
        "period_end",
        "total_amount",
        "tickets_sold",
        "average_ticket_price",
        "occupancy_rate",
        "movie_revenues",
        "movie_occupancies",
    }


def test_query_strings_are_converted_to_date_and_admin_id_comes_from_token(service):
    service.generate_report.return_value = october_report()

    client.get(URL, params=PARAMS, headers=ADMIN)

    service.generate_report.assert_called_once_with(OCT_START, OCT_END, 1)


def test_id_admin_in_query_is_ignored(service):
    """On ne peut pas se faire passer pour un autre admin : seul le token compte."""
    service.generate_report.return_value = october_report()

    client.get(URL, params={**PARAMS, "id_admin": 42}, headers=ADMIN)

    service.generate_report.assert_called_once_with(OCT_START, OCT_END, 1)


def test_without_token_is_refused(service):
    response = client.get(URL, params=PARAMS)

    assert response.status_code in (401, 403)
    service.generate_report.assert_not_called()


def test_customer_cannot_see_accounting(service):
    response = client.get(URL, params=PARAMS, headers=CUSTOMER)

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin only"
    service.generate_report.assert_not_called()


def test_empty_period_returns_an_empty_report(service):
    service.generate_report.return_value = AccountingReport(OCT_START, OCT_END, [], id_admin=1)

    response = client.get(URL, params=PARAMS, headers=ADMIN)

    assert response.status_code == 200
    assert response.json()["movie_revenues"] == []
    assert response.json()["total_amount"] == 0
    assert response.json()["average_ticket_price"] == 0


@pytest.mark.parametrize(
    "exception, status",
    [
        pytest.param(ValueError(
            "period_start must be before or equal to period_end"), 400, id="bad-period"),
        pytest.param(PermissionError(
            "Only an administrator can generate an accounting report"), 403, id="not-admin"),
        pytest.param(LookupError("User 999 not found"), 404, id="unknown-user"),
    ],
)
def test_service_errors_become_http_errors(service, exception, status):
    service.generate_report.side_effect = exception

    response = client.get(URL, params=PARAMS, headers=ADMIN)

    assert response.status_code == status
    assert response.json()["detail"] == str(exception)


def test_unexpected_error_gives_500(service):
    """A database failure is not one of the 3 expected cases: FastAPI answers 500."""
    service.generate_report.side_effect = Exception("db down")
    client_500 = TestClient(app, raise_server_exceptions=False)

    response = client_500.get(URL, params=PARAMS, headers=ADMIN)

    assert response.status_code == 500


@pytest.mark.parametrize("missing", ["period_start", "period_end"])
def test_missing_parameter_gives_422(service, missing):
    params = {k: v for k, v in PARAMS.items() if k != missing}

    response = client.get(URL, params=params, headers=ADMIN)

    assert response.status_code == 422
    service.generate_report.assert_not_called()


@pytest.mark.parametrize(
    "field, value",
    [
        pytest.param("period_start", "2026-13-01", id="month-13"),
        pytest.param("period_end", "31/10/2026", id="french-format"),
        pytest.param("period_start", "2026-02-30", id="30-february"),
    ],
)
def test_badly_formatted_parameter_gives_422(service, field, value):
    response = client.get(URL, params={**PARAMS, field: value}, headers=ADMIN)

    assert response.status_code == 422
    service.generate_report.assert_not_called()

"""Unit tests of the accounting route GET /accounting-reports/.

The service is replaced by a mock (patch on `accounting_service` in the
controller module), so no business rule and no database is involved here.
We only test what the Controller is responsible for:
- reading and validating the query parameters (FastAPI -> 422 if invalid)
- turning the service's exceptions into HTTP codes (400 / 403 / 404)
- turning the AccountingReport object into the JSON of AccountingReportModel
"""

from datetime import date
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.AccountingReportController import accounting_router
from backend.src.Model.AccountingReport import AccountingReport
from backend.src.Model.MovieRevenue import MovieRevenue

app = FastAPI()
app.include_router(accounting_router)

client = TestClient(app)

URL = "/accounting-reports/"
OCT_START, OCT_END = date(2026, 10, 1), date(2026, 10, 31)
PARAMS = {"period_start": "2026-10-01", "period_end": "2026-10-31", "id_admin": 1}


@pytest.fixture
def service():
    """Mock of the service used by the route."""
    with patch("backend.src.Controller.AccountingReportController.accounting_service") as mock_service:
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
    )


def test_get_report_returns_200_and_the_json_report(service):
    service.generate_report.return_value = october_report()

    response = client.get(URL, params=PARAMS)

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


def test_json_only_contains_the_fields_of_the_model(service):
    """id_admin / id_report are internal: they must not appear in the API response."""
    service.generate_report.return_value = october_report()

    body = client.get(URL, params=PARAMS).json()

    assert set(body) == {
        "period_start",
        "period_end",
        "total_amount",
        "tickets_sold",
        "average_ticket_price",
        "movie_revenues",
    }


def test_query_strings_are_converted_to_date_and_int(service):
    service.generate_report.return_value = october_report()

    client.get(URL, params=PARAMS)

    service.generate_report.assert_called_once_with(OCT_START, OCT_END, 1)


def test_empty_period_returns_an_empty_report(service):
    service.generate_report.return_value = AccountingReport(OCT_START, OCT_END, [], id_admin=1)

    response = client.get(URL, params=PARAMS)

    assert response.status_code == 200
    assert response.json()["movie_revenues"] == []
    assert response.json()["total_amount"] == 0
    assert response.json()["average_ticket_price"] == 0


@pytest.mark.parametrize(
    "exception, status",
    [
        pytest.param(ValueError("period_start must be before or equal to period_end"), 400, id="bad-period"),
        pytest.param(PermissionError("Only an administrator can generate an accounting report"), 403, id="not-admin"),
        pytest.param(LookupError("User 999 not found"), 404, id="unknown-user"),
    ],
)
def test_service_errors_become_http_errors(service, exception, status):
    service.generate_report.side_effect = exception

    response = client.get(URL, params=PARAMS)

    assert response.status_code == status
    assert response.json()["detail"] == str(exception)  # the message is passed on to the client


def test_unexpected_error_gives_500(service):
    """A database failure is not one of the 3 expected cases: FastAPI answers 500."""
    service.generate_report.side_effect = Exception("db down")
    client_500 = TestClient(app, raise_server_exceptions=False)

    response = client_500.get(URL, params=PARAMS)

    assert response.status_code == 500


@pytest.mark.parametrize("missing", ["period_start", "period_end", "id_admin"])
def test_missing_parameter_gives_422(service, missing):
    params = {k: v for k, v in PARAMS.items() if k != missing}

    response = client.get(URL, params=params)

    assert response.status_code == 422
    service.generate_report.assert_not_called()


@pytest.mark.parametrize(
    "field, value",
    [
        pytest.param("period_start", "2026-13-01", id="month-13"),
        pytest.param("period_end", "31/10/2026", id="french-format"),
        pytest.param("period_start", "2026-02-30", id="30-february"),
        pytest.param("id_admin", "abc", id="id-not-int"),
    ],
)
def test_badly_formatted_parameter_gives_422(service, field, value):
    response = client.get(URL, params={**PARAMS, field: value})

    assert response.status_code == 422
    service.generate_report.assert_not_called()

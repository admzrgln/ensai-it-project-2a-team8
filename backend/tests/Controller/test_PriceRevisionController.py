from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.PriceRevisionController import price_revision_router
from backend.src.Model.PriceRevision import PriceRevision
from backend.src.Service.JWTService import JwtService
from backend.src.Service.PriceRevisionService import PriceRevisionError

app = FastAPI()
app.include_router(price_revision_router)
client = TestClient(app)

BASE_URL = "/price-revisions"
SERVICE = "backend.src.Controller.PriceRevisionController.price_revision_service"

jwt = JwtService()
ADMIN = {"Authorization": f"Bearer {jwt.encode_jwt(1, 'admin').access_token}"}
CUSTOMER = {"Authorization": f"Bearer {jwt.encode_jwt(10, 'customer').access_token}"}


@patch(SERVICE)
def test_list_revisions(mock_service):
    mock_service.find_all.return_value = [
        PriceRevision(2027, 2.0, applied_at=datetime(2027, 1, 1, 0, 0, 5)),
        PriceRevision(2028, 3.0),
    ]

    response = client.get(f"{BASE_URL}/", headers=ADMIN)

    assert response.status_code == 200
    assert response.json() == [
        {"year": 2027, "rate_percent": 2.0, "applied_at": "2027-01-01T00:00:05"},
        {"year": 2028, "rate_percent": 3.0, "applied_at": None},
    ]


@patch(SERVICE)
def test_list_revisions_empty(mock_service):
    mock_service.find_all.return_value = []

    response = client.get(f"{BASE_URL}/", headers=ADMIN)

    assert response.status_code == 200
    assert response.json() == []


@patch(SERVICE)
def test_plan_revision(mock_service):
    mock_service.plan_revision.return_value = PriceRevision(2027, 2.5)

    response = client.put(f"{BASE_URL}/2027", json={"rate_percent": 2.5}, headers=ADMIN)

    assert response.status_code == 200
    assert response.json() == {"year": 2027, "rate_percent": 2.5, "applied_at": None}
    mock_service.plan_revision.assert_called_once_with(2027, 2.5)


@patch(SERVICE)
def test_plan_revision_business_error_gives_400(mock_service):
    mock_service.plan_revision.side_effect = PriceRevisionError(
        "A revision can only be planned for a future year (current year: 2026)"
    )

    response = client.put(f"{BASE_URL}/2026", json={"rate_percent": 2.0}, headers=ADMIN)

    assert response.status_code == 400
    assert "future year" in response.json()["detail"]


@patch(SERVICE)
def test_plan_revision_already_applied_gives_400(mock_service):
    mock_service.plan_revision.side_effect = PriceRevisionError(
        "The 2027 revision has already been applied")

    response = client.put(f"{BASE_URL}/2027", json={"rate_percent": 2.0}, headers=ADMIN)

    assert response.status_code == 400


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"rate_percent": -1}, id="taux-negatif"),
        pytest.param({"rate_percent": 10.5}, id="taux-trop-grand"),
        pytest.param({"rate_percent": "deux"}, id="taux-texte"),
        pytest.param({}, id="taux-manquant"),
    ],
)
@patch(SERVICE)
def test_plan_revision_invalid_body_gives_422(mock_service, body):
    response = client.put(f"{BASE_URL}/2027", json=body, headers=ADMIN)

    assert response.status_code == 422
    mock_service.plan_revision.assert_not_called()


@patch(SERVICE)
def test_plan_revision_year_not_int_gives_422(mock_service):
    response = client.put(f"{BASE_URL}/next-year", json={"rate_percent": 2.0}, headers=ADMIN)

    assert response.status_code == 422
    mock_service.plan_revision.assert_not_called()


@patch(SERVICE)
def test_cancel_revision(mock_service):
    mock_service.cancel_revision.return_value = True

    response = client.delete(f"{BASE_URL}/2027", headers=ADMIN)

    assert response.status_code == 200
    assert response.json() == {"message": "Revision 2027 cancelled"}
    mock_service.cancel_revision.assert_called_once_with(2027)


@patch(SERVICE)
def test_cancel_revision_not_found_gives_404(mock_service):
    mock_service.cancel_revision.side_effect = PriceRevisionError(
        "Revision 2027 not found or already applied")

    response = client.delete(f"{BASE_URL}/2027", headers=ADMIN)

    assert response.status_code == 404
    assert response.json()["detail"] == "Revision 2027 not found or already applied"


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        pytest.param("GET", f"{BASE_URL}/", None, id="list"),
        pytest.param("PUT", f"{BASE_URL}/2027", {"rate_percent": 2.0}, id="plan"),
        pytest.param("DELETE", f"{BASE_URL}/2027", None, id="cancel"),
    ],
)
@patch(SERVICE)
def test_customer_is_refused(mock_service, method, url, body):
    response = client.request(method, url, json=body, headers=CUSTOMER)

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin only"
    assert not mock_service.method_calls


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        pytest.param("GET", f"{BASE_URL}/", None, id="list"),
        pytest.param("PUT", f"{BASE_URL}/2027", {"rate_percent": 2.0}, id="plan"),
        pytest.param("DELETE", f"{BASE_URL}/2027", None, id="cancel"),
    ],
)
@patch(SERVICE)
def test_without_token_is_refused(mock_service, method, url, body):
    response = client.request(method, url, json=body)

    assert response.status_code in (401, 403)
    assert not mock_service.method_calls

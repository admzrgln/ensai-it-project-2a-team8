from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.TariffController import tariff_router
from backend.src.Model.Tariff import Tariff
from backend.src.Service.JWTService import JwtService
from backend.src.Service.TariffService import TariffError

app = FastAPI()
app.include_router(tariff_router)
client = TestClient(app)

BASE_URL = "/tariffs"
SERVICE = "backend.src.Controller.TariffController.tariff_service"

jwt = JwtService()
ADMIN = {"Authorization": f"Bearer {jwt.encode_jwt(1, 'admin').access_token}"}
CUSTOMER = {"Authorization": f"Bearer {jwt.encode_jwt(10, 'customer').access_token}"}

senior_data = {"code": "senior", "label": "65 ans et +", "price": 5.5, "min_age": 65}


# --- GET -----------------------------------------------------------------------
@patch(SERVICE)
def test_list_active_tariffs_is_public(mock_service):
    mock_service.find_all.return_value = [Tariff("child", "Moins de 14 ans", 4.5, max_age=13),
                                          Tariff("full", "Plein tarif")]

    response = client.get(f"{BASE_URL}/")

    assert response.status_code == 200
    assert [t["code"] for t in response.json()] == ["child", "full"]
    assert response.json()[1]["price"] is None
    mock_service.find_all.assert_called_once_with(only_active=True)


@patch(SERVICE)
def test_list_all_tariffs_admin(mock_service):
    mock_service.find_all.return_value = [Tariff("old", "Ancien tarif", 3.0, is_active=False)]

    response = client.get(f"{BASE_URL}/all", headers=ADMIN)

    assert response.status_code == 200
    assert response.json()[0]["is_active"] is False
    mock_service.find_all.assert_called_once_with(only_active=False)


@patch(SERVICE)
def test_list_all_tariffs_refused_for_customer(mock_service):
    assert client.get(f"{BASE_URL}/all", headers=CUSTOMER).status_code == 403
    mock_service.find_all.assert_not_called()


# --- POST ----------------------------------------------------------------------
@patch(SERVICE)
def test_create_tariff(mock_service):
    mock_service.create_tariff.side_effect = lambda t: t  # renvoie le tarif reçu

    response = client.post(f"{BASE_URL}/", json=senior_data, headers=ADMIN)

    assert response.status_code == 201
    assert response.json()["code"] == "senior"
    sent = mock_service.create_tariff.call_args.args[0]
    assert isinstance(sent, Tariff)
    assert (sent.price, sent.min_age, sent.max_age, sent.is_active) == (5.5, 65, None, True)


@patch(SERVICE)
def test_create_tariff_refused_for_customer(mock_service):
    response = client.post(f"{BASE_URL}/", json=senior_data, headers=CUSTOMER)
    assert response.status_code == 403
    mock_service.create_tariff.assert_not_called()


def test_create_tariff_refused_without_token():
    assert client.post(f"{BASE_URL}/", json=senior_data).status_code in (401, 403)


@patch(SERVICE)
def test_create_tariff_business_error_gives_400(mock_service):
    mock_service.create_tariff.side_effect = TariffError("Tariff 'senior' already exists")

    response = client.post(f"{BASE_URL}/", json=senior_data, headers=ADMIN)

    assert response.status_code == 400
    assert response.json()["detail"] == "Tariff 'senior' already exists"


@patch(SERVICE)
def test_create_tariff_invalid_body_gives_422(mock_service):
    response = client.post(f"{BASE_URL}/", json={"code": "x"}, headers=ADMIN)  # label manquant
    assert response.status_code == 422
    mock_service.create_tariff.assert_not_called()


@patch(SERVICE)
def test_create_tariff_code_too_long_gives_422(mock_service):
    response = client.post(f"{BASE_URL}/", json={**senior_data, "code": "x" * 31}, headers=ADMIN)
    assert response.status_code == 422


# --- PUT -----------------------------------------------------------------------
@patch(SERVICE)
def test_update_tariff_uses_code_from_url(mock_service):
    mock_service.update_tariff.side_effect = lambda t: t

    response = client.put(f"{BASE_URL}/student", json={"code": "autre", "label": "Étudiant·e", "price": 5.0,
                                                       "requires_student": True}, headers=ADMIN)

    assert response.status_code == 200
    sent = mock_service.update_tariff.call_args.args[0]
    assert sent.code == "student"  # le code de l'URL fait foi
    assert sent.price == 5.0


@patch(SERVICE)
def test_update_unknown_tariff_gives_404(mock_service):
    mock_service.update_tariff.side_effect = TariffError("Tariff not found")
    response = client.put(f"{BASE_URL}/nope", json=senior_data, headers=ADMIN)
    assert response.status_code == 404


@patch(SERVICE)
def test_update_tariff_refused_for_customer(mock_service):
    assert client.put(f"{BASE_URL}/student", json=senior_data, headers=CUSTOMER).status_code == 403
    mock_service.update_tariff.assert_not_called()


# --- DELETE (désactivation) -----------------------------------------------------
@patch(SERVICE)
def test_deactivate_tariff(mock_service):
    mock_service.deactivate_tariff.return_value = True

    response = client.delete(f"{BASE_URL}/child", headers=ADMIN)

    assert response.status_code == 200
    mock_service.deactivate_tariff.assert_called_once_with("child")


@patch(SERVICE)
def test_deactivate_full_tariff_gives_400(mock_service):
    mock_service.deactivate_tariff.side_effect = TariffError("The 'full' tariff can't be deactivated")
    assert client.delete(f"{BASE_URL}/full", headers=ADMIN).status_code == 400


@patch(SERVICE)
def test_deactivate_unknown_tariff_gives_404(mock_service):
    mock_service.deactivate_tariff.side_effect = TariffError("Tariff not found or already inactive")
    assert client.delete(f"{BASE_URL}/nope", headers=ADMIN).status_code == 404


@patch(SERVICE)
def test_deactivate_tariff_refused_for_customer(mock_service):
    assert client.delete(f"{BASE_URL}/child", headers=CUSTOMER).status_code == 403
    mock_service.deactivate_tariff.assert_not_called()

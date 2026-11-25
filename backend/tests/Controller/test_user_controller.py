from datetime import date, time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.Controller.UserController import user_router
from backend.src.Model.Administrator import Administrator
from backend.src.Model.Customer import Customer
from backend.src.Model.Tariff import Tariff
from backend.src.Service.JWTService import JwtService

app = FastAPI()
app.include_router(user_router)
client = TestClient(app)

BASE_URL = "/users"
SERVICE = "backend.src.Controller.UserController.user_service"

jwt = JwtService()
ADMIN = {"Authorization": f"Bearer {jwt.encode_jwt(1, 'admin').access_token}"}
LOUISE = {"Authorization": f"Bearer {jwt.encode_jwt(2, 'customer').access_token}"}
OTHER = {"Authorization": f"Bearer {jwt.encode_jwt(3, 'customer').access_token}"}

signup_data = {
    "first_name": "Louise",
    "last_name": "F",
    "email": "louise@mail.fr",
    "password": "motdepasse123",
    "date_of_birth": "2004-03-01",
}


def make_customer(**overrides) -> Customer:
    data = dict(
        id_user=2,
        first_name="Louise",
        last_name="F",
        email="louise@mail.fr",
        password="hash",
        date_of_birth=date(2004, 3, 1),
        is_ensai_student=False,
        salt="sel",
    )
    data.update(overrides)
    return Customer(**data)


FAKE_GRID = [
    Tariff("ensai", "ENSAI Student", 7.8, requires_ensai=True),
    Tariff("child", "Under 14", 6.0, max_age=13),
    Tariff("senior", "Over 65", 9.5, min_age=65),
    Tariff("wed", "Wednesday afternoon", 6.5, weekday=2, time_from=time(12, 0), time_until=time(18, 0)),
    Tariff("full", "Full price", 11.0),
]


@pytest.fixture(autouse=True)
def tariff_service():
    """Remplace le TariffService du contrôleur (sinon l'inscription irait lire la vraie base)."""
    with patch("backend.src.Controller.UserController.tariff_service") as mock_tariff_service:
        mock_tariff_service.find_all.return_value = FAKE_GRID
        yield mock_tariff_service


def make_admin() -> Administrator:
    return Administrator(1, "Ad", "Min", "admin@mail.fr", "hash", date(1990, 1, 1), salt="sel")


def years_ago(years: int) -> date:
    """Date de naissance pour avoir `years` ans aujourd'hui (évite que les tests vieillissent)."""
    today = date.today()
    return today.replace(year=today.year - years, day=min(today.day, 28))


@patch(SERVICE)
def test_find_all_users_admin(mock_service):
    mock_service.find_all.return_value = [make_admin(), make_customer()]

    response = client.get(f"{BASE_URL}/", headers=ADMIN)

    assert response.status_code == 200
    assert [u["role"] for u in response.json()] == ["admin", "customer"]


@patch(SERVICE)
def test_find_all_users_refused_for_customer(mock_service):
    assert client.get(f"{BASE_URL}/", headers=LOUISE).status_code == 403
    mock_service.find_all.assert_not_called()


def test_find_all_users_refused_without_token():
    assert client.get(f"{BASE_URL}/").status_code in (401, 403)


@patch(SERVICE)
def test_user_by_email_admin(mock_service):
    mock_service.find_by_email.return_value = make_customer()

    response = client.get(f"{BASE_URL}/search/louise@mail.fr", headers=ADMIN)

    assert response.status_code == 200
    assert response.json()["id_user"] == 2
    mock_service.find_by_email.assert_called_once_with("louise@mail.fr")


@patch(SERVICE)
def test_user_by_email_not_found(mock_service):
    mock_service.find_by_email.return_value = None
    assert client.get(f"{BASE_URL}/search/nobody@mail.fr", headers=ADMIN).status_code == 404


@patch(SERVICE)
def test_user_by_email_refused_for_customer(mock_service):
    assert client.get(f"{BASE_URL}/search/louise@mail.fr", headers=LOUISE).status_code == 403
    mock_service.find_by_email.assert_not_called()


@patch(SERVICE)
def test_customer_can_see_own_account(mock_service):
    mock_service.find_by_id.return_value = make_customer()

    response = client.get(f"{BASE_URL}/2", headers=LOUISE)

    assert response.status_code == 200
    assert response.json()["email"] == "louise@mail.fr"


@patch(SERVICE)
def test_customer_cannot_see_another_account(mock_service):
    response = client.get(f"{BASE_URL}/2", headers=OTHER)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    mock_service.find_by_id.assert_not_called()


@patch(SERVICE)
def test_admin_can_see_any_account(mock_service):
    mock_service.find_by_id.return_value = make_customer()
    assert client.get(f"{BASE_URL}/2", headers=ADMIN).status_code == 200


@patch(SERVICE)
def test_user_by_id_not_found(mock_service):
    mock_service.find_by_id.return_value = None
    response = client.get(f"{BASE_URL}/999", headers=ADMIN)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_user_by_id_refused_without_token():
    assert client.get(f"{BASE_URL}/2").status_code in (401, 403)


@patch(SERVICE)
def test_signup_creates_a_customer(mock_service):
    mock_service.create_user.return_value = make_customer(date_of_birth=years_ago(30))

    response = client.post(f"{BASE_URL}/", json=signup_data)

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "customer"
    sent = mock_service.create_user.call_args.args[0]
    assert isinstance(sent, Customer)
    assert (sent.email, sent.password, sent.id_user) == ("louise@mail.fr", "motdepasse123", None)


@patch(SERVICE)
def test_signup_cannot_create_an_admin(mock_service):
    """Même si quelqu'un envoie "role": "admin", l'inscription crée un client."""
    mock_service.create_user.return_value = make_customer(date_of_birth=years_ago(30))

    client.post(f"{BASE_URL}/", json={**signup_data, "role": "admin"})

    sent = mock_service.create_user.call_args.args[0]
    assert isinstance(sent, Customer)
    assert sent.role == "customer"


@patch(SERVICE)
def test_signup_adult_gets_full_price_only(mock_service):
    mock_service.create_user.return_value = make_customer(date_of_birth=years_ago(30))

    message = client.post(f"{BASE_URL}/", json=signup_data).json()["message"]

    assert message.startswith("Registration successful.")
    assert "(30 years old)" in message
    assert "Full price" in message
    assert "Under 14" not in message and "Over 65" not in message and "ENSAI" not in message
    assert "student ID" not in message


@patch(SERVICE)
def test_signup_child_gets_under_14_tariff(mock_service):
    mock_service.create_user.return_value = make_customer(date_of_birth=years_ago(10))
    message = client.post(f"{BASE_URL}/", json=signup_data).json()["message"]
    assert "(10 years old)" in message
    assert "Under 14" in message


@patch(SERVICE)
def test_signup_senior_gets_over_65_tariff(mock_service):
    mock_service.create_user.return_value = make_customer(date_of_birth=years_ago(70))
    message = client.post(f"{BASE_URL}/", json=signup_data).json()["message"]
    assert "Over 65" in message


@patch(SERVICE)
def test_signup_ensai_student_message(mock_service):
    mock_service.create_user.return_value = make_customer(date_of_birth=years_ago(20), is_ensai_student=True)
    message = client.post(f"{BASE_URL}/", json={**signup_data, "email": "louise@ensai.fr"}).json()["message"]
    assert "ENSAI Student" in message
    assert "Your student ID will be checked at the ticket office." in message


@patch(SERVICE)
def test_signup_each_tariff_is_listed_once(mock_service):
    """Un enfant ne doit pas voir "Under 14" deux fois dans le message."""
    mock_service.create_user.return_value = make_customer(date_of_birth=years_ago(10))
    message = client.post(f"{BASE_URL}/", json=signup_data).json()["message"]
    assert message.count("Under 14") == 1


@patch(SERVICE)
def test_signup_prices_come_from_the_grid(mock_service, tariff_service):
    """Si un admin change un prix, le message d'inscription affiche le nouveau prix."""
    tariff_service.find_all.return_value = [
        Tariff("child", "Under 14", 5.0, max_age=13),
        Tariff("full", "Full price", 11.0),
    ]
    mock_service.create_user.return_value = make_customer(date_of_birth=years_ago(10))

    message = client.post(f"{BASE_URL}/", json=signup_data).json()["message"]

    assert "Under 14 (5.00€)" in message
    assert "6€" not in message
    tariff_service.find_all.assert_called_once_with(only_active=True)


@patch(SERVICE)
def test_signup_schedule_tariffs_are_not_listed(mock_service):
    """Les tarifs liés à un horaire
    (ex. mercredi après-midi) dépendent de la séance, pas du client."""
    mock_service.create_user.return_value = make_customer(date_of_birth=years_ago(30))
    message = client.post(f"{BASE_URL}/", json=signup_data).json()["message"]
    assert "Wednesday afternoon" not in message


def test_signup_age_birthday_not_yet_passed():
    """La veille de ses 20 ans, on a encore 19 ans."""
    today = date.today()
    if (today.month, today.day) == (12, 31):
        pytest.skip("pas de lendemain dans la même année")
    tomorrow_20_years_ago = date.fromordinal(today.toordinal() + 1).replace(year=today.year - 20)
    with patch(SERVICE) as mock_service:
        mock_service.create_user.return_value = make_customer(date_of_birth=tomorrow_20_years_ago)
        message = client.post(f"{BASE_URL}/", json=signup_data).json()["message"]
    assert "(19 years old)" in message


@patch(SERVICE)
def test_signup_failure_gives_400(mock_service):
    mock_service.create_user.return_value = None

    response = client.post(f"{BASE_URL}/", json=signup_data)

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already exists, weak password or creation failed"


@patch(SERVICE)
def test_signup_invalid_body_gives_422(mock_service):
    response = client.post(f"{BASE_URL}/", json={**signup_data, "date_of_birth": "pas une date"})
    assert response.status_code == 422
    mock_service.create_user.assert_not_called()


@patch(SERVICE)
def test_create_admin(mock_service):
    mock_service.create_user.return_value = make_admin()

    response = client.post(f"{BASE_URL}/admin", json=signup_data, headers=ADMIN)

    assert response.status_code == 201
    assert response.json()["role"] == "admin"
    assert isinstance(mock_service.create_user.call_args.args[0], Administrator)


@patch(SERVICE)
def test_create_admin_refused_for_customer(mock_service):
    assert client.post(f"{BASE_URL}/admin", json=signup_data, headers=LOUISE).status_code == 403
    mock_service.create_user.assert_not_called()


@patch(SERVICE)
def test_create_admin_failure_gives_400(mock_service):
    mock_service.create_user.return_value = None
    assert client.post(f"{BASE_URL}/admin", json=signup_data, headers=ADMIN).status_code == 400


@patch(SERVICE)
def test_login_returns_a_valid_jwt(mock_service):
    mock_service.authenticate.return_value = make_customer()

    response = client.post(f"{BASE_URL}/login", json={"email": "louise@mail.fr", "password": "motdepasse123"})

    assert response.status_code == 200
    payload = jwt.validate_user_jwt(response.json()["access_token"])
    assert (payload["user_id"], payload["role"]) == (2, "customer")
    mock_service.authenticate.assert_called_once_with("louise@mail.fr", "motdepasse123")


@patch(SERVICE)
def test_login_wrong_credentials(mock_service):
    mock_service.authenticate.return_value = None

    response = client.post(f"{BASE_URL}/login", json={"email": "louise@mail.fr", "password": "faux"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


update_data = {**signup_data, "role": "customer", "is_ensai_student": False}


@patch(SERVICE)
def test_customer_updates_own_account(mock_service):
    mock_service.update_user.return_value = make_customer(first_name="Lou")

    response = client.put(f"{BASE_URL}/2", json={**update_data, "first_name": "Lou"}, headers=LOUISE)

    assert response.status_code == 200
    assert response.json()["message"] == "User updated successfully"
    id_user, sent = mock_service.update_user.call_args.args
    assert id_user == 2
    assert isinstance(sent, Customer) and sent.first_name == "Lou"


@patch(SERVICE)
def test_customer_cannot_make_himself_admin(mock_service):
    mock_service.update_user.return_value = make_customer()

    client.put(f"{BASE_URL}/2", json={**update_data, "role": "admin"}, headers=LOUISE)

    sent = mock_service.update_user.call_args.args[1]
    assert isinstance(sent, Customer)
    assert sent.role == "customer"


@patch(SERVICE)
def test_admin_can_promote_a_user(mock_service):
    mock_service.update_user.return_value = make_admin()

    response = client.put(f"{BASE_URL}/2", json={**update_data, "role": "ADMIN"}, headers=ADMIN)

    assert response.status_code == 200
    assert isinstance(mock_service.update_user.call_args.args[1], Administrator)


@patch(SERVICE)
def test_customer_cannot_update_another_account(mock_service):
    assert client.put(f"{BASE_URL}/2", json=update_data, headers=OTHER).status_code == 403
    mock_service.update_user.assert_not_called()


@patch(SERVICE)
def test_update_user_failure_gives_404(mock_service):
    mock_service.update_user.return_value = None
    response = client.put(f"{BASE_URL}/2", json=update_data, headers=LOUISE)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found or update failed"


@patch(SERVICE)
def test_update_unknown_user_gives_404(mock_service):
    mock_service.find_by_id.return_value = None

    response = client.put(f"{BASE_URL}/999", json=update_data, headers=ADMIN)

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found or update failed"
    mock_service.update_user.assert_not_called()


@patch(SERVICE)
def test_admin_cannot_set_an_invalid_role(mock_service):
    mock_service.find_by_id.return_value = make_customer()

    response = client.put(f"{BASE_URL}/2", json={**update_data, "role": "superuser"}, headers=ADMIN)

    assert response.status_code == 400
    assert response.json()["detail"] == "Role must be 'admin' or 'customer'"
    mock_service.update_user.assert_not_called()


@patch(SERVICE)
def test_customer_deletes_own_account(mock_service):
    mock_service.delete_user.return_value = True

    response = client.delete(f"{BASE_URL}/2", headers=LOUISE)

    assert response.status_code == 200
    assert response.json()["message"] == "User 2 deleted successfully"
    mock_service.delete_user.assert_called_once_with(2)


@patch(SERVICE)
def test_admin_deletes_any_account(mock_service):
    mock_service.delete_user.return_value = True
    assert client.delete(f"{BASE_URL}/2", headers=ADMIN).status_code == 200


@patch(SERVICE)
def test_customer_cannot_delete_another_account(mock_service):
    assert client.delete(f"{BASE_URL}/2", headers=OTHER).status_code == 403
    mock_service.delete_user.assert_not_called()


@patch(SERVICE)
def test_delete_user_not_found(mock_service):
    mock_service.delete_user.return_value = False
    assert client.delete(f"{BASE_URL}/999", headers=ADMIN).status_code == 404

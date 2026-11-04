import asyncio
import time
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from backend.src.Controller.JWTBearer import (
    JWTBearer,
    get_current_user,
    jwt_service,
    require_admin,
    require_customer,
)

# Petite application de test avec une route par niveau de protection
app = FastAPI()


@app.get("/me")
async def me(user: Annotated[dict, Depends(get_current_user)]):
    return user


@app.get("/admin")
async def admin_only(user: Annotated[dict, Depends(require_admin)]):
    return user


@app.get("/customer")
async def customer_only(user: Annotated[dict, Depends(require_customer)]):
    return user


client = TestClient(app)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def token_for(user_id: int, role: str | None = None) -> str:
    return jwt_service.encode_jwt(user_id, role).access_token


def raw_token(payload: dict) -> str:
    """Token signé avec le bon secret mais avec un contenu choisi (ex. déjà expiré)."""
    return jwt.encode(payload, jwt_service.secret, algorithm=jwt_service.algorithm)


# --- Token valide -------------------------------------------------------------------
def test_valid_token_returns_payload():
    response = client.get("/me", headers=bearer(token_for(3, "customer")))
    assert response.status_code == 200
    assert response.json()["user_id"] == 3
    assert response.json()["role"] == "customer"


# --- Tokens refusés -------------------------------------------------------------------
def test_missing_header_is_refused():
    assert client.get("/me").status_code in (401, 403)


def test_expired_token():
    token = raw_token({"user_id": 3, "role": "customer", "expiry_timestamp": time.time() - 1})
    response = client.get("/me", headers=bearer(token))
    assert response.status_code == 403
    assert response.json()["detail"] == "Expired token"


def test_malformed_token():
    response = client.get("/me", headers=bearer("pas-un-token"))
    assert response.status_code == 403
    assert response.json()["detail"] == "Error decoding token"


def test_token_without_expiry_gives_unknown_error():
    """Signature correcte mais pas de champ expiry_timestamp -> erreur imprévue."""
    response = client.get("/me", headers=bearer(raw_token({"user_id": 3})))
    assert response.status_code == 403
    assert response.json()["detail"] == "Unknown error"


def test_no_credentials_when_auto_error_disabled():
    """Avec auto_error=False, HTTPBearer renvoie None au lieu de lever : c'est JWTBearer qui refuse."""
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    with pytest.raises(HTTPException) as error:
        asyncio.run(JWTBearer(auto_error=False)(request))
    assert error.value.status_code == 403
    assert error.value.detail == "Invalid authorization code."


# --- Rôles ---------------------------------------------------------------------------
def test_admin_route_accepts_admin():
    assert client.get("/admin", headers=bearer(token_for(1, "admin"))).status_code == 200


@pytest.mark.parametrize("role", ["customer", None])
def test_admin_route_refuses_others(role):
    response = client.get("/admin", headers=bearer(token_for(10, role)))
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin only"


def test_customer_route_accepts_customer():
    assert client.get("/customer", headers=bearer(token_for(10, "customer"))).status_code == 200


@pytest.mark.parametrize("role", ["admin", None])
def test_customer_route_refuses_others(role):
    response = client.get("/customer", headers=bearer(token_for(1, role)))
    assert response.status_code == 403
    assert response.json()["detail"] == "Customers only"

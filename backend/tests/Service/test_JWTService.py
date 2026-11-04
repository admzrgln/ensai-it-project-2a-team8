import datetime

import pytest
from freezegun import freeze_time
from jwt import DecodeError, ExpiredSignatureError

from backend.src.Service.JWTService import JwtService

jwt_service = JwtService("mysecret")


@freeze_time("2024-08-26 12:00:00")
def test_encode_jwt():
    user_id = "myUser"
    jwtResponse = jwt_service.encode_jwt(user_id=user_id)
    assert (
        jwtResponse.access_token
        == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoibXlVc2VyIiwiZXhwaXJ5X3RpbWVzdGFtcCI6MTcyNDY3NDIwMC4wfQ.eUjNbpMCDNuPESsMHF2dpeRlDl6fMJmjUWsHSZT_n1Q"  # noqa: E501
    )


@freeze_time("2024-08-26 12:00:00")
def test_decode_jwt():
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoibXlVc2VyIiwiZXhwaXJ5X3RpbWVzdGFtcCI6MTcyNDY3NDIwMC4wfQ.eUjNbpMCDNuPESsMHF2dpeRlDl6fMJmjUWsHSZT_n1Q"  # noqa: E501
    decoded_jwt = jwt_service.decode_jwt(jwt)
    assert decoded_jwt.get("user_id") == "myUser"
    assert datetime.datetime.fromtimestamp(decoded_jwt.get("expiry_timestamp")) == datetime.datetime.fromisoformat(
        "2024-08-26 12:10:00"
    )


def test_secret_from_environment(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "secret-from-env")
    assert JwtService().secret == "secret-from-env"


def test_secret_given_explicitly():
    service = JwtService("explicit-secret", algorithm="HS512")
    assert (service.secret, service.algorithm) == ("explicit-secret", "HS512")


def test_encode_with_role():
    token = jwt_service.encode_jwt(user_id=3, role="admin").access_token
    payload = jwt_service.decode_jwt(token)
    assert (payload["user_id"], payload["role"]) == (3, "admin")


def test_encode_without_role_has_no_role_key():
    payload = jwt_service.decode_jwt(jwt_service.encode_jwt(user_id=3).access_token)
    assert "role" not in payload


def test_validate_valid_token():
    token = jwt_service.encode_jwt(user_id=3, role="customer").access_token
    assert jwt_service.validate_user_jwt(token)["user_id"] == 3


def test_validate_expired_token():
    with freeze_time("2024-08-26 12:00:00"):
        token = jwt_service.encode_jwt(user_id=3).access_token
    with freeze_time("2024-08-26 12:10:01"), pytest.raises(ExpiredSignatureError):  # 10 min + 1 s
        jwt_service.validate_user_jwt(token)


def test_token_signed_with_another_secret_is_refused():
    token = JwtService("other-secret").encode_jwt(user_id=3).access_token
    with pytest.raises(DecodeError):
        jwt_service.validate_user_jwt(token)

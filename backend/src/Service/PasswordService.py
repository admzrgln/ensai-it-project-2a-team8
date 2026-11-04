import hashlib
import secrets
from backend.src.Model.User import User


def hash_password(password: str, salt: str | None = None) -> str:
    """Retourne le hash SHA-256 du mot de passe, préfixé par le sel s'il y en a un."""
    return hashlib.sha256(((salt or "") + password).encode()).hexdigest()


def create_salt() -> str:
    return secrets.token_hex(128)


def check_password_strength(password: str):
    if len(password) < 8:
        raise Exception("Password length must be at least 8 characters")


def validate_username_password(username: str, password: str, user_repo) -> User:
    user = user_repo.get_by_username(username)
    if user is None:
        raise Exception(f"user with username {username} not found")

    hashed_input_password = hash_password(password, user.salt)
    if hashed_input_password != user.password:
        raise Exception("Incorrect password")

    return user
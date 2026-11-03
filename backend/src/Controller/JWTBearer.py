from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import DecodeError, ExpiredSignatureError

from backend.src.Service.JWTService import JwtService

jwt_service = JwtService()


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict:
        credentials: HTTPAuthorizationCredentials | None = await super().__call__(request)
        if not credentials:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")
        try:
            return jwt_service.validate_user_jwt(credentials.credentials)
        except ExpiredSignatureError as e:
            raise HTTPException(status_code=403, detail="Expired token") from e
        except DecodeError as e:
            raise HTTPException(status_code=403, detail="Error decoding token") from e
        except Exception as e:
            raise HTTPException(status_code=403, detail="Unknown error") from e


def get_current_user(payload: dict = Depends(JWTBearer())) -> dict:
    """Retourne le contenu du token : {"user_id": ..., "role": ...}"""
    return payload


def require_admin(payload: dict = Depends(get_current_user)) -> dict:
    """Refuse l'accès si l'utilisateur n'est pas administrateur."""
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return payload
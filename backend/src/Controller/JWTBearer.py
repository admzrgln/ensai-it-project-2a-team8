from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import DecodeError, ExpiredSignatureError

from backend.src.Service.JWTService import JwtService

jwt_service = JwtService()

# Content of a valid token: {"user_id": ..., "role": ..., "expiry_timestamp": ...}
TokenPayload = dict[str, Any]


class JWTBearer(HTTPBearer):
    """FastAPI security dependency: reads and checks the "Authorization: Bearer <token>" header.

    Parameters
    ----------
    auto_error : bool, optional
        If True (default), a request without the header is refused by HTTPBearer itself.
    """

    def __init__(self, auto_error: bool = True) -> None:
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> TokenPayload:  # type: ignore[override]
        # HTTPBearer.__call__ returns the credentials: here we return the content of the token
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


def get_current_user(payload: Annotated[TokenPayload, Depends(JWTBearer())]) -> TokenPayload:
    """Return the content of the token of the logged-in user.

    Parameters
    ----------
    payload : dict
        Content of the token, given by JWTBearer.

    Returns
    -------
    dict
        {"user_id": ..., "role": ..., "expiry_timestamp": ...}
    """
    return payload


CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


def require_admin(payload: CurrentUser) -> TokenPayload:
    """Refuse the request if the user is not an administrator.

    Parameters
    ----------
    payload : dict
        Content of the token of the logged-in user.

    Returns
    -------
    dict
        The same content, if the user is an administrator.

    Raises
    ------
    HTTPException
        403 if the user is not an administrator.
    """
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return payload


def require_customer(payload: CurrentUser) -> TokenPayload:
    """Refuse the request if the user is not a customer (e.g. to book).

    Parameters
    ----------
    payload : dict
        Content of the token of the logged-in user.

    Returns
    -------
    dict
        The same content, if the user is a customer.

    Raises
    ------
    HTTPException
        403 if the user is not a customer.
    """
    if payload.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Customers only")
    return payload


# To use in the routes: `admin: AdminPayload`, `user: CustomerPayload`, `current: CurrentUser`
AdminPayload = Annotated[TokenPayload, Depends(require_admin)]
CustomerPayload = Annotated[TokenPayload, Depends(require_customer)]

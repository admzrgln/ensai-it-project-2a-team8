from pydantic import BaseModel


class JWTResponse(BaseModel):
    """Response of a successful login.

    Parameters
    ----------
    access_token : str
        JWT token to send in the Authorization header ("Bearer <token>").
    """

    access_token: str

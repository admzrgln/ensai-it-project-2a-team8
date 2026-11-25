import os
import time
from typing import Any

import jwt
from jwt import ExpiredSignatureError

from backend.src.Model.JWTResponse import JWTResponse


class JwtService:
    """Creation and validation of the JWT authentication tokens.

    Parameters
    ----------
    secret : str, optional
        Secret key used to sign the tokens; read from the JWT_SECRET variable if empty.
    algorithm : str, optional
        Signature algorithm ("HS256" by default).
    """

    def __init__(self, secret: str = "", algorithm: str = "HS256") -> None:
        if secret == "":
            self.secret = os.environ["JWT_SECRET"]
        else:
            self.secret = secret
        self.algorithm = algorithm

    def encode_jwt(self, user_id: int, role: str | None = None) -> JWTResponse:
        """Create a token valid for 10 minutes.

        Parameters
        ----------
        user_id : int
            Identifier of the user.
        role : str or None, optional
            Role of the user ("admin" or "customer"), stored in the token if given.

        Returns
        -------
        JWTResponse
            The signed token.
        """
        payload: dict[str, Any] = {"user_id": user_id}
        if role is not None:
            payload["role"] = role
        payload["expiry_timestamp"] = time.time() + 600
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return JWTResponse(access_token=token)

    def decode_jwt(self, token: str) -> dict[str, Any]:
        """Decode a token and check its signature.

        Parameters
        ----------
        token : str
            The token.

        Returns
        -------
        dict
            The content of the token ("user_id", "role", "expiry_timestamp").
        """
        payload: dict[str, Any] = jwt.decode(token, self.secret, algorithms=[self.algorithm])
        return payload

    def validate_user_jwt(self, token: str) -> dict[str, Any]:
        """Check a token: signature and expiry.

        Parameters
        ----------
        token : str
            The token.

        Returns
        -------
        dict
            The content of the token.

        Raises
        ------
        jwt.DecodeError
            If the token is invalid.
        jwt.ExpiredSignatureError
            If the token has expired.
        """
        decoded_jwt = self.decode_jwt(token)
        if decoded_jwt["expiry_timestamp"] < time.time():
            raise ExpiredSignatureError("Expired JWT")
        return decoded_jwt

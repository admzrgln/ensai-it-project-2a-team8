import os
import time

import jwt
from jwt import ExpiredSignatureError

from backend.src.Model.JWTResponse import JWTResponse


class JwtService:
    """Handler for JWT encryption and validation"""

    def __init__(self, secret: str = "", algorithm: str = "HS256"):
        if secret == "":
            self.secret = os.environ["JWT_SECRET"]
        else:
            self.secret = secret
        self.algorithm = algorithm

    def encode_jwt(self, user_id: int, role: str | None = None) -> JWTResponse:
        """Creates a token with a 10 minutes expiry time"""
        payload = {"user_id": user_id}
        if role is not None:
            payload["role"] = role
        payload["expiry_timestamp"] = time.time() + 600
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return JWTResponse(access_token=token)

    def decode_jwt(self, token: str) -> dict:
        """Unciphers an authentication token"""
        return jwt.decode(token, self.secret, algorithms=[self.algorithm])

    def validate_user_jwt(self, token: str) -> dict:
        """Returns the payload of the JWT. Throws if invalid or expired."""
        decoded_jwt = self.decode_jwt(token)
        if decoded_jwt["expiry_timestamp"] < time.time():
            raise ExpiredSignatureError("Expired JWT")
        return decoded_jwt
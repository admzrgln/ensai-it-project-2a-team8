from pydantic import BaseModel


class APIUser(BaseModel):
    """User as exposed by the API (identifier and name only).

    Parameters
    ----------
    id : int
        Identifier of the user.
    username : str
        Name of the user.
    """

    id: int
    username: str

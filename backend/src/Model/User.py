from abc import ABC
from datetime import date


class User(ABC):
    """Abstract base class representing a generic user."""
    
    def __init__(self, id_user: int | None, first_name: str, last_name: str, 
                 email: str, password: str, date_of_birth: date | None, role: str):
        self.id_user = id_user
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password
        self.date_of_birth = date_of_birth
        self.role = role

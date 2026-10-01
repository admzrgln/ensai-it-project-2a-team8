from backend.src.Model.User import User
from datetime import date


class Administrator(User):
    """Class representing an administrator, inheriting from User."""
    
    def __init__(self, id_user: int | None, first_name: str, last_name: str, 
                 email: str, password: str, date_of_birth: date | None):
        
        super().__init__(id_user, first_name, last_name, email, password, date_of_birth, 
                        role="admin")
    
    def __str__(self):
        """Définit le comportement de l'objet lorsqu'il est passé à print()"""
        return f"Movie {self.id_user} : {self.first_name} {self.last_name} {self.date_of_birth} {self.role} - {self.email}]"

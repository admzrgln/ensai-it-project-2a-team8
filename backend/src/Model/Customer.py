from backend.src.Model.User import User
from datetime import date


class Customer(User):
    """Class representing a customer, inheriting from User."""
    
    def __init__(self, id_user: int | None, first_name: str, last_name: str, 
                 email: str, password: str, date_of_birth: date | None, 
                 is_ensai_student: bool = False):
        
        # Le rôle est automatiquement forcé à 'customer' pour éviter toute erreur
        super().__init__(id_user, first_name, last_name, email, password, date_of_birth, role="customer")
        self.is_ensai_student = is_ensai_student
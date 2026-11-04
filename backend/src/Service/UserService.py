from backend.src.DAO.UserDAO import UserDao  # noqa: N999
from backend.src.Model.User import User
from backend.src.Model.Customer import Customer
from backend.src.Model.Administrator import Administrator
from utils.log_utils import log
from backend.src.Service.PasswordService import check_password_strength, create_salt, hash_password


class UserService:
    """Class containing User service methods (Business Logic Layer)"""

    def __init__(self):
        self.user_dao = UserDao()

    @log
    def find_all(self) -> list[User]:
        """List all users available in the database"""
        return self.user_dao.find_all_user()

    @log
    def find_by_id(self, id_user: int) -> User | None:
        """Find a specific user by its id"""
        return self.user_dao.find_by_id(id_user)

    @log
    def find_by_email(self, email: str) -> User | None:
        """Find a user by their email address"""
        return self.user_dao.find_user_by_email(email)

    @log
    def create_user(self, user: User) -> User | None:
        """Validate and create a new user"""
        # 1. Vérifier que l'email n'est pas déjà utilisé (contrainte UNIQUE)
        existing_user = self.user_dao.find_user_by_email(user.email)
        if existing_user is not None:
            return None

        # 2. Règle du rapport d'analyse : statut étudiant avec une adresse ensai.fr
        if isinstance(user, Customer) and user.email.lower().endswith("@ensai.fr"):
            user.is_ensai_student = True

        # 3. Vérifier la solidité du mot de passe
        try:
            check_password_strength(user.password)
        except Exception:
            return None

        # 4. Générer un sel et hacher le mot de passe avant l'insertion
        user.salt = create_salt()
        user.password = hash_password(user.password, user.salt)

        return self.user_dao.insert_user(user)

    @log
    def update_user(self, id_user: int, user: User) -> User | None:
        """Validate and update an existing user"""
        if id_user is None:
            return None

        if isinstance(user, Customer) and user.email.lower().endswith("@ensai.fr"):
            user.is_ensai_student = True

        try:
            check_password_strength(user.password)
        except Exception:
            return None

        user.salt = create_salt()
        user.password = hash_password(user.password, user.salt)

        return self.user_dao.update_user(id_user, user)

    @log
    def delete_user(self, id_user: int) -> bool:
        """Validate and delete a user by its id"""
        return self.user_dao.delete_user(id_user)

    @log
    def authenticate(self, email: str, password: str) -> User | None:
        """Authenticate a user with their email and password"""
        user = self.user_dao.find_user_by_email(email)
        if user and user.salt and user.password == hash_password(password, user.salt):
            return user
        return None
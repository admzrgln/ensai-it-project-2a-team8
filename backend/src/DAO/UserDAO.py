from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Administrator import Administrator
from backend.src.Model.Customer import Customer
from backend.src.Model.User import User
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class UserDao(metaclass=Singleton):
    """Class containing methods to access User in the database."""

    @staticmethod
    def _to_user(row: dict) -> User:
        """Convertit une ligne SQL en Administrator ou Customer."""
        if row["role"] == "admin":
            return Administrator(
                id_user=row["id_user"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                email=row["email"],
                password=row["password"],
                date_of_birth=row["date_of_birth"],
                salt=row.get("salt"),
            )
        return Customer(
            id_user=row["id_user"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            email=row["email"],
            password=row["password"],
            date_of_birth=row["date_of_birth"],
            is_ensai_student=row.get("is_ensai_student", False),
            salt=row.get("salt"),
        )

    # partie GET
    @log
    def find_all_user(self) -> list[User]:
        """List all users in the database."""
        try:
            query = "SELECT * FROM public.app_user ORDER BY last_name;"
            res = DBConnector().sql_query(query, return_type="all")
        except Exception as e:
            logger.error(e)
            raise

        return [self._to_user(row) for row in (res or [])]

    @log
    def find_by_id(self, id_user: int) -> User | None:
        """Find a user by its id."""
        try:
            query = "SELECT * FROM public.app_user WHERE id_user = %(id_user)s;"
            row = DBConnector().sql_query(query, data={"id_user": id_user}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        return self._to_user(row) if row else None

    @log
    def find_user_by_email(self, email: str) -> User | None:
        """Find a user by their email address (crucial for authentication)."""
        try:
            query = "SELECT * FROM public.app_user WHERE email = %(email)s;"
            res = DBConnector().sql_query(query, data={"email": email}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        return self._to_user(res) if res else None

    # partie POST
    @log
    def insert_user(self, user: User) -> User | None:
        """Insert a new user (Customer or Administrator) into the database."""
        try:
            query = """
            INSERT INTO public.app_user
            (first_name, last_name, email, password, salt, role, date_of_birth, is_ensai_student)
            VALUES
            (%(first_name)s, %(last_name)s, %(email)s, %(password)s, %(salt)s, %(role)s,
             %(date_of_birth)s, %(is_ensai_student)s)
            RETURNING *;
            """

            data = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "password": user.password,
                "salt": user.salt,
                "role": user.role,
                "date_of_birth": user.date_of_birth,
                "is_ensai_student": getattr(user, "is_ensai_student", False),
            }

            res = DBConnector().sql_query(query, data=data, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        return self._to_user(res) if res else None

    # partie UPDATE
    @log
    def update_user(self, id_user: int, user: User) -> User | None:
        """Update an existing user in the database."""
        try:
            query = """
            UPDATE public.app_user
            SET first_name = %(first_name)s, last_name = %(last_name)s,
                email = %(email)s, password = %(password)s, salt = %(salt)s,
                role = %(role)s, date_of_birth = %(date_of_birth)s,
                is_ensai_student = %(is_ensai_student)s
            WHERE id_user = %(id_user)s
            RETURNING *;
            """

            data = {
                "id_user": id_user,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "password": user.password,
                "salt": user.salt,
                "role": user.role,
                "date_of_birth": user.date_of_birth,
                "is_ensai_student": getattr(user, "is_ensai_student", False),
            }

            res = DBConnector().sql_query(query, data=data, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        return self._to_user(res) if res else None

    # partie DELETE
    @log
    def delete_user(self, id_user: int) -> bool:
        """Delete a user by their id."""
        try:
            query = "DELETE FROM public.app_user WHERE id_user = %(id_user)s RETURNING id_user;"
            res = DBConnector().sql_query(query, data={"id_user": id_user}, return_type="one")
            return res is not None
        except Exception as e:
            logger.error(e)
            raise
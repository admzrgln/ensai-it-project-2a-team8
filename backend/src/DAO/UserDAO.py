from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Administrator import Administrator
from backend.src.Model.Customer import Customer
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

if TYPE_CHECKING:
    from backend.src.Model.User import User

logger = get_logger(__name__)


class UserDao(metaclass=Singleton):
    """Access to the users (administrators and customers) in the database."""

    @staticmethod
    def _to_user(row: dict[str, Any]) -> User:
        """Convert a row of the app_user table into an Administrator or a Customer.

        Parameters
        ----------
        row : dict
            Row returned by the database.

        Returns
        -------
        User
            An Administrator if the role is "admin", a Customer otherwise.
        """
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

    # GET
    @log
    def find_all_user(self) -> list[User]:
        """List all the users, ordered by last name.

        Returns
        -------
        list of User
            All the users (empty list if there is none).
        """
        try:
            query = "SELECT * FROM public.app_user ORDER BY last_name;"
            res = DBConnector().sql_query(query, return_type="all")
        except Exception as e:
            logger.error(e)
            raise

        return [self._to_user(row) for row in (res or [])]

    @log
    def find_by_id(self, id_user: int) -> User | None:
        """Find a user by their identifier.

        Parameters
        ----------
        id_user : int
            Identifier of the user.

        Returns
        -------
        User or None
            The user, or None if they do not exist.
        """
        try:
            query = "SELECT * FROM public.app_user WHERE id_user = %(id_user)s;"
            row = DBConnector().sql_query(query, data={"id_user": id_user}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        return self._to_user(row) if row else None

    @log
    def find_user_by_email(self, email: str) -> User | None:
        """Find a user by their email address (used to log in).

        Parameters
        ----------
        email : str
            Email address of the user.

        Returns
        -------
        User or None
            The user, or None if no account uses this address.
        """
        try:
            query = "SELECT * FROM public.app_user WHERE email = %(email)s;"
            res = DBConnector().sql_query(query, data={"email": email}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        return self._to_user(res) if res else None

    # POST
    @log
    def insert_user(self, user: User) -> User | None:
        """Insert a new user (Customer or Administrator).

        Parameters
        ----------
        user : User
            The user to insert, with an already hashed password.

        Returns
        -------
        User or None
            The user as saved in the database (with its id_user), or None.
        """
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

    # UPDATE
    @log
    def update_user(self, id_user: int, user: User) -> User | None:
        """Update an existing user.

        Parameters
        ----------
        id_user : int
            Identifier of the user to update.
        user : User
            The new values of the user.

        Returns
        -------
        User or None
            The user as saved in the database, or None if they do not exist.
        """
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

    # DELETE
    @log
    def delete_user(self, id_user: int) -> bool:
        """Delete a user by their identifier.

        Parameters
        ----------
        id_user : int
            Identifier of the user.

        Returns
        -------
        bool
            True if the user was deleted, False if they do not exist.
        """
        try:
            query = "DELETE FROM public.app_user WHERE id_user = %(id_user)s RETURNING id_user;"
            res = DBConnector().sql_query(query, data={"id_user": id_user}, return_type="one")
            return res is not None
        except Exception as e:
            logger.error(e)
            raise

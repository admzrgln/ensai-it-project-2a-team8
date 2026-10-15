# import logging

from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.User import User
from backend.src.Model.Customer import Customer
from backend.src.Model.Administrator import Administrator
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class UserDao(metaclass=Singleton):
    """Class containing methods to access User in the database."""

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

        users_list = []

        if res:
            for row in res:
                if row["role"] == "admin":
                    admin = Administrator(
                        id_user=row["id_user"],
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        email=row["email"],
                        password=row["password"],
                        date_of_birth=row["date_of_birth"]
                    )
                    users_list.append(admin)

                else:
                    customer = Customer(
                        id_user=row["id_user"],
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        email=row["email"],
                        password=row["password"],
                        date_of_birth=row["date_of_birth"],
                        is_ensai_student=row.get("is_ensai_student", False)  
                    )
                    users_list.append(customer)  

        return users_list

    @log
    def find_by_id(self, id_user: int) -> User | None:
        """Find a user by its id."""
        try:
            query = "SELECT * FROM public.app_user WHERE id_user = %(id_user)s;"
            row = DBConnector().sql_query(query, data={"id_user": id_user}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        if not row:
            return None

        if row["role"] == "admin":
            return Administrator(
                id_user=row["id_user"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                email=row["email"],
                password=row["password"],
                date_of_birth=row["date_of_birth"],
            )
        return Customer(
            id_user=row["id_user"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            email=row["email"],
            password=row["password"],
            date_of_birth=row["date_of_birth"],
            is_ensai_student=row.get("is_ensai_student", False),
        )

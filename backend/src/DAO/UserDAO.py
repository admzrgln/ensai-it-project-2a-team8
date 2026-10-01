#import logging

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
            # Correction 1 & 2 : app_user et last_name
            query = "SELECT * FROM public.app_user ORDER BY last_name;"
            res = DBConnector().sql_query(query, return_type="all")

        except Exception as e:
            logger.error(e)
            raise

        users_list = []

        if res:
            for row in res:
                # Correction 3 : row["role"]
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
                        is_ensai_student=row.get("is_ensai_student", False) # Correction 4
                    )
                    users_list.append(customer) # Correction 5 : ajout à la liste

        return users_list

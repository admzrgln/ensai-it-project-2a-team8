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
    def find_user_by_id(self, id_user: int) -> User:
        """List all users in the database."""
        try:
            query = """
            SELECT * FROM public.app_user
            WHERE id_user = %(id_user)s;
            """
            res = DBConnector().sql_query(
                query, data={"id_user": id_user}, return_type="one"
            )
        except Exception as e:
            logger.error(e)
            raise

        admin = None
        customer = None
        
        if res["role"] == "admin":
            admin = Administrator(
                id_user=res["id_user"],
                first_name=res["first_name"],
                last_name=res["last_name"],
                email=res["email"],
                password=res["password"],
                date_of_birth=res["date_of_birth"]
            )   

            return admin

        else:
            customer = Customer(
                id_user=res["id_user"],
                first_name=res["first_name"],
                last_name=res["last_name"],
                email=res["email"],
                password=res["password"],
                date_of_birth=res["date_of_birth"],
                is_ensai_student=res.get("is_ensai_student", False) 
            )   

            return customer

    @log
    def find_user_by_email(self, email: str) -> User | None:
        """Find a user by their email address (crucial for authentication)."""
        try:
            query = "SELECT * FROM public.app_user WHERE email = %(email)s;"
            res = DBConnector().sql_query(query, data={"email": email}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        if not res:
            return None

        if res["role"] == "admin":
            return Administrator(
                id_user=res["id_user"],
                first_name=res["first_name"],
                last_name=res["last_name"],
                email=res["email"],
                password=res["password"],
                date_of_birth=res["date_of_birth"]
            )
        else:
            return Customer(
                id_user=res["id_user"],
                first_name=res["first_name"],
                last_name=res["last_name"],
                email=res["email"],
                password=res["password"],
                date_of_birth=res["date_of_birth"],
                is_ensai_student=res.get("is_ensai_student", False)
            )

    @log
    def insert_user(self, user: User) -> User | None:
        """Insert a new user (Customer or Administrator) into the database."""
        try:
            query = """
            INSERT INTO public.app_user 
            (first_name, last_name, email, password, role, date_of_birth, is_ensai_student)
            VALUES 
            (%(first_name)s, %(last_name)s, %(email)s, %(password)s, %(role)s, %(date_of_birth)s, %(is_ensai_student)s)
            RETURNING *;
            """
            
            data = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "password": user.password,
                "role": user.role,
                "date_of_birth": user.date_of_birth,
                "is_ensai_student": getattr(user, "is_ensai_student", False) # Gère l'absence de l'attribut chez l'admin
            }
            
            res = DBConnector().sql_query(query, data=data, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        if not res:
            return None
            
        if res["role"] == "admin":
            return Administrator(
                id_user=res["id_user"], first_name=res["first_name"], last_name=res["last_name"],
                email=res["email"], password=res["password"], date_of_birth=res["date_of_birth"]
            )
        else:
            return Customer(
                id_user=res["id_user"], first_name=res["first_name"], last_name=res["last_name"],
                email=res["email"], password=res["password"], date_of_birth=res["date_of_birth"],
                is_ensai_student=res.get("is_ensai_student", False)
            )

    @log
    def update_user(self, id_user: int, user: User) -> User | None:
        """Update an existing user in the database."""
        try:
            query = """
            UPDATE public.app_user
            SET first_name = %(first_name)s, last_name = %(last_name)s, 
                email = %(email)s, password = %(password)s, 
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
                "role": user.role,
                "date_of_birth": user.date_of_birth,
                "is_ensai_student": getattr(user, "is_ensai_student", False)
            }
            
            res = DBConnector().sql_query(query, data=data, return_type="one")
        except Exception as e:
            logger.error(e)
            raise

        if not res:
            return None
            
        if res["role"] == "admin":
            return Administrator(
                id_user=res["id_user"], first_name=res["first_name"], last_name=res["last_name"],
                email=res["email"], password=res["password"], date_of_birth=res["date_of_birth"]
            )
        else:
            return Customer(
                id_user=res["id_user"], first_name=res["first_name"], last_name=res["last_name"],
                email=res["email"], password=res["password"], date_of_birth=res["date_of_birth"],
                is_ensai_student=res.get("is_ensai_student", False)
            )

    @log
    def delete_user(self, id_user: int) -> bool:
        """Delete a user by their id."""
        try:
            query = "DELETE FROM public.app_user WHERE id_user = %(id_user)s RETURNING id_user;"
            res = DBConnector().sql_query(query, data={"id_user": id_user}, return_type="one")
            
            # Si res n'est pas None, c'est que la suppression a réussi
            return res is not None
        except Exception as e:
            logger.error(e)
            raise
        
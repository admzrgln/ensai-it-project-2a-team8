from __future__ import annotations

from typing import TYPE_CHECKING

from backend.src.DAO.UserDAO import UserDao
from backend.src.Model.Customer import Customer
from backend.src.Service.PasswordService import check_password_strength, create_salt, hash_password
from utils.log_utils import log

if TYPE_CHECKING:
    from backend.src.Model.User import User


class UserService:
    """Business rules on the users: accounts, passwords and authentication."""

    def __init__(self) -> None:
        self.user_dao: UserDao = UserDao()

    @log
    def find_all(self) -> list[User]:
        """List all the users.

        Returns
        -------
        list of User
            All the users, ordered by last name.
        """
        return self.user_dao.find_all_user()

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
        return self.user_dao.find_by_id(id_user)

    @log
    def find_by_email(self, email: str) -> User | None:
        """Find a user by their email address.

        Parameters
        ----------
        email : str
            Email address.

        Returns
        -------
        User or None
            The user, or None if no account uses this address.
        """
        return self.user_dao.find_user_by_email(email)

    @log
    def create_user(self, user: User) -> User | None:
        """Check and create a new user, with a salted and hashed password.

        A customer with an @ensai.fr address becomes an ENSAI student.

        Parameters
        ----------
        user : User
            The user to create, with their password in clear text.

        Returns
        -------
        User or None
            The user created, or None if the email is already used,
            the password is too weak or the insertion failed.
        """
        existing_user = self.user_dao.find_user_by_email(user.email)
        if existing_user is not None:
            return None

        if isinstance(user, Customer) and user.email.lower().endswith("@ensai.fr"):
            user.is_ensai_student = True

        try:
            check_password_strength(user.password)
        except Exception:
            return None

        user.salt = create_salt()
        user.password = hash_password(user.password, user.salt)

        return self.user_dao.insert_user(user)

    @log
    def update_user(self, id_user: int, user: User, change_password: bool = True) -> User | None:
        """Check and update an existing user.

        Parameters
        ----------
        id_user : int
            Identifier of the user to update.
        user : User
            The new values of the user.
        change_password : bool, optional
            If False, user.password is already the hash saved in the database (and user.salt
            its salt): it is not hashed again.

        Returns
        -------
        User or None
            The user updated, or None if the email belongs to another account,
            the new password is too weak or the user does not exist.
        """
        if id_user is None:
            return None

        other = self.user_dao.find_user_by_email(user.email)
        if other is not None and other.id_user != id_user:
            return None

        if isinstance(user, Customer) and user.email.lower().endswith("@ensai.fr"):
            user.is_ensai_student = True

        if change_password:
            try:
                check_password_strength(user.password)
            except Exception:
                return None
            user.salt = create_salt()
            user.password = hash_password(user.password, user.salt)

        return self.user_dao.update_user(id_user, user)

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
            True if the user was deleted, False otherwise.
        """
        return self.user_dao.delete_user(id_user)

    @log
    def authenticate(self, email: str, password: str) -> User | None:
        """Check the email and password of a user.

        Parameters
        ----------
        email : str
            Email address.
        password : str
            Password in clear text.

        Returns
        -------
        User or None
            The user if the credentials are correct, None otherwise.
        """
        user = self.user_dao.find_user_by_email(email)
        if user and user.salt and user.password == hash_password(password, user.salt):
            return user
        return None

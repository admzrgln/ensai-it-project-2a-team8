import logging
from datetime import date
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.src.Controller.JWTBearer import AdminPayload, CurrentUser, TokenPayload, jwt_service, require_admin
from backend.src.Model.Administrator import Administrator
from backend.src.Model.Customer import Customer
from backend.src.Model.JWTResponse import JWTResponse
from backend.src.Model.Role import Role
from backend.src.Model.User import User
from backend.src.Service.TariffService import TariffService
from backend.src.Service.UserService import UserService

user_router = APIRouter(prefix="/users")
user_service = UserService()
tariff_service = TariffService()

VALID_ROLES = {role.value for role in Role}

T = TypeVar("T")


class UserResponseModel(BaseModel):
    """User as returned by the API: never the hashed password nor the salt."""

    id_user: int | None = None
    first_name: str
    last_name: str
    email: str
    role: str
    date_of_birth: date | None = None
    is_ensai_student: bool = False


def to_response(user: User) -> UserResponseModel:
    """Convert a user into what the API returns.

    Parameters
    ----------
    user : User
        The user.

    Returns
    -------
    UserResponseModel
        The user without the password and the salt.
    """
    return UserResponseModel(
        id_user=user.id_user,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user.role,
        date_of_birth=user.date_of_birth,
        is_ensai_student=getattr(user, "is_ensai_student", False),
    )


class UserCreateModel(BaseModel):
    """Body of the registration: no role (always a customer for POST /users/)."""

    first_name: str
    last_name: str
    email: str
    password: str
    date_of_birth: date
    is_ensai_student: bool = Field(
        default=False,
        description="If is_ensai_student = true, your student card will be checked at the cinema desk.",
    )


class UserUpdateModel(BaseModel):
    """Body of a partial update: only the fields sent are changed."""

    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    password: str | None = Field(default=None, description="If missing, the current password is kept.")
    role: str | None = Field(default=None, description="Only an administrator can change the role.")
    date_of_birth: date | None = None
    is_ensai_student: bool | None = Field(
        default=None,
        description="If is_ensai_student = true, your student card will be checked at the cinema desk.",
    )


class LoginModel(BaseModel):
    """Body of the login request."""

    email: str
    password: str


def _pick(new: T | None, old: T) -> T:
    """Keep the value sent if there is one, the current value otherwise.

    Parameters
    ----------
    new : Any or None
        Value sent in the request (None if not sent).
    old : Any
        Current value.

    Returns
    -------
    Any
        new if it is not None, old otherwise.
    """
    return old if new is None else new


def check_self_or_admin(id_user: int, current: TokenPayload) -> None:
    """Refuse the request unless it is about one's own account or comes from an administrator.

    Parameters
    ----------
    id_user : int
        Identifier of the account concerned.
    current : dict
        Token of the logged-in user.

    Raises
    ------
    HTTPException
        403 if a customer acts on another account.
    """
    if current["role"] != Role.ADMIN and current["user_id"] != id_user:
        raise HTTPException(status_code=403, detail="Forbidden")


@user_router.get("/", tags=["Users"], dependencies=[Depends(require_admin)], response_model=list[UserResponseModel])
async def find_all_users() -> list[UserResponseModel]:
    """List all the users (administrators only).

    Returns
    -------
    list of UserResponseModel
        All the users, without their passwords.
    """
    logging.info("List all users")
    return [to_response(u) for u in user_service.find_all()]


@user_router.get(
    "/search/{email}", tags=["Users"], dependencies=[Depends(require_admin)], response_model=UserResponseModel
)
async def user_by_email(email: str) -> UserResponseModel:
    """Find a user by their email address (administrators only).

    Parameters
    ----------
    email : str
        Email address.

    Returns
    -------
    UserResponseModel
        The user (error 404 if no account uses this address).
    """
    logging.info(f"Find a user by email: {email}")
    user = user_service.find_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_response(user)


@user_router.get("/{id_user}", tags=["Users"], response_model=UserResponseModel)
async def user_by_id(id_user: int, current: CurrentUser) -> UserResponseModel:
    """Find a user by their identifier (own account, or any account for an administrator).

    Parameters
    ----------
    id_user : int
        Identifier of the user.
    current : dict
        Token of the logged-in user.

    Returns
    -------
    UserResponseModel
        The user (error 403 for another account, 404 if they do not exist).
    """
    check_self_or_admin(id_user, current)
    logging.info(f"Find a user by id: {id_user}")
    user = user_service.find_by_id(id_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_response(user)


@user_router.post("/", tags=["Users"], status_code=201, response_model=None)
async def create_user(user_data: UserCreateModel) -> dict[str, Any]:
    """Create a customer account (public registration).

    Parameters
    ----------
    user_data : UserCreateModel
        Information of the new customer.

    Returns
    -------
    dict
        The account created and a message listing the tariffs the customer is entitled to
        (error 400 if the email is already used or the password is too weak).
    """
    logging.info(f"Create a new user: {user_data.email}")

    # Public registration: always a customer, nobody can make themselves an administrator here
    new_user = Customer(
        id_user=None,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password=user_data.password,
        date_of_birth=user_data.date_of_birth,
        is_ensai_student=user_data.is_ensai_student,
    )

    created_user = user_service.create_user(new_user)
    if not created_user:
        raise HTTPException(status_code=400, detail="Email already exists, weak password or creation failed")

    today = date.today()
    dob = created_user.date_of_birth or user_data.date_of_birth
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    is_ensai_student = isinstance(created_user, Customer) and created_user.is_ensai_student
    eligible_tariffs = [
        f"{t.label} ({t.price:.2f}€)"
        for t in tariff_service.find_all(only_active=True)
        if not t.has_schedule_condition and t.is_eligible(age, is_ensai_student, False)
    ]

    message = "Registration successful. "
    if is_ensai_student:
        message += "Your student ID will be checked at the ticket office. "

    message += (
        f"Based on your age ({age} years old) and status, "
        f"you are eligible for the following tariffs: {', '.join(eligible_tariffs)}."
    )

    return {"user": to_response(created_user), "message": message}


@user_router.post("/admin", tags=["Users"], status_code=201, response_model=UserResponseModel)
async def create_admin(user_data: UserCreateModel, admin: AdminPayload) -> UserResponseModel:
    """Create an administrator account (administrators only).

    Parameters
    ----------
    user_data : UserCreateModel
        Information of the new administrator.
    admin : dict
        Token of the logged-in administrator.

    Returns
    -------
    UserResponseModel
        The account created (error 400 if the email is already used or the password is too weak).
    """
    logging.info(f"Admin {admin['user_id']} creates an admin: {user_data.email}")

    new_admin = Administrator(
        id_user=None,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password=user_data.password,
        date_of_birth=user_data.date_of_birth,
    )

    created_admin = user_service.create_user(new_admin)
    if not created_admin:
        raise HTTPException(status_code=400, detail="Email already exists, weak password or creation failed")
    return to_response(created_admin)


@user_router.post("/login", tags=["Users"])
async def login(credentials: LoginModel) -> JWTResponse:
    """Log in with an email and a password.

    Parameters
    ----------
    credentials : LoginModel
        Email and password.

    Returns
    -------
    JWTResponse
        The token to send in the Authorization header (error 401 if the credentials are wrong).
    """
    logging.info(f"Login attempt for: {credentials.email}")
    user = user_service.authenticate(credentials.email, credentials.password)
    if not user or user.id_user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return jwt_service.encode_jwt(user.id_user, user.role)


@user_router.put("/{id_user}", tags=["Users"], response_model=None)
async def update_user(id_user: int, user_data: UserUpdateModel, current: CurrentUser) -> dict[str, Any]:
    """Update a user (own account, or any account for an administrator); only the fields sent change.

    Parameters
    ----------
    id_user : int
        Identifier of the user.
    user_data : UserUpdateModel
        Fields to change.
    current : dict
        Token of the logged-in user (only an administrator can change a role).

    Returns
    -------
    dict
        Confirmation message and the user updated
        (errors 403 another account, 400 invalid role, 404 update failed).
    """
    logging.info(f"Update user id: {id_user}")
    check_self_or_admin(id_user, current)

    existing = user_service.find_by_id(id_user)
    if existing is None:
        raise HTTPException(status_code=404, detail="User not found or update failed")

    # Only an administrator can change the role; otherwise the current role is kept
    role: str = existing.role
    if current["role"] == Role.ADMIN and user_data.role is not None:
        role = user_data.role.lower()
        if role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail="Role must be 'admin' or 'customer'")

    change_password = user_data.password is not None
    first_name = _pick(user_data.first_name, existing.first_name)
    last_name = _pick(user_data.last_name, existing.last_name)
    email = _pick(user_data.email, existing.email)
    # without a new password, we keep the hash and the salt already in the database
    password = _pick(user_data.password, existing.password)
    date_of_birth = _pick(user_data.date_of_birth, existing.date_of_birth)

    user_to_update: User
    if role == Role.ADMIN:
        user_to_update = Administrator(
            id_user, first_name, last_name, email, password, date_of_birth, salt=existing.salt
        )
    else:
        current_status = isinstance(existing, Customer) and existing.is_ensai_student
        is_ensai_student = _pick(user_data.is_ensai_student, current_status)
        user_to_update = Customer(
            id_user, first_name, last_name, email, password, date_of_birth, is_ensai_student, salt=existing.salt
        )

    updated_user = user_service.update_user(id_user, user_to_update, change_password=change_password)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found or update failed")

    return {"message": "User updated successfully", "user": to_response(updated_user)}


@user_router.delete("/{id_user}", tags=["Users"], response_model=None)
async def delete_user(id_user: int, current: CurrentUser) -> dict[str, str]:
    """Delete a user (own account, or any account for an administrator).

    Parameters
    ----------
    id_user : int
        Identifier of the user.
    current : dict
        Token of the logged-in user.

    Returns
    -------
    dict
        Confirmation message (errors 403 another account, 404 unknown user).
    """
    logging.info(f"Delete user id: {id_user}")
    check_self_or_admin(id_user, current)

    if not user_service.delete_user(id_user):
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"User {id_user} deleted successfully"}

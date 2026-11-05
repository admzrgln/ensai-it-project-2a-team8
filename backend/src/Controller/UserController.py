import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.src.Controller.JWTBearer import get_current_user, jwt_service, require_admin
from backend.src.Model.Administrator import Administrator
from backend.src.Model.Customer import Customer
from backend.src.Model.User import User
from backend.src.Service.UserService import UserService

user_router = APIRouter(prefix="/users")
user_service = UserService()

VALID_ROLES = {"admin", "customer"}


class UserResponseModel(BaseModel):
    """Ce que l'API renvoie d'un utilisateur : jamais le mot de passe haché ni le sel."""
    id_user: int | None = None
    first_name: str
    last_name: str
    email: str
    role: str
    date_of_birth: date | None = None
    is_ensai_student: bool = False


def to_response(user: User) -> UserResponseModel:
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
    """Modèle d'inscription : pas de rôle (toujours client pour POST /users/)"""
    first_name: str
    last_name: str
    email: str
    password: str
    date_of_birth: date
    is_ensai_student: bool = Field(
        default=False,
        description="Si is_ensai_student = true, votre carte étudiante sera vérifiée au guichet.",
    )


class UserUpdateModel(BaseModel):
    """Mise à jour partielle : seuls les champs envoyés sont modifiés."""
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    password: str | None = Field(default=None, description="Si absent, le mot de passe actuel est conservé.")
    role: str | None = Field(default=None, description="Seul un administrateur peut modifier le rôle.")
    date_of_birth: date | None = None
    is_ensai_student: bool | None = Field(
        default=None,
        description="Si is_ensai_student = true, votre carte étudiante sera vérifiée au guichet.",
    )


class LoginModel(BaseModel):
    """Define a Pydantic model for Authentication"""
    email: str
    password: str


def _pick(new, old):
    """Valeur envoyée si elle existe, sinon valeur actuelle."""
    return old if new is None else new


def check_self_or_admin(id_user: int, current: dict):
    if current["role"] != "admin" and current["user_id"] != id_user:
        raise HTTPException(status_code=403, detail="Forbidden")


@user_router.get("/", tags=["Users"], dependencies=[Depends(require_admin)],
                 response_model=list[UserResponseModel])
async def find_all_users():
    """List all users"""
    logging.info("List all users")
    return [to_response(u) for u in user_service.find_all()]


@user_router.get("/search/{email}", tags=["Users"], dependencies=[Depends(require_admin)],
                 response_model=UserResponseModel)
async def user_by_email(email: str):
    """Find a user by email"""
    logging.info(f"Find a user by email: {email}")
    user = user_service.find_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_response(user)


@user_router.get("/{id_user}", tags=["Users"], response_model=UserResponseModel)
async def user_by_id(id_user: int, current: dict = Depends(get_current_user)):
    """Find a user by id"""
    check_self_or_admin(id_user, current)
    logging.info(f"Find a user by id: {id_user}")
    user = user_service.find_by_id(id_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_response(user)


@user_router.post("/", tags=["Users"], status_code=201)
async def create_user(user_data: UserCreateModel):
    """Create a new customer account"""
    logging.info(f"Create a new user: {user_data.email}")

    # Inscription publique : on force le rôle client, personne ne peut se créer admin ici
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
    dob = created_user.date_of_birth
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    eligible_tariffs = ["Full price (11.5€)"]

    if age <= 13:
        eligible_tariffs.append("Under 14 (6€)")
    if age >= 65:
        eligible_tariffs.append("Over 65 (9.5€)")
    if created_user.is_ensai_student:
        eligible_tariffs.append("ENSAI Student (7.8€)")

    message = "Registration successful. "
    if created_user.is_ensai_student:
        message += "Your student ID will be checked at the ticket office. "

    message += (f"Based on your age ({age} years old) and status, "
                f"you are eligible for the following tariffs: {', '.join(eligible_tariffs)}.")

    return {"user": to_response(created_user), "message": message}


@user_router.post("/admin", tags=["Users"], status_code=201, response_model=UserResponseModel)
async def create_admin(user_data: UserCreateModel, admin: dict = Depends(require_admin)):
    """Create a new administrator account (admin only)"""
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
async def login(credentials: LoginModel):
    """Authenticate a user and return a JWT"""
    logging.info(f"Login attempt for: {credentials.email}")
    user = user_service.authenticate(credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return jwt_service.encode_jwt(user.id_user, user.role)


@user_router.put("/{id_user}", tags=["Users"])
async def update_user(id_user: int, user_data: UserUpdateModel, current: dict = Depends(get_current_user)):
    """Update a user (own account, or any account for an admin). Only the sent fields are changed."""
    logging.info(f"Update user id: {id_user}")
    check_self_or_admin(id_user, current)

    existing = user_service.find_by_id(id_user)
    if existing is None:
        raise HTTPException(status_code=404, detail="User not found or update failed")

    # Le rôle ne change que si c'est un admin qui le demande ; sinon on garde l'actuel
    role = existing.role
    if current["role"] == "admin" and user_data.role is not None:
        role = user_data.role.lower()
        if role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail="Role must be 'admin' or 'customer'")

    change_password = user_data.password is not None
    common = dict(
        id_user=id_user,
        first_name=_pick(user_data.first_name, existing.first_name),
        last_name=_pick(user_data.last_name, existing.last_name),
        email=_pick(user_data.email, existing.email),
        # sans nouveau mot de passe, on repart du hash et du sel déjà en base
        password=_pick(user_data.password, existing.password),
        date_of_birth=_pick(user_data.date_of_birth, existing.date_of_birth),
        salt=existing.salt,
    )

    if role == "admin":
        user_to_update = Administrator(**common)
    else:
        user_to_update = Customer(
            **common,
            is_ensai_student=_pick(user_data.is_ensai_student, getattr(existing, "is_ensai_student", False)),
        )

    updated_user = user_service.update_user(id_user, user_to_update, change_password=change_password)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found or update failed")

    return {"message": "User updated successfully", "user": to_response(updated_user)}


@user_router.delete("/{id_user}", tags=["Users"])
async def delete_user(id_user: int, current: dict = Depends(get_current_user)):
    """Delete a user (own account, or any account for an admin)"""
    logging.info(f"Delete user id: {id_user}")
    check_self_or_admin(id_user, current)

    if not user_service.delete_user(id_user):
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"User {id_user} deleted successfully"}
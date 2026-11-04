import logging
from datetime import date
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.src.Controller.JWTBearer import require_admin, get_current_user
from backend.src.Service.UserService import UserService
from backend.src.Model.Customer import Customer
from backend.src.Model.Administrator import Administrator
from backend.src.Controller.JWTBearer import jwt_service

user_router = APIRouter(prefix="/users")
user_service = UserService()


class UserModel(BaseModel):
    """Modèle de mise à mise à jour d'un compte"""
    id_user: int | None = None
    first_name: str
    last_name: str
    email: str
    password: str
    role: str = Field(default="customer", description="Seul un administrateur peut modifier le rôle.")
    date_of_birth: date
    is_ensai_student: bool = Field(
        default=False,
        description="Si is_ensai_student = true, votre carte étudiante sera vérifiée au guichet.",
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


class LoginModel(BaseModel):
    """Define a Pydantic model for Authentication"""
    email: str
    password: str


@user_router.get("/", tags=["Users"], dependencies=[Depends(require_admin)])
async def find_all_users():
    """List all users"""
    logging.info("List all users")
    users_list = user_service.find_all()
    return users_list


@user_router.get("/search/{email}", tags=["Users"], dependencies=[Depends(require_admin)])
async def user_by_email(email: str):
    """Find a user by email"""
    logging.info(f"Find a user by email: {email}")
    user = user_service.find_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def check_self_or_admin(id_user: int, current: dict):
    if current["role"] != "admin" and current["user_id"] != id_user:
        raise HTTPException(status_code=403, detail="Forbidden")


@user_router.get("/{id_user}", tags=["Users"])
async def user_by_id(id_user: int, current: dict = Depends(get_current_user)):
    """Find a user by id"""
    check_self_or_admin(id_user, current)
    logging.info(f"Find a user by id: {id_user}")
    user = user_service.find_by_id(id_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


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

    message += f"Based on your age ({age} years old) and status, you are eligible for the following tariffs: {', '.join(eligible_tariffs)}."

    return {
        "user": created_user,
        "message": message
    }


@user_router.post("/admin", tags=["Users"], status_code=201)
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
    return created_admin


@user_router.post("/login", tags=["Users"])
async def login(credentials: LoginModel):
    """Authenticate a user and return a JWT"""
    logging.info(f"Login attempt for: {credentials.email}")
    user = user_service.authenticate(credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return jwt_service.encode_jwt(user.id_user, user.role)


@user_router.put("/{id_user}", tags=["Users"])
async def update_user(id_user: int, user_data: UserModel, current: dict = Depends(get_current_user)):
    """Update a user (own account, or any account for an admin)"""
    logging.info(f"Update user id: {id_user}")
    check_self_or_admin(id_user, current)

    # Seul un admin peut attribuer le rôle admin
    role = user_data.role.lower() if current["role"] == "admin" else "customer"

    if role == "admin":
        user_to_update = Administrator(
            id_user=id_user,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            password=user_data.password,
            date_of_birth=user_data.date_of_birth,
        )
    else:
        user_to_update = Customer(
            id_user=id_user,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            password=user_data.password,
            date_of_birth=user_data.date_of_birth,
            is_ensai_student=user_data.is_ensai_student,
        )

    updated_user = user_service.update_user(id_user, user_to_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found or update failed")

    return {"message": "User updated successfully", "user": updated_user}


@user_router.delete("/{id_user}", tags=["Users"])
async def delete_user(id_user: int, current: dict = Depends(get_current_user)):
    """Delete a user (own account, or any account for an admin)"""
    logging.info(f"Delete user id: {id_user}")
    check_self_or_admin(id_user, current)

    if not user_service.delete_user(id_user):
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"User {id_user} deleted successfully"}
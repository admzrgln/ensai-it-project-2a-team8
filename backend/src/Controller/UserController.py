import logging
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.Service.UserService import UserService
from backend.src.Model.Customer import Customer
from backend.src.Model.Administrator import Administrator
from backend.src.Controller.JWTBearer import jwt_service

user_router = APIRouter(prefix="/users")
user_service = UserService()


class UserModel(BaseModel):
    """Define a Pydantic model for Users"""
    id_user: int | None = None
    first_name: str
    last_name: str
    email: str
    password: str
    role: str = "customer"  # "customer" ou "admin"
    date_of_birth: date
    is_ensai_student: bool = False


class LoginModel(BaseModel):
    """Define a Pydantic model for Authentication"""
    email: str
    password: str


@user_router.get("/", tags=["Users"])
async def find_all_users():
    """List all users"""
    logging.info("List all users")
    users_list = user_service.find_all()
    return users_list


@user_router.get("/search/{email}", tags=["Users"])
async def user_by_email(email: str):
    """Find a user by email"""
    logging.info(f"Find a user by email: {email}")
    user = user_service.find_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@user_router.get("/{id_user}", tags=["Users"])
async def user_by_id(id_user: int):
    """Find a user by id"""
    logging.info(f"Find a user by id: {id_user}")
    user = user_service.find_by_id(id_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@user_router.post("/", tags=["Users"], status_code=201)
async def create_user(user_data: UserModel):
    """Create a new user (Customer or Administrator)"""
    logging.info(f"Create a new user: {user_data.email}")

    # Conversion du Pydantic Model vers le Modèle Python selon le rôle
    if user_data.role.lower() == "admin":
        new_user = Administrator(
            id_user=None,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            password=user_data.password,
            date_of_birth=user_data.date_of_birth
        )
    else:
        new_user = Customer(
            id_user=None,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            password=user_data.password,
            date_of_birth=user_data.date_of_birth,
            is_ensai_student=user_data.is_ensai_student
        )

    created_user = user_service.create_user(new_user)
    if not created_user:
        raise HTTPException(status_code=400, detail="Email already exists or creation failed")

    return created_user


@user_router.post("/login", tags=["Users"])
async def login(credentials: LoginModel):
    """Authenticate a user and return a JWT"""
    logging.info(f"Login attempt for: {credentials.email}")
    user = user_service.authenticate(credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return jwt_service.encode_jwt(user.id_user, user.role)


@user_router.put("/{id_user}", tags=["Users"])
async def update_user(id_user: int, user_data: UserModel):
    """Update an existing user"""
    logging.info(f"Update user id: {id_user}")

    if user_data.role.lower() == "admin":
        user_to_update = Administrator(
            id_user=id_user,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            password=user_data.password,
            date_of_birth=user_data.date_of_birth
        )
    else:
        user_to_update = Customer(
            id_user=id_user,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            password=user_data.password,
            date_of_birth=user_data.date_of_birth,
            is_ensai_student=user_data.is_ensai_student
        )

    updated_user = user_service.update_user(id_user, user_to_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found or update failed")

    return {"message": "User updated successfully", "user": updated_user}


@user_router.delete("/{id_user}", tags=["Users"])
async def delete_user(id_user: int):
    """Delete a user by id"""
    logging.info(f"Delete user id: {id_user}")

    is_deleted = user_service.delete_user(id_user)
    if not is_deleted:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"User {id_user} deleted successfully"}
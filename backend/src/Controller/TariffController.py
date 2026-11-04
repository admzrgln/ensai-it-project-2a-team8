import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.src.Controller.JWTBearer import require_admin
from backend.src.Model.Tariff import Tariff
from backend.src.Service.TariffService import TariffError, TariffService

tariff_router = APIRouter(prefix="/tariffs")
tariff_service = TariffService()


class TariffModel(BaseModel):
    """Define a Pydantic model for Tariffs"""
    code: str = Field(max_length=30)
    label: str = Field(max_length=100)
    price: float | None = None  # None = prix de base de la séance
    min_age: int | None = None  # âge minimum inclus (None = pas de minimum)
    max_age: int | None = None  # âge maximum inclus (None = pas de maximum)
    requires_ensai: bool = False
    requires_student: bool = False
    is_active: bool = True


def _call(fn, *args):
    try:
        return fn(*args)
    except TariffError as e:
        status = 404 if "not found" in str(e) else 400
        raise HTTPException(status_code=status, detail=str(e)) from e


@tariff_router.get("/", tags=["Tariffs"])
async def list_active_tariffs():
    """List the active tariffs (public)"""
    return tariff_service.find_all(only_active=True)


@tariff_router.get("/all", tags=["Tariffs"])
async def list_all_tariffs(admin: dict = Depends(require_admin)):
    """List all tariffs, including inactive ones (admin only)"""
    return tariff_service.find_all(only_active=False)


@tariff_router.post("/", tags=["Tariffs"], status_code=201)
async def create_tariff(data: TariffModel, admin: dict = Depends(require_admin)):
    """Create a new tariff (admin only)"""
    logging.info(f"Admin {admin['user_id']} creates tariff {data.code}")
    return _call(tariff_service.create_tariff, Tariff(**data.model_dump()))


@tariff_router.put("/{code}", tags=["Tariffs"])
async def update_tariff(code: str, data: TariffModel, admin: dict = Depends(require_admin)):
    """Update a tariff (admin only). Tickets already sold keep their price"""
    logging.info(f"Admin {admin['user_id']} updates tariff {code}")
    tariff = Tariff(**{**data.model_dump(), "code": code})  # le code de l'URL fait foi
    return _call(tariff_service.update_tariff, tariff)


@tariff_router.delete("/{code}", tags=["Tariffs"])
async def deactivate_tariff(code: str, admin: dict = Depends(require_admin)):
    """Deactivate a tariff (admin only). It is kept for the history of tickets already sold"""
    logging.info(f"Admin {admin['user_id']} deactivates tariff {code}")
    _call(tariff_service.deactivate_tariff, code)
    return {"message": f"Tariff {code} deactivated"}

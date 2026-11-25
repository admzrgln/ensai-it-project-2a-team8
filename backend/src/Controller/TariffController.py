import logging
from collections.abc import Callable
from datetime import time
from typing import ParamSpec, TypeVar

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.src.Controller.JWTBearer import AdminPayload
from backend.src.Model.Tariff import Tariff
from backend.src.Service.TariffService import TariffError, TariffService

tariff_router = APIRouter(prefix="/tariffs")
tariff_service = TariffService()

P = ParamSpec("P")
R = TypeVar("R")


class TariffModel(BaseModel):
    """Body of the requests creating or updating a tariff."""

    code: str = Field(max_length=30)
    label: str = Field(max_length=100)
    price: float = Field(ge=0)  # price in euros, the same for every screening
    min_age: int | None = None  # minimum age, inclusive (None = no minimum)
    max_age: int | None = None  # maximum age, inclusive (None = no maximum)
    requires_ensai: bool = False
    requires_student: bool = False
    is_active: bool = True
    weekday: int | None = Field(default=None, ge=0, le=6, description="0 = Monday ... 6 = Sunday (None = every day)")
    time_from: time | None = Field(default=None, description="Earliest start time of the screening (inclusive)")
    time_until: time | None = Field(default=None, description="Latest start time of the screening (exclusive)")


def _call(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    """Call a service method and turn its business errors into HTTP errors.

    Parameters
    ----------
    fn : Callable
        The service method.
    *args : Any
        Its positional arguments.
    **kwargs : Any
        Its keyword arguments.

    Returns
    -------
    Any
        What the method returns (HTTP error 404 "not found", 400 otherwise).
    """
    try:
        return fn(*args, **kwargs)
    except TariffError as e:
        status = 404 if "not found" in str(e) else 400
        raise HTTPException(status_code=status, detail=str(e)) from e


@tariff_router.get("/", tags=["Tariffs"], response_model=None)
async def list_active_tariffs() -> list[Tariff]:
    """List the active tariffs (public).

    Returns
    -------
    list of Tariff
        The active tariffs, from the cheapest.
    """
    return tariff_service.find_all(only_active=True)


@tariff_router.get("/all", tags=["Tariffs"], response_model=None)
async def list_all_tariffs(admin: AdminPayload) -> list[Tariff]:
    """List all the tariffs, including the inactive ones (administrators only).

    Parameters
    ----------
    admin : dict
        Token of the logged-in administrator.

    Returns
    -------
    list of Tariff
        All the tariffs.
    """
    return tariff_service.find_all(only_active=False)


@tariff_router.post("/", tags=["Tariffs"], status_code=201, response_model=None)
async def create_tariff(data: TariffModel, admin: AdminPayload) -> Tariff:
    """Create a new tariff (administrators only).

    Parameters
    ----------
    data : TariffModel
        The tariff to create.
    admin : dict
        Token of the logged-in administrator.

    Returns
    -------
    Tariff
        The tariff created (error 400 with the reason if it is invalid).
    """
    logging.info(f"Admin {admin['user_id']} creates tariff {data.code}")
    return _call(tariff_service.create_tariff, Tariff(**data.model_dump()))


@tariff_router.put("/{code}", tags=["Tariffs"], response_model=None)
async def update_tariff(code: str, data: TariffModel, admin: AdminPayload) -> Tariff:
    """Update a tariff (administrators only); tickets already sold keep their price.

    Parameters
    ----------
    code : str
        Code of the tariff (the code of the URL wins over the one of the body).
    data : TariffModel
        New values of the tariff.
    admin : dict
        Token of the logged-in administrator.

    Returns
    -------
    Tariff
        The tariff updated (error 404 if it does not exist, 400 if it is invalid).
    """
    logging.info(f"Admin {admin['user_id']} updates tariff {code}")
    tariff = Tariff(**{**data.model_dump(), "code": code})  # the code of the URL wins
    return _call(tariff_service.update_tariff, tariff)


@tariff_router.delete("/{code}", tags=["Tariffs"], response_model=None)
async def deactivate_tariff(code: str, admin: AdminPayload) -> dict[str, str]:
    """Deactivate a tariff (administrators only); it is kept for the tickets already sold.

    Parameters
    ----------
    code : str
        Code of the tariff.
    admin : dict
        Token of the logged-in administrator.

    Returns
    -------
    dict
        Confirmation message (error 404 if the tariff does not exist, 400 for the full tariff).
    """
    logging.info(f"Admin {admin['user_id']} deactivates tariff {code}")
    _call(tariff_service.deactivate_tariff, code)
    return {"message": f"Tariff {code} deactivated"}

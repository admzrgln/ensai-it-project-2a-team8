import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, ParamSpec, TypeVar

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.src.Controller.JWTBearer import AdminPayload
from backend.src.Model.PriceRevision import PriceRevision
from backend.src.Service.PriceRevisionService import MAX_RATE_PERCENT, PriceRevisionError, PriceRevisionService

price_revision_router = APIRouter(prefix="/price-revisions")
price_revision_service = PriceRevisionService()

P = ParamSpec("P")
R = TypeVar("R")


class PriceRevisionRequestModel(BaseModel):
    """Body of the request planning a revision."""

    rate_percent: float = Field(ge=0, le=MAX_RATE_PERCENT, description="Increase in % (e.g. 2.0 for +2 %)")


class PriceRevisionModel(BaseModel):
    """Yearly price revision, as returned by the API."""

    year: int
    rate_percent: float
    applied_at: datetime | None = None  # None = planned, not applied yet


def _to_model(revision: PriceRevision) -> PriceRevisionModel:
    """Convert a PriceRevision into its API model.

    Parameters
    ----------
    revision : PriceRevision
        The revision.

    Returns
    -------
    PriceRevisionModel
        The revision as returned by the API.
    """
    return PriceRevisionModel(year=revision.year, rate_percent=revision.rate_percent, applied_at=revision.applied_at)


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
    except PriceRevisionError as e:
        status = 404 if "not found" in str(e) else 400
        raise HTTPException(status_code=status, detail=str(e)) from e


@price_revision_router.get("/", tags=["Price revisions"], response_model=list[PriceRevisionModel])
async def list_revisions(admin: AdminPayload) -> list[PriceRevisionModel]:
    """List the planned and applied yearly revisions (administrators only).

    Parameters
    ----------
    admin : dict
        Token of the logged-in administrator.

    Returns
    -------
    list of PriceRevisionModel
        The revisions, by year.
    """
    return [_to_model(r) for r in price_revision_service.find_all()]


@price_revision_router.put("/{year}", tags=["Price revisions"], response_model=PriceRevisionModel)
async def plan_revision(year: int, data: PriceRevisionRequestModel, admin: AdminPayload) -> PriceRevisionModel:
    """Plan the price increase of a future year, applied on January 1st at midnight (administrators only).

    Parameters
    ----------
    year : int
        Year of the increase.
    data : PriceRevisionRequestModel
        Rate of the increase.
    admin : dict
        Token of the logged-in administrator.

    Returns
    -------
    PriceRevisionModel
        The planned revision (error 400 if the year or the rate is invalid).
    """
    logging.info(f"Admin {admin['user_id']} plans +{data.rate_percent} % for {year}")
    return _to_model(_call(price_revision_service.plan_revision, year, data.rate_percent))


@price_revision_router.delete("/{year}", tags=["Price revisions"], response_model=None)
async def cancel_revision(year: int, admin: AdminPayload) -> dict[str, Any]:
    """Cancel a planned revision that has not been applied yet (administrators only).

    Parameters
    ----------
    year : int
        Year of the revision.
    admin : dict
        Token of the logged-in administrator.

    Returns
    -------
    dict
        Confirmation message (error 404 if the revision does not exist or is already applied).
    """
    logging.info(f"Admin {admin['user_id']} cancels the {year} revision")
    _call(price_revision_service.cancel_revision, year)
    return {"message": f"Revision {year} cancelled"}

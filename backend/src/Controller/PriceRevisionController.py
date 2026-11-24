import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.src.Controller.JWTBearer import require_admin
from backend.src.Model.PriceRevision import PriceRevision
from backend.src.Service.PriceRevisionService import MAX_RATE_PERCENT, PriceRevisionError, PriceRevisionService

price_revision_router = APIRouter(prefix="/price-revisions")
price_revision_service = PriceRevisionService()


class PriceRevisionRequestModel(BaseModel):
    rate_percent: float = Field(ge=0, le=MAX_RATE_PERCENT, description="Augmentation en % (ex. 2.0 pour +2 %)")


class PriceRevisionModel(BaseModel):
    year: int
    rate_percent: float
    applied_at: datetime | None = None  # None = planifiée, pas encore appliquée


def _to_model(revision: PriceRevision) -> PriceRevisionModel:
    return PriceRevisionModel(year=revision.year, rate_percent=revision.rate_percent,
                              applied_at=revision.applied_at)


def _call(fn, *args):
    try:
        return fn(*args)
    except PriceRevisionError as e:
        status = 404 if "not found" in str(e) else 400
        raise HTTPException(status_code=status, detail=str(e)) from e


@price_revision_router.get("/", tags=["Price revisions"], response_model=list[PriceRevisionModel])
async def list_revisions(admin: dict = Depends(require_admin)):
    """List the planned and applied yearly revisions (admin only)"""
    return [_to_model(r) for r in price_revision_service.find_all()]


@price_revision_router.put("/{year}", tags=["Price revisions"], response_model=PriceRevisionModel)
async def plan_revision(year: int, data: PriceRevisionRequestModel, admin: dict = Depends(require_admin)):
    """Plan the price increase of a future year: applied on January 1st at midnight (admin only)"""
    logging.info(f"Admin {admin['user_id']} plans +{data.rate_percent} % for {year}")
    return _to_model(_call(price_revision_service.plan_revision, year, data.rate_percent))


@price_revision_router.delete("/{year}", tags=["Price revisions"])
async def cancel_revision(year: int, admin: dict = Depends(require_admin)):
    """Cancel a planned revision that has not been applied yet (admin only)"""
    logging.info(f"Admin {admin['user_id']} cancels the {year} revision")
    _call(price_revision_service.cancel_revision, year)
    return {"message": f"Revision {year} cancelled"}

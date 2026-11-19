import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.src.Controller.JWTBearer import require_admin
from backend.src.Service.AccountingReportService import AccountingReportService

accounting_router = APIRouter(prefix="/accounting-reports")
accounting_service = AccountingReportService()


class MovieRevenueModel(BaseModel):
    """Pydantic model for one revenue line of the report"""

    id_movie: int
    title: str
    revenue: float
    tickets_sold: int


class MovieOccupancyModel(BaseModel):
    """Pydantic model for one occupancy line of the report"""

    id_movie: int
    title: str
    screenings: int
    seats_offered: int
    seats_sold: int
    occupancy_rate: float  # in %


class AccountingReportModel(BaseModel):
    """Pydantic model returned by the API"""

    period_start: date
    period_end: date
    total_amount: float
    tickets_sold: int
    average_ticket_price: float
    occupancy_rate: float  # in %, over the screenings already started in the period
    movie_revenues: list[MovieRevenueModel]
    movie_occupancies: list[MovieOccupancyModel]


@accounting_router.get("/", tags=["Accounting"], response_model=AccountingReportModel)
async def get_accounting_report(period_start: date, period_end: date, admin: dict = Depends(require_admin)):
    """Accounting report for a period (dates YYYY-MM-DD, both inclusive). Admin only."""
    logging.info(f"Accounting report {period_start} -> {period_end} by admin {admin['user_id']}")
    try:
        report = accounting_service.generate_report(period_start, period_end, admin["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    return AccountingReportModel(
        period_start=report.period_start,
        period_end=report.period_end,
        total_amount=report.total_amount,
        tickets_sold=report.tickets_sold,
        average_ticket_price=report.average_ticket_price,
        occupancy_rate=report.occupancy_rate,
        movie_revenues=[
            MovieRevenueModel(
                id_movie=m.id_movie,
                title=m.title,
                revenue=m.revenue,
                tickets_sold=m.tickets_sold,
            )
            for m in report.movie_revenues
        ],
        movie_occupancies=[
            MovieOccupancyModel(
                id_movie=o.id_movie,
                title=o.title,
                screenings=o.screenings,
                seats_offered=o.seats_offered,
                seats_sold=o.seats_sold,
                occupancy_rate=o.occupancy_rate,
            )
            for o in report.movie_occupancies
        ],
    )
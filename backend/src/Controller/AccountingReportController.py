import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.Service.AccountingReportService import AccountingReportService

accounting_router = APIRouter(prefix="/accounting-reports")
accounting_service = AccountingReportService()


class MovieRevenueModel(BaseModel):
    """Pydantic model for one line of the report"""

    id_movie: int
    title: str
    revenue: float
    tickets_sold: int


class AccountingReportModel(BaseModel):
    """Pydantic model returned by the API"""

    period_start: date
    period_end: date
    total_amount: float
    tickets_sold: int
    average_ticket_price: float
    movie_revenues: list[MovieRevenueModel]


@accounting_router.get("/", tags=["Accounting"], response_model=AccountingReportModel)
async def get_accounting_report(period_start: date, period_end: date, id_admin: int):
    """Accounting report for a period (dates YYYY-MM-DD, both inclusive).

    id_admin is passed as a parameter for now (later: taken from the JWT).
    """
    logging.info(f"Accounting report {period_start} -> {period_end} by admin {id_admin}")
    try:
        report = accounting_service.generate_report(period_start, period_end, id_admin)
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
        movie_revenues=[
            MovieRevenueModel(
                id_movie=m.id_movie,
                title=m.title,
                revenue=m.revenue,
                tickets_sold=m.tickets_sold,
            )
            for m in report.movie_revenues
        ],
    )

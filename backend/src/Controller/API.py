from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from backend.src.Service.PriceRevisionService import PriceRevisionService

from .AccountingReportController import accounting_router
from .BookingController import booking_router
from .MovieController import movie_router
from .PriceRevisionController import price_revision_router
from .RoomController import room_router
from .ScreeningController import screening_router
from .TariffController import tariff_router
from .UserController import user_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run at the start of the API: apply the price revisions whose year has started.

    This catches up a January 1st that passed while the server was off.

    Parameters
    ----------
    app : FastAPI
        The application starting.

    Returns
    -------
    AsyncIterator[None]
        Context manager of the life of the application.
    """
    PriceRevisionService().apply_due_revisions()
    yield


def run_app() -> None:
    """Create the FastAPI application with all its routes and start the server on port 8001."""
    app = FastAPI(
        title="Projet Info 2A",
        description="Ensai Cinema Club: screenings, bookings and accounting of the cinema",
        root_path="/proxy/8001",
        lifespan=lifespan,
    )

    app.include_router(user_router)
    app.include_router(movie_router)
    app.include_router(room_router)
    app.include_router(screening_router)
    app.include_router(booking_router)
    app.include_router(tariff_router)
    app.include_router(accounting_router)
    app.include_router(price_revision_router)

    @app.get("/", include_in_schema=False)
    async def redirect_to_docs() -> RedirectResponse:
        """Redirect to the API documentation.

        Returns
        -------
        RedirectResponse
            Redirection to /docs.
        """
        return RedirectResponse(url="/docs")

    uvicorn.run(app, port=8001, host="0.0.0.0")

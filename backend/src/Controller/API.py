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
async def lifespan(app: FastAPI):
    """Exécuté au démarrage de l'API : applique les révisions de prix dont l'année a commencé
    (rattrape un 1er janvier passé pendant que le serveur était éteint)."""
    PriceRevisionService().apply_due_revisions()
    yield


def run_app():
    app = FastAPI(
        title="Projet Info 2A",
        description="Example project for ENSAI students",
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
    async def redirect_to_docs():
        """Redirect to the API documentation"""
        return RedirectResponse(url="/docs")

    uvicorn.run(app, port=8001, host="0.0.0.0")

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.src.Controller.API import run_app


@pytest.fixture
def app():
    """Lance run_app() sans démarrer le serveur : on récupère l'application passée à uvicorn.run."""
    with patch("backend.src.Controller.API.uvicorn.run") as uvicorn_run:
        run_app()
    uvicorn_run.assert_called_once()
    assert uvicorn_run.call_args.kwargs == {"port": 8001, "host": "0.0.0.0"}
    return uvicorn_run.call_args.args[0]


def test_app_configuration(app):
    assert app.title == "Projet Info 2A"
    assert app.root_path == "/proxy/8001"


@pytest.mark.parametrize("prefix", [
    "/users", "/movies", "/rooms", "/screenings", "/bookings", "/tariffs", "/accounting-reports",
])
def test_all_routers_are_registered(app, prefix):
    paths = app.openapi()["paths"]
    assert any(path.startswith(prefix) for path in paths), f"aucune route {prefix}"


def test_root_redirects_to_docs(app):
    response = TestClient(app).get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].endswith("/docs")


def test_due_price_revisions_are_applied_at_startup(app):
    """Au démarrage, l'API applique les révisions de prix dont l'année a commencé.

    `with TestClient(app)` déclenche le lifespan (démarrage puis arrêt de l'application).
    """
    with patch("backend.src.Controller.API.PriceRevisionService") as service_cls:
        with TestClient(app):
            pass

    service_cls.return_value.apply_due_revisions.assert_called_once_with()

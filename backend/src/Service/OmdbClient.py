import os

import requests


class OmdbError(Exception):
    """Erreur de communication avec OMDb (réseau, clé invalide...)."""


class OmdbClient:
    BASE_URL = "https://www.omdbapi.com/"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["OMDB_API_KEY"]

    def _get(self, params: dict) -> dict | None:
        try:
            response = requests.get(
                self.BASE_URL,
                params={"apikey": self.api_key, **params},
                timeout=5,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise OmdbError("OMDb unreachable") from error

        data = response.json()
        if data.get("Response") == "False":
            error_msg = data.get("Error", "")
            if "not found" in error_msg.lower():
                return None  # film introuvable : cas normal
            raise OmdbError(error_msg)  # clé invalide, quota dépassé...
        return data

    def search(self, title: str) -> list[dict]:
        """Recherche par mot-clé : renvoie une liste légère (titre, année, imdbID, poster)."""
        data = self._get({"s": title, "type": "movie"})
        return data["Search"] if data else []

    def get_by_imdb_id(self, imdb_id: str) -> dict | None:
        """Détails complets d'un film (durée, genre...)."""
        return self._get({"i": imdb_id, "plot": "short"})
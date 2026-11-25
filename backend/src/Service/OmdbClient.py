import os
from typing import Any

import requests


class OmdbError(Exception):
    """Communication error with OMDb (network, invalid key, quota exceeded...)."""


class OmdbClient:
    """Client of the OMDb API (https://www.omdbapi.com), used to import movies.

    Parameters
    ----------
    api_key : str or None, optional
        OMDb API key; read from the OMDB_API_KEY variable if None.
    """

    BASE_URL = "https://www.omdbapi.com/"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ["OMDB_API_KEY"]

    def _get(self, params: dict[str, str]) -> dict[str, Any] | None:
        """Send a request to OMDb.

        Parameters
        ----------
        params : dict of str to str
            Parameters of the request (the API key is added).

        Returns
        -------
        dict or None
            The JSON answer, or None if OMDb did not find the movie.

        Raises
        ------
        OmdbError
            If OMDb is unreachable or returns an error (invalid key, quota...).
        """
        try:
            response = requests.get(
                self.BASE_URL,
                params={"apikey": self.api_key, **params},
                timeout=5,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise OmdbError("OMDb unreachable") from error

        data: dict[str, Any] = response.json()
        if data.get("Response") == "False":
            error_msg = data.get("Error", "")
            if "not found" in error_msg.lower():
                return None  # movie not found: normal case
            raise OmdbError(error_msg)  # invalid key, quota exceeded...
        return data

    def search(self, title: str) -> list[dict[str, Any]]:
        """Search movies by keyword.

        Parameters
        ----------
        title : str
            Words of the title.

        Returns
        -------
        list of dict
            Light description of each movie found (title, year, imdbID, poster); empty if none.
        """
        data = self._get({"s": title, "type": "movie"})
        results: list[dict[str, Any]] = data["Search"] if data else []
        return results

    def get_by_imdb_id(self, imdb_id: str) -> dict[str, Any] | None:
        """Get the full details of a movie (runtime, genre...).

        Parameters
        ----------
        imdb_id : str
            IMDb identifier, e.g. "tt1375666".

        Returns
        -------
        dict or None
            The details given by OMDb, or None if the movie does not exist.
        """
        return self._get({"i": imdb_id, "plot": "short"})

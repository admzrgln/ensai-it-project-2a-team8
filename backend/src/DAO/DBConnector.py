from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Literal

import psycopg2
from psycopg2.extras import RealDictCursor

if TYPE_CHECKING:
    from psycopg2.extensions import connection


class DBConnector:
    """Connection to the PostgreSQL database.

    Parameters
    ----------
    config : dict of str to str or None, optional
        Keys "host", "port", "database", "user", "password" and "schema".
        If None, the values are read from the environment variables POSTGRES_*.
    """

    def __init__(self, config: dict[str, str] | None = None) -> None:
        if config is not None:
            self.host = config["host"]
            self.port = config["port"]
            self.database = config["database"]
            self.user = config["user"]
            self.password = config["password"]
            self.schema = config["schema"]
        else:
            self.host = os.environ["POSTGRES_HOST"]
            self.port = os.environ["POSTGRES_PORT"]
            self.database = os.environ["POSTGRES_DATABASE"]
            self.user = os.environ["POSTGRES_USER"]
            self.password = os.environ["POSTGRES_PASSWORD"]
            self.schema = os.environ["POSTGRES_SCHEMA"]

    def get_connection(self) -> connection:
        """Open a connection to run several queries in ONE transaction.

        Usage::

            conn = DBConnector().get_connection()
            try:
                with conn:                    # COMMIT if everything is fine, ROLLBACK otherwise
                    with conn.cursor() as cur:
                        cur.execute(...)
            finally:
                conn.close()

        Returns
        -------
        connection
            An open psycopg2 connection whose cursors return rows as dictionaries.
        """
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            options=f"-c search_path={self.schema}",
            cursor_factory=RealDictCursor,
        )

    def sql_query(
        self,
        query: str,
        data: tuple[Any, ...] | list[Any] | dict[str, Any] | None = None,
        return_type: Literal["one", "all"] = "one",
    ) -> Any:
        """Run one SQL query in its own transaction.

        Parameters
        ----------
        query : str
            The SQL query, with %(name)s placeholders.
        data : tuple, list, dict or None, optional
            Values of the placeholders.
        return_type : {"one", "all"}, optional
            "one" to fetch the first row, "all" to fetch every row.

        Returns
        -------
        Any
            With "one": the row as a dict, or None if there is no row.
            With "all": the list of the rows (dicts).
        """
        try:
            with psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                options=f"-c search_path={self.schema}",
                cursor_factory=RealDictCursor,
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, data)
                    if return_type == "one":
                        return cursor.fetchone()
                    if return_type == "all":
                        return cursor.fetchall()
        except Exception as e:
            print("ERROR")
            print(e)
            raise e
        return None

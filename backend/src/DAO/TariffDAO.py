from backend.src.DAO.DBConnector import DBConnector
from backend.src.Model.Tariff import Tariff
from utils.log_utils import get_logger, log
from utils.singleton import Singleton

logger = get_logger(__name__)


class TariffDao(metaclass=Singleton):
    """Class containing methods to access Tariffs in the database."""

    @staticmethod
    def _to_tariff(row: dict) -> Tariff:
        return Tariff(
            code=row["code"],
            label=row["label"],
            price=float(row["price"]) if row["price"] is not None else None,
            min_age=row["min_age"],
            max_age=row["max_age"],
            requires_ensai=row["requires_ensai"],
            requires_student=row["requires_student"],
            is_active=row["is_active"],
        )

    @staticmethod
    def _to_data(tariff: Tariff) -> dict:
        return {
            "code": tariff.code,
            "label": tariff.label,
            "price": tariff.price,
            "min_age": tariff.min_age,
            "max_age": tariff.max_age,
            "requires_ensai": tariff.requires_ensai,
            "requires_student": tariff.requires_student,
            "is_active": tariff.is_active,
        }

    # GET
    @log
    def find_all(self, only_active: bool = True) -> list[Tariff]:
        query = "SELECT * FROM public.tariff"
        if only_active:
            query += " WHERE is_active"
        query += " ORDER BY price NULLS LAST, code;"
        try:
            res = DBConnector().sql_query(query, return_type="all")
        except Exception as e:
            logger.error(e)
            raise
        return [self._to_tariff(r) for r in (res or [])]

    @log
    def find_by_code(self, code: str) -> Tariff | None:
        query = "SELECT * FROM public.tariff WHERE code = %(code)s;"
        try:
            res = DBConnector().sql_query(query, data={"code": code}, return_type="one")
        except Exception as e:
            logger.error(e)
            raise
        return self._to_tariff(res) if res else None

    # POST
    @log
    def insert_tariff(self, tariff: Tariff) -> bool:
        query = """
            INSERT INTO public.tariff
                (code, label, price, min_age, max_age, requires_ensai, requires_student, is_active)
            VALUES
                (%(code)s, %(label)s, %(price)s, %(min_age)s, %(max_age)s,
                 %(requires_ensai)s, %(requires_student)s, %(is_active)s)
            RETURNING code;
        """
        try:
            return bool(DBConnector().sql_query(query, data=self._to_data(tariff), return_type="one"))
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion du tarif : {e}")
        return False

    # UPDATE
    @log
    def update_tariff(self, tariff: Tariff) -> bool:
        query = """
            UPDATE public.tariff
            SET label = %(label)s, price = %(price)s, min_age = %(min_age)s, max_age = %(max_age)s,
                requires_ensai = %(requires_ensai)s, requires_student = %(requires_student)s,
                is_active = %(is_active)s
            WHERE code = %(code)s
            RETURNING code;
        """
        try:
            return bool(DBConnector().sql_query(query, data=self._to_data(tariff), return_type="one"))
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du tarif : {e}")
        return False

    # "DELETE" = désactivation (les anciens billets gardent leur tarif)
    @log
    def deactivate_tariff(self, code: str) -> bool:
        query = """
            UPDATE public.tariff SET is_active = FALSE
            WHERE code = %(code)s AND is_active
            RETURNING code;
        """
        try:
            return bool(DBConnector().sql_query(query, data={"code": code}, return_type="one"))
        except Exception as e:
            logger.error(f"Erreur lors de la désactivation du tarif : {e}")
        return False

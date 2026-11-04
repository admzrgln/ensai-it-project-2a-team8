from datetime import date

from backend.src.Model.Ticket import Ticket


def test_ticket_constructor_defaults():
    t = Ticket("Louise", "F", date(2004, 3, 1))
    assert (t.first_name, t.last_name, t.date_of_birth) == ("Louise", "F", date(2004, 3, 1))
    assert t.is_holder is False
    assert t.is_ensai_student is False
    assert t.is_student is False
    # le tarif et le prix sont remplis plus tard par le TariffService
    assert t.tariff_code is None
    assert t.price is None
    assert t.id_ticket is None
    assert t.id_booking is None


def test_ticket_constructor_all_fields():
    t = Ticket("Kid", "F", date(2018, 1, 1), is_holder=True, is_ensai_student=True, is_student=True,
               tariff_code="child", price=4.5, id_booking=3, id_ticket=7)
    assert t.is_holder and t.is_ensai_student and t.is_student
    assert (t.tariff_code, t.price, t.id_booking, t.id_ticket) == ("child", 4.5, 3, 7)


def test_ticket_str():
    t = Ticket("Kid", "F", date(2018, 1, 1), tariff_code="child", price=4.5, id_ticket=7)
    assert str(t) == "Ticket 7 : Kid F - child 4.5€"

from enum import StrEnum


class Role(StrEnum):
    """Role of a user of the application.

    A Role is also a str: Role.ADMIN == "admin", so it can be saved in the database
    and in the JWT tokens as plain text.
    """

    ADMIN = "admin"
    CUSTOMER = "customer"

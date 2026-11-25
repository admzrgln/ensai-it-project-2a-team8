from typing import Any, ClassVar


class Singleton(type):
    """Metaclass: every class using it has only one instance.

    https://refactoring.guru/fr/design-patterns/singleton
    """

    _instances: ClassVar[dict[type, Any]] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

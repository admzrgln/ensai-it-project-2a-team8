import logging
import logging.config
import numbers
from collections.abc import Awaitable, Callable
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

import yaml
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

P = ParamSpec("P")
R = TypeVar("R")


def initialize_logs(name: str) -> None:
    """Initialize logging from the configuration file logging_config.yml.

    Parameters
    ----------
    name : str
        Name of the application, written in the first log lines.
    """

    # Create the logs folder at project root if it doesn't exist
    logs_dir = Path(__file__).resolve().parents[2] / "logs"
    logs_dir.mkdir(exist_ok=True)

    config_file = Path(__file__).resolve().parents[2] / "logging_config.yml"

    with open(config_file, encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
        logging.config.dictConfig(config)

        logging.info("-" * 50)
        logging.info(f"Starting {name}                           ")
        logging.info("-" * 50)


def get_logger(module_name: str, max_size: int = 25) -> logging.Logger:
    """Return a logger with a shortened name based on the module path.

    If the path is longer than max_size, the prefix parts are replaced by their initials.

    Parameters
    ----------
    module_name : str
        Dotted path of the module, e.g. backend.src.DAO.MovieDAO.
    max_size : int, optional
        Maximum length of the logger name before shortening (25 by default).

    Returns
    -------
    logging.Logger
        The logger to use in the module.
    """
    if len(module_name) <= max_size:
        return logging.getLogger(module_name)

    parts = module_name.split(".")
    short_prefix = [p[0] for p in parts[:-1]]
    short_name = ".".join(short_prefix + [parts[-1]])

    return logging.getLogger(short_name)


class LogIndentation:
    """For indenting logs when entering a new method"""

    current_indentation = 0
    indentation_size = 2

    @classmethod
    def increase_indentation(cls) -> None:
        """Increase the indentation by one level."""
        cls.current_indentation += 1

    @classmethod
    def decrease_indentation(cls) -> None:
        """Decrease the indentation by one level."""
        cls.current_indentation -= 1

    @classmethod
    def get_indentation(cls) -> str:
        """Get the current indentation.

        Returns
        -------
        str
            The spaces to put at the beginning of a log line.
        """
        return " " * cls.indentation_size * cls.current_indentation


SENSITIVE_KEYWORDS = {"password", "passwd", "pwd", "pass", "token", "secret", "key"}


def _loggable(name: str, value: Any) -> Any:
    """Prepare a parameter value for the logs, hiding sensitive values.

    Parameters
    ----------
    name : str
        Name of the parameter.
    value : Any
        Value of the parameter.

    Returns
    -------
    Any
        "*****" if the name looks sensitive (password, token...), the number itself
        for a number, its text otherwise.
    """
    if any(keyword in name.lower() for keyword in SENSITIVE_KEYWORDS):
        return "*****"
    return value if isinstance(value, numbers.Number) else str(value)


def _short_output(result: Any) -> str:
    """Shorten a returned value so that the logs stay readable.

    Parameters
    ----------
    result : Any
        Value returned by a method.

    Returns
    -------
    str
        The value as text: only the first 3 elements of a list or dict,
        and only the first 50 characters of a long string.
    """
    if isinstance(result, list):
        return str([str(item) for item in result[:3]]) + f" ... ({len(result)} elements)"
    if isinstance(result, dict):
        return str([(str(k), str(v)) for k, v in list(result.items())[:3]]) + f" ... ({len(result)} elements)"
    if isinstance(result, str) and len(result) > 50:
        return result[:50] + f" ... ({len(result)} characters)"
    return str(result)


def log(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator to log method calls and their outputs.

    When applied to a method, it logs the call with its parameter values (sensitive
    values such as passwords are hidden) and the value returned by the method.

    Parameters
    ----------
    func : Callable
        The method to decorate.

    Returns
    -------
    Callable
        The decorated method, with the same signature as func.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if args and hasattr(args[0], "__class__"):
            logger = get_logger(f"{args[0].__class__.__module__}")
        else:
            logger = logging.getLogger(__name__)

        LogIndentation.increase_indentation()
        indentation = LogIndentation.get_indentation()
        try:
            # Parameters of the method (args[0] is self)
            method_name = func.__name__
            param_names = func.__code__.co_varnames[1 : func.__code__.co_argcount]
            args_list = [_loggable(name, arg) for name, arg in zip(param_names, args[1:], strict=False)]
            args_list += [_loggable(k, v) for k, v in kwargs.items()]
            args_tuple = tuple(args_list)

            logger.info(f"{indentation}{method_name}{args_tuple} - START")
            result = func(*args, **kwargs)
            logger.info(f"{indentation}{method_name}{args_tuple} - END")
            logger.info(f"{indentation}  └─> Output: {_short_output(result)}")
            return result
        finally:
            # Also when func raises an exception: otherwise the indentation would keep growing
            LogIndentation.decrease_indentation()

    return wrapper


class LogMiddleware(BaseHTTPMiddleware):
    """Middleware logging every HTTP request and its response."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Log the method, path, status code and error details of a request.

        Parameters
        ----------
        request : Request
            The incoming HTTP request.
        call_next : Callable
            Function passing the request to the rest of the application.

        Returns
        -------
        Response
            The response returned by the application.
        """

        method = request.method
        path = str(request.url.path)

        logging.info(f"{method} {path} - START")

        try:
            response = await call_next(request)
            logging.info(f"{method} {path} - END [Status: {response.status_code}]")
            return response

        except Exception as e:
            logging.error(f"{method} {path} - FAILED [Status: 500] Error: {str(e)}")
            raise e

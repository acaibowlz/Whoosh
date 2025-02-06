import logging
from typing import Optional

from flask import Request

from app.config import ENV


def return_client_ip(request: Request, env: str) -> Optional[str]:
    """
    Returns the client's IP address based on the environment.
    """
    if env == "dev":
        return request.remote_addr
    elif env == "prod":
        return request.headers.get("X-Forwarded-For")
    return None


def _setup_prod_logger() -> logging.Logger:
    """
    Sets up the production logger. Returns a logger instance.
    """
    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(fmt="[%(asctime)s] %(levelname)s: %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    return logger


def _setup_dev_logger() -> logging.Logger:
    """
    Sets up the development logger. Returns a logger instance.
    """
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.ERROR)

    stream_formatter = logging.Formatter(fmt="[%(asctime)s] %(levelname)s: %(message)s")
    file_formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s in %(funcName)s, %(module)s: %(message)s"
    )

    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(stream_formatter)
    stream_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler("app.log", "w", "utf-8")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    return logger


class Logger:
    """
    Wrapper class for logging based on the environment (dev or prod).
    Provides methods for logging debug, info, warning, and error messages.
    """

    def __init__(self, env: str) -> None:
        if env == "prod":
            self._logger = _setup_prod_logger()
        elif env == "dev":
            self._logger = _setup_dev_logger()
        else:
            raise ValueError("Invalid environment specified. Use 'dev' or 'prod'.")

    def debug(self, msg: str) -> None:
        self._logger.debug(msg)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)


class LoggerUtils:
    """
    Wrapper class for common logging events for Whoosh.
    Provides methods for logging specific events.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def login_failed(self, request: Request, msg: str) -> None:
        """
        Logs a failed login attempt. Log level: DEBUG.
        Needs to pass the reason for the failure to form the message.
        """
        msg = msg.strip().strip(".")
        client_ip = return_client_ip(request, ENV)
        self._logger.debug(f"{client_ip} - Login failed. Msg: {msg}.")

    def login_succeeded(self, request: Request, username: str) -> None:
        """
        Logs a successful login event. Log level: INFO.
        """
        client_ip = return_client_ip(request, ENV)
        self._logger.info(f"{client_ip} - User {username} has logged in.")

    def logout(self, request: Request, username: str) -> None:
        """
        Logs a user logout event. Log level: INFO.
        """
        client_ip = return_client_ip(request, ENV)
        self._logger.info(f"{client_ip} - User {username} has logged out.")

    def registration_failed(self, request: Request, msg: str) -> None:
        """
        Logs a failed registration attempt. Log level: DEBUG.
        Needs to pass the reason for the failure to form the message.
        """
        msg = msg.strip().strip(".")
        client_ip = return_client_ip(request, ENV)
        self._logger.debug(f"{client_ip} - Registration failed. Msg: {msg}.")

    def registration_succeeded(self, username: str) -> None:
        """
        Logs a successful registration event. Log level: INFO.
        """
        self._logger.info(f"New user {username} has been created.")

    def pagination(self, request: Request, page: int, count: int) -> None:
        """
        Logs pagination events. Log level: DEBUG.
        """
        if "posts" in request.url:
            panel = "posts"
        elif "projects" in request.url:
            panel = "projects"
        elif "archive" in request.url:
            panel = "archive"
        elif "changelog" in request.url:
            panel = "changelog"
        else:
            raise Exception("Unknown pagination option in logger_utils.pagination.")
        self._logger.debug(f"Showing {count} records at page {page} of {panel} panel.")


logger = Logger(env=ENV)
logger_utils = LoggerUtils(logger)

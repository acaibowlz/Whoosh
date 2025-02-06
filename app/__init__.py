import time
from datetime import datetime, timedelta, timezone
from typing import Tuple

from flask import Flask, render_template, request, session
from flask_login import LoginManager, current_user, logout_user
from pymongo.errors import ServerSelectionTimeoutError

from app.config import APP_SECRET, ENV, USER_LOGIN_TIMEOUT
from app.helpers.users import UserUtils
from app.logging import logger, return_client_ip
from app.models.users import UserInfo
from app.mongo import mongo_connection
from app.views import backstage_bp, frontstage_bp, main_bp


def create_app() -> Flask:
    """
    In this `create_app()` function, we initialize the Flask app configure by the following steps:
    - Set the secret key for the app.
    - Initialize the debug toolbar if the environment is set to `dev`.
    - Initialize the login manager.
    - Define the user loader function for the login manager.
    - Define a function to log out inactive users.
    - Register error handlers for 404 and 500 errors.
    - Register the blueprints for the app.
    - Check the MongoDB connection before starting the app.

    If all the steps are completed successfully, the function returns the Flask app instance.
    """
    app = Flask(__name__)
    logger.info("App initialization started.")
    app.secret_key = APP_SECRET

    # develop environment configuration
    if ENV == "dev":
        app.config["DEBUG"] = True

        from flask_debugtoolbar import DebugToolbarExtension

        toolbar = DebugToolbarExtension()
        toolbar.init_app(app)
        app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
        logger.debug("Debugtoolbar initialized.")

    # Login manager configuration
    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.login_message = "Please login to proceed."
    login_manager.init_app(app)
    logger.debug("Login manager initialized.")

    @login_manager.user_loader
    def user_loader(username: str) -> UserInfo:
        """
        Load user information from the database.
        Returns an instance of UserInfo if the user exists, otherwise None.
        """
        with mongo_connection() as mongodb:
            user_utils = UserUtils(mongodb)
            user = user_utils.get_user_info(username)
        return user

    @app.before_request
    def logout_inactive() -> None:
        """
        Logs out users who have been inactive for a specified timeout period.
        Resets the timeout if the user is still valid.
        """
        if not current_user.is_authenticated:
            return
        if session.get("user_keep_alive"):
            return
        now = datetime.now(timezone.utc)
        last_active = session.get("user_last_active", now)
        if (now - last_active) > timedelta(seconds=USER_LOGIN_TIMEOUT):
            username = current_user.username
            logout_user()
            session.clear()
            logger.debug(f"User {username} logged out due to inactivity.")
        else:
            session["user_keep_alive"] = False
            session["user_last_active"] = now

    @app.before_request
    def logging_request() -> None:
        """
        Logs the URL and client IP address before processing the request.
        """
        if "static" in request.url or "debug_toolbar" in request.url:
            return
        client_ip = return_client_ip(request, ENV)
        logger.debug(f"{client_ip} - {request.url} was visited.")

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(error) -> Tuple[str, int]:
        client_ip = return_client_ip(request, ENV)
        logger.debug(f"{client_ip} - 404 not found at {request.environ['RAW_URI']}. ")
        return render_template("main/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error) -> Tuple[str, int]:
        client_ip = return_client_ip(request, ENV)
        logger.error(f"{client_ip} - 500 internal error at {request.environ['RAW_URI']}.")
        return render_template("main/500.html"), 500

    logger.debug("Error handlers registered.")

    # Register blueprints
    app.register_blueprint(frontstage_bp, url_prefix="/")
    app.register_blueprint(backstage_bp, url_prefix="/backstage/")
    app.register_blueprint(main_bp, url_prefix="/")
    logger.debug("Blueprints registered.")

    # Check MongoDB connection
    while True:
        try:
            with mongo_connection() as mongodb:
                mongodb.client.server_info()
                logger.debug("MongoDB connected.")
                break
        except ServerSelectionTimeoutError:
            logger.error("MongoDB is NOT connected. Retry in 60 secs.")
            time.sleep(60)

    logger.info("App initialization completed.")

    return app

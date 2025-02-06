from datetime import datetime, timezone

import bcrypt
from flask import (
    Blueprint,
    Response,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.config import DOMAIN, ENV, TEMPLATE_FOLDER
from app.forms.users import LoginForm, SignUpForm
from app.helpers.posts import PostUtils
from app.helpers.projects import ProjectsUtils
from app.helpers.users import UserUtils
from app.logging import logger, logger_utils
from app.mongo import mongo_connection

main = Blueprint("main", __name__, template_folder=TEMPLATE_FOLDER)


def flashing_if_errors(form_errors: dict[str, list[str]]) -> None:
    """
    Takes `form.errors` as argument, where `form` should be a WTForm instance.

    Flashs error message if any error is found in the form.
    """
    if form_errors:
        for field, errors in form_errors.items():
            for error in errors:
                flash(f"{field.capitalize()}: {error}", category="error")


@main.route("/", methods=["GET"])
def landing_page() -> str:
    """
    The landing page of the website. Takes GET request only.
    """
    return render_template("main/landing-page.html")


@main.route("/login", methods=["GET", "POST"])
def login() -> str:
    """
    The login page of the website. Takes GET and POST requests.

    When logging in the user, it also initializes the session keys `user_last_active` and `user_keep_alive`.
    They are is used in the before-request-function `logout_inactive()` defined in `create_app()`.

    If the user is already logged in, they will be redirected to the backstage.
    """
    if current_user.is_authenticated:
        flash("You are already logged in.")
        logger.debug(f"Attempt to duplicate logging from user {current_user.username}.")
        return redirect(url_for("baskstage.root", username=current_user.username))

    form = LoginForm()

    if form.validate_on_submit():
        with mongo_connection() as mongodb:
            if not mongodb.user_creds.exists("email", form.email.data):
                flash("Account not found. Please try again.", category="error")
                logger_utils.login_failed(request=request, msg=f"email {form.email.data} not found")
                return render_template("main/login.html", form=form)

            user_creds = mongodb.user_creds.find_one({"email": form.email.data})
            encoded_input_pw = form.password.data.encode("utf8")
            encoded_valid_user_pw = user_creds.get("password").encode("utf8")

            if not bcrypt.checkpw(encoded_input_pw, encoded_valid_user_pw):
                flash("Invalid password. Please try again.", category="error")
                logger_utils.login_failed(
                    request=request,
                    msg=f"invalid password with email {form.email.data}",
                )
                return render_template("main/login.html", form=form)

            username = user_creds.get("username")
            user_utils = UserUtils(mongodb)
            user = user_utils.get_user_info(username)

        login_user(user)
        session["user_last_active"] = datetime.now(timezone.utc)
        session["user_keep_alive"] = form.persistent.data
        logger_utils.login_succeeded(request=request, username=username)
        flash("Login Succeeded.", category="success")
        return redirect(url_for("backstage.root"))

    flashing_if_errors(form.errors)
    return render_template("main/login.html", form=form)


@main.route("/signup", methods=["GET", "POST"])
def signup() -> str:
    """
    The sign up page of the website. Takes GET and POST requests.

    This page associates with `SignUpForm` class and uses `create_user()` method from `UserUtils` class.
    """
    form = SignUpForm()

    if form.validate_on_submit():
        with mongo_connection() as mongodb:
            user_utils = UserUtils(mongodb)
            username = user_utils.create_user(form)
        logger_utils.registration_succeeded(username)
        flash("Sign up succeeded.", category="success")
        return redirect(url_for("main.login"))

    flashing_if_errors(form.errors)
    return render_template("main/signup.html", form=form)


@main.route("/logout", methods=["GET"])
@login_required
def logout() -> Response:
    """
    Logs out the user and redirects to the last visited page.
    """
    username = current_user.username
    if "backstage" in session["last_visited"]:
        logout_redirect = redirect(url_for("frontstage.home", username=username))
    else:
        logout_redirect = redirect(session["last_visited"])
    logout_user()
    logger_utils.logout(request=request, username=username)
    session.clear()

    return logout_redirect


@main.route("/raise-exception", methods=["GET"])
def error_simulator() -> None:
    """
    This is a simulated error route for debug purpose only.
    """
    raise Exception("this is a simulation error.")


@main.route("/error", methods=["GET"])
def error_page() -> str:
    """
    The error page of the website.
    """
    return render_template("main/500.html")


@main.route("/robots.txt", methods=["GET"])
def robotstxt() -> str:
    """
    Serve the robots.txt file of the website.
    """
    return open("robots.txt", "r").read()


@main.route("/sitemap")
def sitemap() -> str:
    """
    Generate the sitemap for the website.

    It looks into the database and retrieves all users, posts and projects, then put them into the sitemap.
    """
    if ENV == "dev":
        base_url = f"{DOMAIN}"
    else:
        base_url = f"https://{DOMAIN}"

    # Static routes
    static_urls = [{"loc": f"{base_url}/{route}"} for route in ["", "login", "register"]]

    # Dynamic routes
    with mongo_connection() as mongodb:
        user_utils = UserUtils(mongodb)
        post_utils = PostUtils(mongodb)
        projects_utils = ProjectsUtils(mongodb)

        dynamic_urls = []
        for username in user_utils.get_all_username():
            dynamic_urls.extend(
                [
                    {"loc": f"{base_url}/@{username}"},
                    {"loc": f"{base_url}/@{username}/blog"},
                    {"loc": f"{base_url}/@{username}/about"},
                ]
            )
        for username in user_utils.get_all_username_gallery_enabled():
            dynamic_urls.append({"loc": f"{base_url}/@{username}/gallery"})
        for username in user_utils.get_all_username_changelog_enabled():
            dynamic_urls.append({"loc": f"{base_url}/@{username}/changelog"})

        for post in post_utils.get_all_posts_info():
            slug = post.get("custom_slug")
            lastmod = (
                post.get("last_updated")
                .replace(tzinfo=timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            )
            lastmod = lastmod[:-2] + ":" + lastmod[-2:]
            url = {
                "loc": f"{base_url}/@{post.get('author')}/posts/{post.get('post_uid')}/{slug if slug else ''}",
                "lastmod": lastmod,
            }
            dynamic_urls.append(url)

        for project in projects_utils.get_all_projects_info():
            slug = project.get("custom_slug")
            logger.debug(project.get("last_updated"))
            lastmod = (
                project.get("last_updated")
                .replace(tzinfo=timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            )
            lastmod = lastmod[:-2] + ":" + lastmod[-2:]
            url = {
                "loc": f"{base_url}/@{project.get('author')}/projects/{project.get('project_uid')}/{slug if slug else ''}",
                "lastmod": lastmod,
            }
            dynamic_urls.append(url)

    xml_sitemap = render_template(
        "main/sitemap.xml", static_urls=static_urls, dynamic_urls=dynamic_urls
    )
    response = make_response(xml_sitemap)
    response.headers["Content-Type"] = "application/xml"
    logger.debug("Sitemap generated successfully.")

    return response

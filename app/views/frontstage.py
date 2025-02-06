from urllib.parse import unquote

import readtime
from flask import (
    Blueprint,
    Request,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user

from app.config import TEMPLATE_FOLDER
from app.forms.comments import CommentForm
from app.helpers.changelog import ChangelogUtils
from app.helpers.comments import CommentUtils, create_comment
from app.helpers.posts import PostUtils
from app.helpers.projects import ProjectsUtils
from app.helpers.users import UserUtils
from app.helpers.utils import (
    Paging,
    convert_about,
    convert_changelog_content,
    convert_post_content,
    convert_project_content,
    sort_dict,
)
from app.logging import logger, logger_utils
from app.mongo import mongo_connection
from app.views.main import flashing_if_errors

frontstage = Blueprint("frontstage", __name__, template_folder=TEMPLATE_FOLDER)


@frontstage.route("/@<username>", methods=["GET"])
def home(username: str) -> str:
    """Render the home page for a given user.

    Args:
        username (str): The username of the user whose home page is to be rendered.

    Returns:
        str: Rendered HTML of the home page.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url
    logger_utils.page_visited(request)

    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)

        user = mongodb.user_info.find_one({"username": username})
        post_utils = PostUtils(mongodb)
        featured_posts = post_utils.get_featured_posts_info(username)

        user_utils = UserUtils(mongodb)
        user_utils.total_view_increment(username)

    return render_template("frontstage/home.html", user=user, posts=featured_posts)


@frontstage.route("/@<username>/blog", methods=["GET"])
def blog(username: str) -> str:
    """Render the blog page for a given user with pagination.

    Args:
        username (str): The username of the user whose blog page is to be rendered.

    Returns:
        str: Rendered HTML of the blog page.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url
    logger_utils.page_visited(request)

    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)

        current_page = request.args.get("page", default=1, type=int)
        POSTS_EACH_PAGE = 5
        paging = Paging(mongodb)
        pagination = paging.setup(username, "post_info", current_page, POSTS_EACH_PAGE)

        post_utils = PostUtils(mongodb)
        posts = post_utils.get_post_infos_with_pagination(
            username=username, page_number=current_page, posts_per_page=POSTS_EACH_PAGE
        )

        user_utils = UserUtils(mongodb)
        user = user_utils.get_user_info(username)
        tags = sort_dict(user.tags)
        tags = {tag: count for tag, count in tags.items() if count > 0}
        user_utils.total_view_increment(username)

    return render_template(
        "frontstage/blog.html", user=user, posts=posts, tags=tags, pagination=pagination
    )


def blogpost(username: str, post_uid: str, request: Request) -> str:
    """Handle the main actions for rendering a blog post.

    Args:
        username (str): The username of the post author.
        post_uid (str): The unique identifier of the post.
        request (Request): The Flask request object.

    Returns:
        str: Rendered HTML of the blog post page.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url
    logger_utils.page_visited(request)

    with mongo_connection() as mongodb:
        user = mongodb.user_info.find_one({"username": username})
        post_utils = PostUtils(mongodb)
        post = post_utils.get_full_post(post_uid)

        post["content"] = convert_post_content(post.get("content"))
        post["readtime"] = str(readtime.of_html(post.get("content")))

        form = CommentForm()
        if form.validate_on_submit():
            create_comment(post_uid, form, mongodb)
            flash("Comment published!", category="success")
        flashing_if_errors(form.errors)

        comment_utils = CommentUtils(mongodb)
        comments = comment_utils.get_comments_by_post_uid(post_uid)

        post_utils.view_increment(username, post_uid)
        user_utils = UserUtils(mongodb)
        user_utils.total_view_increment(username)

    return render_template(
        "frontstage/blogpost.html", user=user, post=post, comments=comments, form=form
    )


@frontstage.route("/@<username>/posts/<post_uid>", methods=["GET", "POST"])
def blogpost_no_slug(username: str, post_uid: str) -> str:
    """Render a blog post page, optionally redirecting if a slug is present.

    Args:
        username (str): The username of the post author.
        post_uid (str): The unique identifier of the post.

    Returns:
        str: Rendered HTML of the blog post page or redirect to the slugged URL.
    """
    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)
        if not mongodb.post_info.exists("post_uid", post_uid):
            logger.debug(f"Invalid post uid {post_uid}.")
            abort(404)
        post_info = mongodb.post_info.find_one({"post_uid": post_uid})

    if username != post_info.get("author"):
        logger.debug(f"User {username} does not own post {post_uid}.")
        abort(404)

    custom_slug = post_info.get("custom_slug")
    if custom_slug:
        return redirect(
            url_for(
                "frontstage.blogpost_with_slug",
                username=username,
                post_uid=post_uid,
                slug=custom_slug,
            )
        )
    return blogpost(username, post_uid, request)


@frontstage.route("/@<username>/posts/<post_uid>/<slug>", methods=["GET", "POST"])
def blogpost_with_slug(username: str, post_uid: str, slug: str) -> str:
    """Render a blog post page with a slug, or redirect if the slug does not match.

    Args:
        username (str): The username of the post author.
        post_uid (str): The unique identifier of the post.
        slug (str): The slug of the post.

    Returns:
        str: Rendered HTML of the blog post page or redirect to the correct slug URL.
    """
    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)
        if not mongodb.post_info.exists("post_uid", post_uid):
            logger.debug(f"Invalid post uid {post_uid}.")
            abort(404)
        post_info = mongodb.post_info.find_one({"post_uid": post_uid})

    if username != post_info.get("author"):
        logger.debug(f"User {username} does not own post {post_uid}.")
        abort(404)

    actual_slug = post_info.get("custom_slug")
    if slug != actual_slug:
        return redirect(
            url_for(
                "frontstage.blogpost_with_slug",
                username=username,
                post_uid=post_uid,
                slug=actual_slug,
            )
        )
    return blogpost(username, post_uid, request)


@frontstage.route("/@<username>/tags", methods=["GET"])
def tag(username: str) -> str:
    """Render a page showing posts and projects with a specified tag.

    Args:
        username (str): The username of the user whose posts and projects are to be displayed.

    Returns:
        str: Rendered HTML of the tag page.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url
    logger_utils.page_visited(request)

    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)

        tag_url_encoded = request.args.get("tag", default=None, type=str)
        if tag_url_encoded is None:
            return redirect(url_for("frontstage.blog", username=username))

        tag = unquote(tag_url_encoded)
        user_utils = UserUtils(mongodb)
        user = user_utils.get_user_info(username)

        post_utils = PostUtils(mongodb)
        posts = post_utils.get_post_infos(username)
        posts_with_desired_tag = [post for post in posts if tag in post.get("tags")]

        projects_utils = ProjectsUtils(mongodb)
        projects = projects_utils.get_project_infos(username)
        projects_with_desired_tag = [project for project in projects if tag in project.get("tags")]

        user_utils.total_view_increment(username)

    return render_template(
        "frontstage/tag.html",
        user=user,
        posts=posts_with_desired_tag,
        projects=projects_with_desired_tag,
        tag=tag,
    )


@frontstage.route("/@<username>/gallery", methods=["GET"])
def gallery(username: str) -> str:
    """Render the gallery page for a given user.

    Args:
        username (str): The username of the user whose gallery is to be rendered.

    Returns:
        str: Rendered HTML of the gallery page.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url
    logger_utils.page_visited(request)

    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)
        user_utils = UserUtils(mongodb)
        user = user_utils.get_user_info(username)
        if not user.gallery_enabled:
            logger.debug(f"User {username} did not enable gallery feature.")
            abort(404)

        current_page = request.args.get("page", default=1, type=int)
        PROJECTS_EACH_PAGE = 12
        paging = Paging(mongodb)
        pagination = paging.setup(username, "project_info", current_page, PROJECTS_EACH_PAGE)

        projects_utils = ProjectsUtils(mongodb)
        projects = projects_utils.get_project_infos_with_pagination(
            username=username,
            page_number=current_page,
            projects_per_page=PROJECTS_EACH_PAGE,
        )
        for project in projects:
            project["created_at"] = project.get("created_at").strftime("%Y-%m-%d")

        user_utils.total_view_increment(username)

    return render_template(
        "frontstage/gallery.html", user=user, projects=projects, pagination=pagination
    )


def project(username: str, project_uid: str, request: Request) -> str:
    """Handle the main actions for rendering a project page.

    Args:
        username (str): The username of the project author.
        project_uid (str): The unique identifier of the project.
        request (Request): The Flask request object.

    Returns:
        str: Rendered HTML of the project page.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url
    logger_utils.page_visited(request)

    with mongo_connection() as mongodb:
        user = mongodb.user_info.find_one({"username": username})
        projects_utils = ProjectsUtils(mongodb)
        project = projects_utils.get_full_project(project_uid)
        project["content"] = convert_project_content(project.get("content"))
        projects_utils.view_increment(username, project_uid)

        user_utils = UserUtils(mongodb)
        user_utils.total_view_increment(username)

    return render_template("frontstage/project.html", user=user, project=project)


@frontstage.route("/@<username>/project/<project_uid>", methods=["GET"])
def project_no_slug(username: str, project_uid: str) -> str:
    """Render a project page, optionally redirecting if a slug is present.

    Args:
        username (str): The username of the project author.
        project_uid (str): The unique identifier of the project.

    Returns:
        str: Rendered HTML of the project page or redirect to the slugged URL.
    """
    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)
        if not mongodb.project_info.exists("project_uid", project_uid):
            logger.debug(f"Invalid project uid {project_uid}.")
            abort(404)
        project_info = mongodb.project_info.find_one({"project_uid": project_uid})

    if username != project_info.get("author"):
        logger.debug(f"User {username} does not own project {project_uid}.")
        abort(404)

    custom_slug = project_info.get("custom_slug")
    if custom_slug:
        return redirect(
            url_for(
                "frontstage.project_with_slug",
                username=username,
                project_uid=project_uid,
                slug=custom_slug,
            )
        )
    return project(username, project_uid, request)


@frontstage.route("/@<username>/project/<project_uid>/<slug>", methods=["GET"])
def project_with_slug(username: str, project_uid: str, slug: str) -> str:
    """Render a project page with a slug, or redirect if the slug does not match.

    Args:
        username (str): The username of the project author.
        project_uid (str): The unique identifier of the project.
        slug (str): The slug of the project.

    Returns:
        str: Rendered HTML of the project page or redirect to the correct slug URL.
    """
    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)
        if not mongodb.project_info.exists("project_uid", project_uid):
            logger.debug(f"Invalid project uid {project_uid}.")
            abort(404)
        project_info = mongodb.project_info.find_one({"project_uid": project_uid})

    if username != project_info.get("author"):
        logger.debug(f"User {username} does not own project {project_uid}.")
        abort(404)

    actual_slug = project_info.get("custom_slug")
    if slug != actual_slug:
        return redirect(
            url_for(
                "frontstage.project_with_slug",
                username=username,
                project_uid=project_uid,
                slug=actual_slug,
            )
        )
    return project(username, project_uid, request)


@frontstage.route("/@<username>/changelog", methods=["GET"])
def changelog(username: str) -> str:
    """Render the changelog page for a given user.

    Args:
        username (str): The username of the user whose changelog is to be rendered.

    Returns:
        str: Rendered HTML of the changelog page.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url
    logger_utils.page_visited(request)

    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)
        user_utils = UserUtils(mongodb)
        user = user_utils.get_user_info(username)
        if not user.changelog_enabled:
            logger.debug(f"User {username} did not enable changelog feature.")
            abort(404)
        changelog_utils = ChangelogUtils(mongodb)
        changelogs = changelog_utils.get_changelogs(username, by_date=True)

    for changelog in changelogs:
        changelog["content"] = convert_changelog_content(changelog.get("content"))

    return render_template("frontstage/changelog.html", user=user, changelogs=changelogs)


@frontstage.route("/@<username>/about", methods=["GET"])
def about(username: str) -> str:
    """Render the about page for a given user.

    Args:
        username (str): The username of the user whose about page is to be rendered.

    Returns:
        str: Rendered HTML of the about page.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url
    logger_utils.page_visited(request)

    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)

        user = mongodb.user_info.find_one({"username": username})
        about = mongodb.user_about.find_one({"username": username}).get("about")
        about = convert_about(about)

        user_utils = UserUtils(mongodb)
        user_utils.total_view_increment(username)

    return render_template("frontstage/about.html", user=user, about=about)


@frontstage.route("/@<username>/get-profile-img", methods=["GET"])
def get_profile_img(username: str) -> str:
    """Get the profile image URL of a user.

    Args:
        username (str): The username of the user.

    Returns:
        str: JSON response containing the profile image URL.
    """
    with mongo_connection() as mongodb:
        user_utils = UserUtils(mongodb)
        user = user_utils.get_user_info(username)
    return jsonify({"imageUrl": user.profile_img_url})


@frontstage.route("/is-unique", methods=["GET"])
def is_unique() -> str:
    """Check if the email or username is unique.

    Returns:
        str: JSON response indicating if the email or username is unique.
    """
    email = request.args.get("email", default=None, type=str)
    username = request.args.get("username", default=None, type=str)
    with mongo_connection() as mongodb:
        if email is not None:
            return jsonify(not mongodb.user_info.exists(key="email", value=email))
        elif username is not None:
            return jsonify(not mongodb.user_info.exists(key="username", value=username))


@frontstage.route("/readcount-increment", methods=["GET"])
def readcount_increment() -> str:
    """Increment the read count for a post.

    Returns:
        str: Confirmation message.
    """
    content = request.args.get("content", type=str)

    if content == "post":
        post_uid = request.args.get("post_uid", type=str)
        with mongo_connection() as mongodb:
            author = mongodb.post_info.find_one({"post_uid": post_uid}).get("author")
            if current_user.is_authenticated and current_user.username == author:
                return "OK"
            post_utils = PostUtils(mongodb)
            post_utils.read_increment(author, post_uid)

    elif content == "project":
        project_uid = request.args.get("project_uid", type=str)
        with mongo_connection() as mongodb:
            author = mongodb.project_info.find_one({"project_uid": project_uid}).get("author")
            if current_user.is_authenticated and current_user.username == author:
                return "OK"
            projects_utils = ProjectsUtils(mongodb)
            projects_utils.view_increment(author, project_uid)
        return "OK"

    return "Invalid content type.", 400

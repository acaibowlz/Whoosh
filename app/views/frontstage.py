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
from app.logging import logger
from app.mongo import mongo_connection
from app.views.main import flashing_if_errors

frontstage = Blueprint("frontstage", __name__, template_folder=TEMPLATE_FOLDER)


@frontstage.route("/@<username>", methods=["GET"])
def home(username: str) -> str:
    """
    The home page for a given user. Shows the featured blog posts.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url

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
    """
    The blog page for a given user.
    Shows blog posts in lists and tags with counts.
    """
    POSTS_EACH_PAGE = 5

    if current_user.is_authenticated:
        session["last_visited"] = request.base_url

    with mongo_connection() as mongodb:
        if not mongodb.user_info.exists("username", username):
            logger.debug(f"Invalid username {username}.")
            abort(404)

        current_page = request.args.get("page", default=1, type=int)
        paging = Paging(mongodb)
        pagination = paging.setup(username, "post", current_page, POSTS_EACH_PAGE)

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
    """
    The destination for `blogpost_no_slug()` and `blogpost_with_slug()`.
    Renders a blog post and its comments.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url

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
    """
    Handles blog post by post UID.
    If a slug is defined for the post, redirects to the URL with slug by `blogpost_with_slug()`.
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
    """
    Handles blog post with a slug. If an incorrect slug is provided, redirects to the correct URL.
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
    """
    The page for showing a query result by tag. Includes posts and projects.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url

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
    """
    The gallery page for a given user. Shows projects in grids.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url

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
        pagination = paging.setup(username, "project", current_page, PROJECTS_EACH_PAGE)

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
    """
    The destination for `project_no_slug()` and `project_with_slug()`.
    Renders the content of a project.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url

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
    """
    Handles project by project UID.
    If a slug is defined for the project, redirects to the URL with slug by `project_with_slug()`.
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
    """
    Handles project with a slug. If an incorrect slug is provided, redirects to the correct URL.
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
    """
    The changelog page for a given user. Shows changelogs in a timeline.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url

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
    """
    The about page for a given user.
    """
    if current_user.is_authenticated:
        session["last_visited"] = request.base_url

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
    """
    Get the profile image URL of a user. Sends a JSON response with key `imageUrl`.
    """
    with mongo_connection() as mongodb:
        user_utils = UserUtils(mongodb)
        user = user_utils.get_user_info(username)
    return jsonify({"imageUrl": user.profile_img_url})


@frontstage.route("/is-unique", methods=["GET"])
def is_unique() -> str:
    """
    Check if the email or username is unique.
    Sends a JSON response. A single boolean value will be serialized.
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
    """
    Increment the read count of a post or project by 1.
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
        return "OK"

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

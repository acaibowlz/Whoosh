import io
import json

from bcrypt import checkpw, gensalt, hashpw
from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import current_user, login_required, logout_user

from app.config import TEMPLATE_FOLDER
from app.forms.changelog import EditChangelogForm, NewChangelogForm
from app.forms.posts import EditPostForm, NewPostForm
from app.forms.projects import EditProjectForm, NewProjectForm
from app.forms.users import (
    EditAboutForm,
    GeneralSettingsForm,
    UpdatePasswordForm,
    UpdateSocialLinksForm,
    UserDeletionForm,
)
from app.helpers.changelog import ChangelogUtils, create_changelog, update_changelog
from app.helpers.posts import PostUtils, create_post, update_post
from app.helpers.projects import ProjectsUtils, create_project, update_project
from app.helpers.users import UserUtils
from app.helpers.utils import Paging, slicing_title
from app.logging import logger, logger_utils
from app.mongo import mongo_connection
from app.views.main import flashing_if_errors

backstage = Blueprint("backstage", __name__, template_folder=TEMPLATE_FOLDER)


@backstage.route("/", methods=["GET"])
@login_required
def root() -> Response:
    """Redirects to the posts panel.

    Returns:
        Response: URL to the posts panel.

    """
    return redirect(url_for("backstage.posts_panel"))


@backstage.route("/posts", methods=["GET", "POST"])
@login_required
def posts_panel() -> str:
    """Handles the posts panel view and post creation.

    Manages the display of posts and allows for the creation of new posts.
    It includes pagination for posts and error handling for form submissions.

    Returns:
        str: Rendered template of the posts panel with context.

    """
    session["user_current_panel"] = "posts"
    logger_utils.backstage(username=current_user.username, panel="posts")

    current_page = request.args.get("page", default=1, type=int)

    with mongo_connection() as mongodb:
        user = mongodb.user_info.find_one({"username": current_user.username})
        form = NewPostForm()
        if form.validate_on_submit():
            post_uid = create_post(form, mongodb)
            if post_uid is not None:
                logger.debug(f"Post {post_uid} has been created.")
                flash("New post published successfully!", category="success")
        flashing_if_errors(form.errors)

        POSTS_EACH_PAGE = 20
        paging = Paging(db_handler=mongodb)
        pagination = paging.setup(current_user.username, "post_info", current_page, POSTS_EACH_PAGE)
        post_utils = PostUtils(mongodb)
        posts = post_utils.get_post_infos_with_pagination(
            username=current_user.username,
            page_number=current_page,
            posts_per_page=POSTS_EACH_PAGE,
        )
        for post in posts:
            post["title"] = slicing_title(post.get("title"), 25)
            post["comments"] = mongodb.comment.count_documents({"post_uid": post.get("post_uid")})

    logger_utils.pagination(panel="posts", num=len(posts))

    return render_template(
        "backstage/posts.html", user=user, posts=posts, pagination=pagination, form=form
    )


@backstage.route("/projects", methods=["GET", "POST"])
@login_required
def projects_panel() -> str:
    """Handles the projects panel view and project creation.

    Manages the display of projects and allows for the creation of new projects.
    It includes pagination for projects and error handling for form submissions.

    Returns:
        str: Rendered template of the projects panel with context.

    """
    session["user_current_panel"] = "projects"
    logger_utils.backstage(username=current_user.username, panel="projects")

    current_page = request.args.get("page", default=1, type=int)
    form = NewProjectForm()

    with mongo_connection() as mongodb:

        if form.validate_on_submit():
            project_uid = create_project(form, mongodb)
            if project_uid is not None:
                logger.debug(f"Project {project_uid} has been created.")
                flash("New project published successfully!", category="success")
        flashing_if_errors(form.errors)
        user = mongodb.user_info.find_one({"username": current_user.username})
        PROJECTS_PER_PAGE = 10
        projects_utils = ProjectsUtils(mongodb)
        projects = projects_utils.get_project_infos_with_pagination(
            current_user.username, current_page, PROJECTS_PER_PAGE
        )
        paging = Paging(mongodb)
        paging.setup(current_user.username, "project_info", current_page, PROJECTS_PER_PAGE)

    for project in projects:
        project["title"] = slicing_title(project.get("title"), 40)

    logger_utils.pagination(panel="projects", num=len(projects))

    return render_template(
        "backstage/projects.html", user=user, projects=projects, pagination=paging, form=form
    )


@backstage.route("/archive", methods=["GET"])
@login_required
def archive_panel() -> str:
    """Displays the archived posts and projects for the user.

    Retrieves and formats archived posts and projects for the current user, including
    formatting view counts and comment counts. It then renders the archive page with
    this information.

    Returns:
        str: Rendered template of the archive panel with context.

    """
    session["user_current_panel"] = "archive"
    logger_utils.backstage(username=current_user.username, panel="archive")

    with mongo_connection() as mongodb:
        user = mongodb.user_info.find_one({"username": current_user.username})
        post_utils = PostUtils(mongodb)
        posts = post_utils.get_post_infos(current_user.username, archive="only")
        for post in posts:
            post["views"] = format(post.get("views"), ",")
            post["comments"] = mongodb.comment.count_documents({"post_uid": post.get("post_uid")})
        projects_utils = ProjectsUtils(mongodb)
        projects = projects_utils.get_project_infos(current_user.username, archive="only")
        changelog_utils = ChangelogUtils(mongodb)
        changelogs = changelog_utils.get_archived_changelogs(current_user.username)

    logger_utils.pagination(panel="archive", num=(len(posts) + len(projects)))

    return render_template(
        "backstage/archive.html", user=user, posts=posts, projects=projects, changelogs=changelogs
    )


@backstage.route("/changelog", methods=["GET", "POST"])
@login_required
def changelog_panel() -> str:
    """Render the changelog panel for the backstage section.

    This route handles both GET and POST requests. It displays the changelog panel,
    processes the submission of a new changelog if present, and handles pagination
    for viewing changelogs.

    Returns:
        str: The rendered HTML template for the changelog panel.

    """
    session["user_current_panel"] = "changelog"
    logger_utils.backstage(username=current_user.username, panel="changelog")

    current_page = request.args.get("page", default=1, type=int)

    with mongo_connection() as mongodb:
        user = mongodb.user_info.find_one({"username": current_user.username})
        form = NewChangelogForm()
        if form.validate_on_submit():
            changelog_uid = create_changelog(form, mongodb)
            if changelog_uid is not None:
                logger.debug(f"Changelog {changelog_uid} has been created.")
                flash("New changelog published successfully!", category="success")
        flashing_if_errors(form.errors)

        user = mongodb.user_info.find_one({"username": current_user.username})
        CHANGELOGS_PER_PAGE = 10
        changelog_utils = ChangelogUtils(mongodb)
        changelogs = changelog_utils.get_changelogs_with_pagination(
            current_user.username, current_page, CHANGELOGS_PER_PAGE
        )
        paging = Paging(mongodb)
        paging.setup(current_user.username, "changelog", current_page, CHANGELOGS_PER_PAGE)

    for changelog in changelogs:
        changelog["title"] = slicing_title(changelog.get("title"), 40)

    logger_utils.pagination(panel="changelog", num=len(changelogs))

    return render_template(
        "backstage/changelog.html", user=user, form=form, pagination=paging, changelogs=changelogs
    )


@backstage.route("/theme", methods=["GET", "POST"])
@login_required
def theme_panel() -> str:
    """Displays the theme settings panel for the user.

    Retrieves user information and renders the theme settings page.

    Returns:
        str: Rendered template of the theme settings panel with context.

    """
    session["user_current_panel"] = "theme"
    logger_utils.backstage(username=current_user.username, panel="theme")

    with mongo_connection() as mongodb:
        user = mongodb.user_info.find_one({"username": current_user.username})

    return render_template("backstage/theme.html", user=user)


@backstage.route("/settings", methods=["GET", "POST"])
@login_required
def settings_panel() -> str:
    """Handles the user settings panel, including general settings, social links, password update, and account deletion.

    Manages form submissions for updating general settings, social links, password changes, and account deletion.
    Validates form inputs and updates the user information accordingly. Provides feedback on success or failure.

    Returns:
        str: Rendered template of the settings panel with context.

    """
    session["user_current_panel"] = "settings"
    logger_utils.backstage(username=current_user.username, panel="settings")

    with mongo_connection() as mongodb:
        user = mongodb.user_info.find_one({"username": current_user.username})
        form_general = GeneralSettingsForm(prefix="general")
        form_social = UpdateSocialLinksForm(prefix="social")
        form_update_pw = UpdatePasswordForm(prefix="pw")
        form_deletion = UserDeletionForm(prefix="deletion")

        if form_general.submit_settings.data and form_general.validate_on_submit():
            cover_url = (
                form_general.cover_url.data
                if form_general.cover_url.data
                else user.get("cover_url")
            )
            mongodb.user_info.update_values(
                filter={"username": current_user.username},
                update={
                    "cover_url": cover_url,
                    "blogname": form_general.blogname.data,
                    "gallery_enabled": form_general.gallery_enabled.data,
                    "changelog_enabled": form_general.changelog_enabled.data,
                },
            )
            logger.debug(f"General settings for {current_user.username} have been updated.")
            flash("Update succeeded!", category="success")
            user = mongodb.user_info.find_one({"username": current_user.username})

        if request.method == "GET":
            for i in range(len(user.get("social_links"))):
                if user.get("social_links")[i]:
                    form_social[f"platform{i}"].default = user.get("social_links")[i][1]
            form_social.process()

        if form_social.submit_links.data and form_social.validate_on_submit():
            updated_links = []
            for i in range(5):
                url = form_social.data.get(f"url{i}", "")
                platform = form_social.data.get(f"platform{i}", "")
                if url and platform:
                    updated_links.append((url, platform))
            while len(updated_links) < 5:
                updated_links.append(tuple())

            mongodb.user_info.update_values(
                filter={"username": current_user.username},
                update={"social_links": updated_links},
            )
            logger.debug(f"Social links for {current_user.username} have been updated.")
            flash("Social Links updated!", category="success")
            user = mongodb.user_info.find_one({"username": current_user.username})

        if form_update_pw.submit_pw.data and form_update_pw.validate_on_submit():
            current_pw = form_update_pw.current_pw.data
            current_pw_encoded = current_pw.encode("utf-8")
            user_creds = mongodb.user_creds.find_one({"username": current_user.username})
            real_pw_encoded = user_creds.get("password").encode("utf-8")
            if not checkpw(current_pw_encoded, real_pw_encoded):
                logger.debug("Invalid old password when changing password.")
                flash("Invalid current password. Please try again.", category="error")
                return render_template(
                    "backstage/settings.html",
                    user=user,
                    form_general=form_general,
                    form_social=form_social,
                    form_update_pw=form_update_pw,
                    form_deletion=form_deletion,
                )

            new_pw = form_update_pw.new_pw.data
            new_pw_hashed = hashpw(new_pw.encode("utf-8"), gensalt(12)).decode("utf-8")
            mongodb.user_creds.update_values(
                filter={"username": current_user.username},
                update={"password": new_pw_hashed},
            )
            logger.debug(f"Password for user {current_user.username} has been updated.")
            logout_user()
            logger_utils.logout(request=request, username=username)
            session.clear()
            flash("Password update succeeded!", category="success")
            flash("Please log in again with your new password.", category="info")
            return redirect(url_for("main.login"))

        if form_deletion.submit_delete.data and form_deletion.validate_on_submit():
            pw = form_deletion.password.data
            pw_encoded = pw.encode("utf-8")
            user_creds = mongodb.user_creds.find_one({"username": current_user.username})
            real_pw_encoded = user_creds.get("password").encode("utf-8")

            if not checkpw(pw_encoded, real_pw_encoded):
                flash("Invalid password. Access denied.", category="error")
                return render_template(
                    "backstage/settings.html",
                    user=user,
                    form_general=form_general,
                    form_social=form_social,
                    form_update_pw=form_update_pw,
                    form_deletion=form_deletion,
                )

            # Deletion procedure
            username = current_user.username
            logout_user()
            logger_utils.logout(request=request, username=username)
            session.clear()
            user_utils = UserUtils(mongodb)
            user_utils.delete_user(username, logger)
            flash("Account deleted successfully!", category="success")
            logger.debug(f"User {username} has been deleted.")
            return redirect(url_for("main.signup"))

    flashing_if_errors(form_general.errors)
    flashing_if_errors(form_social.errors)
    flashing_if_errors(form_update_pw.errors)
    flashing_if_errors(form_deletion.errors)

    return render_template(
        "backstage/settings.html",
        user=user,
        form_general=form_general,
        form_social=form_social,
        form_update_pw=form_update_pw,
        form_deletion=form_deletion,
    )


@backstage.route("/edit/post/<post_uid>", methods=["GET", "POST"])
@login_required
def edit_post(post_uid: str) -> str:
    """Handles the editing of a specific post.

    Allows users to update the details of a post. On successful update, flashes a success message and redirects
    to the posts panel. Handles form validation errors and updates post information in the database.

    Args:
        post_uid (str): Unique identifier of the post to be edited.

    Returns:
        str: Rendered template of the edit post page or redirects to the posts panel on POST requests.
    """
    logger_utils.backstage(username=current_user.username, panel="edit_post")

    form = EditPostForm()

    with mongo_connection() as mongodb:
        if form.validate_on_submit():
            update_post(post_uid, form, mongodb)
            logger.debug(f"Post {post_uid} is updated.")
            title = mongodb.post_info.find_one({"post_uid": post_uid}).get("title")
            title_sliced = slicing_title(title, max_len=20)
            flash(f'Your post "{title_sliced}" has been updated!', category="success")
        flashing_if_errors(form.errors)

        user = mongodb.user_info.find_one({"username": current_user.username})
        post_utils = PostUtils(mongodb)
        post = post_utils.get_full_post(post_uid)
        post["tags"] = ", ".join(post.get("tags"))

    if request.method == "POST":
        return redirect(url_for("backstage.posts_panel"))
    return render_template("backstage/edit-post.html", post=post, user=user, form=form)


@backstage.route("/about", methods=["GET", "POST"])
@login_required
def about_panel() -> str:
    """Handles the editing of the user's 'About' section.

    Allows users to update their personal information and 'About' section. On successful update, flashes a success
    message and updates the user cache. Handles form validation errors and updates user information in the database.

    Returns:
        str: Rendered template of the edit about page.
    """
    logger_utils.backstage(username=current_user.username, panel="about")

    with mongo_connection() as mongodb:
        user = mongodb.user_info.find_one({"username": current_user.username})
        about = mongodb.user_about.find_one({"username": current_user.username}).get("about")

        form = EditAboutForm()
        if form.validate_on_submit():
            profile_img_url = (
                form.profile_img_url.data
                if form.profile_img_url.data
                else user.get("profile_img_url")
            )
            updated_info = {
                "profile_img_url": profile_img_url,
                "short_bio": form.short_bio.data,
            }
            updated_about = {"about": form.editor.data}
            mongodb.user_info.update_values(
                filter={"username": user.get("username")}, update=updated_info
            )
            mongodb.user_about.update_values(
                filter={"username": user.get("username")}, update=updated_about
            )
            about = updated_about.get("about")
            logger.debug(f"Information for user {current_user.username} has been updated.")
            flash("Information updated!", category="success")
        flashing_if_errors(form.errors)

    if request.method == "GET":
        return render_template("backstage/about.html", user=user, about=about, form=form)
    return redirect(url_for("frontstage.about", username=current_user.username))


@backstage.route("/edit/project/<project_uid>", methods=["GET", "POST"])
@login_required
def edit_project(project_uid: str) -> str:
    """Handles the editing of a specific project.

    Allows users to update the details of a project. On successful update, flashes a success message and redirects
    to the projects panel. Handles form validation errors and updates project information in the database.

    Args:
        project_uid (str): Unique identifier of the project to be edited.

    Returns:
        str: Rendered template of the edit project page or redirects to the projects panel on POST requests.
    """
    logger_utils.backstage(username=current_user.username, panel="edit_project")

    with mongo_connection() as mongodb:
        user = mongodb.user_info.find_one({"username": current_user.username})
        projects_utils = ProjectsUtils(mongodb)
        project = projects_utils.get_full_project(project_uid)
        project["tags"] = ", ".join(project.get("tags"))

        form = EditProjectForm()
        if form.validate_on_submit():
            update_project(project_uid, form, mongodb)
            logger.debug(f"Project {project_uid} is updated.")
            title_sliced = slicing_title(
                mongodb.project_info.find_one({"project_uid": project_uid}).get("title"),
                max_len=20,
            )
            flash(f'Your project "{title_sliced}" has been updated!', category="success")
            project = projects_utils.get_full_project(project_uid)
            project["tags"] = ", ".join(project.get("tags"))
        flashing_if_errors(form.errors)

    if request.method == "POST":
        return redirect(url_for("backstage.projects_panel"))
    return render_template("backstage/edit-project.html", project=project, user=user, form=form)


@backstage.route("/edit/changelog/<changelog_uid>", methods=["GET", "POST"])
@login_required
def edit_changelog(changelog_uid: str) -> str:
    """_summary_

    Args:
        changelog_uid (str): _description_

    Returns:
        str: _description_
    """
    logger_utils.backstage(username=current_user.username, panel="edit_changelog")

    with mongo_connection() as mongodb:
        user = mongodb.user_info.find_one({"username": current_user.username})
        changelog = mongodb.changelog.find_one({"changelog_uid": changelog_uid})
        changelog["date"] = changelog.get("date").strftime("%m/%d/%Y")
        changelog["tags"] = ", ".join(changelog.get("tags"))

        form = EditChangelogForm()
        if form.validate_on_submit():
            update_changelog(changelog_uid, form, mongodb)
            logger.debug(f"Changelog {changelog_uid} is updated.")
            title_sliced = slicing_title(
                mongodb.changelog.find_one({"changelog_uid": changelog_uid}).get("title"),
                max_len=20,
            )
            flash(f'Your changelog "{title_sliced}" has been updated!', category="success")
            changelog = mongodb.changelog.find_one({"changelog_uid": changelog_uid})
            changelog["tags"] = ", ".join(changelog.get("tags"))
        flashing_if_errors(form.errors)

    if request.method == "POST":
        return redirect(url_for("backstage.changelog_panel"))
    return render_template(
        "backstage/edit-changelog.html", changelog=changelog, user=user, form=form
    )


@backstage.route("/edit-featured", methods=["GET"])
@login_required
def toggle_featured() -> Response:
    """
    Toggles the featured status of a post.
    This action is triggered by the button over the post panel.
    When the action is done, it returns to the same panel where the action was triggered.
    """
    post_uid = request.args.get("uid")
    with mongo_connection() as mongodb:
        post_info = mongodb.post_info.find_one({"post_uid": post_uid})
        truncated_post_title = slicing_title(post_info.get("title"), max_len=20)

        if request.args.get("featured") == "to_true":
            updated_featured_status = True
            flash(
                f'Your post "{truncated_post_title}" is now featured on the home page!',
                category="success",
            )
        else:
            updated_featured_status = False
            flash(
                f'Your post "{truncated_post_title}" is now removed from the home page!',
                category="success",
            )

        mongodb.post_info.update_values(
            filter={"post_uid": post_uid}, update={"featured": updated_featured_status}
        )
        logger.debug(
            f"Featuring status for post {post_uid} is now set to {updated_featured_status}."
        )

    return redirect(url_for("backstage.posts_panel"))


@backstage.route("/edit-archived", methods=["GET"])
@login_required
def toggle_archived() -> Response:
    """
    Toggles the archived status of posts or projects.
    This action is triggered by the botton over the post or project panel.
    When the action is done, it returns to the same panel where the action was triggered.
    """
    content_type = request.args.get("type")

    with mongo_connection() as mongodb:
        if content_type == "post":
            post_uid = request.args.get("uid")
            post_info = mongodb.post_info.find_one({"post_uid": post_uid})

            author = post_info.get("author")
            tags = post_info.get("tags")
            title_sliced = slicing_title(post_info.get("title"), max_len=20)

            if request.args.get("archived") == "to_true":
                updated_archived_status = True
                tags_increment = {f"tags.{tag}": -1 for tag in tags}
                flash(f'Your post "{title_sliced}" is now archived!', category="success")
            else:
                updated_archived_status = False
                tags_increment = {f"tags.{tag}": 1 for tag in tags}
                flash(
                    f'Your post "{title_sliced}" is now restored from the archive!',
                    category="success",
                )

            mongodb.post_info.update_values(
                filter={"post_uid": post_uid}, update={"archived": updated_archived_status}
            )
            mongodb.user_info.make_increments(
                filter={"username": author}, increments=tags_increment, upsert=True
            )
            logger.debug(
                f"Archive status for post {post_uid} is now set to {updated_archived_status}."
            )

        elif content_type == "project":
            project_uid = request.args.get("uid")
            project_info = mongodb.project_info.find_one({"project_uid": project_uid})
            title_sliced = slicing_title(project_info.get("title"), max_len=20)

            if request.args.get("archived") == "to_true":
                updated_archived_status = True
                flash(f'Your project "{title_sliced}" is now archived!', category="success")
            else:
                updated_archived_status = False
                flash(
                    f'Your project "{title_sliced}" is now restored from the archive!',
                    category="success",
                )

            mongodb.project_info.update_values(
                filter={"project_uid": project_uid},
                update={"archived": updated_archived_status},
            )
            logger.debug(
                f"Archive status for project {project_uid} is now set to {updated_archived_status}."
            )

        elif content_type == "changelog":
            changelog_uid = request.args.get("uid")
            changelog = mongodb.changelog.find_one({"changelog_uid": changelog_uid})
            title_sliced = slicing_title(changelog.get("title"), max_len=20)

            if request.args.get("archived") == "to_true":
                updated_archived_status = True
                flash(f'Your changelog "{title_sliced}" is now archived!', category="success")
            else:
                updated_archived_status = False
                flash(
                    f'Your changelog "{title_sliced}" is now restored from the archive!',
                    category="success",
                )

            mongodb.changelog.update_values(
                filter={"changelog_uid": changelog_uid},
                update={"archived": updated_archived_status},
            )
            logger.debug(
                f"Archive status for changelog {changelog_uid} is now set to {updated_archived_status}."
            )

    redirect_mapping = {
        "posts": redirect(url_for("backstage.posts_panel")),
        "archive": redirect(url_for("backstage.archive_panel")),
        "projects": redirect(url_for("backstage.projects_panel")),
        "changelog": redirect(url_for("backstage.changelog_panel")),
    }
    return redirect_mapping.get(session["user_current_panel"])


@backstage.route("/delete/post", methods=["GET"])
@login_required
def delete_post() -> Response:
    """
    Deletes a post. Redirects to the archive panel page when it's done.
    """
    post_uid = request.args.get("uid")
    with mongo_connection() as mongodb:
        post_info = mongodb.post_info.find_one({"post_uid": post_uid})
        title_sliced = slicing_title(post_info.get("title"), max_len=20)
        mongodb.post_info.delete_one({"post_uid": post_uid})
        mongodb.post_content.delete_one({"post_uid": post_uid})
    logger.debug(f"Post {post_uid} has been deleted.")
    flash(f'Your post "{title_sliced}" has been deleted!', category="success")

    return redirect(url_for("backstage.archive_panel"))


@backstage.route("/delete/project", methods=["GET"])
@login_required
def delete_project() -> Response:
    """
    Deletes a project. Redirects to the archive panel page when it's done.
    """
    project_uid = request.args.get("uid")
    with mongo_connection() as mongodb:
        project_info = mongodb.project_info.find_one({"project_uid": project_uid})
        title_sliced = slicing_title(project_info.get("title"), max_len=20)
        mongodb.project_info.delete_one({"project_uid": project_uid})
        mongodb.project_content.delete_one({"project_uid": project_uid})
    logger.debug(f"Project {project_uid} has been deleted.")
    flash(f'Your project "{title_sliced}" has been deleted!', category="success")

    return redirect(url_for("backstage.archive_panel"))


@backstage.route("/delete/changelog", methods=["GET"])
@login_required
def delete_changelog() -> Response:
    """
    Deletes a changelog. Redirects to the archive panel page when it's done.
    """
    changelog_uid = request.args.get("uid")
    with mongo_connection() as mongodb:
        changelog = mongodb.changelog.find_one({"changelog_uid": changelog_uid})
        title_sliced = slicing_title(changelog.get("title"), max_len=20)
        mongodb.changelog.delete_one({"changelog_uid": changelog_uid})
    logger.debug(f"Changelog {changelog_uid} has been deleted.")
    flash(f'Your changelog "{title_sliced}" has been deleted!', category="success")

    return redirect(url_for("backstage.archive_panel"))


@backstage.route("/logout", methods=["GET"])
@login_required
def logout() -> Response:
    """
    Logs out the user and redirects to the home page.
    """
    username = current_user.username
    logout_user()
    logger_utils.logout(request=request, username=username)
    session.clear()

    return redirect(url_for("frontstage.home", username=username))


@backstage.route("/export", methods=["GET"])
@login_required
def export_data():

    result = {}

    with mongo_connection() as mongodb:
        # export user data
        user_data = {}
        user_utils = UserUtils(mongodb)
        user_info = user_utils.get_user_info(current_user.username)
        user_about = user_utils.get_user_about(current_user.username)
        user_data["username"] = user_info.username
        user_data["email"] = user_info.email
        user_data["blogname"] = user_info.blogname
        if "static" in user_info.profile_img_url:
            user_data["profile_img_url"] = ""
        else:
            user_data["profile_img_url"] = user_info.profile_img_url
        if "static" in user_info.cover_url:
            user_data["cover_url"] = ""
        else:
            user_data["cover_url"] = user_info.cover_url
        user_data["created_at"] = f"{user_info.created_at}"
        user_data["short_bio"] = user_info.short_bio
        user_data["about"] = user_about.about
        i = 0
        while user_info.social_links[i]:
            user_data[f"social_link_{i}"] = (
                user_info.social_links[i][0],
                user_info.social_links[i][1],
            )
            i += 1
        user_data["total_views"] = user_info.total_views
        result["info"] = user_data

        # export posts
        post_data = {}
        post_utils = PostUtils(mongodb)
        posts = post_utils.get_post_infos(current_user.username, archive="include")
        for post in posts:
            uid = post.get("post_uid")
            post_data[uid] = {}
            post_data[uid]["title"] = post.get("title")
            post_data[uid]["subtitle"] = post.get("subtitle")
            post_data[uid]["author"] = post.get("author")
            post_data[uid]["content"] = mongodb.post_content.find_one({"post_uid": uid}).get(
                "content"
            )
            post_data[uid]["tags"] = post.get("tags")
            post_data[uid]["cover_url"] = post.get("cover_url")
            post_data[uid]["custom_slug"] = post.get("custom_slug")
            post_data[uid]["created_at"] = f"{post.get('created_at')}"
            post_data[uid]["last_updated"] = f"{post.get('last_updated')}"
            post_data[uid]["archived"] = post.get("archived")
            post_data[uid]["featured"] = post.get("featured")
            post_data[uid]["views"] = post.get("views")
            post_data[uid]["reads"] = post.get("reads")
        result["posts"] = post_data

        # export projects
        if user_info.gallery_enabled:
            project_data = {}
            projects_utils = ProjectsUtils(mongodb)
            projects = projects_utils.get_project_infos(current_user.username, archive="include")
            for project in projects:
                uid = project.get("project_uid")
                project_data[uid] = {}
                project_data[uid]["author"] = project.get("author")
                project_data[uid]["title"] = project.get("title")
                project_data[uid]["short_description"] = project.get("short_description")
                project_data[uid]["content"] = mongodb.project_content.find_one(
                    {"project_uid": uid}
                ).get("content")
                project_data[uid]["tags"] = project.get("tags")
                project_data[uid]["custom_slug"] = project.get("custom_slug")
                i = 0
                while project.get("images")[i]:
                    project_data[uid][f"image_{i}"] = (
                        project.get("images")[i][0],
                        project.get("images")[i][1],
                    )
                    i += 1
                project_data[uid]["created_at"] = f"{project.get('created_at')}"
                project_data[uid]["last_updated"] = f"{project.get('last_updated')}"
                project_data[uid]["archived"] = project.get("archived")
                project_data[uid]["views"] = project.get("views")
                project_data[uid]["reads"] = project.get("reads")
            result["projects"] = project_data

        # export changelogs
        if user_info.changelog_enabled:
            changelog_data = {}
            changelog_utils = ChangelogUtils(mongodb)
            changelogs = changelog_utils.get_changelogs(current_user.username)
            for changelog in changelogs:
                uid = changelog.get("changelog_uid")
                changelog_data[uid] = {}
                changelog_data[uid]["author"] = changelog.get("author")
                changelog_data[uid]["title"] = changelog.get("title")
                changelog_data[uid]["date"] = changelog.get("date")
                changelog_data[uid]["category"] = changelog.get("category")
                changelog_data[uid]["content"] = changelog.get("content")
                changelog_data[uid]["tags"] = changelog.get("tags")
                changelog_data[uid]["link"] = changelog.get("link")
                changelog_data[uid]["link_description"] = changelog.get("link_description")
                changelog_data[uid]["created_at"] = f"{changelog.get('created_at')}"
                changelog_data[uid]["last_updated"] = f"{changelog.get('last_updated')}"
                changelog_data[uid]["archived"] = changelog.get("archived")
            result["changelogs"] = changelog_data

    json_data = json.dumps(result, indent=4, ensure_ascii=False)

    # Create a virtual file to serve as a download
    buffer = io.BytesIO()
    buffer.write(json_data.encode("utf-8"))
    buffer.seek(0)

    # Serve the JSON file as an attachment
    file_name = f"{current_user.username}_data.json"
    return send_file(
        buffer, mimetype="application/json", as_attachment=True, download_name=file_name
    )

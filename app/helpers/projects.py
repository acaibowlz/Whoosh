from dataclasses import asdict
from datetime import datetime, timezone

from flask_login import current_user

from app.forms.projects import EditProjectForm, NewProjectForm
from app.helpers.utils import UIDGenerator, process_tags
from app.models.projects import ProjectContent, ProjectInfo
from app.mongo import Database


def process_form_images(form: NewProjectForm | EditProjectForm) -> list[tuple[str, str]]:
    """
    Process url and caption fields from the form and return them as a single list.

    If there are less than 5 images, the remaining slots will be filled with empty tuples.

    Returns:
        list[tuple[str, str]]: A list of tuples containing image URLs and captions.
    """
    images = []
    for i in range(5):
        url = form.data.get(f"url{i}", "")
        if url:
            caption = form.data.get(f"caption{i}", "")
            images.append((url, caption))
    while len(images) < 5:
        images.append(tuple())
    return images


class NewProjectSetup:
    """
    Handles the setup and creation of new projects.

    Use `create_project()` method to insert a new project into the database, which creates entries in `project_info` and `project_content` collections.
    """

    def __init__(self, project_uid_generator: UIDGenerator, db_handler: Database) -> None:
        self._project_uid = project_uid_generator.generate_project_uid()
        self._db_handler = db_handler

    def _create_project_info(self, form: NewProjectForm, author_name: str) -> dict:
        new_project_info = ProjectInfo(
            project_uid=self._project_uid,
            author=author_name,
            title=form.title.data,
            short_description=form.desc.data,
            tags=process_tags(form.tags.data),
            images=process_form_images(form),
            custom_slug=form.custom_slug.data,
        )
        return asdict(new_project_info)

    def _create_project_content(self, form: NewProjectForm, author_name: str) -> dict:
        new_project_content = ProjectContent(
            project_uid=self._project_uid,
            author=author_name,
            content=form.editor.data,
        )
        return asdict(new_project_content)

    def create_project(self, form: NewProjectForm, author_name: str) -> str:
        """
        Receives the form data and the author name,
        organizes them into `project_info` and `project_content` dataclasses, converts them to dictionaries,
        finally inserts them into the database.

        Returns:
            str: The UID of the newly created project.
        """
        new_project_info = self._create_project_info(form, author_name)
        new_project_content = self._create_project_content(form, author_name)

        self._db_handler.project_info.insert_one(new_project_info)
        self._db_handler.project_content.insert_one(new_project_content)
        return self._project_uid


def create_project(form: NewProjectForm, db_handler: Database) -> str:
    """
    Wraps `NewProjectSetup` setup class to create a new project in the database.

    Note that one project is stored as two separate documents: `project_info` and `project_content`.

    Returns:
        str: The UID of the newly created project.
    """
    uid_generator = UIDGenerator(db_handler=db_handler)
    new_project_setup = NewProjectSetup(project_uid_generator=uid_generator, db_handler=db_handler)
    new_project_uid = new_project_setup.create_project(author_name=current_user.username, form=form)
    return new_project_uid


class ProjectUpdateSetup:
    """
    Handles the update of existing projects in the database.

    Use `update_project()` method to update an existing project with new data.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler

    def update_project(self, project_uid: str, form: EditProjectForm) -> None:
        """
        Update an existing project.

        No return value.
        """
        updated_project_info = {
            "title": form.title.data,
            "short_description": form.desc.data,
            "tags": process_tags(form.tags.data),
            "custom_slug": form.custom_slug.data,
            "images": process_form_images(form),
            "last_updated": datetime.now(timezone.utc),
        }
        updated_project_content = {"content": form.editor.data}

        self._db_handler.project_info.update_values(
            filter={"project_uid": project_uid}, update=updated_project_info
        )
        self._db_handler.project_content.update_values(
            filter={"project_uid": project_uid}, update=updated_project_content
        )


def update_project(project_uid: str, form: EditProjectForm, db_handler: Database) -> None:
    """
    Wraps `ProjectUpdateSetup` setup class to update an existing project in the database.

    No return value.
    """
    project_update_setup = ProjectUpdateSetup(db_handler=db_handler)
    project_update_setup.update_project(project_uid=project_uid, form=form)


class ProjectsUtils:
    """
    Provides utility methods for handling projects.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler

    def get_all_projects_info(self, include_archive=False) -> list[dict]:
        """
        Retrieves all `project_info` documents from all users.

        This is mostly used to generate the sitemap.

        Archived projects are excluded by default, but can be included if needed.

        Returns:
            list[dict]: A list of dictionaries representing `project_info`.
        """
        if include_archive:
            result = self._db_handler.project_info.find({}).as_list()
        else:
            result = self._db_handler.project_info.find({"archived": False}).as_list()
        return result

    def get_project_infos(self, username: str, archive="include") -> list[dict]:
        """
        Retrieves all projects' `project_info` documents for the given user.

        By default, archived projects are excluded, but can be included or returned exclusively if needed.

        Possible values for `archive`: "exclude", "include", "only".

        Returns:
            list[dict]: A list of dictionaries representing `project_info`.
        """
        if archive == "include":
            result = (
                self._db_handler.project_info.find({"author": username})
                .sort("created_at", -1)
                .as_list()
            )
        elif archive == "exclude":
            result = (
                self._db_handler.project_info.find({"author": username, "archived": False})
                .sort("created_at", -1)
                .as_list()
            )
        elif archive == "only":
            result = (
                self._db_handler.project_info.find({"author": username, "archived": True})
                .sort("created_at", -1)
                .as_list()
            )
        return result

    def get_project_infos_with_pagination(
        self, username: str, page_number: int, projects_per_page: int
    ) -> list[dict]:
        """
        Retrieves all projects' `project_info` documents for the given user with pagination.
        The page number and the number of projects per page are therefore required.

        Note that archived projects are excluded.

        Returns:
            list[dict]: A list of dictionaries representing `project_info`.
        """
        if page_number == 1:
            result = (
                self._db_handler.project_info.find({"author": username, "archived": False})
                .sort("created_at", -1)
                .limit(projects_per_page)
                .as_list()
            )
        elif page_number > 1:
            result = (
                self._db_handler.project_info.find({"author": username, "archived": False})
                .sort("created_at", -1)
                .skip((page_number - 1) * projects_per_page)
                .limit(projects_per_page)
                .as_list()
            )
        return result

    def get_full_project(self, project_uid: str) -> dict:
        """
        Retrieves the full project data for a specific project UID.
        `project_info` and `project_content` are merged into one dictionary by `project_uid`.

        Returns:
            dict: A dictionary representing the full project data.
        """
        project = self._db_handler.project_info.find_one({"project_uid": project_uid})
        project_content = self._db_handler.project_content.find_one(
            {"project_uid": project_uid}
        ).get("content")
        project["content"] = project_content
        return project

    def read_increment(self, author: str, project_uid: str) -> None:
        """
        Increases the read count for a specific project.
        Note that the counts won't increase if the user is logged in and viewing their own blog.

        No return value.
        """
        if current_user.is_authenticated and current_user.username == author:
            return
        self._db_handler.project_info.make_increments(
            filter={"project_uid": project_uid}, increments={"reads": 1}
        )

    def view_increment(self, author: str, project_uid: str) -> None:
        """
        Increases the view count for a specific project.
        Note that the counts won't increase if the user is logged in and viewing their own blog.

        No return value.
        """
        if current_user.is_authenticated and current_user.username == author:
            return
        self._db_handler.project_info.make_increments(
            filter={"project_uid": project_uid}, increments={"views": 1}
        )

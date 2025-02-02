from dataclasses import asdict
from datetime import datetime, timezone

from flask_login import current_user

from app.forms.changelog import EditChangelogForm, NewChangelogForm
from app.helpers.utils import UIDGenerator, process_tags
from app.models.changelog import Changelog
from app.mongo import Database


class NewChangelogSetup:
    """
    Handles the setup and creation of new changelog entries.

    Use `create_changelog()` method to insert a new changelog entry into the database.
    """

    def __init__(self, changelog_uid_generator: UIDGenerator, db_handler: Database) -> None:
        self._changelog_uid = changelog_uid_generator.generate_changelog_uid()
        self._db_handler = db_handler

    def _create_changelog(self, form: NewChangelogForm, author_name: str) -> dict:
        new_changelog = Changelog(
            changelog_uid=self._changelog_uid,
            title=form.title.data,
            author=author_name,
            date=datetime.strptime(form.date.data, "%m/%d/%Y").replace(tzinfo=timezone.utc),
            category=form.category.data,
            content=form.editor.data,
            tags=process_tags(form.tags.data),
            link=form.link.data,
            link_description=form.link_description.data,
        )
        return asdict(new_changelog)

    def create_changelog(self, form: NewChangelogForm, author_name: str) -> str:
        """
        Creates and inserts a new changelog entry into the database.

        Returns:
            str: The UID of the newly created changelog.
        """
        new_changelog_entry = self._create_changelog(form, author_name)
        self._db_handler.changelog.insert_one(new_changelog_entry)
        return self._changelog_uid


def create_changelog(form: NewChangelogForm, db_handler: Database) -> str:
    """
    Wraps `NewChangelogSetup` setup class to create a new changelog entry in the database.

    Returns:
        str: The UID of the newly created changelog.
    """
    uid_generator = UIDGenerator(db_handler=db_handler)
    new_changelog_setup = NewChangelogSetup(
        changelog_uid_generator=uid_generator, db_handler=db_handler
    )
    new_changelog_uid = new_changelog_setup.create_changelog(
        form=form, author_name=current_user.username
    )
    return new_changelog_uid


class ChangelogUpdateSetup:
    """
    Handles the update of existing changelog entries in the database.

    Use `update_changelog()` method to update an existing changelog entry with new data.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler

    def update_changelog(self, changelog_uid: str, form: EditChangelogForm) -> None:
        """
        Updates an existing changelog entry with new data. No return value.
        """
        updated_changelog = {
            "title": form.title.data,
            "date": datetime.strptime(form.date.data, "%m/%d/%Y").replace(tzinfo=timezone.utc),
            "category": form.category.data,
            "content": form.editor.data,
            "tags": process_tags(form.tags.data),
            "link": form.link.data,
            "link_description": form.link_description.data,
            "last_updated": datetime.now(timezone.utc),
        }
        self._db_handler.changelog.update_values(
            filter={"changelog_uid": changelog_uid}, update=updated_changelog
        )


def update_changelog(changelog_uid: str, form: EditChangelogForm, db_handler: Database) -> None:
    """
    Wraps `ChangelogUpdateSetup` setup class to update an existing changelog entry in the database.

    No return value.
    """
    changelog_update_setup = ChangelogUpdateSetup(db_handler=db_handler)
    changelog_update_setup.update_changelog(changelog_uid=changelog_uid, form=form)


class ChangelogUtils:
    """
    Provides utility methods for handling changelogs.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler

    def get_changelogs(self, username: str, by_date: bool = False) -> list[dict]:
        """
        Retrieves all non-archived changelog entries for the given user.

        Entries are sorted either by `date` or `created_at` field. Default is `created_at`.

        Returns:
            list[dict]: A list of dictionaries representing `changelog`.
        """
        if by_date:
            result = (
                self._db_handler.changelog.find({"author": username, "archived": False})
                .sort("date", -1)
                .as_list()
            )
        else:
            result = (
                self._db_handler.changelog.find({"author": username, "archived": False})
                .sort("created_at", -1)
                .as_list()
            )
        return result

    def get_archived_changelogs(self, username: str) -> list[dict]:
        """
        Retrieves all archived changelog entries for the given user.

        Entries are sorted by `created_at` timestamps.

        Returns:
            list[dict]: A list of dictionaries representing `changelog`.
        """
        result = (
            self._db_handler.changelog.find({"author": username, "archived": True})
            .sort("created_at", -1)
            .as_list()
        )
        return result

    def get_changelogs_with_pagination(
        self, username: str, page_number: int, changelogs_per_page: int
    ) -> list[dict]:
        """
        Retrieves all non-archived changelog entries for the given user with pagination.
        The page number and the number of changelogs per page are therefore required.

        Entries are sorted by `created_at` timestamps.

        Returns:
            list[dict]: A list of dictionaries representing `changelog`.
        """
        if page_number == 1:
            result = (
                self._db_handler.changelog.find({"author": username, "archived": False})
                .sort("created_at", -1)
                .limit(changelogs_per_page)
                .as_list()
            )
        elif page_number > 1:
            result = (
                self._db_handler.changelog.find({"author": username, "archived": False})
                .sort("created_at", -1)
                .skip((page_number - 1) * changelogs_per_page)
                .limit(changelogs_per_page)
                .as_list()
            )
        return result

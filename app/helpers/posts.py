from dataclasses import asdict
from datetime import datetime, timezone

from flask_login import current_user

from app.forms.posts import EditPostForm, NewPostForm
from app.helpers.utils import UIDGenerator, process_tags
from app.models.posts import PostContent, PostInfo
from app.mongo import Database


class NewPostSetup:
    """
    Handles the setup and creation of new posts.

    Use `create_post()` method to insert a new post the database, which creates entries in `post_info` and `post_content` collections.

    User's tag counts are also incremented when a new post is created.
    """

    def __init__(self, post_uid_generator: UIDGenerator, db_handler: Database) -> None:
        self._post_uid = post_uid_generator.generate_post_uid()
        self._db_handler = db_handler

    def _create_post_info(self, form: NewPostForm, author_name: str) -> dict:
        new_post_info = PostInfo(
            post_uid=self._post_uid,
            title=form.title.data,
            subtitle=form.subtitle.data,
            author=author_name,
            tags=process_tags(form.tags.data),
            custom_slug=form.custom_slug.data,
            cover_url=form.cover_url.data,
        )
        return asdict(new_post_info)

    def _create_post_content(self, form: NewPostForm, author_name: str) -> dict:
        new_post_content = PostContent(
            post_uid=self._post_uid, author=author_name, content=form.editor.data
        )
        return asdict(new_post_content)

    def _increment_tags_for_user(self, new_post_info: dict) -> None:
        username = new_post_info.get("author")
        tags = new_post_info.get("tags")
        tags_increments = {f"tags.{tag}": 1 for tag in tags}
        self._db_handler.user_info.make_increments(
            filter={"username": username}, increments=tags_increments, upsert=True
        )

    def create_post(self, author_name: str, form: NewPostForm) -> str:
        """
        Receives the form data and the author name,
        organizes them into `post_info` and `post_content` dataclasses, converts them to dictionaries,
        finally inserts them into the database.

        User's tag counts are also incremented when a new post is created.

        Returns:
            str: The UID of the newly created post.
        """
        new_post_info = self._create_post_info(form=form, author_name=author_name)
        new_post_content = self._create_post_content(form=form, author_name=author_name)

        self._db_handler.post_info.insert_one(new_post_info)
        self._db_handler.post_content.insert_one(new_post_content)
        self._increment_tags_for_user(new_post_info)

        return self._post_uid


def create_post(form: NewPostForm, db_handler: Database) -> str:
    """
    Wraps `NewPostSetup` setup class to create a new post in the database.

    Note that one post is stored as two separate documents: `post_info` and `post_content`.

    User's tag counts are also incremented when a new post is created.

    Returns:
        str: The UID of the newly created post.
    """
    uid_generator = UIDGenerator(db_handler=db_handler)
    new_post_setup = NewPostSetup(post_uid_generator=uid_generator, db_handler=db_handler)
    new_post_uid = new_post_setup.create_post(author_name=current_user.username, form=form)
    return new_post_uid


class PostUpdateSetup:
    """
    Handles the update of existing posts in the database.

    Use `update_post()` method to update an existing post with new data.

    User's tag counts are also updated when a post is updated.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler

    def _update_tags_for_user(self, post_uid: str, new_tags: dict) -> None:
        post_info = self._db_handler.post_info.find_one({"post_uid": post_uid})
        username = post_info.get("author")
        old_tags = post_info.get("tags")

        tags_reduction = {f"tags.{tag}": -1 for tag in old_tags}
        self._db_handler.user_info.make_increments(
            filter={"username": username}, increments=tags_reduction
        )
        tags_increment = {f"tags.{tag}": 1 for tag in new_tags}
        self._db_handler.user_info.make_increments(
            filter={"username": username}, increments=tags_increment, upsert=True
        )

    def update_post(self, post_uid: str, form: EditPostForm) -> None:
        """
        Update an existing post in the database. No return value.

        User's tag counts are also updated when a post is updated.

        No return value.
        """
        updated_post_info = {
            "title": form.title.data,
            "subtitle": form.subtitle.data,
            "tags": process_tags(form.tags.data),
            "cover_url": form.cover_url.data,
            "custom_slug": form.custom_slug.data,
            "last_updated": datetime.now(timezone.utc),
        }
        updated_post_content = {"content": form.editor.data}

        self._update_tags_for_user(post_uid, updated_post_info.get("tags"))
        self._db_handler.post_info.update_values(
            filter={"post_uid": post_uid}, update=updated_post_info
        )
        self._db_handler.post_content.update_values(
            filter={"post_uid": post_uid}, update=updated_post_content
        )


def update_post(post_uid: str, form: EditPostForm, db_handler: Database) -> None:
    """
    Wraps `PostUpdateSetup` setup class to update an existing post in the database.

    User's tag counts are also updated when a post is updated.

    No return value.
    """
    post_update_setup = PostUpdateSetup(db_handler=db_handler)
    post_update_setup.update_post(post_uid=post_uid, form=form)


class PostUtils:
    """
    Provides utility methods for handling posts.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler

    def get_all_posts_info(self, include_archive=False) -> list[dict]:
        """
        Retrieves all `post_info` documents from all users.

        This is mostly used to generate the sitemap.

        Archived posts are excluded by default, but can be included if needed.

        Returns:
            list[dict]: A list of dictionaries representing `post_info`.
        """
        if include_archive:
            result = self._db_handler.post_info.find({}).as_list()
        else:
            result = self._db_handler.post_info.find({"archived": False}).as_list()
        return result

    def get_featured_posts_info(self, username: str) -> list[dict]:
        """
        Retrieves all featured posts' `post_info` documents for the given user.

        Note that archived posts are excluded.

        Returns:
            list[dict]: A list of dictionaries representing `post_info`.
        """
        result = (
            self._db_handler.post_info.find(
                {"author": username, "featured": True, "archived": False}
            )
            .sort("created_at", -1)
            .limit(10)
            .as_list()
        )
        return result

    def get_post_infos(self, username: str, archive="exclude") -> list[dict]:
        """
        Retrieves all posts' `post_info` documents for the given user.

        By default, archived posts are excluded, but can be included or returned exclusively if needed.

        Possible values for `archive`: "exclude", "include", "only".

        Returns:
            list[dict]: A list of dictionaries representing `post_info`.
        """
        if archive == "exclude":
            result = (
                self._db_handler.post_info.find({"author": username, "archived": False})
                .sort("created_at", -1)
                .as_list()
            )
        elif archive == "include":
            result = (
                self._db_handler.post_info.find({"author": username})
                .sort("created_at", -1)
                .as_list()
            )
        elif archive == "only":
            result = (
                self._db_handler.post_info.find({"author": username, "archived": True})
                .sort("created_at", -1)
                .as_list()
            )
        return result

    def get_post_infos_with_pagination(
        self, username: str, page_number: int, posts_per_page: int
    ) -> list[dict]:
        """
        Retrieves all posts' `post_info` documents for the given user with pagination.
        The page number and the number of posts per page are therefore required.

        Note that archived posts are excluded.

        Returns:
            list[dict]: A list of dictionaries representing `post_info`.
        """
        if page_number == 1:
            result = (
                self._db_handler.post_info.find({"author": username, "archived": False})
                .sort("created_at", -1)
                .limit(posts_per_page)
                .as_list()
            )
        elif page_number > 1:
            result = (
                self._db_handler.post_info.find({"author": username, "archived": False})
                .sort("created_at", -1)
                .skip((page_number - 1) * posts_per_page)
                .limit(posts_per_page)
                .as_list()
            )
        return result

    def get_full_post(self, post_uid: str) -> dict:
        """
        Retrieves the full post data for a specific post UID.
        `post_info` and `post_content` are merged into one dictionary by `post_uid`.

        Returns:
            dict: A dictionary representing the full post data.
        """
        post = self._db_handler.post_info.find_one({"post_uid": post_uid})
        post_content = self._db_handler.post_content.find_one({"post_uid": post_uid}).get("content")
        post["content"] = post_content
        return post

    def read_increment(self, author: str, post_uid: str) -> None:
        """
        Increases the read count for a specific post.
        Note that the counts won't increase if the user is logged in and viewing their own blog.

        No return value.
        """
        if current_user.is_authenticated and current_user.username == author:
            return
        self._db_handler.post_info.make_increments(
            filter={"post_uid": post_uid}, increments={"reads": 1}
        )

    def view_increment(self, author: str, post_uid: str) -> None:
        """
        Increases the view count for a specific post.
        Note that the counts won't increase if the user is logged in and viewing their own blog.

        No return value.
        """
        if current_user.is_authenticated and current_user.username == author:
            return

        self._db_handler.post_info.make_increments(
            filter={"post_uid": post_uid}, increments={"views": 1}
        )

from dataclasses import asdict

import bcrypt
from flask_login import current_user

from app.forms.users import SignUpForm
from app.logging import Logger
from app.models.users import UserAbout, UserCreds, UserInfo
from app.mongo import Database


class NewUserSetup:
    """
    Handles the setup and creation of new users.

    Use `create_user()` method to insert a new user into the database, which creates entries in `user_creds`, `user_info`, and `user_about` collections.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler

    def _create_user_creds(self, username: str, email: str, hashed_password: str) -> dict:
        new_user_creds = UserCreds(username=username, email=email, password=hashed_password)
        return asdict(new_user_creds)

    def _create_user_info(self, username: str, email: str, blogname: str) -> dict:
        new_user_info = UserInfo(username=username, email=email, blogname=blogname)
        return asdict(new_user_info)

    def _create_user_about(self, username: str) -> dict:
        new_user_about = UserAbout(username=username)
        return asdict(new_user_about)

    @staticmethod
    def _hash_password(password: str) -> str:
        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12))
        return hashed_pw.decode("utf-8")

    def create_user(self, form: SignUpForm) -> str:
        """
        Receives the user registration form data,
        organizes it into `user_creds`, `user_info`, and `user_about` dataclasses,
        which will initialize the necessary fields for a new user,
        converts them to dictionaries,
        finally inserts them into the database.

        Returns:
            str: The username of the newly created user.
        """
        hashed_pw = self._hash_password(form.password.data)
        new_user_creds = self._create_user_creds(form.username.data, form.email.data, hashed_pw)
        new_user_info = self._create_user_info(
            form.username.data,
            form.email.data,
            form.blogname.data,
        )
        new_user_about = self._create_user_about(form.username.data)

        self._db_handler.user_creds.insert_one(new_user_creds)
        self._db_handler.user_info.insert_one(new_user_info)
        self._db_handler.user_about.insert_one(new_user_about)

        return form.username.data


class UserDeletionSetup:
    """
    Handles the setup and execution of user deletion.
    """

    def __init__(self, username: str, db_handler: Database, logger: Logger) -> None:
        self._user_to_be_deleted = username
        self._db_handler = db_handler
        self._logger = logger

    def _get_posts_uid_by_user(self) -> list[str]:
        posts = self._db_handler.post_info.find({"author": self._user_to_be_deleted})
        return [post.get("post_uid") for post in posts]

    def _remove_all_posts(self) -> None:
        self._db_handler.post_info.delete_many({"author": self._user_to_be_deleted})
        self._db_handler.post_content.delete_many({"author": self._user_to_be_deleted})
        self._logger.debug(f"Deleted all posts written by user {self._user_to_be_deleted}.")

    def _remove_all_related_comments(self, post_uids: list[str]) -> None:
        for post_uid in post_uids:
            self._db_handler.comment.delete_many({"post_uid": post_uid})
        self._logger.debug(f"Deleted comments under posts by user {self._user_to_be_deleted}.")

    def _remove_all_user_data(self) -> None:
        self._db_handler.user_creds.delete_one({"username": self._user_to_be_deleted})
        self._db_handler.user_info.delete_one({"username": self._user_to_be_deleted})
        self._db_handler.user_about.delete_one({"username": self._user_to_be_deleted})
        self._logger.debug(f"Deleted user information for user {self._user_to_be_deleted}.")

    def start_deletion_process(self) -> None:
        """
        Start the user deletion process, which includes:
        - Removing all posts authored by the user.
        - Removing all comments related to the user's posts.
        - Removing all user data.

        No return value.
        """
        posts_uid = self._get_posts_uid_by_user()
        self._remove_all_posts()
        self._remove_all_related_comments(posts_uid)
        self._remove_all_user_data()


class UserUtils:
    """
    Provides utility methods for handling users.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler

    def get_all_username(self) -> list[str]:
        """
        Retrieves all usernames.

        This is mostly used to generate the sitemap.

        Returns:
            list[dict]: A list of usernames
        """
        all_user_info = self._db_handler.user_info.find({})
        return [user_info.get("username") for user_info in all_user_info]

    def get_all_username_gallery_enabled(self) -> list[str]:
        """
        Retrieves all usernames with gallery enabled.

        This is mostly used to generate the sitemap.

        Returns:
            list[str]: A list of usernames with gallery enabled.
        """
        all_user_info = self._db_handler.user_info.find({"gallery_enabled": True})
        return [user_info.get("username") for user_info in all_user_info]

    def get_all_username_changelog_enabled(self) -> list[str]:
        """
        Retrieves all usernames with changelog enabled.

        This is mostly used to generate the sitemap.

        Returns:
            list[str]: A list of usernames with changelog enabled.
        """
        all_user_info = self._db_handler.user_info.find({"changelog_enabled": True})
        return [user_info.get("username") for user_info in all_user_info]

    def get_user_info(self, username: str) -> UserInfo:
        """
        Retrieve `user_info` document by username and return it as a `UserInfo` object.

        Returns:
            UserInfo: The user information.
        """
        user_info = self._db_handler.user_info.find_one({"username": username})
        if user_info is None:
            return None
        user_info.pop("_id", None)
        return UserInfo(**user_info)

    def get_user_about(self, username: str) -> UserAbout:
        """
        Retrieve `user_about` document by username and return it as a `UserAbout` object.

        Returns:
            UserAbout: The user about information.
        """
        user_about = self._db_handler.user_about.find_one({"username": username})
        if user_about is None:
            return None
        user_about.pop("_id", None)
        return UserAbout(**user_about)

    def get_user_creds(self, email: str) -> UserCreds:
        """
        Retrieve `user_creds` document by email and return it as a `UserCreds` object.

        Returns:
            UserCreds: The user credentials.
        """
        user_creds = self._db_handler.user_creds.find_one({"email": email})
        if user_creds is None:
            return None
        user_creds.pop("_id", None)
        return UserCreds(**user_creds)

    def delete_user(self, username: str, logger: Logger) -> None:
        """
        Wraps `UserDeletionSetup` setup class to delete a user from the database.

        No return value.
        """
        user_deletion = UserDeletionSetup(
            username=username, db_handler=self._db_handler, logger=logger
        )
        user_deletion.start_deletion_process()

    def create_user(self, form: SignUpForm) -> str:
        """
        Wraps `NewUserSetup` setup class to create a new user in the database.

        Returns:
            str: The username of the newly created user.
        """
        user_registration = NewUserSetup(self._db_handler)
        return user_registration.create_user(form)

    def total_view_increment(self, username: str) -> None:
        """
        Increases the total view count for a user.
        Now the counts won't increase if the user is logged in and viewing their own blog.

        No return value.
        """
        if current_user.is_authenticated and current_user.username == username:
            return
        self._db_handler.user_info.make_increments(
            filter={"username": username}, increments={"total_views": 1}
        )

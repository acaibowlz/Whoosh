from dataclasses import asdict

import requests
from flask import Request, request
from flask_login import current_user

from app.config import RECAPTCHA_SECRET
from app.forms.comments import CommentForm
from app.helpers.utils import UIDGenerator
from app.models.comments import AnonymousComment, RegisteredComment
from app.mongo import Database


class NewCommentSetup:
    """
    Handles the setup and creation of new comments.

    Use `create_comment()` method to insert a new comment into the database.

    Note that commects are created only if the Recaptcha verification is successful.
    """

    def __init__(self, comment_uid_generator: UIDGenerator, db_handler: Database) -> None:
        self._db_handler = db_handler
        self._comment_uid = comment_uid_generator.generate_comment_uid()

    @staticmethod
    def _recaptcha_verified(request: Request) -> bool:
        """
        Verifies the Recaptcha response to ensure it's valid.

        Returns:
            bool: True if Recaptcha verification is successful, otherwise False.
        """
        token = request.form.get("g-recaptcha-response")
        payload = {"secret": RECAPTCHA_SECRET, "response": token}
        resp = requests.post("https://www.google.com/recaptcha/api/siteverify", params=payload)
        resp = resp.json()
        return resp.get("success", False)

    def create_comment(self, post_uid: str, form: CommentForm) -> str:
        """
        Creates and insert a new comment associating to the given post into the database.

        Returns the UID of the newly created comment.
        """
        if not self._recaptcha_verified(request):
            return

        if current_user.is_authenticated:
            new_comment = RegisteredComment(
                name=current_user.username,
                email=current_user.email,
                post_uid=post_uid,
                comment_uid=self._comment_uid,
                comment=form.data.get("comment"),
            )
        else:
            new_comment = AnonymousComment(
                name=f'{form.data.get("name")} (Visitor)',
                email=form.data.get("email"),
                post_uid=post_uid,
                comment_uid=self._comment_uid,
                comment=form.data.get("comment"),
            )

        new_comment_data = asdict(new_comment)
        self._db_handler.comment.insert_one(new_comment_data)
        return self._comment_uid


def create_comment(post_uid: str, form: CommentForm, db_handler: Database) -> str:
    """
    Wraps `NewCommentSetup` setup class to create a new comment in the database.

    Returns the UID of the newly created comment.
    """
    uid_generator = UIDGenerator(db_handler=db_handler)
    comment_setup = NewCommentSetup(comment_uid_generator=uid_generator, db_handler=db_handler)
    new_comment_uid = comment_setup.create_comment(post_uid=post_uid, form=form)
    return new_comment_uid


class CommentUtils:
    """
    Provides utility methods for handling comments.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler

    def get_comments_by_post_uid(self, post_uid: str) -> list[dict]:
        """
        Retrieves all comments associated with a specific post UID.

        Returns:
            list[dict]: A list of dictionaries representing `comment`.
        """
        result = (
            self._db_handler.comment.find({"post_uid": post_uid}).sort("created_at", 1).as_list()
        )
        return result

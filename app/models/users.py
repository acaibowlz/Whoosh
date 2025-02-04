import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Tuple

from flask import url_for
from flask_login import UserMixin


def select_profile_img() -> str:
    """
    Returns a random profile image url.

    Available options: img/profile{0-4}.png
    """
    idx = random.choice(range(5))
    return url_for("static", filename=f"img/profile{idx}.png")


@dataclass
class UserInfo(UserMixin):
    """
    This `UserInfo` inherits from `UserMixin` and is used in the `user_loader()` callback function for `flask_login`.

    Data required to create a new `UserInfo`:
    - `username`
    - `email`
    - `blogname`

    Fields that are automatically generated:
    - `profile_img_url`
    - `cover_url`
    - `created_at`
    - `short_bio`
    - `social_links`
    - `gallery_enabled`
    - `changelog_enabled`
    - `total_views`
    - `tags`
    """

    username: str
    email: str
    blogname: str
    profile_img_url: str = ""
    cover_url: str = ""
    created_at: Optional[datetime] = None
    short_bio: str = ""
    social_links: list[Tuple[str, str]] = None
    gallery_enabled: bool = False
    changelog_enabled: bool = False
    total_views: int = 0
    tags: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if not self.profile_img_url:
            self.profile_img_url = select_profile_img()
        if not self.cover_url:
            self.cover_url = url_for("static", filename="img/default-cover.jpg")
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.social_links is None:
            self.social_links = [[]] * 5

    def get_id(self) -> str:
        """Overrides the get_id method from UserMixin to return the username.

        Returns:
            str: Username of the user.
        """
        return self.username


@dataclass
class UserCreds:
    """
    Data required to create a new `UserCreds`:
    - `username`
    - `email`
    - `password` -> should be hashed using `_hash_password()` in `create_user()`
    """

    username: str
    email: str
    password: str


@dataclass
class UserAbout:
    """
    Data required to create a new `UserAbout`:
    - `username`
    - `about`
    """

    username: str
    about: str = ""

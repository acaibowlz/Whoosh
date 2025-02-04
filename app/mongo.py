from contextlib import contextmanager
from typing import Any, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from typing_extensions import Self

from app.config import MONGO_URL


class ExtendedCollection:
    """
    This class extends the `Collection` class from `pymongo` and provides additional methods for working with MongoDB collections.

    Modified or new methods:
    - `find`
    - `find_one`
    - `exists`
    - `update_values`
    - `make_increments`

    Other methods inherited and unchanged:
    - `insert_one`
    - `count_documents`
    - `delete_one`
    - `delete_many`
    - `update_one`
    """

    def __init__(self, collection: Collection) -> None:
        self._col = collection

    def insert_one(self, document: dict[str, Any]) -> None:
        """
        See `Collection.insert_one()` for information.
        """
        self._col.insert_one(document)

    def count_documents(self, filter: dict[str, Any]) -> int:
        """
        See `Collection.count_documents()` for information.
        """
        return self._col.count_documents(filter)

    def delete_one(self, filter: dict[str, Any]) -> None:
        """
        See `Collection.delete_one()` for information.
        """
        self._col.delete_one(filter)

    def delete_many(self, filter: dict[str, Any]) -> None:
        """
        See `Collection.delete_many()` for information.
        """
        self._col.delete_many(filter)

    def update_one(
        self, filter: dict[str, Any], update: dict[str, Any], upsert: bool = False
    ) -> None:
        """
        See `Collection.update_one()` for information.
        """
        self._col.update_one(filter, update, upsert=upsert)

    def find(self, filter: dict[str, Any]) -> "ExtendedCursor":
        """
        See `Collection.find()` for information.

        Note that this method returns a `ExtendedCursor` object instead of a `Cursor` object.
        """
        return ExtendedCursor(self._col, filter)

    def find_one(self, filter: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        See `Collection.find_one()` for information.

        Note that this method returns a dictionary instead of a `Document` object.
        """
        result = self._col.find_one(filter)
        return dict(result) if result else None

    def exists(self, key: str, value: Any) -> bool:
        """
        Check if a document with a certain value of a key exists in the collection.
        """
        return self.find_one({key: value}) is not None

    def update_values(self, filter: dict[str, Any], update: dict[str, Any]) -> None:
        """
        This function is a wrapper around `update_one()` to update fields in a document using the $set operator.

        Use `filter` to filter the documents to update, and `update` to overwrite the fields with new values.

        Example usage:
        ```
        update_values(filter={"_id": 123}, update={"name": "Alice", "age": 25})
        ```
        """
        self.update_one(filter=filter, update={"$set": update})

    def make_increments(
        self, filter: dict[str, Any], increments: dict[str, int], upsert: bool = False
    ) -> None:
        """
        This function is a wrapper around `update_one()` to increment fields in a document using the $inc operator.

        Use `filter` to filter the documents to update, and `increments` to specify the fields to increment.

        Example usage:
        ```
        make_increments(filter={"_id": 123}, increments={"views": 1, "likes": 1})
        ```
        """
        self.update_one(filter=filter, update={"$inc": increments}, upsert=upsert)


class ExtendedCursor(Cursor):
    """
    Basically just `Cursor` from `pymongo` with a new method `as_list()` to convert the cursor to a list of documents.

    It can also be used to chain multiple cursor operations together.

    Other methods inherited:
    - `sort`
    - `skip`
    - `limit`
    """

    def __init__(
        self, collection: ExtendedCollection, filter: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(collection, filter)

    def sort(self, key_or_list: Any, direction: int) -> Self:
        """
        See `Cursor.sort()` for information.
        """
        super().sort(key_or_list, direction)
        return self

    def skip(self, skip: int) -> Self:
        """
        See `Cursor.skip()` for information.
        """
        super().skip(skip)
        return self

    def limit(self, limit: int) -> Self:
        """
        See `Cursor.limit()` for information.
        """
        super().limit(limit)
        return self

    def as_list(self) -> list[dict[str, Any]]:
        """
        Convert the cursor to a list of documents.
        """
        self.__check_okay_to_chain()
        return list(self)

    def __check_okay_to_chain(self) -> None:
        """
        Check if it is okay to chain more options onto this cursor.
        """
        return super(ExtendedCursor, self)._Cursor__check_okay_to_chain()


class Database:
    """
    This class combined all mongo databse in this project, and serves all the collections as properties.

    Note that the collections are stored as the `ExtendedCollection` class, which provides additional methods for working with MongoDB collections.
    """

    def __init__(self, client: MongoClient) -> None:
        self._client = client
        users_db = client["users"]
        posts_db = client["posts"]
        comments_db = client["comments"]
        project_db = client["projects"]
        changelog_db = client["changelog"]

        self._user_info = ExtendedCollection(users_db["user-info"])
        self._user_creds = ExtendedCollection(users_db["user-creds"])
        self._user_about = ExtendedCollection(users_db["user-about"])
        self._post_info = ExtendedCollection(posts_db["posts-info"])
        self._post_content = ExtendedCollection(posts_db["posts-content"])
        self._comment = ExtendedCollection(comments_db["comment"])
        self._project_info = ExtendedCollection(project_db["project-info"])
        self._project_content = ExtendedCollection(project_db["project-content"])
        self._changelog = ExtendedCollection(changelog_db["changelog-entry"])

    @property
    def client(self) -> MongoClient:
        return self._client

    @property
    def user_info(self) -> ExtendedCollection:
        return self._user_info

    @property
    def user_creds(self) -> ExtendedCollection:
        return self._user_creds

    @property
    def user_about(self) -> ExtendedCollection:
        return self._user_about

    @property
    def post_info(self) -> ExtendedCollection:
        return self._post_info

    @property
    def post_content(self) -> ExtendedCollection:
        return self._post_content

    @property
    def comment(self) -> ExtendedCollection:
        return self._comment

    @property
    def project_info(self) -> ExtendedCollection:
        return self._project_info

    @property
    def project_content(self) -> ExtendedCollection:
        return self._project_content

    @property
    def changelog(self) -> ExtendedCollection:
        return self._changelog


@contextmanager
def mongo_connection():
    """
    Context manager for handling MongoDB connections.
    """
    client = MongoClient(MONGO_URL, maxPoolSize=10, minPoolSize=1)
    try:
        mongodb = Database(client=client)
        yield mongodb
    finally:
        client.close()

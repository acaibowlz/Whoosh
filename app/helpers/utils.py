import random
import string
from math import ceil

from bs4 import BeautifulSoup
from flask import abort
from markdown import Markdown
from typing_extensions import Self

from app.mongo import Database


class UIDGenerator:
    """
    A generic class to generate UID for new entries in the database.

    It checks the database to ensure the generated UID is unique before returning it.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler

    def generate_comment_uid(self) -> str:
        """
        Looks into the comment database and generates an UID for a new comment.

        Returns:
            str: A unique comment UID string.
        """
        alphabet = string.ascii_lowercase + string.digits
        while True:
            comment_uid = "".join(random.choices(alphabet, k=8))
            if not self._db_handler.comment.exists("comment_uid", comment_uid):
                return comment_uid

    def generate_post_uid(self) -> str:
        """
        Looks into the post database and generates an UID for a new post.

        Returns:
            str: A unique post UID string.
        """
        alphabet = string.ascii_lowercase + string.digits
        while True:
            post_uid = "".join(random.choices(alphabet, k=8))
            if not self._db_handler.post_info.exists("post_uid", post_uid):
                return post_uid

    def generate_project_uid(self) -> str:
        """
        Looks into the project database and generates an UID for a new project.

        Returns:
            str: A unique project UID string.
        """
        alphabet = string.ascii_lowercase + string.digits
        while True:
            project_uid = "".join(random.choices(alphabet, k=8))
            if not self._db_handler.project_info.exists("project_uid", project_uid):
                return project_uid

    def generate_changelog_uid(self) -> str:
        """
        Looks into the changelog database and generates an UID for a new changelog entry.

        Returns:
            str: A unique changelog UID string.
        """
        alphabet = string.ascii_lowercase + string.digits
        while True:
            changelog_uid = "".join(random.choices(alphabet, k=8))
            if not self._db_handler.changelog.exists("changelog_uid", changelog_uid):
                return changelog_uid


class HTMLFormatter:
    """
    A collection of methods to add bootstrap classes of modifications to HTML content.

    Modifications can be applied through chained method calls.

    This formatter is meant for styling blog posts, about page, and project pages.

    It takes in an HTML string. Once the modifications are done, use the `to_string()` method to get the formatted HTML as string.
    """

    def __init__(self, html: str) -> None:
        self._soup = BeautifulSoup(html, "html.parser")

    def add_padding(self) -> Self:
        """
        Append `py-1` class to HTML elements except 'figure' and 'img'.

        Returns:
            HTMLFormatter: The formatter instance.
        """
        blocks = self._soup.find_all(lambda tag: tag.name not in ["figure", "img"], recursive=False)
        for block in blocks:
            current_class = block.get("class", [])
            current_class.append("py-1")
            block["class"] = current_class

        return self

    def change_headings(self) -> Self:
        """
        Changes the heading levels and styles.

        Returns:
            HTMLFormatter: The formatter instance.
        """
        small_headings = self._soup.find_all("h3")
        for heading in small_headings:
            heading.name = "h6"
            heading["class"] = "pt-2 pb-1 fw-bold"

        medium_headings = self._soup.find_all("h2")
        for heading in medium_headings:
            heading.name = "h5"
            heading["class"] = "pt-3 pb-1 fw-bold"

        big_headings = self._soup.find_all("h1")
        for heading in big_headings:
            heading.name = "h2"
            heading["class"] = "pt-4 pb-1 fw-bold"

        return self

    def modify_figure(self) -> Self:
        """
        Modify figure and image elements to center them and adjust their sizes.

        Returns:
            HTMLFormatter: The formatter instance.
        """
        figures = self._soup.find_all("figure")
        for figure in figures:
            current_class = figure.get("class", [])
            current_class.extend(["figure", "w-100", "mx-auto"])
            figure["class"] = current_class

        imgs = self._soup.find_all(["img"])
        for img in imgs:
            img_src = img["src"]
            img["src"] = ""
            img["data-src"] = img_src
            current_class = img.get("class", [])
            current_class.extend(["lazyload", "figure-img", "img-fluid", "rounded", "w-100"])
            img["class"] = current_class

        captions = self._soup.find_all(["figcaption"])
        for caption in captions:
            current_class = caption.get("class", [])
            current_class.extend(["figure-caption", "text-center", "py-2"])
            caption["class"] = current_class

        return self

    def modify_hyperlink(self) -> Self:
        """
        Apply color theme to hyperlinks.

        Returns:
            HTMLFormatter: The formatter instance.
        """
        links = self._soup.find_all("a")
        for link in links:
            current_class = link.get("class", [])
            current_class.extend(["in-content-link"])
            link["class"] = current_class

        return self

    def to_string(self) -> str:
        """
        Convert the formatted HTML back to a string.

        Returns:
            str: The formatted HTML string.
        """
        return str(self._soup)


def convert_post_content(content: str) -> str:
    """
    Convert the text stored as Markdown format to HTML string and add additional styling tp look better as a blog post.

    Returns:
        str: The converted HTML content.
    """
    md = Markdown(extensions=["markdown_captions", "fenced_code", "footnotes", "toc"])
    html = md.convert("[TOC]\r\n\r\n" + content)
    formatter = HTMLFormatter(html)
    html = formatter.add_padding().change_headings().modify_figure().modify_hyperlink().to_string()

    return html


def convert_about(about: str) -> str:
    """
    Convert the text stored as Markdown format to HTML string and add additional styling to look better on the about page.

    Returns:
        str: The converted HTML content.
    """
    md = Markdown(extensions=["markdown_captions", "fenced_code"])
    html = md.convert(about)
    formatter = HTMLFormatter(html)
    html = formatter.add_padding().change_headings().modify_figure().to_string()

    return html


def convert_project_content(content: str) -> str:
    """
    Convert the text stored as Markdown format to HTML string and add additional styling to look better on the project page.

    Returns:
        str: The converted HTML content.
    """
    md = Markdown(extensions=["markdown_captions", "fenced_code", "footnotes", "toc"])
    html = md.convert(content)
    formatter = HTMLFormatter(html)
    html = formatter.add_padding().change_headings().modify_figure().to_string()

    return html


def convert_changelog_content(content: str) -> str:
    """
    Convert the text stored as Markdown format to HTML string and add additional styling to look better on the changelog page.

    Returns:
        str: The converted HTML content.
    """
    md = Markdown(extensions=["markdown_captions", "fenced_code", "footnotes"])
    html = md.convert(content)
    formatter = HTMLFormatter(html)
    html = formatter.add_padding().change_headings().modify_figure().to_string()

    return html


class Paging:
    """
    A class to handle pagination for the user's posts, projects, and changelogs.

    Use `setup()` method to set up the pagination, then pass the instance to the template to decide if the prev/next button is allowed.
    """

    def __init__(self, db_handler: Database) -> None:
        self._db_handler = db_handler
        self._has_setup = False
        self._allow_previous_page = None
        self._allow_next_page = None
        self._current_page = None

    def setup(self, username: str, content: str, current_page: int, num_per_page: int) -> Self:
        """
        Setting up the pagination for the corresponding content.
        Possible content options: "post", "project", and "changelog".

        This method will directly show a 404 error if the current page is not a legal page number (i.e., too large or too small).

        Otherwise, it gives two properties `is_previous_page_allowed` and `is_next_page_allowed` for templates to decide if the prev/next button is allowed.
        """
        self._has_setup = True
        self._allow_previous_page = False
        self._allow_next_page = False
        self._current_page = current_page

        # set up for pagination
        # factory mode
        if content == "post":
            not_archived_count = self._db_handler.post_info.count_documents(
                {"author": username, "archived": False}
            )
        elif content == "project":
            not_archived_count = self._db_handler.project_info.count_documents(
                {"author": username, "archived": False}
            )
        elif content == "changelog":
            not_archived_count = self._db_handler.changelog.count_documents(
                {"author": username, "archived": False}
            )
        else:
            raise Exception("Unknown content option for paging class.")

        if not_archived_count == 0:
            max_page = 1
        else:
            max_page = ceil(not_archived_count / num_per_page)

        if current_page > max_page or current_page < 1:
            # not a legal page number
            abort(404)

        if current_page * num_per_page < not_archived_count:
            self._allow_next_page = True

        if current_page > 1:
            self._allow_previous_page = True

        return self

    @property
    def is_previous_page_allowed(self) -> bool:
        if not self._has_setup:
            raise AttributeError("Pagination has not been set up yet.")
        return self._allow_previous_page

    @property
    def is_next_page_allowed(self) -> bool:
        if not self._has_setup:
            raise AttributeError("Pagination has not been set up yet.")
        return self._allow_next_page

    @property
    def current_page(self) -> int:
        if not self._has_setup:
            raise AttributeError("Pagination has not been set up yet.")
        return self._current_page


def slicing_title(text: str, max_len: int) -> str:
    """
    Truncate the input string to the given max length, with trailing ellipsis if truncated.

    This function is used to truncate the title being too long.

    Returns:
        str: The truncated string.
    """
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}..."


def sort_dict(_dict: dict[str, int]) -> dict[str, int]:
    """
    Sort the dictionary by value in descending order.

    This function is used to sort the tags by the number of posts associated with them.

    Returns:
        dict: The sorted dictionary.
    """
    sorted_dict_key = sorted(_dict, key=_dict.get, reverse=True)
    sorted_dict = {}
    for key in sorted_dict_key:
        sorted_dict[key] = _dict[key]
    return sorted_dict


def process_tags(tag_string: str) -> list[str]:
    """
    Process a comma-separated tag string into a list of tags.

    Returns:
        list[str]: The list of processed tags.
    """
    if tag_string == "":
        return []
    return [tag.strip(" ") for tag in tag_string.split(",")]

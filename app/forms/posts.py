import re

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import URL, InputRequired, Optional, Regexp

slug_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class NewPostForm(FlaskForm):
    """
    Form for creating a new post. Inherits from FlaskWTForm.

    Fields:
        - title: StringField, required.
        - subtitle: StringField, required.
        - tags: StringField, required. Tags are separated by commas.
        - cover_url: StringField, optional.
        - custom_slug: StringField, optional.
        - editor: TextAreaField, required. Connected to EasyMDE.
        - submit_: SubmitField, with a validation function defined in `/static/js/backstage/posts.js`.
    """

    title = StringField(validators=[InputRequired(message="Title is required.")])
    subtitle = StringField(validators=[InputRequired(message="Subtitle is required.")])
    tags = StringField(
        render_kw={"placeholder": "Separate tags with ','"},
        validators=[InputRequired(message="Tags are required.")],
    )
    cover_url = StringField(
        render_kw={"placeholder": "Insert image URL"},
        validators=[Optional(), URL(message="Invalid URL.")],
    )
    custom_slug = StringField(
        render_kw={"placeholder": "Must be an URL-friendly string"},
        validators=[Optional(), Regexp(slug_pattern, message="Slug must be URL-friendly.")],
    )
    editor = TextAreaField()
    submit_ = SubmitField(label="Submit", render_kw={"onclick": "return validateNewPost()"})


class EditPostForm(FlaskForm):
    """
    Form for editing an existing post. Inherits from FlaskWTForm.

    Fields:
        - title: StringField, required.
        - subtitle: StringField, required.
        - tags: StringField, required. Tags are separated by commas.
        - cover_url: StringField, optional.
        - custom_slug: StringField, optional.
        - editor: TextAreaField, required. Connected to EasyMDE.
        - submit_: SubmitField, with a validation function defined in `/static/js/backstage/edit-post.js`.
    """

    title = StringField(validators=[InputRequired(message="Title is required.")])
    subtitle = StringField(validators=[InputRequired(message="Subtitle is required.")])
    tags = StringField(
        render_kw={"placeholder": "Separate tags with ','"},
        validators=[InputRequired(message="Tags are required.")],
    )
    cover_url = StringField(
        render_kw={"placeholder": "Insert image URL"},
        validators=[Optional(), URL(message="Invalid URL.")],
    )
    custom_slug = StringField(
        render_kw={"placeholder": "Must be a URL-friendly slug"},
        validators=[Optional(), Regexp(slug_pattern, message="Slug must be URL-friendly.")],
    )
    editor = TextAreaField()
    submit_ = SubmitField(label="Save Changes", render_kw={"onclick": "return validateUpdate()"})

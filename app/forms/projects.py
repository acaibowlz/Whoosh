import re

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import URL, InputRequired, Optional, Regexp

slug_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class NewProjectForm(FlaskForm):
    """
    Form for creating a new project. Inherits from FlaskWTForm.

    Fields:
        - title: StringField, required.
        - desc: StringField, required.
        - tags: StringField, required. Tags are separated by commas.
        - url0, url1, url2, url3, url4: StringField, required.
        - caption0, caption1, caption2, caption3, caption4: StringField, optional.
        - custom_slug: StringField, optional.
        - editor: TextAreaField, required. Connected to EasyMDE.
        - submit_: SubmitField, with a validation function defined in `/static/js/backstage/projects.js`.
    """

    title = StringField(validators=[InputRequired(message="Title is required.")])
    desc = StringField(validators=[InputRequired(message="Description is required.")])
    tags = StringField(
        render_kw={"placeholder": "Separate tags with ','"},
        validators=[InputRequired(message="Tags are required.")],
    )
    url0 = StringField(
        validators=[
            InputRequired(message="At least one image URL is required."),
            URL(message="Invalid URL."),
        ],
        render_kw={"placeholder": "URL"},
    )
    url1 = StringField(
        validators=[Optional(), URL(message="Invalid URL.")], render_kw={"placeholder": "URL"}
    )
    url2 = StringField(
        validators=[Optional(), URL(message="Invalid URL.")], render_kw={"placeholder": "URL"}
    )
    url3 = StringField(
        validators=[Optional(), URL(message="Invalid URL.")], render_kw={"placeholder": "URL"}
    )
    url4 = StringField(
        validators=[Optional(), URL(message="Invalid URL.")], render_kw={"placeholder": "URL"}
    )
    caption0 = StringField(validators=[Optional()], render_kw={"placeholder": "Caption"})
    caption1 = StringField(validators=[Optional()], render_kw={"placeholder": "Caption"})
    caption2 = StringField(validators=[Optional()], render_kw={"placeholder": "Caption"})
    caption3 = StringField(validators=[Optional()], render_kw={"placeholder": "Caption"})
    caption4 = StringField(validators=[Optional()], render_kw={"placeholder": "Caption"})
    custom_slug = StringField(
        render_kw={"placeholder": "Must be a URL-friendly string"},
        validators=[Optional(), Regexp(slug_pattern, message="Slug must be URL-friendly.")],
    )
    editor = TextAreaField()
    submit_ = SubmitField(label="Submit", render_kw={"onclick": "return validateNewProject()"})


class EditProjectForm(FlaskForm):
    """
    Form for editing an existing project. Inherits from FlaskWTForm.

    Fields:
        - title: StringField, required.
        - desc: StringField, required.
        - tags: StringField, required. Tags are separated by commas.
        - url0, url1, url2, url3, url4: StringField, required.
        - caption0, caption1, caption2, caption3, caption4: StringField, optional.
        - custom_slug: StringField, optional.
        - editor: TextAreaField, required. Connected to EasyMDE.
        - submit_: SubmitField, with a validation function defined in `/static/js/backstage/edit-project.js`.
    """

    title = StringField(validators=[InputRequired(message="Title is required.")])
    desc = StringField(validators=[InputRequired(message="Description is required.")])
    tags = StringField(
        render_kw={"placeholder": "Separate tags with ','"},
        validators=[InputRequired(message="Tags are required.")],
    )
    url0 = StringField(
        validators=[InputRequired(message="URL is required."), URL(message="Invalid URL.")],
        render_kw={"placeholder": "URL"},
    )
    url1 = StringField(
        validators=[Optional(), URL(message="Invalid URL.")], render_kw={"placeholder": "URL"}
    )
    url2 = StringField(
        validators=[Optional(), URL(message="Invalid URL.")], render_kw={"placeholder": "URL"}
    )
    url3 = StringField(
        validators=[Optional(), URL(message="Invalid URL.")], render_kw={"placeholder": "URL"}
    )
    url4 = StringField(
        validators=[Optional(), URL(message="Invalid URL.")], render_kw={"placeholder": "URL"}
    )
    caption0 = StringField(validators=[Optional()], render_kw={"placeholder": "Caption"})
    caption1 = StringField(validators=[Optional()], render_kw={"placeholder": "Caption"})
    caption2 = StringField(validators=[Optional()], render_kw={"placeholder": "Caption"})
    caption3 = StringField(validators=[Optional()], render_kw={"placeholder": "Caption"})
    caption4 = StringField(validators=[Optional()], render_kw={"placeholder": "Caption"})
    custom_slug = StringField(
        render_kw={"placeholder": "Must be a URL-friendly string"},
        validators=[Optional(), Regexp(slug_pattern, message="Slug must be URL-friendly.")],
    )
    editor = TextAreaField()
    submit_ = SubmitField(label="Submit", render_kw={"onclick": "return validateUpdate()"})

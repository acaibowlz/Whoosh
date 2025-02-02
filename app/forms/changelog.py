from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import URL, InputRequired, Optional

CATEGORY_CHOICES = ["Career", "Personal", "About this site", "Others"]


class NewChangelogForm(FlaskForm):
    """Form for creating a new changelog entry. Inherits from FlaskWTForm.

    Fields:
        - title: StringField, required.
        - date: StringField, required.
        - category: SelectField, required.
        - tags: StringField, required. Tags are separated by commas.
        - editor: TextAreaField, required. Connected to EasyMDE.
        - link: StringField, optional.
        - link_description: StringField, optional.
        - submit_: SubmitField, with a validation function defined in `/static/js/backstage/changelog.js`.
    """

    title = StringField(validators=[InputRequired()])
    date = StringField(validators=[InputRequired()])
    category = SelectField(choices=CATEGORY_CHOICES, validators=[InputRequired()])
    tags = StringField(
        render_kw={"placeholder": "Separate tags with ','"},
        validators=[InputRequired()],
    )
    editor = TextAreaField()
    link = StringField(render_kw={"placeholder": "Link"}, validators=[Optional(), URL()])
    link_description = StringField(
        render_kw={"placeholder": "Link description"}, validators=[Optional()]
    )
    submit_ = SubmitField(label="Submit", render_kw={"onclick": "return validateNewChangelog()"})


class EditChangelogForm(FlaskForm):
    """Form for editing an existing changelog entry. Inherits from FlaskWTForm.

    Fields:
        - title: StringField, required.
        - date: StringField, required.
        - category: SelectField, required.
        - tags: StringField, required. Tags are separated by commas.
        - editor: TextAreaField, required. Connected to EasyMDE.
        - link: StringField, optional.
        - link_description: StringField, optional.
        - submit_: SubmitField, with a validation function defined in `/static/js/backstage/edit-changelog.js`.
    """

    title = StringField(validators=[InputRequired()])
    date = StringField(validators=[InputRequired()])
    category = SelectField(choices=CATEGORY_CHOICES, validators=[InputRequired()])
    tags = StringField(
        render_kw={"placeholder": "Separate tags with ','"},
        validators=[InputRequired()],
    )
    editor = TextAreaField()
    link = StringField(render_kw={"placeholder": "Link"}, validators=[Optional(), URL()])
    link_description = StringField(
        render_kw={"placeholder": "Link description"}, validators=[Optional()]
    )
    submit_ = SubmitField(label="Submit", render_kw={"onclick": "return validateUpdate()"})

from flask_wtf import FlaskForm
from wtforms import PasswordField, EmailField, StringField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo

class CheckEmailForm(FlaskForm):
    pass
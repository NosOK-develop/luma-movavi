from flask_pagedown.fields import PageDownField
from flask_wtf import FlaskForm
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class PostForm(FlaskForm):
    """Форма создания поста Luma 0.99.3"""

    title = StringField(
        'Название поста',
        validators=[DataRequired(),Length(max=50)],
        render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "Название"}
    )
    text = PageDownField(
        'Введите текст поста (разметка Markdown)'
    )
    submit = SubmitField()


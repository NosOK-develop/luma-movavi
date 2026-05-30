from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FileField, SubmitField
from wtforms.validators import DataRequired, Length

class CreateChatGroupForm(FlaskForm):
    """Форма Flask-WTF для создания групповых чатов и каналов Luma."""
    title = StringField(
        'Название сообщества',
        validators=[DataRequired(message="Обязательное поле"), Length(min=2, max=100, message="От 2 до 100 символов")],
        render_kw={"class": "form-control", "placeholder": "Введите название..."}
    )
    type = SelectField(
        'Тип сообщества',
        choices=[('group', 'Групповой чат (Общение)'), ('channel', 'Информационный канал (Только авторы)')],
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    description = TextAreaField(
        'Описание',
        validators=[Length(max=500, message="Максимум 500 символов")],
        render_kw={"class": "form-control", "rows": 3, "placeholder": "О чем это сообщество?..."}
    )
    avatar = FileField(
        'Аватар сообщества',
        render_kw={"class": "form-control", "accept": "image/*"}
    )
    submit = SubmitField(
        'Создать',
        render_kw={"class": "btn btn-luma text-white fw-bold px-4"}
    )

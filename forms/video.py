from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length


class VideoUploadForm(FlaskForm):
    """Светлая форма Bootstrap 5 для загрузки горизонтальных видео"""
    channel_id = SelectField('Выберите канал Luma Media', coerce=int, validators=[DataRequired()],
                             render_kw={"class": "form-select bg-white border-secondary-subtle"})

    title = StringField('Название видео', validators=[DataRequired(), Length(min=3, max=100)],
                        render_kw={"class": "form-control bg-white border-secondary-subtle",
                                   "placeholder": "Придумайте яркое название..."})

    description = TextAreaField('Описание',
                                render_kw={"class": "form-control bg-white border-secondary-subtle", "rows": 4,
                                           "placeholder": "Расскажите, о чем ваше видео..."})

    video = FileField('Файл видео',
                      validators=[FileAllowed(['mp4', 'avi', 'mov', 'mkv'], 'Разрешены только видеофайлы!')],
                      render_kw={"class": "form-control bg-white border-secondary-subtle"})

    thumbnail = FileField('Обложка (Превью)',
                          validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Только изображения!')],
                          render_kw={"class": "form-control bg-white border-secondary-subtle"})

    submit = SubmitField('Опубликовать видео', render_kw={"class": "btn btn-luma text-white w-100 py-2fw-bold"})


class ClipUploadForm(FlaskForm):
    """Светлая форма Bootstrap 5 для загрузки вертикальных клипов"""
    channel_id = SelectField('Выберите канал Luma Media', coerce=int, validators=[DataRequired()],
                             render_kw={"class": "form-select bg-white border-secondary-subtle"})

    title = StringField('Описание клипа', validators=[DataRequired(), Length(min=1, max=100)],
                        render_kw={"class": "form-control bg-white border-secondary-subtle",
                                   "placeholder": "Добавьте описание и хэштеги..."})

    video = FileField('Вертикальное видео',
                      validators=[FileAllowed(['mp4', 'mov', '3gp'], 'Допускаются только видеофайлы!')],
                      render_kw={"class": "form-control bg-white border-secondary-subtle"})

    thumbnail = FileField('Превью-кадр (Обложка)',
                          validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Только картинки!')],
                          render_kw={"class": "form-control bg-white border-secondary-subtle"})

    submit = SubmitField('Поделиться клипом', render_kw={"class": "btn btn-luma text-white w-100 py-2 fw-bold"})


class CreateMediaAccountForm(FlaskForm):
    """Форма создания профиля Luma Media (Канала)"""
    channel_name = StringField('Название канала Luma Media', validators=[DataRequired(), Length(min=3, max=30)],
                               render_kw={"class": "form-control bg-white border-secondary-subtle",
                                          "placeholder": "Придумайте название медиа-профиля"})
    submit = SubmitField('Создать профиль', render_kw={"class": "btn btn-luma text-white w-100 py-2 fw-bold"})

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FileField, SubmitField
from wtforms.validators import DataRequired, Length

class EditMediaChannelForm(FlaskForm):
    """Форма WTForms для изменения оформления и информации канала Luma Media."""
    channel_name = StringField(
        'Название канала',
        validators=[DataRequired(message="Обязательное поле"), Length(min=2, max=50, message="От 2 до 50 символов")],
        render_kw={"class": "form-control"}
    )
    description = TextAreaField(
        'Описание канала',
        validators=[Length(max=1000, message="Максимум 1000 символов")],
        render_kw={"class": "form-control", "rows": 4, "placeholder": "Расскажите зрителям о своем канале..."}
    )
    avatar = FileField(
        'Аватарка канала (Квадратная)',
        render_kw={"class": "form-control", "accept": "image/*"}
    )
    banner = FileField(
        'Шапка / Баннер канала (Горизонтальный)',
        render_kw={"class": "form-control", "accept": "image/*"}
    )
    player_icon = FileField(
        'Иконка в плеере (Вотермарка)',
        render_kw={"class": "form-control", "accept": "image/*"}
    )
    submit = SubmitField(
        'Сохранить изменения',
        render_kw={"class": "btn btn-luma text-white fw-bold px-4"}
    )

from wtforms import PasswordField, BooleanField
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import PasswordField, BooleanField
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional
from wtforms.validators import EqualTo


class EditProfileForm(FlaskForm):
    """Форма тонкой кастомизации профиля Luma v0.99.2.1"""
    name = StringField(
        'Имя',
        validators=[DataRequired(), Length(max=40)],
        render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "Ваше имя"}
    )
    email = StringField(
        'Электронная почта',
        validators=[DataRequired(), Email()],
        render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "name@example.com"}
    )
    password = StringField(
        'Пароль',
        validators=[DataRequired("Введите новый или старый пароль, это обязательно"), Length(min=6, max=20)],
        render_kw={"class": "form-control bg-secondary text-white border-0"}
    )
    about = TextAreaField(
        'О себе',
        validators=[Optional(), Length(max=500)],
        render_kw={"class": "form-control bg-secondary text-white border-0", "rows": 3,
                   "placeholder": "Расскажите о себе..."}
    )
    phone = StringField(
        'Номер телефона',
        validators=[Optional(), Length(min=5, max=20)],
        render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "+7 (999) 000-00-00"}
    )
    social_telegram = StringField(
        'Telegram никнейм',
        validators=[Optional(), Length(max=32)],
        render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "@username"}
    )
    social_vk = StringField(
        'Ссылка VK',
        validators=[Optional(), Length(max=64)],
        render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "id12345 или vk_nickname"}
    )

    # Селектор уровней приватности аккаунта (Правила видимости)
    privacy_level = SelectField(
        'Видимость аккаунта',
        choices=[
            ('0', 'Виден всем пользователям Luma'),
            ('1', 'Виден только моим друзьям'),
            ('2', 'Виден только моим подписчикам'),
            ('3', 'Скрыт от всех (Никому)')
        ],
        render_kw={"class": "form-select bg-secondary text-white border-0"}
    )

    # Поле асинхронной загрузки новой аватарки формата медиа-файла
    avatar = FileField(
        'Сменить аватарку профиля',
        validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Разрешены только изображения!')],
        render_kw={"class": "form-control bg-secondary text-white border-0"}
    )

    submit = SubmitField(
        'Сохранить изменения',
        render_kw={"class": "btn btn-luma w-100 py-2 fw-bold text-white"}
    )

class LoginForm(FlaskForm):
    nickname = StringField('Никнейм', validators=[DataRequired()],
                           render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "Ваш никнейм"})
    password = PasswordField('Пароль', validators=[DataRequired()],
                             render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "Ваш пароль"})
    remember = BooleanField('Запомнить меня', render_kw={"class": "form-check-input"})
    submit = SubmitField('Войти в аккаунт', render_kw={"class": "btn btn-luma w-100 py-2 fw-bold text-white"})

class RegisterForm(FlaskForm):
    nickname = StringField('Никнейм', validators=[DataRequired(), Length(min=3, max=20)],
                           render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "Придумайте никнейм"})
    name = StringField('Имя', validators=[DataRequired()],
                       render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "Как вас зовут?"})
    email = StringField('Электронная почта', validators=[DataRequired(), Email()],
                        render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "name@example.com"})
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)],
                             render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "Минимум 6 символов"})
    password_again = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password', message='Пароли должны совпадать')],
                                   render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "Повторите пароль"})
    about = TextAreaField('О себе', render_kw={"class": "form-control bg-secondary text-white border-0", "rows": 3, "placeholder": "Расскажите немного о себе..."})
    submit = SubmitField('Создать аккаунт', render_kw={"class": "btn btn-luma w-100 py-2 fw-bold text-white"})

class CreateMediaAccountForm(FlaskForm):
    """Форма создания профиля Luma Media"""
    channel_name = StringField('Название канала Luma Media', validators=[DataRequired(), Length(min=3, max=30)],
                              render_kw={"class": "form-control bg-secondary text-white border-0", "placeholder": "Придумайте название медиа-профиля"})
    submit = SubmitField('Создать профиль', render_kw={"class": "btn btn-luma w-100 py-2 fw-bold text-white"})

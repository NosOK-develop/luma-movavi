from flask import Blueprint, render_template, redirect, url_for, abort, request
from flask_login import login_user, logout_user, login_required, current_user
from data import db_session
from data.posts import Post
from data.users import User, LumaMediaAccount
from forms.user import RegisterForm, LoginForm
import os
import uuid
from werkzeug.utils import secure_filename
from forms.user import EditProfileForm
import datetime as dt

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
@auth_bp.route('/index')
@auth_bp.route('/main')
def hello_world():
    db_sess = db_session.create_session()
    posts = db_sess.query(Post).all()
    return render_template('index.html', title='Luma', posts=posts)


@auth_bp.route('/profile/<string:nickname>')
@login_required
def user_profile(nickname):
    """Страница личного профиля Luma со списком медиа-каналов, постами и социальным блоком v0.99.2.4."""
    db_sess = db_session.create_session()
    try:
        # Ищем пользователя по его уникальному никнейму
        user = db_sess.query(User).filter(User.nickname == nickname).first()
        if not user:
            abort(404)

        # Загружаем привязанные медиа-каналы
        channels = db_sess.query(LumaMediaAccount).filter_by(luma_user_id=user.id).all()

        # Загружаем посты
        posts = db_sess.query(Post).filter_by(author_id=user.id).all()

        # Принудительно подгружаем текущего авторизованного пользователя в сессию для точной проверки отношений
        me = db_sess.get(User, current_user.id)

        # Вычисляем социальные маркеры для отображения кнопок и проверки приватности
        is_owner = (user.id == me.id)
        is_following = me.is_following(user)
        is_friend = me.is_friend_with(user)

        # Защита приватности (0: Все, 1: Друзья, 2: Подписчики, 3: Никто)
        if not is_owner:
            if user.privacy_level == 3:
                abort(403)  # Скрыт от всех полностью
            if user.privacy_level == 1 and not is_friend:
                # Если профиль только для друзей, выведем его в урезанном виде или кинем 403
                # Для удобства Luma, отдадим шаблон с флагом блокировки контента
                return render_template('profile.html', title=f'Профиль @{user.nickname}', user=user, channels=[], is_owner=is_owner, is_following=is_following, is_friend=is_friend, private_locked=True)
            if user.privacy_level == 2 and not user.is_followed_by(me):
                return render_template('profile.html', title=f'Профиль @{user.nickname}', user=user, channels=[], is_owner=is_owner, is_following=is_following, is_friend=is_friend, private_locked=True)

        # Получаем Google-подобные метаданные аватара для отображения на странице
        avatar_meta = user.get_avatar_meta()

        return render_template(
            'profile.html',
            title=f'Профиль @{user.nickname}',
            user=user,
            channels=channels,
            is_owner=is_owner,
            is_following=is_following,
            is_friend=is_friend,
            avatar_meta=avatar_meta,
            private_locked=False,
            posts = posts
        )
    finally:
        db_sess.close()

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            if db_sess.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html', title='Регистрация', form=form, message='Почта уже занята')
            if db_sess.query(User).filter(User.nickname == form.nickname.data).first():
                return render_template('register.html', title='Регистрация', form=form, message="Никнейм уже занят")
            user = User(email=form.email.data, nickname=form.nickname.data, about=form.about.data, name=form.name.data)
            user.set_password(form.password.data)
            db_sess.add(user)
            db_sess.commit()
            return redirect(url_for('auth.login'))
        finally:
            db_sess.close()
    return render_template('register.html', title='Регистрация', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.nickname == form.nickname.data).first()
            if user and user.check_password(form.password.data):
                # --- ПРОВЕРКА БАНА ПРИ АВТОРИЗАЦИИ Luma v0.99.2.5 ---
                if user.is_banned():
                    # Вычисляем оставшееся время
                    remaining = user.ban_until - dt.datetime.now()
                    # Если бан больше 50 лет — значит он навсегда
                    time_str = "НАВСЕГДА" if remaining.days > 18000 else f"до {user.ban_until.strftime('%d.%m.%Y %H:%M:%S')}"
                    return render_template('login.html', title='Вход', form=form,
                                           message=f'🚫 Ваш аккаунт заблокирован администрацией {time_str}.')
                login_user(user, remember=form.remember.data)
                return redirect('/')
            return render_template('login.html', title='Авторизация', form=form, message='Неверный никнейм или пароль')
        finally:
            db_sess.close()
    return render_template('login.html', title='Авторизация', form=form)



# Константа директории для хранения кастомных аватарок пользователей Luma
UPLOAD_AVATARS_DIR = os.path.join('static', 'images', 'users')


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Маршрут тонкой кастомизации единого профиля Luma v0.99.2.1"""
    form = EditProfileForm()
    db_sess = db_session.create_session()

    try:
        if form.validate_on_submit():
            # Защита от дублирования уникальных контактов в базе данных
            if form.phone.data:
                existing_phone = db_sess.query(User).filter(
                    User.phone == form.phone.data,
                    User.id != current_user.id
                ).first()
                if existing_phone:
                    return render_template('edit_profile.html', title='Настройки профиля', form=form,
                                           message='Этот номер телефона уже привязан к другому аккаунту')

            # Обработка асинхронной загрузки графического файла аватарки
            if form.avatar.data:
                file = form.avatar.data
                ext = secure_filename(file.filename).split('.')[-1]
                # Генерируем уникальное имя файла для исключения затирания данных
                filename = f"avatar_{current_user.id}_{uuid.uuid4().hex}.{ext}"

                # Создаем папки на сервере, если они еще не созданы физически
                os.makedirs(UPLOAD_AVATARS_DIR, exist_ok=True)

                full_path = os.path.join(UPLOAD_AVATARS_DIR, filename)
                file.save(full_path)

                # Записываем относительный веб-путь в базу данных Luma
                current_user.avatar_path = f"/{full_path}".replace('\\', '/')

            # Перезаписываем кастомизированные текстовые метаданные
            current_user.name = form.name.data
            current_user.email = form.email.data
            current_user.about = form.about.data
            current_user.phone = form.phone.data if form.phone.data else None
            current_user.set_password(form.password.data)

            # Чистим префикс @ из телеграма, если пользователь ввел его вручную
            tg_data = form.social_telegram.data.strip() if form.social_telegram.data else None
            if tg_data and tg_data.startswith('@'):
                tg_data = tg_data[1:]
            current_user.social_telegram = tg_data

            current_user.social_vk = form.social_vk.data.strip() if form.social_vk.data else None
            current_user.privacy_level = int(form.privacy_level.data)

            db_sess.merge(current_user)
            db_sess.commit()

            return redirect(f'/profile/{current_user.nickname}')

        # Первичное открытие страницы: предзаполняем поля текущими данными из БД
        elif request.method == 'GET':
            form.name.data = current_user.name
            form.email.data = current_user.email
            form.about.data = current_user.about
            form.phone.data = current_user.phone
            form.social_telegram.data = current_user.social_telegram
            form.social_vk.data = current_user.social_vk
            form.privacy_level.data = str(current_user.privacy_level)

        # Вызываем метод получения метаданных аватара (изображение или Google-текст)
        avatar_meta = current_user.get_avatar_meta()
        return render_template('edit_profile.html', title='Настройки профиля', form=form, avatar_meta=avatar_meta)

    finally:
        db_sess.close()

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

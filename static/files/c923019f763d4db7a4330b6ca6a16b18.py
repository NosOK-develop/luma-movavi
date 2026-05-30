import os
from flask import Flask, session
from flask_assets import Environment, Bundle
from flask_login import LoginManager, current_user
from flask_socketio import SocketIO

import config
from data import db_session
from data.users import User

app = Flask(__name__)
app.config['SECRET_KEY'] = config.FLASK_SECRET_KEY
app.config['ASSETS_DEBUG'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static')

# Обеспечение структуры папок загрузок
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'images'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'files'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'videos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails'), exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Инициализация Flask-Assets
assets = Environment(app)
assets.url = app.static_url_path
assets.directory = app.static_folder

scss_bundle = Bundle(
    'scss/main.scss',
    filters='libsass,cssmin',
    output='css/main.css',
    depends='scss/*.scss'
)
assets.register('scss_all', scss_bundle)

# ИСПРАВЛЕНО v0.99.1.6: Бронебойные параметры для стандартного сервера Flask (Werkzeug)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25
)





@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    try:
        return db_sess.get(User, user_id)
    finally:
        db_sess.close()


@app.before_request
def check_role_updates():
    if current_user.is_authenticated:
        if session.get('role_updated'):
            db_sess = db_session.create_session()
            try:
                fresh_user = db_sess.get(User, current_user.id)
                if fresh_user:
                    current_user.role_level = fresh_user.role_level
                    print(f"[SYSTEM] Роль пользователя @{current_user.nickname} синхронизирована локально.")
            finally:
                db_sess.close()
            session.pop('role_updated', None)


# --- РЕГИСТРАЦИЯ МОДУЛЕЙ (Никаких круговых зависимостей сверху нет) ---
from routes.auth import auth_bp
from routes.media import media_bp
from routes.messenger import messenger_bp
from routes.admin import admin_bp
from routes.sockets import init_sockets

app.register_blueprint(auth_bp)
app.register_blueprint(media_bp)
app.register_blueprint(messenger_bp)
app.register_blueprint(admin_bp)

init_sockets(socketio)


def main():
    db_session.global_init('db/luma.db')

    # Инициализация и системное сжатие базы данных SQLite
    db_sess = db_session.create_session()
    try:
        db_sess.execute(db_session.sa.text("PRAGMA auto_vacuum = FULL;"))
        db_sess.commit()

        # ПОЛОЖЕНИЕ ДОРОЖНОЙ КАРТЫ v0.98.3.1: Авто-создание Главного Администратора
        admin_nickname = "Luma"
        chief_admin = db_sess.query(User).filter(User.nickname == admin_nickname).first()

        if not chief_admin:
            print(f"[SYSTEM] Аккаунт Главного Администратора @{admin_nickname} не обнаружен. Инициализация...")

            # Создаем корневой профиль платформы
            root_admin = User(
                email="admin@luma.media",
                nickname=admin_nickname,
                name="Luma Official",
                about="Официальный системный аккаунт Главного Администратора медиаплатформы Luma.",
                role_level=4  # ROLE_CHIEF_ADMIN
            )
            # Устанавливаем безопасный дефолтный пароль. Измените его при первом входе!
            root_admin.set_password("LumaRootPassword2026")

            db_sess.add(root_admin)
            db_sess.commit()
            print(f"[SYSTEM] Главный администратор @{admin_nickname} успешно создан. Пароль: LumaRootPassword2026")
        else:
            # Гарантируем, что уровень роли аккаунта @Luma всегда остается наивысшим
            if chief_admin.role_level != 4:
                chief_admin.role_level = 4
                db_sess.commit()
                print(
                    f"[SYSTEM] Права аккаунта @{admin_nickname} принудительно обновлены до уровня Главного Администратора.")

    except Exception as e:
        print(f"[CRITICAL] Ошибка инициализации системных таблиц Luma: {e}")
    finally:
        db_sess.close()

    socketio.run(app, host='127.0.0.1', port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()

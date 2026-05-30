import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from data import db_session
from data.users import User, LumaMediaAccount  # Убедитесь в правильности импортов ваших моделей

messenger_bp = Blueprint('messenger', __name__)

UPLOAD_FILES_DIR = os.path.join('static', 'files')


@messenger_bp.route('/messenger')
@login_required
def messenger_index():
    """Главная страница мессенджера-заглушки Luma v0.99.1fix1"""
    return render_messenger_view()


@messenger_bp.route('/messenger/<string:nickname>')
@login_required
def messenger_private(nickname):
    """Роут личной переписки по никнейму пользователя Luma (Пример: /messenger/danil)"""
    # Очищаем префикс @, если пользователь ввел его в адресную строку руками
    clean_nickname = nickname[1:] if nickname.startswith('@') else nickname

    db_sess = db_session.create_session()
    try:
        target_user = db_sess.query(User).filter(User.nickname == clean_nickname).first()
        if not target_user:
            abort(404)
        return render_messenger_view(active_target=target_user, chat_type='private')
    finally:
        db_sess.close()


@messenger_bp.route('/messenger/group/<int:group_id>')
@login_required
def messenger_group(group_id):
    """Роут группового чата по его уникальному идентификатору ID"""
    db_sess = db_session.create_session()
    try:
        # Для интеграции групп Luma используется модель LumaMediaAccount или отдельная таблица
        # На данный момент привязываем к существующей структуре сообществ Luma Media
        group = db_sess.query(LumaMediaAccount).get(group_id)
        if not group:
            abort(404)
        return render_messenger_view(active_target=group, chat_type='group')
    finally:
        db_sess.close()


@messenger_bp.route('/messenger/channel/<int:channel_id>')
@login_required
def messenger_channel(channel_id):
    """Роут вещательного канала по его уникальному идентификатору ID"""
    db_sess = db_session.create_session()
    try:
        channel = db_sess.query(LumaMediaAccount).get(channel_id)
        if not channel:
            abort(404)
        return render_messenger_view(active_target=channel, chat_type='channel')
    finally:
        db_sess.close()


def render_messenger_view(active_target=None, chat_type=None):
    """Вспомогательный единый рендерер социального графа мессенджера"""
    db_sess = db_session.create_session()
    try:
        # 1. Извлекаем ВСЕХ пользователей из системы
        all_users = db_sess.query(User).filter(User.id != current_user.id).all()

        # 2. ФИЛЬТР ЛИЧНЫХ ДИАЛОГОВ (Пункт 8): Только взаимные друзья!
        # (В будущем здесь можно добавить фильтр по наличию истории в БД)
        me = db_sess.get(User, current_user.id)
        active_dialogs = [u for u in all_users if me.is_friend_with(u)]

        # Если чат открыт по прямой ссылке, но пользователя еще нет в друзьях — принудительно добавляем его в список видимых
        if active_target and chat_type == 'private' and active_target not in active_dialogs:
            active_dialogs.append(active_target)

        # 3. Извлекаем сообщества Luma Media для вывода в боковую панель
        all_communities = db_sess.query(LumaMediaAccount).all()

        return render_template(
            'messenger.html',
            title='Мессенджер Luma',
            active_dialogs=active_dialogs,
            all_communities=all_communities,
            active_chat=active_target,
            chat_type=chat_type
        )
    finally:
        db_sess.close()


@messenger_bp.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    """ЖЕСТКИЙ ФИКС ПУТЕЙ ЗАГРУЗКИ (Пункт 4): Сохранение и отдача из одной папки static/files/"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл отсутствует в запросе'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Имя файла пустое'}), 400

    if file:
        filename = secure_filename(file.filename)
        # Генерируем уникальное имя для исключения затирания файлов с одинаковым названием
        unique_filename = f"{uuid.uuid4().hex}_{filename}"

        os.makedirs(UPLOAD_FILES_DIR, exist_ok=True)
        full_path = os.path.join(UPLOAD_FILES_DIR, unique_filename)
        file.save(full_path)

        # Определяем тип медиа-вложения
        ext = filename.split('.')[-1].lower()
        msg_type = 'image' if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif'] else 'file'

        # Формируем корректный веб-URL адрес, по которому файл лежит физически
        web_url = f"/static/files/{unique_filename}"

        return jsonify({
            'file_url': web_url,
            'file_name': filename,
            'message_type': msg_type
        }), 200


@messenger_bp.route('/save_client_logs', methods=['POST'])
@login_required
def save_client_logs():
    try:
        log_data = request.data.decode('utf-8')
        with open('luma_client.log', 'a', encoding='utf-8') as log_file:
            log_file.write(log_data)
        return {"status": "success"}, 200
    except Exception:
        return {"status": "error"}, 500

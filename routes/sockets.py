import sys
import threading
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

# Потокобезопасный RAM-реестр соединений Luma Core v0.99.1.21
_registry_lock = threading.Lock()
active_users = {}  # Структура: {user_id: request.sid}


def init_sockets(socketio):
    @socketio.on('connect')
    def handle_connect():
        print(f"[LUMA SOCKET] Клиент зарезервировал сокет-туннель. Локальный SID: {request.sid}", flush=True)

    @socketio.on('authorize_socket')
    def handle_authorize_socket(data):
        """Гарантированная привязка сокета к user_id."""
        if not data or not isinstance(data, dict):
            return

        user_id = data.get('user_id')
        if not user_id:
            return

        try:
            user_id = int(user_id)
            with _registry_lock:
                # Обновляем или записываем актуальный SID сессии для пользователя
                active_users[user_id] = request.sid
            print(f"[LUMA SOCKET SUCCESS] ПОЛЬЗОВАТЕЛЬ ID {user_id} УСПЕШНО ДОБАВЛЕН В РЕЕСТР -> SID {request.sid}",
                  flush=True)
        except (TypeError, ValueError) as e:
            print(f"[LUMA SOCKET ERROR] Битый UID при авторизации сокета: {e}", flush=True)

    @socketio.on('send_message')
    def handle_send_message(data):
        """Прямая адресная доставка сообщений по зарегистрированным SID сессий."""
        if not data or not isinstance(data, dict):
            return

        try:
            target_id = int(data.get('target_id'))
            sender_id = int(data.get('sender_id', 0))
        except (TypeError, ValueError):
            print("[LUMA SOCKET ERROR] Пропуск пакета: некорректный target_id или sender_id", flush=True)
            return

        chat_type = data.get('chat_type', 'private')
        text_content = data.get('text', '').strip()

        # Безопасно извлекаем кастомизацию инвентаря Luma v0.99.2.4fix2
        name_style = ""
        badge = None
        role = 0

        if current_user.is_authenticated:
            try:
                name_style = current_user.get_equipped_name_style()
                badge = current_user.get_equipped_badge()
                role = current_user.role_level
            except Exception as e:
                print(f"[LUMA SOCKET WARN] Не удалось считать стили автора: {e}", flush=True)

        msg_payload = {
            'msg_id': data.get('msg_id'),
            'target_id': target_id,
            'chat_type': chat_type,
            'message_type': data.get('message_type', 'text'),
            'text': text_content,
            'file_url': data.get('file_url'),
            'file_name': data.get('file_name'),
            'sender_id': sender_id,
            'sender_name': data.get('sender_name', 'User'),
            'timestamp': data.get('timestamp'),

            # Передаем полностью защищенные и вычисленные стили никнейма
            'sender_name_style': name_style,
            'sender_badge': badge,
            'sender_role': role
        }
        print(f"[LUMA ENGINE] Маршрутизация сообщения от ID {sender_id} к ID {target_id} ({chat_type})", flush=True)

        # 1. ОБРАБОТКА ПРИВАТНЫХ ДИАЛОГОВ
        if chat_type == 'private':
            with _registry_lock:
                target_sid = active_users.get(target_id)

            if target_sid:
                # Шлем напрямую на активное сокет-соединение получателя во вторую вкладку
                emit('receive_message', msg_payload, room=target_sid)
                print(f"[LUMA ROUTER] Доставлено получателю ID {target_id} на сокет {target_sid}", flush=True)
            else:
                print(f"[LUMA ROUTER] Получатель ID {target_id} сейчас офлайн.", flush=True)

            # Эхо отправителю: возвращаем на сокет автора, чтобы закрыть лоадер
            emit('receive_message', msg_payload, room=request.sid)

        # 2. ОБРАБОТКА СООБЩЕСТВ (ГРУППЫ И КАНАЛЫ)
        else:
            emit('receive_message', msg_payload, room=f"group_{target_id}", include_self=True)
            print(f"[LUMA ROUTER] Сообщение сообщества отправлено в room group_{target_id}.", flush=True)

    @socketio.on('disconnect')
    def handle_disconnect():
        with _registry_lock:
            for uid, sid in list(active_users.items()):
                if sid == request.sid:
                    active_users.pop(uid, None)
                    print(f"[LUMA SOCKET] Сессия сокета {request.sid} удалена. Пользователь ID {uid} теперь офлайн.",
                          flush=True)
                    break

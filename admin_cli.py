import threading
import sys
import time
import datetime as dt
from data import db_session
from data.users import User
from data.inventory import InventoryItem, UserItem


def cli_console_worker():
    """Фоновый поток, слушающий продвинутые команды модерации и аналитики Luma v0.99.2.5"""
    # Задержка, чтобы логи Flask успели отгреметь в терминале при запуске app.py
    time.sleep(3)

    print("\n" + "=" * 60)
    print(" [LUMA ADMIN CLI] Обновленная консоль безопасности запущена!")
    print(" Новые команды управления:")
    print("   ban <nickname> [минуты]       - Бан аккаунта (без минут — навсегда)")
    print("   grant_item_all <type> <title> <val> - Выдать вещь ВСЕМ пользователям")
    print("   users [ver]                   - Список всех (ver — только с галочкой)")
    print("   users_online [ver]            - Список онлайн (ver — только с галочкой)")
    print("   admins                        - Список всей администрации")
    print("   admins_online                 - Список админов в сети")
    print("   help                          - Показать старые и новые команды")
    print("=" * 60 + "\n", flush=True)

    while True:
        try:
            sys.stdout.write("luma-admin> ")
            sys.stdout.flush()
            line = sys.stdin.readline().strip()
            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()

            # Импортируем реестр активных WebSocket-сессий из сокет-модуля
            from routes.sockets import active_users

            if cmd == "help":
                print("\nСправочник команд модерации:")
                print("  ban <nickname> [минуты]             - Если минуты не указаны — бан перманентный")
                print("  grant_item <nickname> <type> <title> <value>")
                print("  grant_item_all <type> <title> <value> - Массовое зачисление в инвентарь")
                print("  users [ver] / users_online [ver]   - Флаг 'ver' фильтрует аккаунты с галочкой")
                print("  admins / admins_online             - Мониторинг модераторов и админов\n")
                continue

            db_sess = db_session.create_session()
            try:
                # --- 1. КОМАНДА БЛОКИРОВКИ: ban <nickname> [time] ---
                if cmd == "ban":
                    if len(parts) < 2:
                        print("Ошибка: Синтаксис: ban <nickname> [минуты]")
                        continue

                    nickname = parts[1]
                    user = db_sess.query(User).filter(User.nickname == nickname).first()
                    if not user:
                        print(f"Ошибка: Пользователь @{nickname} не найден.")
                        continue

                    if len(parts) >= 3:
                        try:
                            minutes = int(parts[2])
                            user.ban_until = dt.datetime.now() + dt.timedelta(minutes=minutes)
                            print(
                                f"УСПЕХ: Пользователь @{user.nickname} заблокирован на {minutes} мин. (До {user.ban_until.strftime('%H:%M:%S')})")
                        except ValueError:
                            print("Ошибка: Количество минут должно быть числом!")
                            continue
                    else:
                        # Если аргумент времени отсутствует — блокируем «навсегда» (на 100 лет вперед)
                        user.ban_until = dt.datetime.now() + dt.timedelta(days=36500)
                        print(f"УСПЕХ: Пользователь @{user.nickname} заблокирован НАВСЕГДА (Перманентно).")

                    db_sess.commit()

                # --- 2. МАССОВАЯ ВЫДАЧА ПРЕДМЕТА ВСЕМ: grant_item_all ---
                elif cmd == "grant_item_all":
                    if len(parts) < 4:
                        print("Ошибка: Синтаксис: grant_item_all <badge|name_color|profile_theme> <title> <value>")
                        continue

                    item_type = parts[1]
                    title = parts[2]
                    value = " ".join(parts[3:])

                    if item_type not in ['badge', 'name_color', 'profile_theme']:
                        print("Ошибка: Неверный тип предмета. Допустимы: badge, name_color, profile_theme")
                        continue

                    # Создаем или ищем предмет в общем каталоге
                    item = db_sess.query(InventoryItem).filter(
                        InventoryItem.item_type == item_type,
                        InventoryItem.value == value
                    ).first()

                    if not item:
                        item = InventoryItem(title=title, item_type=item_type, value=value,
                                             description="Глобальная CLI выдача всем")
                        db_sess.add(item)
                        db_sess.flush()

                    all_users = db_sess.query(User).all()
                    granted_count = 0

                    for u in all_users:
                        already_has = db_sess.query(UserItem).filter(UserItem.user_id == u.id,
                                                                     UserItem.item_id == item.id).first()
                        if not already_has:
                            db_sess.add(UserItem(user_id=u.id, item_id=item.id, is_equipped=False))
                            granted_count += 1

                    db_sess.commit()
                    print(
                        f"ГЛОБАЛЬНЫЙ УСПЕХ: Предмет '{title}' зачислен в инвентарь {granted_count} пользователям системы Luma!")
                # --- 3. РЕЕСТР ПОЛЬЗОВАТЕЛЕЙ: users [ver] ---
                elif cmd == "users":
                    only_ver = (len(parts) >= 2 and parts[1].lower() == "ver")
                    query = db_sess.query(User)
                    if only_ver:
                        query = query.filter(User.role_level == 1)

                    users_list = query.all()
                    print(f"\n--- Реестр пользователей Luma ({'Только верифицированные' if only_ver else 'Все'}) ---")
                    for u in users_list:
                        print(
                            f" ID: {u.id} | @{u.nickname} | Имя: {u.name} | Роль: {u.get_role_name()} | Статус: {'[ЗАБАНЕН]' if u.is_banned() else '[ОК]'}")
                    print(f"Всего аккаунтов в выборке: {len(users_list)}\n")

                # --- 4. ПОЛЬЗОВАТЕЛИ ОНЛАЙН: users_online [ver] ---
                elif cmd == "users_online":
                    only_ver = (len(parts) >= 2 and parts[1].lower() == "ver")
                    online_ids = list(active_users.keys())  # Считываем RAM-ключи веб-сокетов

                    if not online_ids:
                        print("\n[LUMA] В сети сейчас 0 пользователей.\n")
                        continue

                    query = db_sess.query(User).filter(User.id.in_(online_ids))
                    if only_ver:
                        query = query.filter(User.role_level == 1)

                    online_list = query.all()
                    print(f"\n--- Пользователи ОНЛАЙН ({'Только верифицированные' if only_ver else 'Все'}) ---")
                    for u in online_list:
                        print(f" ID: {u.id} | @{u.nickname} | Сокет SID: {active_users.get(u.id)}")
                    print(f"Всего онлайн в выборке: {len(online_list)}\n")

                # --- 5. АДМИНИСТРАЦИЯ: admins ---
                elif cmd == "admins":
                    admins_list = db_sess.query(User).filter(User.role_level >= 2).all()
                    print("\n--- Список всей администрации Luma ---")
                    for a in admins_list:
                        print(f" ID: {a.id} | @{a.nickname} | Уровень доступа: {a.role_level} ({a.get_role_name()})")
                    print(f"Всего представителей АДМ: {len(admins_list)}\n")

                # --- 6. АДМИНЫ ОНЛАЙН: admins_online ---
                elif cmd == "admins_online":
                    online_ids = list(active_users.keys())
                    if not online_ids:
                        print("\n[LUMA] Никого из администрации нет в сети.\n")
                        continue

                    online_admins = db_sess.query(User).filter(User.id.in_(online_ids), User.role_level >= 2).all()
                    print("\n--- Администрация ОНЛАЙН ---")
                    for a in online_admins:
                        print(
                            f" ID: {a.id} | @{a.nickname} | Роль: {a.get_role_name()} | SID: {active_users.get(a.id)}")
                    print(f"Всего админов в сети: {len(online_admins)}\n")

                # --- ОСТАВЛЯЕМ СТАРЫЕ КОМАНДЫ ДЛЯ СОВМЕСТИМОСТИ ---
                elif cmd == "grant_role":
                    if len(parts) < 3:
                        print("Ошибка: Синтаксис: grant_role <nickname> <0-4>")
                        continue
                    nickname, role_lvl = parts[1], parts[2]
                    user = db_sess.query(User).filter(User.nickname == nickname).first()
                    if user:
                        user.role_level = int(role_lvl)
                        db_sess.commit()
                        print(f"Успех: Пользователю @{user.nickname} присвоена роль {user.role_level}")

                elif cmd == "grant_item":
                    if len(parts) < 5:
                        print("Ошибка: Синтаксис: grant_item <nickname> <type> <title> <value>")
                        continue
                    nickname, item_type, title = parts[1], parts[2], parts[3]
                    value = " ".join(parts[4:])
                    user = db_sess.query(User).filter(User.nickname == nickname).first()
                    if user:
                        item = db_sess.query(InventoryItem).filter(InventoryItem.item_type == item_type,
                                                                   InventoryItem.value == value).first()
                        if not item:
                            item = InventoryItem(title=title, item_type=item_type, value=value, description="CLI")
                            db_sess.add(item)
                            db_sess.flush()
                        if not db_sess.query(UserItem).filter(UserItem.user_id == user.id,
                                                              UserItem.item_id == item.id).first():
                            db_sess.add(UserItem(user_id=user.id, item_id=item.id, is_equipped=False))
                            db_sess.commit()
                            print(f"Успех: Выдано '{title}' для @{user.nickname}")

                # --- НОВАЯ КОМАНДА УДАЛЕНИЯ ПРЕДМЕТА v0.99.2.5fix2 ---
                elif cmd == "remove_item":
                    if len(parts) < 3:
                        print("Ошибка: Синтаксис: remove_item <nickname> <badge|name_color|profile_theme>")
                        continue

                    # ИСПРАВЛЕНО: Добавляем правильные индексы элементов списка
                    nickname = parts[1]  # Получит значение 'danil'
                    item_type = parts[2]  # Получит значение 'name_color'

                    user = db_sess.query(User).filter(User.nickname == nickname).first()
                    if not user:
                        print(f"Ошибка: Пользователь @{nickname} не найден.")
                        continue

                    # Ищем все записи этого типа в инвентаре данного юзера
                    user_items_to_remove = db_sess.query(UserItem).join(InventoryItem).filter(
                        UserItem.user_id == user.id,
                        InventoryItem.item_type == item_type
                    ).all()

                    if not user_items_to_remove:
                        print(f"Внимание: У пользователя @{user.nickname} нет предметов типа '{item_type}'")
                    else:
                        count = 0
                        for ui in user_items_to_remove:
                            db_sess.delete(ui)
                            count += 1
                        db_sess.commit()
                        print(
                            f"УСПЕХ: Из инвентаря @{user.nickname} полностью удалено предметов типа '{item_type}': {count}")
                else:
                    print(f"Неизвестная команда '{cmd}'. Наберите help для справки.")
            except Exception as e:
                print(f"Ошибка выполнения CLI-команды: {e}")
            finally:
                db_sess.close()

        except Exception as e:
            print(f"Ошибка консоли ввода: {e}")


def start_admin_cli():
    """Запускает поток прослушивания терминала в параллельном режиме"""
    cli_thread = threading.Thread(target=cli_console_worker, daemon=True)
    cli_thread.start()

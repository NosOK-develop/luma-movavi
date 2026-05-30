import datetime as dt
import sqlalchemy as sa
import sqlalchemy.orm as orm
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from . import db_session
from .db_session import SqlAlchemyBase

# Вспомогательная таблица для связи многие-ко-многим (Подписки/Читатели)
followers = sa.Table(
    'followers',
    SqlAlchemyBase.metadata,
    sa.Column('follower_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    sa.Column('followed_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    sa.Column('created_date', sa.DateTime, default=dt.datetime.now)
)


class User(SqlAlchemyBase, UserMixin):
    """Основной аккаунт Luma v0.99.2.5 (Кастомизация, инвентарь и система модерации)"""
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    nickname = sa.Column(sa.String, unique=True, nullable=False, index=True)
    name = sa.Column(sa.String, nullable=False)
    email = sa.Column(sa.String, unique=True, nullable=False)
    hashed_password = sa.Column(sa.String, nullable=False)
    about = sa.Column(sa.Text, nullable=True)
    created_date = sa.Column(sa.DateTime, default=dt.datetime.now)
    role_level = sa.Column(sa.Integer, default=0, nullable=False)

    avatar_path = sa.Column(sa.String, nullable=True, default=None)
    phone = sa.Column(sa.String, unique=True, nullable=True)
    social_telegram = sa.Column(sa.String, nullable=True)
    social_vk = sa.Column(sa.String, nullable=True)
    privacy_level = sa.Column(sa.Integer, default=0, nullable=False)
    active_badge_id = sa.Column(sa.Integer, nullable=True, default=None)

    # --- НОВОЕ ПОЛЕ СИСТЕМЫ МОДЕРАЦИИ v0.99.2.5 ---
    ban_until = sa.Column(sa.DateTime, nullable=True, default=None)  # Если None — бана нет

    # --- СВЯЗИ СОЦИАЛЬНОГО ГРАФА ---
    followed = orm.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=orm.backref('followers_list', lazy='dynamic'),
        lazy='dynamic'
    )

    media_profiles = orm.relationship('LumaMediaAccount', back_populates='luma_user', cascade='all, delete-orphan')
    inventory_items = orm.relationship('UserItem', back_populates='user', cascade='all, delete-orphan')

    posts = orm.relationship('Post', back_populates='author', cascade='all, delete-orphan')

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def get_role_name(self):
        roles = {0: "Пользователь", 1: "Верифицированный пользователь", 2: "Админ Media", 3: "Администратор",
                 4: "Главный администратор"}
        return roles.get(self.role_level, "Пользователь")

    def get_avatar_meta(self):
        if self.avatar_path:
            return {"type": "image", "src": self.avatar_path}
        google_colors = ["#1abc9c", "#2ecc71", "#3498db", "#9b59b6", "#e67e22", "#e74c3c", "#34495e"]
        random_color = google_colors[self.id % len(google_colors)]
        first_letter = self.name.upper() if self.name else (self.nickname.upper() if self.nickname else 'U')
        return {"type": "text", "letter": first_letter, "color": random_color}

    # --- МЕТОД ПРОВЕРКИ СТАТУСА БАНА ---
    def is_banned(self):
        """Проверяет, заблокирован ли пользователь в данный момент времени."""
        if not self.ban_until:
            return False
        # Если время бана больше текущего времени — бан активен
        return dt.datetime.now() < self.ban_until

    # --- СОЦИАЛЬНЫЕ МЕТОДЫ ---
    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def is_followed_by(self, user):
        return user.followed.filter(followers.c.followed_id == self.id).count() > 0

    def is_friend_with(self, user):
        return self.is_following(user) and self.is_followed_by(user)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    # --- ДИНАМИЧЕСКИЕ МЕТОДЫ ИНВЕНТАРЯ ---
    def get_equipped_badge(self):
        db_sess = db_session.create_session()
        try:
            from data.inventory import UserItem
            equipped = db_sess.query(UserItem).options(orm.joinedload(UserItem.item)).filter(
                UserItem.user_id == self.id,
                UserItem.is_equipped == True
            ).all()
            for user_item in equipped:
                if user_item.item and user_item.item.item_type == 'badge':
                    return user_item.item.value
            return None
        except Exception:
            return None
        finally:
            db_sess.close()

    def get_equipped_name_style(self):
        db_sess = db_session.create_session()
        try:
            from data.inventory import UserItem
            equipped = db_sess.query(UserItem).options(orm.joinedload(UserItem.item)).filter(
                UserItem.user_id == self.id,
                UserItem.is_equipped == True
            ).all()
            for user_item in equipped:
                if user_item.item and user_item.item.item_type == 'name_color':
                    return user_item.item.value
            return ""
        except Exception:
            return ""
        finally:
            db_sess.close()

    def get_equipped_theme(self):
        db_sess = db_session.create_session()
        try:
            from data.inventory import UserItem
            equipped = db_sess.query(UserItem).options(orm.joinedload(UserItem.item)).filter(
                UserItem.user_id == self.id,
                UserItem.is_equipped == True
            ).all()
            for user_item in equipped:
                if user_item.item and user_item.item.item_type == 'profile_theme':
                    return user_item.item.value
            return None
        except Exception:
            return None
        finally:
            db_sess.close()


class LumaMediaAccount(SqlAlchemyBase):
    __tablename__ = 'luma_media_accounts'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    channel_name = sa.Column(sa.String, unique=True, nullable=False)
    luma_user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    luma_user = orm.relationship('User', back_populates='media_profiles')

    description = sa.Column(sa.String, nullable=True, default='')
    avatar_path = sa.Column(sa.String, nullable=True, default='/static/images/default_channel_avatar.png')
    banner_path = sa.Column(sa.String, nullable=True, default='/static/images/default_channel_banner.png')
    player_icon_path = sa.Column(sa.String, nullable=True, default='/static/images/default_player_icon.png')

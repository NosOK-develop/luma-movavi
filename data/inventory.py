import datetime as dt
import sqlalchemy as sa
import sqlalchemy.orm as orm
from .db_session import SqlAlchemyBase


class InventoryItem(SqlAlchemyBase):
    """Каталог уникальных предметов кастомизации Luma v0.99.2.4"""
    __tablename__ = 'inventory_items'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String, nullable=False)

    # Тип предмета: 'badge' (значок), 'name_color' (перекрас), 'profile_theme' (тема профиля)
    item_type = sa.Column(sa.String, nullable=False, index=True)

    # Техническое значение (для значка — эмодзи/ссылка, для цвета — HEX/CSS класс, для темы — имя темы)
    value = sa.Column(sa.String, nullable=False)

    description = sa.Column(sa.String, nullable=True)
    created_date = sa.Column(sa.DateTime, default=dt.datetime.now)

    # Связь владения
    owners = orm.relationship('UserItem', back_populates='item', cascade='all, delete-orphan')


class UserItem(SqlAlchemyBase):
    """Таблица владения предметами (Инвентарь конкретного пользователя)"""
    __tablename__ = 'user_inventories'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = sa.Column(sa.Integer, sa.ForeignKey('inventory_items.id', ondelete='CASCADE'), nullable=False)

    is_equipped = sa.Column(sa.Boolean, default=False, nullable=False)  # Надет ли предмет сейчас
    acquired_date = sa.Column(sa.DateTime, default=dt.datetime.now)

    # Отношения
    item = orm.relationship('InventoryItem', back_populates='owners')
    user = orm.relationship('User', back_populates='inventory_items')

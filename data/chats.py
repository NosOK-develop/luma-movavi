import datetime as dt
import sqlalchemy as sa
import sqlalchemy.orm as orm
from .db_session import SqlAlchemyBase

class ChatGroup(SqlAlchemyBase):
    """
    Модель для Групп и Каналов.
    type: 'group' — обычная группа (пишут все участники)
    type: 'channel' — канал (пишут только админы)
    """
    __tablename__ = 'chat_groups'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String, nullable=False)
    type = sa.Column(sa.String, default='group', nullable=False)  # 'group' или 'channel'
    creator_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    created_date = sa.Column(sa.DateTime, default=dt.datetime.now)
    avatar_path = sa.Column(sa.String, default='static/images/chats/default_group.png')
    description = sa.Column(sa.Text, nullable=True)

    # Связь с участниками
    members = orm.relationship('GroupMember', back_populates='chat', cascade='all, delete-orphan')


class GroupMember(SqlAlchemyBase):
    """
    Промежуточная таблица связи пользователей с группами/каналами.
    role: 'creator' (создатель), 'admin' (администратор), 'member' (участник)
    """
    __tablename__ = 'group_members'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    chat_id = sa.Column(sa.Integer, sa.ForeignKey('chat_groups.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role = sa.Column(sa.String, default='member', nullable=False)  # 'creator', 'admin', 'member'
    joined_date = sa.Column(sa.DateTime, default=dt.datetime.now)

    chat = orm.relationship('ChatGroup', back_populates='members')
    user = orm.relationship('User')

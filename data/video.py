import datetime
import sqlalchemy as sa
import sqlalchemy.orm as orm
import zlib
from .db_session import SqlAlchemyBase


class Video(SqlAlchemyBase):
    __tablename__ = 'videos'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String(100), nullable=False, index=True)
    description = sa.Column(sa.Text, nullable=True)
    video_path = sa.Column(sa.String, nullable=False)
    thumbnail_path = sa.Column(sa.String, nullable=False)
    views = sa.Column(sa.Integer, default=0)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)

    # ИЗМЕНЕНО: Связь с конкретным медиа-каналом Luma Media вместо основного аккаунта Luma
    media_account_id = sa.Column(sa.Integer, sa.ForeignKey('luma_media_accounts.id', ondelete='CASCADE'),
                                 nullable=False)
    media_account = orm.relationship('LumaMediaAccount')

    likes = orm.relationship('VideoLike', back_populates='video', cascade='all, delete-orphan')
    dislikes = orm.relationship('VideoDislike', back_populates='video', cascade='all, delete-orphan')
    comments = orm.relationship('VideoComment', back_populates='video', order_by='VideoComment.created_date.desc()',
                                cascade='all, delete-orphan')

    def get_rating_score(self):
        likes_count = len(self.likes)
        penalty = len(self.dislikes) // 2
        return max(0, likes_count - penalty)


class VideoLike(SqlAlchemyBase):
    __tablename__ = 'video_likes'
    # Лайки ставятся от основного аккаунта пользователя
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    video_id = sa.Column(sa.Integer, sa.ForeignKey('videos.id', ondelete='CASCADE'), primary_key=True)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    video = orm.relationship('Video', back_populates='likes')


class VideoDislike(SqlAlchemyBase):
    __tablename__ = 'video_dislikes'
    # Дизлайки ставятся от основного аккаунта пользователя
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    video_id = sa.Column(sa.Integer, sa.ForeignKey('videos.id', ondelete='CASCADE'), primary_key=True)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    video = orm.relationship('Video', back_populates='dislikes')


class VideoComment(SqlAlchemyBase):
    __tablename__ = 'video_comments'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    video_id = sa.Column(sa.Integer, sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False, index=True)

    # Комментарии оставляются от основного аккаунта пользователя
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    _compressed_text = sa.Column('text', sa.LargeBinary, nullable=False)

    video = orm.relationship('Video', back_populates='comments')
    user = orm.relationship('User')

    @property
    def text(self):
        if self._compressed_text:
            return zlib.decompress(self._compressed_text).decode('utf-8')
        return ""

    @text.setter
    def text(self, value):
        if value:
            self._compressed_text = zlib.compress(value.encode('utf-8'))
        else:
            self._compressed_text = b""


class Clip(SqlAlchemyBase):
    """Модель для коротких вертикальных видео «Клипы»."""
    __tablename__ = 'clips'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String(100), nullable=False)
    video_path = sa.Column(sa.String, nullable=False)
    thumbnail_path = sa.Column(sa.String, nullable=False)
    views = sa.Column(sa.Integer, default=0)
    likes_count = sa.Column(sa.Integer, default=0)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)

    # ИЗМЕНЕНО: Клипы теперь тоже публикуются от имени канала Luma Media
    media_account_id = sa.Column(sa.Integer, sa.ForeignKey('luma_media_accounts.id', ondelete='CASCADE'),
                                 nullable=False)
    media_account = orm.relationship('LumaMediaAccount')

class ChannelSubscription(SqlAlchemyBase):
    """Таблица подписок пользователей на медиа-каналы Luma Media (v0.98.3.5)"""
    __tablename__ = 'channel_subscriptions'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    media_account_id = sa.Column(sa.Integer, sa.ForeignKey('luma_media_accounts.id', ondelete='CASCADE'), nullable=False)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)

    # Уникальный индекс, чтобы пользователь не мог подписаться дважды на один канал
    __table_args__ = (
        sa.UniqueConstraint('user_id', 'media_account_id', name='_user_channel_sub_uc'),
    )


class LumaRepost(SqlAlchemyBase):
    """Таблица репостов контента на каналы Luma Media (v0.98.4.2)"""
    __tablename__ = 'luma_reposts'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    # Канал LumaMediaAccount, КУДА делают репост
    media_account_id = sa.Column(sa.Integer, sa.ForeignKey('luma_media_accounts.id', ondelete='CASCADE'),
                                 nullable=False)

    # Полиморфные поля типа контента
    content_type = sa.Column(sa.String, nullable=False)  # 'video' или 'clip'
    content_id = sa.Column(sa.Integer, nullable=False)  # ID самого ролика или клипа

    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)

    # Защита от дубликатов: нельзя репостить один контент на один и тот же канал дважды
    __table_args__ = (
        sa.UniqueConstraint('media_account_id', 'content_type', 'content_id', name='_media_repost_uc'),
    )
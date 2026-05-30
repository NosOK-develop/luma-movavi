import sqlalchemy as sa
import zlib
from .db_session import SqlAlchemyBase


class PendingMessage(SqlAlchemyBase):
    """
    Таблица для временного хранения сообщений, которые получатели еще не увидели.
    Используется для минимизации постоянного дискового пространства SQLite.
    Как только адресат заходит в сеть, сообщения отсюда выгружаются и удаляются.
    """
    __tablename__ = 'pending_messages'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    sender_id = sa.Column(sa.Integer, nullable=False)

    # Может быть ID пользователя или ID группы/канала
    recipient_id = sa.Column(sa.Integer, nullable=False, index=True)

    # Типы: 'private', 'group', 'channel'
    chat_type = sa.Column(sa.String, default='private', nullable=False)

    # Типы содержимого: 'text', 'file', 'image', 'call_log'
    message_type = sa.Column(sa.String, default='text', nullable=False)

    # Экономичное хранение сжатого текста/метаданных
    _compressed_text = sa.Column('text', sa.LargeBinary, nullable=True)

    # Ссылки на медиафайлы (хранятся отдельно на диске в WebP/оптимизированном виде)
    file_url = sa.Column(sa.Text, nullable=True)
    file_name = sa.Column(sa.String, nullable=True)

    timestamp = sa.Column(sa.DateTime, default=sa.func.now())
    is_edited = sa.Column(sa.Boolean, default=False)

    # Автоматическое сжатие текста на лету через zlib
    @property
    def text(self):
        if self._compressed_text:
            return zlib.decompress(self._compressed_text).decode('utf-8')
        return None

    @text.setter
    def text(self, value):
        if value:
            self._compressed_text = zlib.compress(value.encode('utf-8'))
        else:
            self._compressed_text = None

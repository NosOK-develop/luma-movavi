import datetime as dt
import sqlalchemy as sa
import sqlalchemy.orm as orm
from . import db_session
from .db_session import SqlAlchemyBase

class Post(SqlAlchemyBase):
    __tablename__ = 'posts'

    id = sa.Column(sa.Integer, primary_key=True)
    title = sa.Column(sa.String)
    text = sa.Column(sa.Text)
    created_at = sa.Column(sa.DateTime)

    author_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'))
    author = orm.relationship('User', back_populates='posts')


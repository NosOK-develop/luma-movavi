import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session

SqlAlchemyBase = orm.declarative_base()
__factory = None


def global_init(db_url):
    global __factory

    if __factory:
        return

    if not db_url or not db_url.strip():
        raise Exception('Необходимо указать строку подключения к базе данных.')

    db_url = db_url.strip()

    # Корректируем строку под нужную СУБД
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif not db_url.startswith("sqlite://"):
        # Если это не postgres и не sqlite, значит передан чистый путь к файлу.
        # Оборачиваем его в валидный для SQLAlchemy протокол SQLite:
        db_url = f"sqlite:///{db_url}"

    # Для локального SQLite нужно отключать проверку потоков
    if "sqlite" in db_url:
        engine = sa.create_engine(db_url, echo=False, connect_args={"check_same_thread": False})
    else:
        engine = sa.create_engine(db_url, echo=False)

    __factory = orm.sessionmaker(bind=engine)

    from . import __all_models
    SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    global __factory
    return __factory()

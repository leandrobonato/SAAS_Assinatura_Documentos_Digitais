from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

if settings.database_url.startswith("sqlite:///"):
    # Built via sqlalchemy.engine.URL instead of passing the raw string to
    # create_engine: the project path contains accented characters that
    # broke make_url()'s string parser (ArgumentError) even though the path
    # itself is perfectly valid.
    db_url = URL.create("sqlite", database=settings.database_url.removeprefix("sqlite:///"))
else:
    db_url = settings.database_url

engine = create_engine(db_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

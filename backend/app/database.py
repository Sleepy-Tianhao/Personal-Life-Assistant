from pathlib import Path

from sqlalchemy import StaticPool, create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    connect_args: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {}

    if url.get_backend_name() == "sqlite":
        connect_args["check_same_thread"] = False
        if url.database and url.database != ":memory:":
            Path(url.database).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )
        if url.database in (None, "", ":memory:"):
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        **engine_kwargs,
    )

    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def build_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    # Importing models registers all mapped classes on Base.metadata.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.database import build_engine, build_session_factory, init_db
from app.routers.api import api_router


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    engine = build_engine(app_settings.database_url)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_db(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description=(
            "Local, single-user API for tasks, personal finance, schedules, diary entries, "
            "and imported class timetables. Timestamps are ISO 8601 UTC; timetable clock "
            "times are local wall-clock times."
        ),
        debug=app_settings.debug,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=app_settings.api_prefix)

    @app.get("/", tags=["System"])
    def root() -> dict[str, str]:
        return {
            "name": app_settings.app_name,
            "version": app_settings.app_version,
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    @app.get("/health", tags=["System"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

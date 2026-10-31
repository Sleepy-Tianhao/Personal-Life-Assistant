from fastapi import APIRouter

from app.routers import diary, ledger, schedules, timetables, todos

api_router = APIRouter()
api_router.include_router(todos.router)
api_router.include_router(ledger.router)
api_router.include_router(schedules.router)
api_router.include_router(diary.router)
api_router.include_router(timetables.router)

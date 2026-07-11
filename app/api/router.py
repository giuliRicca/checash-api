from fastapi import APIRouter

from app.api.routes import (
    accounts,
    activity,
    auth,
    categories,
    chat,
    transactions,
    transfers,
    users,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(activity.router)
api_router.include_router(categories.router)
api_router.include_router(accounts.router)
api_router.include_router(transactions.router)
api_router.include_router(transfers.router)
api_router.include_router(chat.router)

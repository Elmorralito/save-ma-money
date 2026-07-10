"""Version 1 API router aggregator."""

from fastapi import APIRouter

from papita_txnsapi.routers.v1 import accounts, auth, budgets, categories, health

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(accounts.router)
api_v1_router.include_router(categories.router)
api_v1_router.include_router(budgets.router)

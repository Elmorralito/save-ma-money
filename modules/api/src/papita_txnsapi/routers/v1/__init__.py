"""Version 1 API router aggregator."""

from fastapi import APIRouter

from papita_txnsapi.routers.v1 import budgets, health

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(budgets.router)

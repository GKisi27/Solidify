from fastapi import APIRouter
from app.api.routes.auth import router as auth_router
from app.api.routes.convert import router as convert_router
# from app.api.routes.estimate import router as estimate_router #Uncomment for estimate endpoint
from app.api.routes.health import router as health_router
from app.api.routes.history_endpoint import router as history_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(convert_router)
# api_router.include_router(estimate_router) #Uncomment for estimate endpoint
api_router.include_router(health_router)
api_router.include_router(history_router)
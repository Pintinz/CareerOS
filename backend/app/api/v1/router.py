from fastapi import APIRouter

from app.api.v1 import auth, health, profile

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])

# Future phases register their routers here, e.g.:
# from app.api.v1 import jobs, scholarships, ...
# api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

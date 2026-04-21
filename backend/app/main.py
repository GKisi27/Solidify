from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://127.0.0.1:3000", "http://localhost:5173","http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers
app.include_router(api_router)

@app.on_event("startup")
def startup_event():
    from app.services.cost_estimator import _ensure_kb
    from app.core.database import Base, engine
    import app.models

    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")

    Base.metadata.create_all(bind=engine)
    # Initialize knowledge base or other services
    # _ensure_kb()
    print("✅ API ready")

@app.get("/")
def root():
    return {
        "message": "2D CAD Cost Estimator and Conversion API is running",
        "docs": "/docs",
        "health": "/health",
    }
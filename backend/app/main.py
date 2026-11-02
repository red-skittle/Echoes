from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.seed.demo_data import seed_demo_data
from app.routers import (
    auth,
    streamers,
    videos,
    wiki,
    search,
    contributions,
    dashboard
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and seed initial demo dataset
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Afterlife — Every streamer has a story. Make it searchable.",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth.router)
app.include_router(streamers.router)
app.include_router(videos.router)
app.include_router(wiki.router)
app.include_router(search.router)
app.include_router(contributions.router)
app.include_router(dashboard.router)

@app.get("/")
def root():
    return {
        "platform": "Afterlife",
        "tagline": "Every streamer has a story. Make it searchable.",
        "status": "healthy",
        "version": settings.VERSION,
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}


from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.routers import (
    users_router,
    groups_router,
    expenses_router,
    balances_router,
    settlements_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist upon startup
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Production-ready Expense Sharing Backend Service (Decentro SDE Assignment)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend/API consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(users_router)
app.include_router(groups_router)
app.include_router(expenses_router)
app.include_router(balances_router)
app.include_router(settlements_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "1.0.0"
    }


@app.get("/", tags=["Root"])
def root():
    """Welcome endpoint providing documentation navigation."""
    return {
        "message": "Welcome to the Expense Sharing Service API",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }

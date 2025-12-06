from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.auth.router import router as auth_router
from app.admin.router import router as admin_router
from app.linkedin.router import router as linkedin_router
from app.linkedin.dependencies import initialize_linkedin_service, shutdown_linkedin_browser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - connect/disconnect from MongoDB and LinkedIn."""
    # Startup
    await connect_to_mongo()

    # Initialize LinkedIn service (auto-reconnect if previously connected)
    try:
        db = get_database()
        await initialize_linkedin_service(db)
        logger.info("LinkedIn service initialized")
    except Exception as e:
        logger.warning(f"LinkedIn initialization failed (non-fatal): {e}")

    yield

    # Shutdown
    await shutdown_linkedin_browser()
    await close_mongo_connection()


app = FastAPI(title="FB Leads API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(linkedin_router)


@app.get("/")
def root():
    return {"message": "Hello from FB Leads API! With new deploy."}


@app.get("/health")
def health():
    return {"status": "ok"}

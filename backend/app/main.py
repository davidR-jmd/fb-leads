from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import connect_to_mongo, close_mongo_connection
from app.auth.router import router as auth_router
from app.admin.router import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - connect/disconnect from MongoDB."""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(title="FB Leads API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {"message": "Hello from FB Leads API! With new deploy."}


@app.get("/health")
def health():
    return {"status": "ok"}

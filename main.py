from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from routes.dynamic import router as dynamic_router
from database import VALID_API_KEY, APP_ROOT_PATH

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if VALID_API_KEY is None:
        # If no API key is configured, allow access (for local dev dev/first run)
        # Or you might want to raise an error. Given the user's request, 
        # let's assume if it's set, we enforce it.
        return api_key_header
    
    if api_key_header == VALID_API_KEY:
        return api_key_header
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )

# Handle potential trailing/leading slashes for prefix
PREFIX = APP_ROOT_PATH.rstrip("/")
if PREFIX and not PREFIX.startswith("/"):
    PREFIX = "/" + PREFIX

app = FastAPI(
    title="Mongo Client API",
    # root_path handles proxy stripping, but for non-stripping proxies we also prefix routes
    root_path=PREFIX, 
    openapi_url="/openapi.json", # These are relative to root_path internally
    docs_url="/docs",
    redoc_url="/redoc",
    description="""
A generic RESTful API using FastAPI and MongoDB.

## Features

- **Authentication**: API Key protection via `X-API-KEY` header.
- **Dynamic Routes**: managing any collection.
- **Docker**: support for easy deployment.
    """,
    version="1.0.0"
)

# Use include_router with the prefix as well to ensure routes catch the full path
app.include_router(
    dynamic_router, 
    prefix="", # Routes in dynamic.py are already dynamic, prefix set at app level if needed
    tags=["dynamic"], 
    dependencies=[Depends(get_api_key)]
)

# For root path, we might need a redirect or alias if the proxy hits the full path
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Mongo Client API!", "root_path": PREFIX}

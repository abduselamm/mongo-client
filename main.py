from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from routes.dynamic import router as dynamic_router
from database import VALID_API_KEY

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

app = FastAPI(
    title="Mongo Client API",
    description="""
A generic RESTful API using FastAPI and MongoDB.

## Features

- **Authentication**: API Key protection via `X-API-KEY` header.
- **Dynamic Routes**: managing any collection.
- **Docker**: support for easy deployment.
    """,
    version="1.0.0"
)

app.include_router(
    dynamic_router, 
    tags=["dynamic"], 
    dependencies=[Depends(get_api_key)]
)

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Mongo Client API!"}

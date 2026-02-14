from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from routes.dynamic import router as dynamic_router
from database import VALID_API_KEY, APP_ROOT_PATH, MONGODB_URL

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    # Debug logging
    incoming_key = api_key_header if api_key_header else "MISSING"
    expected_prefix = str(VALID_API_KEY)[:3] + "..." if VALID_API_KEY else "NONE"
    
    if VALID_API_KEY is None:
        return api_key_header
    
    if api_key_header == VALID_API_KEY:
        return api_key_header
    
    print(f"Auth: Unauthorized access attempt. Received: '{incoming_key}', Expected: '{expected_prefix}'")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )

# Handle potential trailing/leading slashes for prefix
PREFIX = APP_ROOT_PATH.rstrip("/")
if PREFIX and not PREFIX.startswith("/"):
    PREFIX = "/" + PREFIX

# Log configuration on module load
print(f"--- Configuration ---")
print(f"MONGO_URI: {'[HIDDEN]' if MONGODB_URL else 'NOT SET'}")
print(f"API_KEY: {'[SET]' if VALID_API_KEY else 'NOT SET'}")
print(f"APP_ROOT_PATH: '{APP_ROOT_PATH}'")
print(f"Computed PREFIX: '{PREFIX}'")
print(f"---------------------")

app = FastAPI(
    title="Mongo Client API",
    # We use explicit prefixes for documentation to ensure it works even if root_path logic fails
    openapi_url=f"{PREFIX}/openapi.json" if PREFIX else "/openapi.json",
    docs_url=f"{PREFIX}/docs" if PREFIX else "/docs",
    redoc_url=f"{PREFIX}/redoc" if PREFIX else "/redoc",
    description="""
A generic RESTful API using FastAPI and MongoDB.

## Features

- **Authentication**: API Key protection via `X-API-KEY` header.
- **Dynamic Routes**: managing any collection.
- **Docker**: support for easy deployment.
    """,
    version="1.0.0"
)

# CORS Configuration
from fastapi.middleware.cors import CORSMiddleware
origins = [
    "http://localhost:5173",  
    "http://127.0.0.1:5173",
    "https://mongo-client-ui.vercel.app"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# if the proxy hits the full path but doesn't strip it.
app.include_router(
    dynamic_router, 
    prefix=PREFIX, 
    tags=["dynamic"], 
    dependencies=[Depends(get_api_key)]
)

@app.on_event("startup")
async def startup_db_client():
    try:
        # Ping the database to verify connectivity
        from database import client
        await client.admin.command('ping')
        print(f"MongoDB: Connected successfully!")
    except Exception as e:
        print(f"MongoDB: Connection failed! Error: {e}")

@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": "Welcome to the Mongo Client API!", 
        "root_path": PREFIX,
        "docs": f"{PREFIX}/docs" if PREFIX else "/docs"
    }

from fastapi import FastAPI
from routes.dynamic import router as dynamic_router

app = FastAPI(
    title="Mongo Client API",
    description="""
A generic RESTful API using FastAPI and MongoDB.

## Features

- **Dynamic Routes** for managing any collection.
- **Docker** support for easy deployment.
    """,
    version="1.0.0"
)

app.include_router(dynamic_router, tags=["dynamic"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Mongo Client API!"}

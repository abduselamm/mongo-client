# Mongo Client API

A generic, production-ready RESTful API built with **FastAPI** and **MongoDB** (Motor driver). This API is designed to be dynamic, allowing you to perform CRUD operations on *any* collection in your database without defining specific models.

## Features

- **Dynamic Routes**: Interact with any generic collection via the URL (e.g., `/users`, `/products`, `/logs`).
- **Bulk Operations**: Support for bulk document insertion.
- **Extended JSON Support**: Automatically parses MongoDB Extended JSON formats (e.g., `{"$oid": "..."}`, `{"$date": ...}`), making it compatible with data exported from MongoDB Compass or `mongoexport`.
- **Dockerized**: specific `Dockerfile` and `docker-compose.yml` for easy deployment.
- **Async I/O**: Non-blocking database operations using `motor`.
- **Interactive Documentation**: Auto-generated Swagger UI.

## Prerequisites

- **Docker** and **Docker Compose** (Recommended)
- *Or* Python 3.10+ and a running MongoDB instance.

## Getting Started

### Using Docker (Recommended)

1. **Clone the repository** (if applicable).
2. **Run the application**:
   ```bash
   docker-compose up --build
   ```
   This will start both the API service (port `8000`) and a MongoDB instance (port `27017`).

### Running Locally

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure Environment**:
   Ensure you have a `.env` file or set the `MONGODB_URL` environment variable.
   ```bash
   export MONGODB_URL="mongodb://localhost:27017/testdb"
   ```
3. **Start the server**:
   ```bash
   uvicorn main:app --reload
   ```

## Usage

Once running, access the interactive API documentation at:
**[http://localhost:8000/docs](http://localhost:8000/docs)**

### Endpoints

You can replace `{collection_name}` with the name of any collection you wish to use.

- **GET** `/{collection_name}/`: List all documents.
- **POST** `/{collection_name}/`: Create one or many documents.
- **GET** `/{collection_name}/{id}`: Get a document by ID.
- **PATCH** `/{collection_name}/{id}`: Partial update.
- **DELETE** `/{collection_name}/{id}`: Delete a document.

### Examples

**Create a User**
```bash
curl -X POST "http://localhost:8000/users/" \
     -H "Content-Type: application/json" \
     -d '{"name": "Alice", "role": "admin"}'
```

**Bulk Insert**
```bash
curl -X POST "http://localhost:8000/users/" \
     -H "Content-Type: application/json" \
     -d '[{"name": "Bob"}, {"name": "Charlie"}]'
```

**List Users**
```bash
curl "http://localhost:8000/users/"
```

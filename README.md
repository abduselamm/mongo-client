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

1.    - [x] Handle Extended JSON (`$oid`, `$date`) <!-- id: 28 -->
- [x] Vault Integration <!-- id: 29 -->
    - [x] Add `hvac` to `requirements.txt` <!-- id: 30 -->
    - [x] Update `database.py` to fetch secrets from Vault <!-- id: 31 -->
    - [x] Update `README.md` <!-- id: 32 -->
environment variable.
   ```bash
   export MONGODB_URL="mongodb://localhost:27017/testdb"
   ```
3. **Start the server**:
   ```bash
   uvicorn main:app --reload
   ```

## Vault Integration

The application can retrieve the MongoDB connection string securely from **HashiCorp Vault**.

### Configuration

The following environment variables (typically passed via K8s ConfigMap/Secrets) enable Vault integration:

- `VAULT_ADDR`: The address of your Vault server (e.g., `https://vault.example.com`).
- `VAULT_TOKEN`: A valid Vault token for authentication.
- `VAULT_SECRET_PATH`: The path to the secret (e.g., `myapp/database`).

The application expects a key named **`MONGO_URI`** inside the secret at the specified path.

### Fallback

If Vault configuration is missing, the application will fallback to:
1. Environment variable `MONGO_URI`.
2. Environment variable `MONGODB_URL`.
3. Local default: `mongodb://localhost:27017/testdb`.

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

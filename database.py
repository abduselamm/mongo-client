import os
import hvac
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

def get_mongo_db_name(vault_secrets=None):
    # 1. Try from Vault secrets if provided
    if vault_secrets and "MONGODB_DATABASE" in vault_secrets:
        print(f"Vault: Retrieved MONGODB_DATABASE.")
        return vault_secrets["MONGODB_DATABASE"]
    
    # 2. Fallback to environmental variables
    return os.environ.get("MONGODB_DATABASE") or os.environ.get("MONGO_DB") or "testdb"


def get_all_secrets():
    """Fetches all secrets from Vault once and returns them as a dict."""
    vault_addr = os.environ.get("VAULT_ADDR")
    vault_token = os.environ.get("VAULT_TOKEN")
    vault_path = os.environ.get("VAULT_PATH")

    if vault_addr and vault_token and vault_path:
        try:
            client = hvac.Client(url=vault_addr, token=vault_token)
            if client.is_authenticated():
                parts = vault_path.strip("/").split("/", 1)
                mount_point = parts[0]
                secret_path = parts[1] if len(parts) > 1 else ""
                
                try:
                    read_response = client.secrets.kv.v2.read_secret_version(mount_point=mount_point, path=secret_path)
                    secrets = read_response['data']['data']
                except Exception:
                    read_response = client.read(vault_path)
                    secrets = read_response['data'] if (read_response and 'data' in read_response) else {}

                if isinstance(secrets, dict) and "data" in secrets and "metadata" in secrets:
                    secrets = secrets["data"]
                
                return secrets
        except Exception as e:
            print(f"Vault error during bulk fetch: {e}")
    return {}

# Load everything
VAULT_SECRETS = get_all_secrets()

# 1. Mongo URL
def resolve_mongo_url(secrets):
    for key in ["MONGODB_URI", "MONGO_URI", "MONGODB_URL"]:
        if key in secrets:
            print(f"Vault: Found {key} in secret.")
            return secrets[key]
    return os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URL") or "mongodb://localhost:27017/testdb"

# 2. API Key
def resolve_api_key(secrets):
    if "API_KEY" in secrets:
        print(f"Vault: Found API_KEY in secret.")
        return secrets["API_KEY"]
    return os.environ.get("API_KEY")

# 3. DB Name
def resolve_db_name(secrets):
    if "MONGODB_DATABASE" in secrets:
        print(f"Vault: Found MONGODB_DATABASE in secret.")
        return secrets["MONGODB_DATABASE"]
    return os.environ.get("MONGODB_DATABASE") or os.environ.get("MONGO_DB") or "testdb"

# 4. Root Path
def resolve_root_path(secrets):
    return "/api/v1/mongo-client"

MONGODB_URL = resolve_mongo_url(VAULT_SECRETS)
VALID_API_KEY = resolve_api_key(VAULT_SECRETS)
MONGODB_NAME = resolve_db_name(VAULT_SECRETS)
APP_ROOT_PATH = resolve_root_path(VAULT_SECRETS)

client = AsyncIOMotorClient(MONGODB_URL)

try:
    # Use the DB name from Vault/Env if the URI doesn't have one
    db_name = client.get_database().name
    if db_name is None:
        db = client[MONGODB_NAME]
    else:
        db = client.get_database()
    print(f"MongoDB: Target database set to '{db.name}'.")
except Exception:
    db = client[MONGODB_NAME]
    print(f"MongoDB: Fallback target database set to '{db.name}'.")

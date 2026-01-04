import os
import hvac
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

def get_mongo_url():
    # 1. Try to get from HashiCorp Vault if configured
    vault_addr = os.environ.get("VAULT_ADDR")
    vault_token = os.environ.get("VAULT_TOKEN")
    vault_path = os.environ.get("VAULT_PATH")

    if vault_addr and vault_token and vault_path:
        try:
            client = hvac.Client(url=vault_addr, token=vault_token)
            if client.is_authenticated():
                print(f"Vault: Authenticated successfully to {vault_addr}")
                
                # Split path to handle custom mount points
                # e.g., "cbesuperapp/data/dev" -> mount="cbesuperapp", path="data/dev"
                parts = vault_path.strip("/").split("/", 1)
                mount_point = parts[0]
                secret_path = parts[1] if len(parts) > 1 else ""
                
                print(f"Vault: Attempting read from mount='{mount_point}', path='{secret_path}'")
                
                # Try KV v2 first
                try:
                    read_response = client.secrets.kv.v2.read_secret_version(mount_point=mount_point, path=secret_path)
                    secrets = read_response['data']['data']
                except Exception:
                    # Fallback to KV v1 if v2 fails
                    read_response = client.read(vault_path)
                    secrets = read_response['data'] if read_response else {}

                if "MONGODB_URI" in secrets:
                    print(f"Vault: Retrieved MONGODB_URI.")
                    return secrets["MONGODB_URI"]
                elif "MONGO_URI" in secrets:
                    print(f"Vault: Retrieved MONGO_URI.")
                    return secrets["MONGO_URI"]
                else:
                    print(f"Vault: Secret found at '{vault_path}' but MONGO_URI/MONGODB_URI keys are missing! Keys found: {list(secrets.keys())}")
            else:
                print(f"Vault: Authentication failed for {vault_addr}")
        except Exception as e:
            print(f"Vault Error: {e}")

    # 2. Fallback to environment variable or local .env
    print("Database: Using environment variable or local fallback for MongoDB URL.")
    return os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URL") or "mongodb://localhost:27017/testdb"

def get_api_key():
    # 1. Try to get from HashiCorp Vault if configured
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
                    secrets = read_response['data'] if read_response else {}

                if "API_KEY" in secrets:
                    print(f"Vault: Retrieved API_KEY.")
                    return secrets["API_KEY"]
                else:
                    print(f"Vault: API_KEY missing in secret at '{vault_path}'.")
        except Exception as e:
            print(f"Vault API Key Error: {e}")

    # 2. Fallback to environment variable or local .env
    return os.environ.get("API_KEY")

MONGODB_URL = get_mongo_url()
VALID_API_KEY = get_api_key()
APP_ROOT_PATH = os.environ.get("APP_ROOT_PATH", "")

client = AsyncIOMotorClient(MONGODB_URL)
db = client.get_database()

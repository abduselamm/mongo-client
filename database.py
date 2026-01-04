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
                    # Fallback to general read
                    read_response = client.read(vault_path)
                    secrets = read_response['data'] if (read_response and 'data' in read_response) else {}

                # If we have a 'data' key inside secrets, it's a double-wrapped KV v2 response
                if isinstance(secrets, dict) and "data" in secrets and "metadata" in secrets:
                    print(f"Vault: Detected nested KV v2 envelope, unwrapping 'data' key.")
                    secrets = secrets["data"]

                # Check for various possible keys
                found_url = None
                for key in ["MONGODB_URI", "MONGO_URI", "MONGODB_URL"]:
                    if key in secrets:
                        print(f"Vault: Retrieved {key}.")
                        found_url = secrets[key]
                        break
                
                if found_url:
                    return found_url
                else:
                    print(f"Vault: Path found, but no MongoDB URL keys discovered. Available keys: {list(secrets.keys())}")
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
                    secrets = read_response['data'] if (read_response and 'data' in read_response) else {}

                # Unwrap if nested
                if isinstance(secrets, dict) and "data" in secrets and "metadata" in secrets:
                    secrets = secrets["data"]

                if "API_KEY" in secrets:
                    print(f"Vault: Retrieved API_KEY.")
                    return secrets["API_KEY"]
                else:
                    print(f"Vault: API_KEY missing in secret at '{vault_path}'. Available keys: {list(secrets.keys())}")
            else:
                print(f"Vault: API Key Auth failed for {vault_addr}")
        except Exception as e:
            print(f"Vault API Key Error: {e}")

    # 2. Fallback to environment variable or local .env
    return os.environ.get("API_KEY")

MONGODB_URL = get_mongo_url()
VALID_API_KEY = get_api_key()
APP_ROOT_PATH = os.environ.get("APP_ROOT_PATH", "")

client = AsyncIOMotorClient(MONGODB_URL)
db = client.get_database()

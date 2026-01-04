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
                read_response = client.secrets.kv.v2.read_secret_version(path=vault_path)
                secrets = read_response['data']['data']
                if "MONGODB_URI" in secrets:
                    print(f"Vault: Reached secret path '{vault_path}' and retrieved MONGODB_URI.")
                    return secrets["MONGODB_URI"]
                else:
                    print(f"Vault: Reached secret path '{vault_path}' but 'MONGODB_URI' key is missing!")
            else:
                print(f"Vault: Authentication failed for {vault_addr}")
        except Exception as e:
            print(f"Vault Error: {e}")

    # 2. Fallback to environment variable or local .env
    print("Database: Using environment variable or local fallback for MongoDB URL.")
    return os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URL") or "mongodb://localhost:27017/testdb"

def get_api_key():
    # 1. Try to get from HashiCorp Vault if configured
    vault_addr = os.environ.get("VAULT_ADDR")
    vault_token = os.environ.get("VAULT_TOKEN")
    vault_path = os.environ.get("VAULT_SECRET_PATH")

    if vault_addr and vault_token and vault_path:
        try:
            client = hvac.Client(url=vault_addr, token=vault_token)
            if client.is_authenticated():
                read_response = client.secrets.kv.v2.read_secret_version(path=vault_path)
                secrets = read_response['data']['data']
                if "API_KEY" in secrets:
                    print(f"Vault: Retrieved API_KEY from path '{vault_path}'.")
                    return secrets["API_KEY"]
                else:
                    print(f"Vault: Key 'API_KEY' missing in path '{vault_path}'.")
        except Exception as e:
            print(f"Vault API Key Error: {e}")

    # 2. Fallback to environment variable or local .env
    return os.environ.get("API_KEY")

MONGODB_URL = get_mongo_url()
VALID_API_KEY = get_api_key()
APP_ROOT_PATH = os.environ.get("APP_ROOT_PATH", "")

client = AsyncIOMotorClient(MONGODB_URL)
db = client.get_database()

import os
import hvac
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

def get_mongo_url():
    # 1. Try to get from HashiCorp Vault if configured
    vault_addr = os.environ.get("VAULT_ADDR")
    vault_token = os.environ.get("VAULT_TOKEN")
    vault_path = os.environ.get("VAULT_SECRET_PATH")

    if vault_addr and vault_token and vault_path:
        try:
            client = hvac.Client(url=vault_addr, token=vault_token)
            # Check if authenticated
            if client.is_authenticated():
                # Assuming KV engine v2. adjust if v1 is used.
                read_response = client.secrets.kv.v2.read_secret_version(path=vault_path)
                secrets = read_response['data']['data']
                if "MONGO_URI" in secrets:
                    return secrets["MONGO_URI"]
        except Exception as e:
            print(f"Error fetching secret from Vault: {e}")

    # 2. Fallback to environment variable or local .env
    return os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URL") or "mongodb://localhost:27017/testdb"

MONGODB_URL = get_mongo_url()

client = AsyncIOMotorClient(MONGODB_URL)
db = client.get_database()

import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.environ.get("MONGODB_URL")

if not MONGODB_URL:
    # Fallback or raise error? It's better to default or inform.
    # For this task, I'll default if missing but the requirements said "Include environment variable handling"
    MONGODB_URL = "mongodb://localhost:27017/testdb"

client = AsyncIOMotorClient(MONGODB_URL)
db = client.get_database()

"""Single shared MongoDB client + GridFS bucket for the entire app."""
from __future__ import annotations
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

load_dotenv(Path(__file__).parent.parent / ".env")

_MONGO_URL = os.environ["MONGO_URL"]
_DB_NAME = os.environ["DB_NAME"]

client = AsyncIOMotorClient(_MONGO_URL)
db = client[_DB_NAME]

# Collections
messages = db["ai4life_messages"]
sessions = db["ai4life_sessions"]
telemetry = db["ai4life_telemetry"]

# GridFS bucket for large binary payloads (generated images)
images_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="ai4life_images")


async def close_db() -> None:
    client.close()

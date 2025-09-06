import asyncio
import sys
from sqlalchemy import text
from src.db import engine

# Cross-platform event loop fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def migrate_database():
    """Add missing columns to existing users table"""
    async with engine.begin() as conn:
        print("No migrations are pending.")

if __name__ == "__main__":
    asyncio.run(migrate_database())

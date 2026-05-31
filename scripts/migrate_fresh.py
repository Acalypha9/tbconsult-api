import asyncio
import os
import sys

# Add backend dir to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.db.models import Base
from sqlalchemy import text
from alembic.config import Config
from alembic import command

async def reset_database():
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        print("Dropping all application tables...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("Dropping alembic_version and LangChain pgvector tables...")
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS langchain_pg_embedding CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS langchain_pg_collection CASCADE;"))
        
        print("Ensuring pgvector extension is enabled...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        
    await engine.dispose()
    print("Database cleared and initialized.")

def run_migrations():
    print("Running alembic upgrade head...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Migration fresh complete!")

if __name__ == "__main__":
    # Change working directory to backend so alembic.ini is found
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    asyncio.run(reset_database())
    run_migrations()
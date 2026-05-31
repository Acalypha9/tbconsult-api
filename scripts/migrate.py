import asyncio
import os
import subprocess
import sys

# Add backend dir to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def ensure_vector_extension():
    print("Connecting to database to ensure pgvector extension is enabled...")
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    await engine.dispose()
    print("pgvector extension check complete.")

def main():
    # Change working directory to backend so alembic.ini is found
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    # Run the extension check
    asyncio.run(ensure_vector_extension())
    
    print("Running Alembic migrations (migrate)...")
    os.environ["PYTHONPATH"] = "."
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=".")
    if result.returncode != 0:
        print("Migration failed.")
        sys.exit(1)
    print("Migration successful.")

if __name__ == "__main__":
    main()
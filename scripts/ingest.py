import sys
import time
import uuid
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from app.core.config import settings

# Prevent encoding crashes in Windows console when printing/logging emojis
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def get_db_engine():
    """Returns a synchronous SQLAlchemy engine for PGVector."""
    sync_url = str(settings.DATABASE_URL).replace("postgresql+asyncpg://", "postgresql+psycopg://")
    return create_engine(sync_url, poolclass=NullPool)

def load_and_split_docs(source_dir: Path) -> list[Document]:
    """Loads PDF/TXT/MD files and splits them into parent-child chunks."""
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = []

    for file_path in source_dir.glob("**/*"):
        if not file_path.is_file() or file_path.name == "README.md":
            continue

        if file_path.suffix == ".pdf":
            loader = PyPDFLoader(str(file_path))
            content = "\n\n".join([page.page_content for page in loader.load()])
        elif file_path.suffix in [".md", ".txt"]:
            content = file_path.read_text(encoding="utf-8")
        else:
            continue

        print(f"Processing: {file_path.name}", flush=True)
        
        # Parent-child chunking structure
        parent_chunks = parent_splitter.split_text(content)
        for parent_chunk in parent_chunks:
            parent_id = str(uuid.uuid4())
            child_chunks = child_splitter.split_text(parent_chunk)
            for child_chunk in child_chunks:
                docs.append(Document(
                    page_content=child_chunk,
                    metadata={"source": file_path.name, "parent_id": parent_id}
                ))
    return docs

def main():
    # Default to the local 'sources' directory unless custom path is passed
    source_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "sources"
    print(f"Reading documents from local directory: {source_dir.resolve()}", flush=True)

    if not source_dir.exists():
        print(f"Error: Directory '{source_dir}' does not exist.", flush=True)
        sys.exit(1)

    try:
        docs = load_and_split_docs(source_dir)
        if not docs:
            print("No valid documents found.", flush=True)
            return

        print(f"Loaded {len(docs)} chunks. Initializing PGVector store...", flush=True)
        embeddings = OpenAIEmbeddings(
            api_key=settings.DIGITALOCEAN_API_KEY,
            base_url=settings.DIGITALOCEAN_BASE_URL,
            model=settings.EMBED_MODEL_ID,
            check_embedding_ctx_length=False,
            timeout=30.0,
        )
        
        vectorstore = PGVector(
            embeddings=embeddings,
            collection_name="knowledge_base",
            connection=get_db_engine(),
            use_jsonb=True,
        )
        vectorstore.create_tables_if_not_exists()

        # Upload in batches of 10 with a 2s delay to prevent API rate-limiting
        batch_size = 10
        total_batches = (len(docs) + batch_size - 1) // batch_size
        print("Uploading embeddings...", flush=True)
        
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i+batch_size]
            print(f"-> Batch {i//batch_size + 1}/{total_batches}", flush=True)
            vectorstore.add_documents(batch)
            time.sleep(2)

        print("Ingestion complete successfully!", flush=True)
    except Exception as e:
        print(f"Error during ingestion: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

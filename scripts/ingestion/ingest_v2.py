import argparse
import uuid
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_core.documents import Document
from app.core.config import settings

def get_sync_db_url():
    url = str(settings.DATABASE_URL)
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    return url

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=str, default=str(Path(__file__).parent.parent.parent.parent / "sources"))
    args = parser.parse_args()
    
    source_dir = Path(args.source_dir)
    
    embeddings_model = OpenAIEmbeddings(
        api_key=settings.DIGITALOCEAN_API_KEY,
        base_url=settings.DIGITALOCEAN_BASE_URL,
        model=settings.EMBED_MODEL_ID,
        check_embedding_ctx_length=False
    )
    
    vectorstore = PGVector(
        embeddings=embeddings_model,
        collection_name="knowledge_base",
        connection=get_sync_db_url(),
        use_jsonb=True,
    )
    
    # Create tables if they do not exist
    vectorstore.create_tables_if_not_exists()
    
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    
    docs_to_insert = []
    
    for file_path in source_dir.glob("**/*"):
        if file_path.is_file() and file_path.suffix in [".md", ".txt", ".pdf"]:
            if file_path.name == "README.md": continue
            if file_path.suffix == ".pdf":
                loader = PyPDFLoader(str(file_path))
                pages = loader.load()
                content = "\n\n".join([page.page_content for page in pages])
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
            parent_chunks = parent_splitter.split_text(content)
            for parent_chunk in parent_chunks:
                parent_id = str(uuid.uuid4())
                child_chunks = child_splitter.split_text(parent_chunk)
                for child_chunk in child_chunks:
                    doc = Document(
                        page_content=child_chunk,
                        metadata={
                            "source": file_path.name,
                            "parent_id": parent_id
                        }
                    )
                    docs_to_insert.append(doc)
    
    print(f"Total child chunks to embed: {len(docs_to_insert)}")
    
    # Batch add
    batch_size = 50
    for i in range(0, len(docs_to_insert), batch_size):
        batch = docs_to_insert[i:i+batch_size]
        print(f"Embedding batch {i//batch_size + 1}/{(len(docs_to_insert)//batch_size) + 1}...")
        vectorstore.add_documents(batch)
        
    print("Ingestion complete.")

if __name__ == "__main__":
    main()

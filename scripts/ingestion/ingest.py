import argparse
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.models import KnowledgeBase
from app.services.llm import LLMService

def get_sync_db_url():
    # Convert asyncpg:// to psycopg2:// for synchronous operations
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url

def main():
    parser = argparse.ArgumentParser(description="Ingest medical guidelines into pgvector")
    parser.add_argument("--source-dir", type=str, default="./scripts/ingestion/sources/", help="Directory containing source documents")
    args = parser.parse_args()
    
    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        print(f"Source directory {source_dir} does not exist.")
        return
        
    engine = create_engine(get_sync_db_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    llm_service = LLMService()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    
    total_docs = 0
    total_chunks = 0
    
    for file_path in source_dir.glob("**/*"):
        if file_path.is_file() and file_path.suffix in [".md", ".txt"]:
            if file_path.name == "README.md":
                continue
                
            total_docs += 1
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            chunks = text_splitter.split_text(content)
            
            # Determine category from filename (e.g., who_guideline_symptom-screening.md)
            filename = file_path.name
            category = "guideline"
            if "faq" in filename.lower():
                category = "faq"
            elif "protocol" in filename.lower():
                category = "protocol"
                
            for chunk in chunks:
                embedding = llm_service._embed_text_sync(chunk, input_type="search_document")
                
                kb_entry = KnowledgeBase(
                    content=chunk,
                    embedding=embedding,
                    metadata_={
                        "source": filename,
                        "category": category
                    }
                )
                db.add(kb_entry)
                total_chunks += 1
                
    db.commit()
    db.close()
    
    print(f"Ingestion complete: {total_docs} documents, {total_chunks} chunks embedded and stored.")

if __name__ == "__main__":
    main()

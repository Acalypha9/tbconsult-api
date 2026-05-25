import os
import sys
import glob

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector

def ingest_documents():
    sources_dir = os.path.join(os.path.dirname(__file__), "..", "sources")
    if not os.path.exists(sources_dir):
        print(f"Sources directory not found at {sources_dir}. Creating it.")
        os.makedirs(sources_dir)
        return

    files = glob.glob(os.path.join(sources_dir, "**", "*.md"), recursive=True) + \
            glob.glob(os.path.join(sources_dir, "**", "*.txt"), recursive=True)

    if not files:
        print("No markdown or text files found in sources directory.")
        return

    documents = []
    for file in files:
        print(f"Loading {file}")
        try:
            loader = TextLoader(file, encoding="utf-8")
            documents.extend(loader.load())
        except Exception as e:
            print(f"Error loading {file}: {e}")

    if not documents:
        print("No content loaded.")
        return

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    docs = text_splitter.split_documents(documents)
    print(f"Split into {len(docs)} chunks.")

    embeddings = OpenAIEmbeddings(
        openai_api_base=settings.DIGITALOCEAN_BASE_URL,
        openai_api_key=settings.DIGITALOCEAN_API_KEY,
        model=settings.EMBED_MODEL_ID,
        check_embedding_ctx_length=False
    )

    # Convert asyncpg to psycopg or psycopg2 for synchronous Langchain usage
    connection_string = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg")
    
    print("Initializing PGVector and storing documents...")
    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name="tbconsult_knowledge",
        connection=connection_string,
        use_jsonb=True
    )
    
    vectorstore.add_documents(docs)
    print("Ingestion complete!")

if __name__ == "__main__":
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    ingest_documents()
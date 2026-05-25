# TBConsult Backend - Medical Triage Chatbot

This is the FastAPI backend for the TBConsult medical triage chatbot. It uses LangGraph to orchestrate a deterministic RAG (Retrieval-Augmented Generation) pipeline powered by DigitalOcean Serverless Inference and pgvector.

## Architecture

- **Web Framework:** FastAPI
- **Orchestration:** LangGraph (State Machine for Triage)
- **Database:** PostgreSQL + pgvector (via SQLAlchemy)
- **Deployment:** Docker & Docker Compose (Targeted for DigitalOcean VPS)

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- DigitalOcean Account with Serverless Inference configured for Model Routing:
  - Utilizing DigitalOcean Inference Model Router (e.g., `router:[router-name]`).
  - Access to supported embedding models (e.g., `bge-m3` or DO native embeddings).

## Setup & Running Locally

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Set up Environment Variables:**
   Copy the example environment file and fill in your DigitalOcean credentials.
   ```bash
   cp .env.example .env
   ```
   *Note: Ensure you have `DIGITALOCEAN_API_KEY` configured.*

3. **Start the API:**
   ```bash
   docker-compose up -d --build
   ```
   
   The following service will start:
   - **api**: `http://localhost:8000`

4. **Verify Health:**
   Check if the system is running and dependencies are connected:
   ```bash
   curl http://localhost:8000/v1/health
   ```

## API Documentation

Once the app is running, interactive API documentation is available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Data Ingestion (RAG Knowledge Base)

To populate the chatbot's knowledge base with medical guidelines:

1. Place your medical `.txt` or `.md` files in `backend/scripts/ingestion/sources/`.
2. Run the ingestion script. You can run this inside the Docker container:
   ```bash
   docker-compose exec api python scripts/ingestion/ingest.py
   ```
   *This script chunks the documents, generates embeddings via the configured embedding model, and stores them in pgvector.*

## Development & Testing

If you want to run tests locally (outside Docker), set up a virtual environment:

```bash
# Create and activate virtual env
python -m venv .venv
source .venv/Scripts/activate

uvicorn app.main:app --reload --port 8000

# Install dependencies including dev tools
pip install -e .[dev]

# Run tests
pytest tests/ -v
```

## Security & Guardrails

The pipeline includes deterministic safety gates:
- **Red Flag Keyword Detection:** Instantly escalates cases mentioning blood, severe chest pain, or breathing issues (<5ms latency).
- **Output Guardrails:** Post-generation checks prevent the LLM from attempting formal diagnosis and enforce medical source citations.
- **Audit Logging:** Every user query, extracted entity, and LLM output is securely hashed and stored in Postgres.
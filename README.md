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

## Setup & Running the API

### 1. Configure Environment Variables
Copy the example environment file and fill in your DigitalOcean and database credentials.
```bash
# Navigate to the backend directory
cd backend

# Copy env template
cp .env.example .env
```
*Note: Make sure `DIGITALOCEAN_API_KEY`, `DIGITALOCEAN_BASE_URL`, and database credentials are correctly set.*

---

### Option A: Using Docker (Recommended for production-like environment)

1. **Start the API and Database:**
   ```bash
   docker-compose up -d --build
   ```
2. **Verify Health:**
   ```bash
   curl http://localhost:8000/v1/health
   ```

---

### Option B: Local Setup (Outside Docker)

1. **Set up the virtual environment:**
   ```bash
   python -m venv .venv
   ```
2. **Activate the environment:**
   * **Windows PowerShell:** `.venv\Scripts\Activate.ps1`
   * **Git Bash / macOS / Linux:** `source .venv/Scripts/activate`
3. **Install the package and dependencies:**
   ```bash
   # Install in editable mode along with dev dependencies
   pip install -e .
   ```
4. **Run the development server:**
   Always use the virtual environment's explicit Python path to avoid shell path resolution issues (especially on Windows):
   ```bash
   # Windows PowerShell
   .venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

   # Windows Git Bash
   .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

   # Unix / macOS
   .venv/bin/python -m uvicorn app.main:app --reload --port 8000
   ```

---

## Database Migrations

You must run migrations to set up or update the PostgreSQL tables.

### Option A: Using Docker
Ensure your docker container is running, then execute:
```bash
# Run pending migrations
docker-compose exec api python scripts/migrate.py

# Wipe database and run fresh migrations
docker-compose exec api python scripts/migrate_fresh.py
```

### Option B: Local Setup (Outside Docker)
Make sure your virtual environment is active, then execute:
```bash
# Windows PowerShell
.venv\Scripts\python scripts/migrate.py        # Run pending migrations
.venv\Scripts\python scripts/migrate_fresh.py  # Wipe database and run fresh migrations

# Windows Git Bash
.venv/Scripts/python scripts/migrate.py
.venv/Scripts/python scripts/migrate_fresh.py

# Unix / macOS
.venv/bin/python scripts/migrate.py
.venv/bin/python scripts/migrate_fresh.py
```

---

## Data Ingestion (RAG Knowledge Base)

To populate the chatbot's knowledge base with medical guidelines:

1. **Place source documents:** Copy your `.txt`, `.md`, or `.pdf` files into `backend/scripts/sources/`.
2. **Run ingestion script:**

### Option A: Using Docker
```bash
docker-compose exec api python scripts/ingest.py
```

### Option B: Local Setup (Outside Docker)
```bash
# Windows PowerShell
.venv\Scripts\python scripts/ingest.py

# Windows Git Bash
.venv/Scripts/python scripts/ingest.py

# Unix / macOS
.venv/bin/python scripts/ingest.py
```
*This script will chunk the documents, generate embeddings via the configured DigitalOcean Serverless Inference model, and store them in the pgvector database.*

---

## API Documentation

Once the app is running, interactive API documentation is available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running Tests

To run the unit and integration tests locally outside of Docker:
```bash
# Ensure virtual environment is active
pytest tests/ -v
```

## Security & Guardrails

The pipeline includes deterministic safety gates:
- **Red Flag Keyword Detection:** Instantly escalates cases mentioning blood, severe chest pain, or breathing issues (<5ms latency).
- **Output Guardrails:** Post-generation checks prevent the LLM from attempting formal diagnosis and enforce medical source citations.
- **Audit Logging:** Every user query, extracted entity, and LLM output is securely hashed and stored in Postgres.
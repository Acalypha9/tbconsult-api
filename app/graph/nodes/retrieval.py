import logging
import asyncio
from app.graph.state import TriageState
from app.services.llm import get_llm_service
from app.core.config import settings

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

# Lazy singletons – avoid instantiation at import time so that tests
# (and any other importer) don't need live API credentials.
_chat_model = None
_embeddings = None
_vectorstore = None
_retriever = None


def _get_chat_model():
    global _chat_model
    if _chat_model is None:
        _chat_model = ChatOpenAI(
            base_url=settings.DIGITALOCEAN_BASE_URL,
            api_key=settings.DIGITALOCEAN_API_KEY,
            model=settings.LLM_MODEL_ID,
            temperature=0.0,
        )
    return _chat_model


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            base_url=settings.DIGITALOCEAN_BASE_URL,
            api_key=settings.DIGITALOCEAN_API_KEY,
            model=settings.EMBED_MODEL_ID,
            check_embedding_ctx_length=False,
        )
    return _embeddings


def _get_sync_db_url() -> str:
    """
    Convert the async DATABASE_URL to a sync psycopg3-compatible URL
    for use with langchain-postgres PGVector.
    Handles postgres://, postgresql://, and postgresql+asyncpg:// variants.
    """
    raw_url = str(settings.DATABASE_URL)

    if raw_url.startswith("postgresql+asyncpg://"):
        return raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    elif raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif "+asyncpg" in raw_url:
        return raw_url.replace("+asyncpg", "+psycopg", 1)

    return raw_url


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        db_url = _get_sync_db_url()
        logger.info(f"Initializing PGVector singleton (DB scheme: {db_url.split('://')[0]})")
        _vectorstore = PGVector(
            embeddings=_get_embeddings(),
            collection_name="knowledge_base",
            connection=db_url,
            use_jsonb=True,
        )
    return _vectorstore


def _get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = _get_vectorstore().as_retriever(search_kwargs={"k": 5})
    return _retriever


async def retrieve_documents(state: TriageState) -> dict:
    extracted_entities = state.get("extracted_entities", {})
    symptoms = extracted_entities.get("symptoms", [])
    chat_history = state.get("chat_history", [])
    user_message = state.get("user_message", "")
    
    present_symptoms = [s.get("name") for s in symptoms if s.get("present")]
    
    # 1. Generate a history-aware query manually via LCEL to avoid langchain.chains dependency
    contextualize_q_system_prompt = (
        "You are an expert medical triage assistant. "
        "Review the entire chat history and the latest user response. "
        "Extract all medical symptoms, risk factors, durations, and conditions reported by the patient across the ENTIRE conversation. "
        "Combine them into a single, comprehensive medical search query for a database. "
        "If the user is answering 'no' or 'tidak' to a question, ensure you still include the previously mentioned positive symptoms in the query. "
        "Output ONLY the search query, without any conversational filler."
    )
    
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    
    # Create an LCEL chain for query rephrasing
    rephrase_chain = contextualize_q_prompt | _get_chat_model() | StrOutputParser()
    
    try:
        # Convert simple dict chat_history to Langchain Message objects
        lc_history = []
        for msg in chat_history:
            if msg.get('role') == 'user':
                lc_history.append(HumanMessage(content=msg.get('content', '')))
            elif msg.get('role') == 'assistant':
                lc_history.append(AIMessage(content=msg.get('content', '')))
                
        # Invoke history-aware query generation
        rephrased_query = await rephrase_chain.ainvoke({
            "chat_history": lc_history,
            "input": str(user_message)
        })

        rephrased_str = str(rephrased_query).strip()
        if not rephrased_str:
            rephrased_str = str(user_message)

        logger.debug(f"DEBUG RAG: Rephrased Query: {rephrased_str}")

        # Invoke vector retrieval with the rephrased query (using to_thread for sync invoke)
        retriever = _get_retriever()
        logger.debug("DEBUG RAG: Invoking to_thread retriever...")
        pg_timeout = settings.PGVECTOR_TIMEOUT_MS / 1000.0
        docs = await asyncio.wait_for(
            asyncio.to_thread(retriever.invoke, rephrased_str),
            timeout=pg_timeout,
        )
        logger.info(f"DEBUG RAG: Retriever returned {len(docs)} docs")

        retrieved_docs = []
        for doc in docs:
            retrieved_docs.append({
                "id": doc.metadata.get("parent_id", "unknown"),
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": 0.0  # Langchain retriever doesn't expose scores by default easily
            })

        return {"retrieved_docs": retrieved_docs[:5]}
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}", exc_info=True)
        return {"retrieved_docs": []}

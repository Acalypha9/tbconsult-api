import logging
import asyncio
from app.graph.state import TriageState
from app.services.llm import llm_service
from app.core.config import settings

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

# Initialize LangChain models wrapping DigitalOcean Serverless Inference
chat_model = ChatOpenAI(
    base_url=settings.DIGITALOCEAN_BASE_URL,
    api_key=settings.DIGITALOCEAN_API_KEY,
    model=settings.LLM_MODEL_ID,
    temperature=0.0
)
embeddings = OpenAIEmbeddings(
    base_url=settings.DIGITALOCEAN_BASE_URL,
    api_key=settings.DIGITALOCEAN_API_KEY,
    model=settings.EMBED_MODEL_ID,
    check_embedding_ctx_length=False
)

async def retrieve_documents(state: TriageState) -> dict:
    extracted_entities = state.get("extracted_entities", {})
    symptoms = extracted_entities.get("symptoms", [])
    chat_history = state.get("chat_history", [])
    user_message = state.get("user_message", "")
    
    present_symptoms = [s.get("name") for s in symptoms if s.get("present")]
    
    # Base connection string for psycopg3 used by langchain-postgres
    db_url = str(settings.DATABASE_URL).replace("postgresql+asyncpg", "postgresql+psycopg")
    
    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name="knowledge_base",
        connection=db_url,
        use_jsonb=True,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    
    # 1. Generate a history-aware query manually via LCEL to avoid langchain.chains dependency
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )
    
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    
    # Create an LCEL chain for query rephrasing
    rephrase_chain = contextualize_q_prompt | chat_model | StrOutputParser()
    
    try:
        # Convert simple dict chat_history to Langchain Message objects
        lc_history = []
        for msg in chat_history[-3:]:
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
            
        print(f"DEBUG RAG: Rephrased Query Type: {type(rephrased_query)}, Value: {rephrased_str}")
        
        # Invoke vector retrieval with the rephrased query (using to_thread for sync invoke)
        print("DEBUG RAG: Invoking to_thread retriever...")
        docs = await asyncio.to_thread(retriever.invoke, rephrased_str)
        print(f"DEBUG RAG: Retriever returned {len(docs)} docs")
        
        retrieved_docs = []
        for doc in docs:
            retrieved_docs.append({
                "id": doc.metadata.get("parent_id", "unknown"),
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": 0.0 # Langchain retriever doesn't expose scores by default easily
            })
            
        return {"retrieved_docs": retrieved_docs[:5]}
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        return {"retrieved_docs": []}

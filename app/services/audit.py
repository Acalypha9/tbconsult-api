import hashlib
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    @staticmethod
    async def log_triage(
        db: AsyncSession,
        session_id: str,
        user_query: str,
        extracted_entities: dict | None = None,
        red_flags_detected: bool = False,
        risk_level: str | None = None,
        retrieved_doc_ids: list[str] | None = None,
        llm_response: str | None = None,
        processing_time_ms: int = 0,
    ) -> None:
        try:
            query_hash = hashlib.sha256(user_query.encode("utf-8")).hexdigest()

            audit_log = AuditLog(
                session_id=session_id,
                user_query_hash=query_hash,
                extracted_entities=extracted_entities or {},
                red_flags_detected=red_flags_detected,
                risk_level=risk_level,
                retrieved_doc_ids=retrieved_doc_ids or [],
                llm_response=llm_response,
                processing_time_ms=processing_time_ms,
            )

            db.add(audit_log)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            await db.rollback()

"""Query API Route (Phase 4)

Endpoints for grounded question answering using local Qwen3 4B and database evidence.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import Message
from backend.api.schemas import QueryRequest, GroundedAnswer
from backend.generation.grounded_generator import GroundedAnswerGenerator
from backend.conversation.service import ConversationService
from backend.ollama_runtime.arbiter import OllamaBusyError, MemoryThresholdError
from backend.ai.providers.base import (
    AIProviderAuthError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIProviderError
)

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=GroundedAnswer)
def execute_grounded_query(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Submits a natural-language question against indexed document knowledge.
    Returns grounded answer with multi-stage verified citations, claim breakdown,
    numerical fact checks, and explicit abstention when ungrounded.
    """
    generator = GroundedAnswerGenerator(db=db)

    # 1. Establish persistent conversation thread & preserve document scope
    active_conv_id = request.conversation_id
    effective_doc_ids = request.document_ids
    history = None

    if active_conv_id:
        conv = ConversationService.get_conversation(db, active_conv_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{active_conv_id}' not found."
            )
        history = ConversationService.get_history(db, active_conv_id, limit=4)
        # If no explicit document_ids passed on follow-up, inherit scope from conversation's prior turn
        if not effective_doc_ids:
            last_assistant_msg = (
                db.query(Message)
                .filter(Message.conversation_id == active_conv_id, Message.role == "assistant")
                .order_by(Message.created_at.desc())
                .first()
            )
            if last_assistant_msg and last_assistant_msg.message_metadata:
                prev_doc_ids = last_assistant_msg.message_metadata.get("processing_metadata", {}).get("document_ids") or []
                if prev_doc_ids:
                    effective_doc_ids = prev_doc_ids
    else:
        # Auto-initialize persisted research session
        conv = ConversationService.create_conversation(db, title=request.question[:60])
        active_conv_id = conv.id

    # 2. Run grounded generation
    try:
        answer = generator.answer_question(
            question=request.question,
            document_ids=effective_doc_ids,
            conversation_id=active_conv_id,
            conversation_history=history
        )
    except OllamaBusyError as busy_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama inference engine is currently busy: {busy_err}"
        )
    except MemoryThresholdError as mem_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Query rejected to protect system memory headroom: {mem_err}"
        )
    except AIProviderAuthError as auth_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Provider authentication failed. Please check provider configuration in backend environment."
        )
    except AIProviderRateLimitError as rate_err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(rate_err)
        )
    except AIProviderTimeoutError as timeout_err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(timeout_err)
        )
    except AIProviderUnavailableError as unavail_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(unavail_err)
        )
    except AIProviderError as prov_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Provider error: {prov_err}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grounded query processing failed: {e}"
        )

    # 3. Persist conversation turn and citations
    ConversationService.record_turn(
        db=db,
        conversation_id=active_conv_id,
        question=request.question,
        answer=answer
    )
    answer.conversation_id = active_conv_id

    return answer

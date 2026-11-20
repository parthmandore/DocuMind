"""Conversations API Routes (Phase 4)

Endpoints for conversation creation, history retrieval, and lifecycle management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.api.schemas import (
    ConversationResponse,
    ConversationDetailResponse,
    CreateConversationRequest,
    UpdateConversationRequest
)
from backend.conversation.service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: CreateConversationRequest,
    db: Session = Depends(get_db)
):
    """Creates a new conversation thread."""
    conv = ConversationService.create_conversation(db, title=payload.title)
    return ConversationResponse.model_validate(conv)

@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = Query(default=None, description="Filter by title substring"),
    db: Session = Depends(get_db)
):
    """Lists conversations ordered by latest update."""
    convs = ConversationService.list_conversations(db, skip=skip, limit=limit, search=search)
    return [ConversationResponse.model_validate(c) for c in convs]

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation_details(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves conversation thread with associated message history."""
    conv = ConversationService.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found."
        )
    return ConversationDetailResponse.model_validate(conv)

@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: str,
    payload: UpdateConversationRequest,
    db: Session = Depends(get_db)
):
    """Renames an existing conversation thread."""
    conv = ConversationService.rename_conversation(db, conversation_id, title=payload.title)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found."
        )
    return ConversationResponse.model_validate(conv)

@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Deletes conversation and cascades deletion to all messages and citations."""
    success = ConversationService.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found."
        )
    return {"message": f"Conversation '{conversation_id}' successfully deleted."}

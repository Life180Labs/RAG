import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.conversation import MessageRole


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    document_id: uuid.UUID
    vector_index_id: uuid.UUID
    prompt_template_id: uuid.UUID | None
    title: str | None
    total_tokens: int
    created_at: datetime
    updated_at: datetime


class CreateConversationRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    prompt_template_id: uuid.UUID | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    token_count: int
    retrieval_id: uuid.UUID | None
    prompt_id: uuid.UUID | None
    llm_request_id: uuid.UUID | None
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class MessageTurnRead(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead


class ConversationSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    summary_text: str
    covers_message_count: int
    covers_up_to_message_id: uuid.UUID | None
    created_at: datetime


class ConversationMemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    repository_id: uuid.UUID
    custom_instructions: str | None
    preferences: dict | None
    created_at: datetime
    updated_at: datetime


class UpdateConversationMemoryRequest(BaseModel):
    custom_instructions: str | None = Field(default=None, max_length=4000)
    preferences: dict | None = None

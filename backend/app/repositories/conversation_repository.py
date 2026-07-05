import uuid

from sqlalchemy import select

from app.models.conversation import Conversation, ConversationMemory, ConversationSummary, Message
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    async def list_by_document(
        self, document_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.document_id == document_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_repository(self, repository_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(Conversation).where(Conversation.repository_id == repository_id)
        )
        return len(result.scalars().all())


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def list_by_conversation(
        self, conversation_id: uuid.UUID, *, after_message_id: uuid.UUID | None = None
    ) -> list[Message]:
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        if after_message_id is None:
            return messages
        for index, message in enumerate(messages):
            if message.id == after_message_id:
                return messages[index + 1 :]
        return messages


class ConversationSummaryRepository(BaseRepository[ConversationSummary]):
    model = ConversationSummary

    async def get_latest(self, conversation_id: uuid.UUID) -> ConversationSummary | None:
        result = await self.session.execute(
            select(ConversationSummary)
            .where(ConversationSummary.conversation_id == conversation_id)
            .order_by(ConversationSummary.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class ConversationMemoryRepository(BaseRepository[ConversationMemory]):
    model = ConversationMemory

    async def get_for_user_repository(
        self, user_id: uuid.UUID, repository_id: uuid.UUID
    ) -> ConversationMemory | None:
        result = await self.session.execute(
            select(ConversationMemory).where(
                ConversationMemory.user_id == user_id,
                ConversationMemory.repository_id == repository_id,
            )
        )
        return result.scalar_one_or_none()

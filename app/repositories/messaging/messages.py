"""
Message CRUD operations.

Handles creation and retrieval of messages within conversations,
including encryption/decryption of message content.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.db.core.models.user_data_models import Message, Conversation
from app.utils.decorators.database import with_session
from app.utils.time_utils import get_current_utc_time
from app.utils.encryption import encrypt_message, decrypt_message

logger = logging.getLogger(__name__)


@with_session('user')
def create_message(
    conversation_id: UUID,
    sender_id: UUID,
    content: str,
    message_type: str = 'text',
    session=None
) -> Optional[Message]:
    """
    Create a new message in a conversation.

    Also updates the conversation's updated_at timestamp.

    Args:
        conversation_id: Conversation UUID
        sender_id: Sender's user UUID
        content: Message content
        message_type: Type of message (text, image, file)

    Returns:
        Created Message object, or None if creation failed
    """
    try:
        # Encrypt message content before storing
        encrypted_content = encrypt_message(content)

        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=encrypted_content,
            message_type=message_type
        )
        session.add(message)

        # Update conversation's updated_at
        conversation = session.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            conversation.updated_at = get_current_utc_time()

        session.commit()
        session.refresh(message)
        return message
    except SQLAlchemyError as e:
        logger.error(f"Failed to create message: {e}")
        session.rollback()
        return None


@with_session('user')
def get_messages(
    conversation_id: UUID,
    limit: int = 50,
    before_timestamp: Optional[datetime] = None,
    session=None
) -> list[Message]:
    """
    Get messages in a conversation with cursor-based pagination.

    Args:
        conversation_id: Conversation UUID
        limit: Maximum number of messages to return
        before_timestamp: Only return messages created before this timestamp (for pagination)

    Returns:
        List of Message objects ordered by created_at descending (newest first)
    """
    try:
        query = session.query(Message).filter(
            Message.conversation_id == conversation_id
        )

        if before_timestamp:
            query = query.filter(Message.created_at < before_timestamp)

        messages = query.order_by(Message.created_at.desc()).limit(limit).all()

        # Decrypt message content
        for msg in messages:
            msg.content = decrypt_message(msg.content)

        # Reason: Reverse to return oldest-first for chat UI display
        # (query uses DESC to efficiently fetch most recent messages for pagination)
        return messages[::-1]
    except SQLAlchemyError as e:
        logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
        return []


@with_session('user')
def get_latest_message(conversation_id: UUID, session=None) -> Optional[Message]:
    """
    Get the most recent message in a conversation.

    Args:
        conversation_id: Conversation UUID

    Returns:
        Most recent Message object, or None if no messages exist
    """
    try:
        message = session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).first()

        # Decrypt message content
        if message:
            message.content = decrypt_message(message.content)

        return message
    except SQLAlchemyError as e:
        logger.error(f"Failed to get latest message for conversation {conversation_id}: {e}")
        return None

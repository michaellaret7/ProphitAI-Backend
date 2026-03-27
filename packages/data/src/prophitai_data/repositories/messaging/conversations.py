"""
Conversation CRUD operations.

Handles creation, retrieval, and lifecycle management of conversations
between two users in the user_data database.
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError

from prophitai_data.db.models.user import Conversation
from prophitai_data.session import with_session

logger = logging.getLogger(__name__)


@with_session('user')
def create_conversation(user_1_id: UUID, user_2_id: UUID, session=None) -> Optional[Conversation]:
    """
    Create a new conversation between two users.

    UUIDs are ordered to ensure consistency (smaller UUID is always user_1_id).
    This prevents duplicate conversations between the same two users.

    Args:
        user_1_id: First user's UUID
        user_2_id: Second user's UUID

    Returns:
        Created Conversation object, or None if creation failed
    """
    try:
        # Order UUIDs to ensure consistency and prevent duplicates
        if str(user_1_id) > str(user_2_id):
            user_1_id, user_2_id = user_2_id, user_1_id

        conversation = Conversation(user_1_id=user_1_id, user_2_id=user_2_id)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    except SQLAlchemyError as e:

        logger.error(f"Failed to create conversation: {e}")
        session.rollback()
        return None


@with_session('user')
def get_conversation(conversation_id: UUID, session=None) -> Optional[Conversation]:
    """
    Get a conversation by its ID.

    Args:
        conversation_id: Conversation UUID

    Returns:
        Conversation object or None if not found
    """
    try:
        return session.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
    except SQLAlchemyError as e:
        logger.error(f"Failed to get conversation {conversation_id}: {e}")
        return None


@with_session('user')
def get_conversation_by_users(user_1_id: UUID, user_2_id: UUID, session=None) -> Optional[Conversation]:
    """
    Get a conversation between two specific users.

    Handles UUID ordering internally to find the conversation regardless
    of the order the user IDs are provided.

    Args:
        user_1_id: First user's UUID
        user_2_id: Second user's UUID

    Returns:
        Conversation object or None if not found
    """
    try:
        # Order UUIDs to match how they're stored
        if str(user_1_id) > str(user_2_id):
            user_1_id, user_2_id = user_2_id, user_1_id

        return session.query(Conversation).filter(
            and_(
                Conversation.user_1_id == user_1_id,
                Conversation.user_2_id == user_2_id
            )
        ).first()
    except SQLAlchemyError as e:
        logger.error(f"Failed to get conversation for users {user_1_id}, {user_2_id}: {e}")
        return None


@with_session('user')
def get_or_create_conversation(user_1_id: UUID, user_2_id: UUID, session=None) -> Optional[Conversation]:
    """
    Get existing conversation between two users, or create one if it doesn't exist.

    Args:
        user_1_id: First user's UUID
        user_2_id: Second user's UUID

    Returns:
        Conversation object or None if operation failed
    """
    try:
        # Order UUIDs for consistency
        if str(user_1_id) > str(user_2_id):
            user_1_id, user_2_id = user_2_id, user_1_id

        # Try to find existing conversation
        conversation = session.query(Conversation).filter(
            and_(
                Conversation.user_1_id == user_1_id,
                Conversation.user_2_id == user_2_id
            )
        ).first()

        if conversation:
            return conversation

        # Create new conversation
        conversation = Conversation(user_1_id=user_1_id, user_2_id=user_2_id)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

        return conversation

    except SQLAlchemyError as e:
        logger.error(f"Failed to get or create conversation: {e}")
        session.rollback()
        return None


@with_session('user')
def get_user_conversations(user_id: UUID, session=None) -> list[Conversation]:
    """
    Get all conversations for a user, ordered by most recently updated.

    Args:
        user_id: User's UUID

    Returns:
        List of Conversation objects (empty list if none found or error)
    """
    try:
        return session.query(Conversation).filter(
            or_(
                Conversation.user_1_id == user_id,
                Conversation.user_2_id == user_id
            )
        ).order_by(Conversation.updated_at.desc()).all()
    except SQLAlchemyError as e:
        logger.error(f"Failed to get conversations for user {user_id}: {e}")
        return []

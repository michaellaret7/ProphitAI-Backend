"""
Read state tracking and user search operations.

Handles unread message counting, last-read timestamp updates,
and user search functionality for the messaging system.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import or_, func
from sqlalchemy.exc import SQLAlchemyError

from prophitai_data.db.models.user import Message, Conversation, User
from prophitai_data.session import with_session
from prophitai_shared import get_current_utc_time

logger = logging.getLogger(__name__)


@with_session('user')
def update_last_read(
    conversation_id: UUID,
    user_id: UUID,
    timestamp: Optional[datetime] = None,
    session=None
) -> bool:
    """
    Update a user's last read timestamp for a conversation.

    Args:
        conversation_id: Conversation UUID
        user_id: User's UUID
        timestamp: Timestamp to set (defaults to current UTC time)

    Returns:
        True if update succeeded, False otherwise
    """
    try:
        if timestamp is None:
            timestamp = get_current_utc_time()

        conversation = session.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return False

        if conversation.user_1_id == user_id:
            conversation.user_1_last_read_at = timestamp
        elif conversation.user_2_id == user_id:
            conversation.user_2_last_read_at = timestamp
        else:
            logger.warning(f"User {user_id} is not a participant in conversation {conversation_id}")
            return False

        session.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to update last read: {e}")
        session.rollback()
        return False


@with_session('user')
def get_unread_count(conversation_id: UUID, user_id: UUID, session=None) -> int:
    """
    Get the count of unread messages for a user in a conversation.

    Counts messages where:
    - created_at > user's last_read_at
    - sender_id != user_id (don't count own messages)

    Args:
        conversation_id: Conversation UUID
        user_id: User's UUID

    Returns:
        Number of unread messages (0 if error or conversation not found)
    """
    try:
        conversation = session.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            return 0

        # Determine user's last read timestamp
        if conversation.user_1_id == user_id:
            last_read = conversation.user_1_last_read_at
        elif conversation.user_2_id == user_id:
            last_read = conversation.user_2_last_read_at
        else:
            return 0

        # Build query for unread messages
        query = session.query(func.count(Message.id)).filter(
            Message.conversation_id == conversation_id,
            Message.sender_id != user_id  # Don't count own messages
        )

        if last_read is not None:
            query = query.filter(Message.created_at > last_read)

        return query.scalar() or 0
    except SQLAlchemyError as e:
        logger.error(f"Failed to get unread count: {e}")
        return 0


@with_session('user')
def get_total_unread_count(user_id: UUID, session=None) -> int:
    """
    Get the total count of unread messages across all conversations for a user.

    Args:
        user_id: User's UUID

    Returns:
        Total number of unread messages across all conversations
    """
    try:
        conversations = session.query(Conversation).filter(
            or_(
                Conversation.user_1_id == user_id,
                Conversation.user_2_id == user_id
            )
        ).all()

        total = 0
        for conv in conversations:
            # Determine user's last read timestamp
            if conv.user_1_id == user_id:
                last_read = conv.user_1_last_read_at
            else:
                last_read = conv.user_2_last_read_at

            # Count unread messages
            query = session.query(func.count(Message.id)).filter(
                Message.conversation_id == conv.id,
                Message.sender_id != user_id
            )

            if last_read is not None:
                query = query.filter(Message.created_at > last_read)

            total += query.scalar() or 0

        return total
    except SQLAlchemyError as e:
        logger.error(f"Failed to get total unread count for user {user_id}: {e}")
        return 0


@with_session('user')
def search_users(search_term: str, session=None) -> list[User]:
    """
    Search for users by name or email.

    Args:
        search_term: Search term to match against user names or emails

    Returns:
        List of User objects matching the search term
    """
    try:
        return session.query(User).filter(
            or_(
                User.first_name.ilike(f"%{search_term}%"),
                User.last_name.ilike(f"%{search_term}%"),
                User.email.ilike(f"%{search_term}%")
            )
        ).all()

    except SQLAlchemyError as e:

        logger.error(f"Failed to search users: {e}")
        return []

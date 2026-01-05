"""
Database operations for messaging system.

Handles CRUD operations for Conversations and Messages in the user_data database.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_, func
from sqlalchemy.exc import SQLAlchemyError

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Message, Conversation, User
from app.utils.decorators.database import with_session
from app.utils.time_utils import get_current_utc_time
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.encryption import encrypt_message, decrypt_message

logger = logging.getLogger(__name__)


# =============================================================================
# CONVERSATION OPERATIONS
# =============================================================================

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


# =============================================================================
# MESSAGE OPERATIONS
# =============================================================================

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

        return messages
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


# =============================================================================
# READ STATE OPERATIONS
# =============================================================================

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
    

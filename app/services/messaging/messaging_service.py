"""
Business logic for messaging system.

Orchestrates repository operations and WebSocket notifications.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User
from app.repositories import messaging_data as messages_repo
from app.models.messaging_models import (
    MessageResponse,
    ConversationResponse,
    ConversationListResponse,
    MessagesListResponse,
    UserSummary,
)
from app.utils.time_utils import get_current_utc_time

logger = logging.getLogger(__name__)


def _get_user_by_id(user_id: UUID) -> Optional[User]:
    """
    Get a user by their UUID.

    Args:
        user_id: User's UUID

    Returns:
        User object or None if not found
    """
    with UserSession() as session:
        return session.query(User).filter(User.id == user_id).first()


def _user_to_summary(user: User) -> UserSummary:
    """Convert a User model to UserSummary schema."""
    return UserSummary(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email
    )


def send_message(
    sender_id: UUID,
    recipient_id: UUID,
    content: str,
    message_type: str = "text"
) -> Optional[MessageResponse]:
    """
    Send a message from one user to another.

    Creates or retrieves the conversation between the two users,
    creates the message, and returns the message response.

    Args:
        sender_id: UUID of the message sender
        recipient_id: UUID of the message recipient
        content: Message content
        message_type: Type of message (text, image, file)

    Returns:
        MessageResponse or None if operation failed
    """
    try:
        # Get or create conversation between the two users
        conversation = messages_repo.get_or_create_conversation(sender_id, recipient_id)
        if not conversation:
            logger.error(f"Failed to get/create conversation for {sender_id} -> {recipient_id}")
            return None

        # Create the message
        message = messages_repo.create_message(
            conversation_id=conversation.id,
            sender_id=sender_id,
            content=content,
            message_type=message_type
        )
        if not message:
            logger.error(f"Failed to create message in conversation {conversation.id}")
            return None

        # Reason: Use original plaintext content, not message.content which is encrypted
        return MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            content=content,
            message_type=message.message_type,
            created_at=message.created_at
        )

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None


def get_conversations(user_id: UUID) -> ConversationListResponse:
    """
    Get all conversations for a user with metadata.

    Returns conversations sorted by most recent activity,
    including the other user's info, last message, and unread count.

    Args:
        user_id: UUID of the user

    Returns:
        ConversationListResponse with list of conversations and total unread count
    """
    try:
        conversations = messages_repo.get_user_conversations(user_id)
        total_unread = 0
        result = []

        for conv in conversations:
            # Determine the other user in the conversation
            other_user_id = conv.user_2_id if conv.user_1_id == user_id else conv.user_1_id
            other_user = _get_user_by_id(other_user_id)

            if not other_user:
                logger.warning(f"Other user {other_user_id} not found for conversation {conv.id}")
                continue

            # Get last message
            last_message = messages_repo.get_latest_message(conv.id)
            last_message_response = None
            if last_message:
                last_message_response = MessageResponse(
                    id=last_message.id,
                    conversation_id=last_message.conversation_id,
                    sender_id=last_message.sender_id,
                    content=last_message.content,
                    message_type=last_message.message_type,
                    created_at=last_message.created_at
                )

            # Get unread count for this conversation
            unread_count = messages_repo.get_unread_count(conv.id, user_id)
            total_unread += unread_count

            result.append(ConversationResponse(
                id=conv.id,
                other_user=_user_to_summary(other_user),
                last_message=last_message_response,
                unread_count=unread_count,
                updated_at=conv.updated_at
            ))

        return ConversationListResponse(
            conversations=result,
            total_unread=total_unread
        )

    except Exception as e:
        logger.error(f"Error getting conversations for user {user_id}: {e}")
        return ConversationListResponse(conversations=[], total_unread=0)


def get_messages(
    user_id: UUID,
    conversation_id: UUID,
    limit: int = 50,
    before: Optional[datetime] = None
) -> Optional[MessagesListResponse]:
    """
    Get paginated messages for a conversation.

    Verifies the user is a participant in the conversation before
    returning messages.

    Args:
        user_id: UUID of the requesting user (for authorization)
        conversation_id: UUID of the conversation
        limit: Maximum number of messages to return
        before: Only return messages before this timestamp (for pagination)

    Returns:
        MessagesListResponse or None if conversation not found or user not authorized
    """
    try:
        # Verify user is part of this conversation
        conversation = messages_repo.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return None

        if conversation.user_1_id != user_id and conversation.user_2_id != user_id:
            logger.warning(f"User {user_id} not authorized for conversation {conversation_id}")
            return None

        # Get messages
        messages = messages_repo.get_messages(conversation_id, limit + 1, before)

        # Check if there are more messages
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]

        message_responses = [
            MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                sender_id=msg.sender_id,
                content=msg.content,
                message_type=msg.message_type,
                created_at=msg.created_at
            )
            for msg in messages
        ]

        return MessagesListResponse(
            messages=message_responses,
            has_more=has_more
        )

    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
        return None


def mark_conversation_read(user_id: UUID, conversation_id: UUID) -> bool:
    """
    Mark all messages in a conversation as read for a user.

    Updates the user's last_read_at timestamp for the conversation.

    Args:
        user_id: UUID of the user marking as read
        conversation_id: UUID of the conversation

    Returns:
        True if successful, False otherwise
    """
    try:
        # Verify user is part of this conversation
        conversation = messages_repo.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return False

        if conversation.user_1_id != user_id and conversation.user_2_id != user_id:
            logger.warning(f"User {user_id} not authorized for conversation {conversation_id}")
            return False

        return messages_repo.update_last_read(conversation_id, user_id)

    except Exception as e:
        logger.error(f"Error marking conversation {conversation_id} as read: {e}")
        return False


def get_unread_count(user_id: UUID, conversation_id: Optional[UUID] = None) -> int:
    """
    Get unread message count for a user.

    If conversation_id is provided, returns count for that conversation only.
    Otherwise, returns total unread count across all conversations.

    Args:
        user_id: UUID of the user
        conversation_id: Optional UUID of a specific conversation

    Returns:
        Number of unread messages
    """
    try:
        if conversation_id:
            # Verify user is part of this conversation
            conversation = messages_repo.get_conversation(conversation_id)
            if not conversation:
                return 0
            if conversation.user_1_id != user_id and conversation.user_2_id != user_id:
                return 0
            return messages_repo.get_unread_count(conversation_id, user_id)
        else:
            return messages_repo.get_total_unread_count(user_id)

    except Exception as e:
        logger.error(f"Error getting unread count for user {user_id}: {e}")
        return 0


def get_or_create_conversation(user_id: UUID, other_user_id: UUID) -> Optional[ConversationResponse]:
    """
    Get or create a conversation between two users.

    Args:
        user_id: UUID of the requesting user
        other_user_id: UUID of the other user

    Returns:
        ConversationResponse or None if operation failed
    """
    try:
        conversation = messages_repo.get_or_create_conversation(user_id, other_user_id)
        if not conversation:
            return None

        other_user = _get_user_by_id(other_user_id)
        if not other_user:
            logger.warning(f"Other user {other_user_id} not found")
            return None

        # Get last message if exists
        last_message = messages_repo.get_latest_message(conversation.id)
        last_message_response = None
        if last_message:
            last_message_response = MessageResponse(
                id=last_message.id,
                conversation_id=last_message.conversation_id,
                sender_id=last_message.sender_id,
                content=last_message.content,
                message_type=last_message.message_type,
                created_at=last_message.created_at
            )

        unread_count = messages_repo.get_unread_count(conversation.id, user_id)

        return ConversationResponse(
            id=conversation.id,
            other_user=_user_to_summary(other_user),
            last_message=last_message_response,
            unread_count=unread_count,
            updated_at=conversation.updated_at
        )

    except Exception as e:
        logger.error(f"Error getting/creating conversation: {e}")
        return None

"""
Messaging repository package.

Re-exports all messaging database operations for convenient importing.
"""
from prophitai_data.repositories.messaging.conversations import (
    create_conversation,
    get_conversation,
    get_conversation_by_users,
    get_or_create_conversation,
    get_user_conversations,
)
from prophitai_data.repositories.messaging.messages import (
    create_message,
    get_messages,
    get_latest_message,
)
from prophitai_data.repositories.messaging.read_state import (
    get_unread_count,
    get_total_unread_count,
    update_last_read,
    search_users,
)

__all__ = [
    # Conversations
    "create_conversation",
    "get_conversation",
    "get_conversation_by_users",
    "get_or_create_conversation",
    "get_user_conversations",
    # Messages
    "create_message",
    "get_messages",
    "get_latest_message",
    # Read state
    "get_unread_count",
    "get_total_unread_count",
    "update_last_read",
    "search_users",
]

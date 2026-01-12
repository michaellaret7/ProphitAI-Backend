"""Script to delete conversation between ProphitAI Messenger and a user."""

from uuid import UUID
from sqlalchemy import and_, or_

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User, Conversation, Message

PROPHITAI_SYSTEM_USER_ID = UUID("e7ab723f-a415-4f3c-8445-4eaf08cf605e")


def delete_system_conversation(user_email: str):
    """Delete conversation and messages between system user and specified user."""
    with UserSession() as session:
        # Find the user
        user = session.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"User not found: {user_email}")
            return

        print(f"Found user: {user.first_name} {user.last_name} ({user.id})")

        # Find conversation between system user and this user
        # UUIDs are ordered in conversations, so check both orderings
        conversation = session.query(Conversation).filter(
            or_(
                and_(
                    Conversation.user_1_id == PROPHITAI_SYSTEM_USER_ID,
                    Conversation.user_2_id == user.id
                ),
                and_(
                    Conversation.user_1_id == user.id,
                    Conversation.user_2_id == PROPHITAI_SYSTEM_USER_ID
                )
            )
        ).first()

        if not conversation:
            print("No conversation found between ProphitAI Messenger and this user.")
            return

        print(f"Found conversation: {conversation.id}")

        # Delete all messages in the conversation
        message_count = session.query(Message).filter(
            Message.conversation_id == conversation.id
        ).delete()
        print(f"Deleted {message_count} messages")

        # Delete the conversation
        session.delete(conversation)
        session.commit()
        print("Deleted conversation successfully")


if __name__ == "__main__":
    delete_system_conversation("michaellaret7@gmail.com")

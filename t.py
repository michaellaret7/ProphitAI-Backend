"""Quick script to get user UUID and conversation IDs for herman@laret.com"""
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User, Conversation
from sqlalchemy import or_

session = UserSession()

# Find user by email
user = session.query(User).filter(User.email == "herman@laret.com").first()

if not user:
    print("User herman@laret.com not found")
else:
    print(f"User: {user.first_name} {user.last_name}")
    print(f"UUID: {user.id}")
    print(f"Email: {user.email}")
    print()

    # Find all conversations where user is either user_1 or user_2
    conversations = session.query(Conversation).filter(
        or_(
            Conversation.user_1_id == user.id,
            Conversation.user_2_id == user.id
        )
    ).all()

    print(f"Conversations ({len(conversations)}):")
    for conv in conversations:
        other_user_id = conv.user_2_id if conv.user_1_id == user.id else conv.user_1_id
        other_user = session.query(User).filter(User.id == other_user_id).first()
        other_name = f"{other_user.first_name} {other_user.last_name}" if other_user else "Unknown"
        print(f"  - ID: {conv.id} (with {other_name})")

session.close()

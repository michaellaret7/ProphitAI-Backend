"""Add messaging tables for DM conversations

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2025-01-05

Creates tables for 1-on-1 direct messaging:
- conversations: Stores DM conversations between two users
- messages: Stores individual messages within conversations

Read state is tracked via last_read_at timestamps per user on the conversation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, None] = 'f6g7h8i9j0k1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_1_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_2_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_1_last_read_at', sa.DateTime(), nullable=True),
        sa.Column('user_2_last_read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_1_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_2_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversations_user_1_id', 'conversations', ['user_1_id'], unique=False)
    op.create_index('ix_conversations_user_2_id', 'conversations', ['user_2_id'], unique=False)
    # Unique constraint to prevent duplicate conversations between same users
    op.create_unique_constraint('uq_conversation_users', 'conversations', ['user_1_id', 'user_2_id'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(20), nullable=True, default='text'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'], unique=False)
    op.create_index('ix_messages_sender_id', 'messages', ['sender_id'], unique=False)
    op.create_index('ix_messages_created_at', 'messages', ['created_at'], unique=False)
    # Composite index for efficient message pagination queries
    op.create_index('ix_messages_conversation_created', 'messages', ['conversation_id', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop messages table and indexes
    op.drop_index('ix_messages_conversation_created', table_name='messages')
    op.drop_index('ix_messages_created_at', table_name='messages')
    op.drop_index('ix_messages_sender_id', table_name='messages')
    op.drop_index('ix_messages_conversation_id', table_name='messages')
    op.drop_table('messages')

    # Drop conversations table and indexes
    op.drop_constraint('uq_conversation_users', 'conversations', type_='unique')
    op.drop_index('ix_conversations_user_2_id', table_name='conversations')
    op.drop_index('ix_conversations_user_1_id', table_name='conversations')
    op.drop_table('conversations')

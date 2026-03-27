"""Tests for message repository encryption/decryption behavior.

Validates that messages are encrypted on create and decrypted on read,
using real Fernet encryption (conftest sets MESSAGE_ENCRYPTION_KEY).
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch, call

from prophitai_data.internal.encryption import encrypt_message, decrypt_message


# ================================
# --> Helper funcs
# ================================

def _make_mock_session():
    """Create a mock SQLAlchemy session with chainable query methods."""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.order_by.return_value = session
    session.limit.return_value = session
    session.first.return_value = None
    session.all.return_value = []
    return session


def _mock_get_session_class(mock_session):
    """Return a factory that yields a callable returning mock_session."""
    def _factory(session_type):
        return lambda: mock_session
    return _factory


def _make_mock_message(content, conversation_id=None):
    """Create a mock Message object with given content."""
    msg = MagicMock()
    msg.content = content
    msg.conversation_id = conversation_id or uuid.uuid4()
    msg.sender_id = uuid.uuid4()
    msg.message_type = "text"
    msg.created_at = MagicMock()
    msg.created_at.desc.return_value = "desc"
    return msg


class TestCreateMessageEncryption:
    """Verify that create_message encrypts content before storing."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_create_message_encrypts_content(self, mock_gsc):
        """The content stored in the session is NOT the plaintext."""
        session = _make_mock_session()
        # Reason: create_message queries Conversation to update updated_at
        session.first.return_value = MagicMock()
        mock_gsc.side_effect = _mock_get_session_class(session)

        from prophitai_data.repositories.messaging.messages import create_message

        conv_id = uuid.uuid4()
        sender_id = uuid.uuid4()
        plaintext = "Hello, this is a secret message!"

        create_message(conv_id, sender_id, plaintext)

        # Reason: session.add() is called with a Message object whose content is encrypted
        assert session.add.called
        added_obj = session.add.call_args[0][0]
        stored_content = added_obj.content

        # The stored content must NOT be the plaintext
        assert stored_content != plaintext

        # The stored content must be decryptable back to plaintext
        assert decrypt_message(stored_content) == plaintext


class TestGetMessagesDecryption:
    """Verify that get_messages decrypts content on read."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_get_messages_decrypts_content(self, mock_gsc):
        """Messages returned by get_messages have decrypted content."""
        session = _make_mock_session()

        # Reason: Encrypt messages as they would be stored in the DB
        plaintext_1 = "First secret message"
        plaintext_2 = "Second secret message"
        encrypted_1 = encrypt_message(plaintext_1)
        encrypted_2 = encrypt_message(plaintext_2)

        msg1 = _make_mock_message(encrypted_1)
        msg2 = _make_mock_message(encrypted_2)
        session.all.return_value = [msg2, msg1]

        mock_gsc.side_effect = _mock_get_session_class(session)

        from prophitai_data.repositories.messaging.messages import get_messages

        conv_id = uuid.uuid4()
        result = get_messages(conv_id)

        # Reason: get_messages reverses the DESC-ordered results for chat UI
        assert len(result) == 2
        assert result[0].content == plaintext_1
        assert result[1].content == plaintext_2


class TestGetLatestMessageDecryption:
    """Verify that get_latest_message decrypts content."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_get_latest_message_decrypts(self, mock_gsc):
        """The latest message has its content decrypted."""
        session = _make_mock_session()

        plaintext = "Latest secret message"
        encrypted = encrypt_message(plaintext)

        msg = _make_mock_message(encrypted)
        session.first.return_value = msg

        mock_gsc.side_effect = _mock_get_session_class(session)

        from prophitai_data.repositories.messaging.messages import get_latest_message

        conv_id = uuid.uuid4()
        result = get_latest_message(conv_id)

        assert result is not None
        assert result.content == plaintext

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_get_latest_message_none(self, mock_gsc):
        """get_latest_message returns None when no messages exist."""
        session = _make_mock_session()
        session.first.return_value = None
        mock_gsc.side_effect = _mock_get_session_class(session)

        from prophitai_data.repositories.messaging.messages import get_latest_message

        result = get_latest_message(uuid.uuid4())
        assert result is None

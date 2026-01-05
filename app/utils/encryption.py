"""
Encryption utilities for message content.

Provides Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) for
encrypting messages at rest in the database.
"""
import os
from cryptography.fernet import Fernet, InvalidToken

_cipher = None


def get_cipher() -> Fernet:
    """
    Get or create the Fernet cipher instance.

    Uses lazy initialization with a module-level singleton.

    Returns:
        Fernet cipher instance

    Raises:
        ValueError: If MESSAGE_ENCRYPTION_KEY is not set in environment
    """
    global _cipher
    if _cipher is None:
        key = os.getenv("MESSAGE_ENCRYPTION_KEY")
        if not key:
            raise ValueError("MESSAGE_ENCRYPTION_KEY not set in .env")
        _cipher = Fernet(key.encode())
    return _cipher


def encrypt_message(content: str) -> str:
    """
    Encrypt message content.

    Args:
        content: Plaintext message content

    Returns:
        Base64-encoded encrypted string
    """
    return get_cipher().encrypt(content.encode()).decode()


def decrypt_message(encrypted_content: str) -> str:
    """
    Decrypt message content.

    Args:
        encrypted_content: Base64-encoded encrypted string

    Returns:
        Decrypted plaintext message

    Raises:
        InvalidToken: If decryption fails (invalid key or corrupted data)
    """
    try:
        return get_cipher().decrypt(encrypted_content.encode()).decode()
    except InvalidToken:
        # Reason: Return placeholder if decryption fails (e.g., old unencrypted messages)
        return "[Unable to decrypt message]"

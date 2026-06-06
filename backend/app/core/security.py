import os
import logging
from cryptography.fernet import Fernet
import keyring

logger = logging.getLogger(__name__)

# Dynamically resolve key file path relative to workspace root
KEY_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "keys", "encryption.key")
)

def _load_or_generate_key() -> bytes:
    key_str = None
    
    # 1. Try Ubuntu GNOME Keyring
    try:
        key_str = keyring.get_password("plam", "encryption_key")
        if key_str:
            logger.info("Symmetric encryption key successfully retrieved from system Keyring.")
            return key_str.encode()
    except Exception as e:
        logger.warning(f"Could not access system Keyring (unsupported or locked environment): {e}")

    # 2. Try Fallback File
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "rb") as f:
                key_bytes = f.read().strip()
                if key_bytes:
                    logger.info(f"Symmetric encryption key loaded from fallback file: {KEY_FILE}")
                    return key_bytes
        except Exception as e:
            logger.error(f"Error reading encryption key file: {e}")

    # 3. Generate a new key if not found in Keyring or File
    logger.info("No existing encryption key found. Generating a new key...")
    new_key_bytes = Fernet.generate_key()
    new_key_str = new_key_bytes.decode()

    # Try to save in system Keyring
    saved_in_keyring = False
    try:
        keyring.set_password("plam", "encryption_key", new_key_str)
        logger.info("New encryption key successfully stored in system Keyring.")
        saved_in_keyring = True
    except Exception as e:
        logger.warning(f"Could not save new key to system Keyring: {e}")

    # Also save to file as fallback/primary
    try:
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
        with open(KEY_FILE, "wb") as f:
            f.write(new_key_bytes)
        logger.info(f"New encryption key saved to fallback file: {KEY_FILE}")
    except Exception as e:
        logger.error(f"Failed to write encryption key to fallback file: {e}")
        # If both Keyring and File failed, we have a memory-only key. That's a fallback.
        if not saved_in_keyring:
            logger.critical("CRITICAL: Failed to persist encryption key to Keyring or File! Credentials will not persist across restarts.")

    return new_key_bytes

# Initialize cipher
_key = _load_or_generate_key()
_cipher = Fernet(_key)

def encrypt_value(value: str) -> str:
    """Encrypt a plain text string using the symmetric encryption key."""
    if not value:
        return ""
    return _cipher.encrypt(value.encode()).decode()

def decrypt_value(cipher_text: str) -> str:
    """Decrypt an encrypted cipher text string back to plain text."""
    if not cipher_text:
        return ""
    try:
        return _cipher.decrypt(cipher_text.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt credential value: {e}")
        return ""

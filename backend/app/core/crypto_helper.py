import os
import sys
import logging
import base64
import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import keyring
from app.core.config import DATA_DIR

logger = logging.getLogger(__name__)

KEY_FILE = os.path.abspath(os.path.join(DATA_DIR, "keys", "encryption.key"))

_key = None
_cipher = None

def _derive_fernet_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a password and salt using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def _load_key_from_env() -> bytes:
    """Load the symmetric encryption key from the environment.
    
    This is used by the backend server process.
    """
    env_key = os.environ.get("PLAM_CREDENTIAL_KEY")
    if not env_key:
        raise RuntimeError(
            "PLAM_CREDENTIAL_KEY environment variable not set. "
            "Please start the application using the setup.sh script."
        )
    return env_key.encode()

def _unlock_or_generate_key_interactive() -> bytes:
    """Unlock the encryption key from Keyring or file, or generate a new one.
    
    This function is run interactively by the bootstrap helper script.
    """
    # 1. Try system Keyring first
    try:
        keyring_key = keyring.get_password("plam", "encryption_key")
        if keyring_key:
            logger.info("Symmetric encryption key successfully retrieved from system Keyring.")
            return keyring_key.encode()
    except Exception as e:
        logger.warning(f"Could not access system Keyring: {e}")

    # 2. Try fallback key file
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "rb") as f:
                data = f.read()
            if len(data) <= 16:
                raise ValueError("Key file is corrupted or empty.")
            
            salt = data[:16]
            ciphertext = data[16:]
            
            # Attempt to decrypt. Prompt up to 3 times.
            attempts = 3
            while attempts > 0:
                if not sys.stdin.isatty():
                    raise RuntimeError("PLAM key file is password-protected and no interactive terminal (TTY) is available.")
                
                try:
                    password = getpass.getpass("Enter password to unlock PLAM credentials: ")
                    derived_key = _derive_fernet_key(password, salt)
                    decryptor = Fernet(derived_key)
                    raw_key = decryptor.decrypt(ciphertext)
                    logger.info("Symmetric encryption key successfully decrypted from key file.")
                    return raw_key
                except Exception:
                    attempts -= 1
                    if attempts > 0:
                        print(f"Incorrect password. {attempts} attempts remaining.")
                    else:
                        raise RuntimeError("Failed to unlock key file: Incorrect password.")
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to load encryption key: {e}")
            raise

    # 3. Generate a new key on first run
    logger.info("No existing encryption key found. Generating a new key...")
    raw_key = Fernet.generate_key()
    
    if not sys.stdin.isatty():
        raise RuntimeError("No existing encryption key found and no interactive terminal (TTY) is available to set a password.")
    
    # Prompt user to define password
    password = ""
    while not password:
        p1 = getpass.getpass("Define a password to protect the PLAM credentials key file: ")
        if not p1:
            print("Password cannot be empty.")
            continue
        p2 = getpass.getpass("Confirm password: ")
        if p1 != p2:
            print("Passwords do not match. Please try again.")
            continue
        password = p1

    # Encrypt and save key to file
    try:
        salt = os.urandom(16)
        derived_key = _derive_fernet_key(password, salt)
        encryptor = Fernet(derived_key)
        ciphertext = encryptor.encrypt(raw_key)
        
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
        with open(KEY_FILE, "wb") as f:
            f.write(salt + ciphertext)
        logger.info(f"New encryption key successfully encrypted and saved to file: {KEY_FILE}")
    except Exception as e:
        logger.error(f"Failed to save encryption key to file: {e}")

    # Try to save to system Keyring (for automatic unlocking next time)
    try:
        keyring.set_password("plam", "encryption_key", raw_key.decode())
        logger.info("New encryption key successfully stored in system Keyring.")
    except Exception as e:
        logger.warning(f"Could not store key in system Keyring: {e}")

    return raw_key

def get_cipher() -> Fernet:
    """Retrieve or lazily initialize the symmetric encryption Fernet cipher."""
    global _cipher, _key
    if _cipher is None:
        _key = _load_key_from_env()
        _cipher = Fernet(_key)
    return _cipher

def get_decrypted_key_string() -> str:
    """Retrieve the symmetric key as a decoded string (used by bootstrap CLI)."""
    global _key
    if _key is None:
        _key = _unlock_or_generate_key_interactive()
    return _key.decode()

def encrypt_value(value: str) -> str:
    """Encrypt a plain text string using the symmetric encryption key."""
    if not value:
        return ""
    return get_cipher().encrypt(value.encode()).decode()

def decrypt_value(cipher_text: str) -> str:
    """Decrypt an encrypted cipher text string back to plain text."""
    if not cipher_text:
        return ""
    try:
        return get_cipher().decrypt(cipher_text.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt credential value: {e}")
        return ""

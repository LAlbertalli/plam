import os
import tempfile
import importlib
import base64
from unittest.mock import patch, MagicMock
import pytest
from cryptography.fernet import Fernet
import keyring

# Import crypto_helper
import app.core.crypto_helper

@pytest.fixture
def test_cipher_mock(monkeypatch):
    """Fixture to mock get_cipher specifically for basic encryption/decryption tests."""
    test_key = Fernet.generate_key()
    test_cipher = Fernet(test_key)
    monkeypatch.setattr("app.core.crypto_helper.get_cipher", lambda: test_cipher)
    monkeypatch.setattr("app.core.crypto_helper._cipher", test_cipher)
    monkeypatch.setattr("app.core.crypto_helper._key", test_key)
    return test_cipher

def test_encryption_decryption(test_cipher_mock):
    plain_text = "test-secret-value"
    cipher_text = app.core.crypto_helper.encrypt_value(plain_text)
    assert cipher_text != plain_text
    
    decrypted = app.core.crypto_helper.decrypt_value(cipher_text)
    assert decrypted == plain_text

def test_decryption_failure(test_cipher_mock):
    assert app.core.crypto_helper.decrypt_value("invalid-cipher-text") == ""
    assert app.core.crypto_helper.decrypt_value("") == ""

def test_encrypt_empty(test_cipher_mock):
    assert app.core.crypto_helper.encrypt_value("") == ""

# --- Testing the real loader logic in isolation from production environment ---

def test_load_from_transient_env_variable():
    test_key = Fernet.generate_key().decode()
    with patch.dict(os.environ, {"PLAM_CREDENTIAL_KEY": test_key}):
        loaded = app.core.crypto_helper._load_key_from_env()
        assert loaded == test_key.encode()

def test_load_from_transient_env_variable_missing():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError) as exc_info:
            app.core.crypto_helper._load_key_from_env()
        assert "PLAM_CREDENTIAL_KEY environment variable not set" in str(exc_info.value)

def test_load_from_keyring_success():
    valid_key = Fernet.generate_key().decode()
    with patch("keyring.get_password", return_value=valid_key), \
         patch("app.core.crypto_helper.os.path.exists", return_value=False):
        
        loaded = app.core.crypto_helper._unlock_or_generate_key_interactive()
        assert loaded == valid_key.encode()

def test_load_from_encrypted_file_success():
    valid_key = Fernet.generate_key()
    password = "secret-passphrase"
    
    # Pre-generate an encrypted key file
    salt = os.urandom(16)
    derived_key = app.core.crypto_helper._derive_fernet_key(password, salt)
    encryptor = Fernet(derived_key)
    ciphertext = encryptor.encrypt(valid_key)
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(salt + ciphertext)
        tmp_name = tmp.name
        
    try:
        with patch("keyring.get_password", return_value=None), \
             patch("app.core.crypto_helper.KEY_FILE", tmp_name), \
             patch("app.core.crypto_helper.sys.stdin.isatty", return_value=True), \
             patch("getpass.getpass", return_value=password):
            
            loaded = app.core.crypto_helper._unlock_or_generate_key_interactive()
            assert loaded == valid_key
    finally:
        os.unlink(tmp_name)

def test_load_from_encrypted_file_wrong_password():
    valid_key = Fernet.generate_key()
    password = "secret-passphrase"
    
    salt = os.urandom(16)
    derived_key = app.core.crypto_helper._derive_fernet_key(password, salt)
    encryptor = Fernet(derived_key)
    ciphertext = encryptor.encrypt(valid_key)
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(salt + ciphertext)
        tmp_name = tmp.name
        
    try:
        with patch("keyring.get_password", return_value=None), \
             patch("app.core.crypto_helper.KEY_FILE", tmp_name), \
             patch("app.core.crypto_helper.sys.stdin.isatty", return_value=True), \
             patch("getpass.getpass", return_value="wrong-password"):
            
            with pytest.raises(RuntimeError) as exc_info:
                app.core.crypto_helper._unlock_or_generate_key_interactive()
            assert "Failed to unlock key file" in str(exc_info.value)
    finally:
        os.unlink(tmp_name)

def test_generate_new_key_on_first_run():
    mock_keyring_set = MagicMock()
    password = "new-secure-password"
    real_exists = os.path.exists
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = os.path.join(tmp_dir, "keys", "encryption.key")
        
        with patch("keyring.get_password", return_value=None), \
             patch("keyring.set_password", mock_keyring_set), \
             patch("app.core.crypto_helper.os.path.exists", return_value=False), \
             patch("app.core.crypto_helper.sys.stdin.isatty", return_value=True), \
             patch("getpass.getpass", return_value=password), \
             patch("app.core.crypto_helper.KEY_FILE", tmp_file):
            
            # This generates a new key and saves it to the temporary file
            generated_key = app.core.crypto_helper._unlock_or_generate_key_interactive()
            
            assert len(generated_key) == 44  # Base64 Fernet key length
            assert mock_keyring_set.called
            assert real_exists(tmp_file)
            
            # Verify we can decrypt the generated file using the password
            with open(tmp_file, "rb") as f:
                data = f.read()
            
            salt = data[:16]
            ciphertext = data[16:]
            derived_key = app.core.crypto_helper._derive_fernet_key(password, salt)
            decryptor = Fernet(derived_key)
            decrypted_key = decryptor.decrypt(ciphertext)
            
            assert decrypted_key == generated_key

def test_unlock_no_tty_raises_error():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"a" * 20)
        tmp_name = tmp.name
        
    try:
        with patch("app.core.crypto_helper.KEY_FILE", tmp_name), \
             patch("keyring.get_password", return_value=None), \
             patch("app.core.crypto_helper.sys.stdin.isatty", return_value=False):
            
            with pytest.raises(RuntimeError) as exc_info:
                app.core.crypto_helper._unlock_or_generate_key_interactive()
            assert "no interactive terminal (TTY) is available" in str(exc_info.value)
    finally:
        os.unlink(tmp_name)



import os
import importlib
import tempfile
from unittest.mock import patch, MagicMock
import pytest
import keyring

# We will test app.core.security by reloading it under mocked circumstances
import app.core.security

def test_encryption_decryption():
    plain_text = "my-super-secret-api-key"
    cipher_text = app.core.security.encrypt_value(plain_text)
    
    assert cipher_text != plain_text
    
    decrypted = app.core.security.decrypt_value(cipher_text)
    assert decrypted == plain_text

def test_decryption_failure():
    assert app.core.security.decrypt_value("invalid-cipher-text") == ""
    assert app.core.security.decrypt_value("") == ""

def test_encrypt_empty():
    assert app.core.security.encrypt_value("") == ""

def test_load_from_keyring_success():
    from cryptography.fernet import Fernet
    valid_key = Fernet.generate_key().decode()
    with patch("keyring.get_password", return_value=valid_key), \
         patch("app.core.security.os.path.exists", return_value=False):
        
        importlib.reload(app.core.security)

        
        # Test encryption using key loaded from keyring
        cipher = app.core.security.encrypt_value("hello")
        assert app.core.security.decrypt_value(cipher) == "hello"

def test_load_from_file_fallback():
    from cryptography.fernet import Fernet
    valid_key = Fernet.generate_key()
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(valid_key)
        tmp_name = tmp.name
        
    original_abspath = os.path.abspath
    def mock_abspath(path):
        if str(path).endswith("encryption.key"):
            return tmp_name
        return original_abspath(path)

    try:
        with patch("keyring.get_password", side_effect=Exception("Keyring locked")), \
             patch("os.path.abspath", side_effect=mock_abspath):
            
            importlib.reload(app.core.security)
            
            cipher = app.core.security.encrypt_value("hello")
            assert app.core.security.decrypt_value(cipher) == "hello"
    finally:
        os.unlink(tmp_name)

def test_generate_new_key_and_save_success():
    mock_keyring_set = MagicMock()
    real_exists = os.path.exists
    original_abspath = os.path.abspath
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = os.path.join(tmp_dir, "keys", "encryption.key")
        
        def mock_abspath(path):
            if str(path).endswith("encryption.key"):
                return tmp_file
            return original_abspath(path)

        with patch("keyring.get_password", return_value=None), \
             patch("keyring.set_password", mock_keyring_set), \
             patch("app.core.security.os.path.exists", return_value=False), \
             patch("os.path.abspath", side_effect=mock_abspath):
            
            importlib.reload(app.core.security)
            
            assert mock_keyring_set.called
            assert real_exists(tmp_file)
            with open(tmp_file, "rb") as f:
                saved_key = f.read()
                assert len(saved_key) > 0


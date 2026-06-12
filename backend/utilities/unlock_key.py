import os
import sys

# Insert backend directory to sys.path to resolve app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app.core.crypto_helper import get_decrypted_key_string
    # Retrieve and print the decrypted key to stdout for setup.sh to capture
    key_str = get_decrypted_key_string()
    print(key_str)
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

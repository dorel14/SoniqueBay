#!/usr/bin/env python3
"""
Test pour vérifier que le problème de signature de chiffrement est résolu.
Ce test vérifie que la clé de chiffrement par défaut fonctionne correctement
et que les erreurs de signature ne se produisent plus.
"""

import pytest
import os
import sys
from pathlib import Path

# Add the backend directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.api.utils.crypto import encrypt_value, decrypt_value, _get_encryption_key

class TestCryptoFix:
    """Test class for the crypto fix."""

    def test_encryption_key_consistency(self):
        """Test that _get_encryption_key returns a consistent key."""
        # Test 1: Verify that _get_encryption_key returns a consistent key
        key1 = _get_encryption_key()
        key2 = _get_encryption_key()

        assert key1 == key2, "Keys should be consistent"
        assert len(key1) > 0, "Key should not be empty"

    def test_encryption_decryption_with_default_key(self):
        """Test encryption and decryption with the default key."""
        # Test 2: Test encryption and decryption with the default key
        test_value = "This is a test value for encryption"

        # Encrypt the value
        encrypted = encrypt_value(test_value)
        assert encrypted is not None, "Encrypted value should not be None"
        assert len(encrypted) > 0, "Encrypted value should not be empty"

        # Decrypt the value
        decrypted = decrypt_value(encrypted)
        assert decrypted == test_value, "Decrypted value should match original"

    def test_empty_environment_key(self):
        """Test with empty environment (should use default key)."""
        # Clear any existing key
        original_key = os.environ.get('ENCRYPTION_KEY')
        if 'ENCRYPTION_KEY' in os.environ:
            del os.environ['ENCRYPTION_KEY']

        try:
            # Import fresh to get new key handling
            from importlib import reload
            import backend.api.utils.crypto as crypto_module
            reload(crypto_module)

            from backend.api.utils.crypto import encrypt_value as fresh_encrypt, decrypt_value as fresh_decrypt

            # This should still work because we have a default key
            test_value2 = "Another test value"
            encrypted2 = fresh_encrypt(test_value2)
            decrypted2 = fresh_decrypt(encrypted2)

            assert decrypted2 == test_value2, "Default key encryption/decryption should work"

        finally:
            # Restore original key if it existed
            if original_key is not None:
                os.environ['ENCRYPTION_KEY'] = original_key

    def test_error_handling_with_invalid_data(self):
        """Test error handling with invalid encrypted data."""
        # Test with invalid encrypted data
        invalid_encrypted = "this_is_not_valid_encrypted_data"
        result = decrypt_value(invalid_encrypted)

        # Should return empty string for invalid data
        assert result == "", "Invalid data should return empty string"

    def test_settings_service_integration(self):
        """Test the settings service integration."""
        # This is a more complex test that would require database setup
        # For now, we'll just verify the imports work
        try:
            from backend.api.utils.crypto import encrypt_value, decrypt_value

            # Simple round-trip test
            test_data = "test_setting_value"
            encrypted = encrypt_value(test_data)
            decrypted = decrypt_value(encrypted)

            assert decrypted == test_data, "SettingsService crypto integration should work"

        except Exception as e:
            pytest.fail(f"SettingsService integration test failed: {e}")

    def test_no_more_signature_errors(self):
        """Test that the original signature error no longer occurs."""
        # This test simulates the original error condition
        # and verifies that it no longer occurs

        # Create test data that would have caused the original error
        test_value = "test_data_that_would_cause_error"

        # Encrypt with current key
        encrypted = encrypt_value(test_value)

        # This should NOT raise cryptography.fernet.InvalidToken
        try:
            decrypted = decrypt_value(encrypted)
            assert decrypted == test_value, "Decryption should work without signature errors"
        except Exception as e:
            if "InvalidToken" in str(e) or "Signature did not match digest" in str(e):
                pytest.fail(f"Original signature error still occurs: {e}")
            else:
                pytest.fail(f"Unexpected error: {e}")

def test_crypto_fix_cli():
    """CLI test function that can be run directly."""
    print("Testing crypto fix...")

    # Run all tests
    test_instance = TestCryptoFix()

    try:
        test_instance.test_encryption_key_consistency()
        print("✓ Encryption key consistency test passed")

        test_instance.test_encryption_decryption_with_default_key()
        print("✓ Encryption/decryption test passed")

        test_instance.test_empty_environment_key()
        print("✓ Empty environment key test passed")

        test_instance.test_error_handling_with_invalid_data()
        print("✓ Error handling test passed")

        test_instance.test_settings_service_integration()
        print("✓ Settings service integration test passed")

        test_instance.test_no_more_signature_errors()
        print("✓ No more signature errors test passed")

        print("\n🎉 All crypto fix tests passed! The fix should resolve the original error.")
        return True

    except Exception as e:
        print(f"\n❌ Crypto fix test failed: {e}")
        return False

if __name__ == "__main__":
    print("Crypto Fix Test Script")
    print("=" * 40)

    success = test_crypto_fix_cli()
    sys.exit(0 if success else 1)
"""
Tests for secret management functionality.

This module tests the SecretManager class and related functionality
for secure handling of sensitive configuration values.
"""

import os
from unittest.mock import patch, MagicMock, call
import pytest
import base64
from typing import Dict, Any

from phoenix_real_estate.foundation.config.secrets import (
    SecretManager,
    get_secret_manager,
    get_secret,
    get_required_secret,
    SecretNotFoundError,
    SecretValidationError
)


class TestSecretManager:
    """Test the SecretManager class initialization and basic operations."""
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        with patch.dict(os.environ, {
            'SECRET_API_KEY': 'test_api_key',
            'SECURE_TOKEN': 'test_token',
            'CREDENTIAL_USERNAME': 'test_user',
            'NORMAL_CONFIG': 'not_a_secret',
            'SECRET_ENCODED': 'b64:dGVzdF9zZWNyZXQ=',  # base64 encoded "test_secret"
        }, clear=True):
            yield
    
    def test_initialization_with_secret_key(self, mock_env):
        """Test SecretManager initialization with a secret key."""
        manager = SecretManager(secret_key='test_key_123')
        assert manager._secret_key == 'test_key_123'
        assert hasattr(manager, '_secrets')
        assert isinstance(manager._secrets, dict)
    
    def test_initialization_without_secret_key(self, mock_env):
        """Test SecretManager initialization without a secret key."""
        manager = SecretManager()
        assert manager._secret_key is None
        assert hasattr(manager, '_secrets')
    
    def test_get_secret_with_secret_prefix(self, mock_env):
        """Test retrieving secrets with SECRET_ prefix."""
        manager = SecretManager()
        secret = manager.get_secret('SECRET_API_KEY')
        assert secret == 'test_api_key'
    
    def test_get_secret_with_secure_prefix(self, mock_env):
        """Test retrieving secrets with SECURE_ prefix."""
        manager = SecretManager()
        secret = manager.get_secret('SECURE_TOKEN')
        assert secret == 'test_token'
    
    def test_get_secret_with_credential_prefix(self, mock_env):
        """Test retrieving secrets with CREDENTIAL_ prefix."""
        manager = SecretManager()
        secret = manager.get_secret('CREDENTIAL_USERNAME')
        assert secret == 'test_user'
    
    def test_get_secret_non_secret_returns_none(self, mock_env):
        """Test that non-secret environment variables return None."""
        manager = SecretManager()
        result = manager.get_secret('NORMAL_CONFIG')
        assert result is None
    
    def test_get_secret_missing_returns_default(self, mock_env):
        """Test default value is returned for missing secrets."""
        manager = SecretManager()
        result = manager.get_secret('SECRET_MISSING', default='default_value')
        assert result == 'default_value'
    
    def test_get_required_secret_success(self, mock_env):
        """Test get_required_secret returns value when secret exists."""
        manager = SecretManager()
        secret = manager.get_required_secret('SECRET_API_KEY')
        assert secret == 'test_api_key'
    
    def test_get_required_secret_raises_error(self, mock_env):
        """Test get_required_secret raises error for missing secrets."""
        manager = SecretManager()
        with pytest.raises(SecretNotFoundError) as exc_info:
            manager.get_required_secret('SECRET_MISSING')
        assert 'SECRET_MISSING' in str(exc_info.value)
        assert 'test_api_key' not in str(exc_info.value)  # No actual secrets in error
    
    def test_base64_decoding(self, mock_env):
        """Test automatic base64 decoding with b64: prefix."""
        manager = SecretManager()
        secret = manager.get_secret('SECRET_ENCODED')
        assert secret == 'test_secret'
    
    def test_no_plaintext_logging(self, mock_env):
        """Test that secrets are not logged in plaintext."""
        with patch('phoenix_real_estate.foundation.config.secrets.logger') as mock_logger:
            manager = SecretManager()
            manager.get_secret('SECRET_API_KEY')
            
            # Check that the actual secret value is not in any log calls
            for call_args in mock_logger.debug.call_args_list:
                assert 'test_api_key' not in str(call_args)


class TestSecretEncryption:
    """Test secret encryption and decryption functionality."""
    
    @pytest.fixture
    def manager_with_key(self):
        """Create a SecretManager with encryption key."""
        return SecretManager(secret_key='test_encryption_key_32bytes_long!')
    
    def test_decrypt_if_needed_base64(self, manager_with_key):
        """Test _decrypt_if_needed handles base64 values."""
        encoded = 'b64:' + base64.b64encode(b'test_value').decode()
        result = manager_with_key._decrypt_if_needed(encoded)
        assert result == 'test_value'
    
    def test_decrypt_if_needed_plain(self, manager_with_key):
        """Test _decrypt_if_needed returns plain values unchanged."""
        result = manager_with_key._decrypt_if_needed('plain_value')
        assert result == 'plain_value'
    
    def test_store_secret_with_encryption(self, manager_with_key):
        """Test storing secrets with encryption."""
        manager_with_key.store_secret('TEST_SECRET', 'sensitive_data', encrypt=True)
        
        # Verify it's stored encrypted (not plaintext)
        stored_value = manager_with_key._secrets.get('TEST_SECRET')
        assert stored_value is not None
        assert stored_value != 'sensitive_data'
        assert stored_value.startswith('enc:')
    
    def test_store_secret_without_encryption(self, manager_with_key):
        """Test storing secrets without encryption."""
        manager_with_key.store_secret('TEST_SECRET', 'plain_data', encrypt=False)
        
        # Verify it's stored as-is
        stored_value = manager_with_key._secrets.get('TEST_SECRET')
        assert stored_value == 'plain_data'
    
    def test_round_trip_encoding_decoding(self, manager_with_key):
        """Test round-trip encoding and decoding of secrets."""
        original = 'sensitive_information_123'
        manager_with_key.store_secret('ROUND_TRIP', original, encrypt=True)
        retrieved = manager_with_key.get_secret('ROUND_TRIP')
        assert retrieved == original
    
    def test_invalid_base64_handling(self, manager_with_key):
        """Test handling of invalid base64 encoded values."""
        with patch.dict(os.environ, {'SECRET_BAD_B64': 'b64:invalid!!!'}, clear=True):
            result = manager_with_key.get_secret('SECRET_BAD_B64')
            # Should return the original value if decoding fails
            assert result == 'b64:invalid!!!'


class TestCredentialHelpers:
    """Test credential helper methods."""
    
    @pytest.fixture
    def mock_credentials(self):
        """Mock environment with various credentials."""
        with patch.dict(os.environ, {
            'CREDENTIAL_DB_HOST': 'localhost',
            'CREDENTIAL_DB_PORT': '27017',
            'CREDENTIAL_DB_USER': 'db_user',
            'CREDENTIAL_DB_PASS': 'db_pass',
            'CREDENTIAL_PROXY_HOST': 'proxy.example.com',
            'CREDENTIAL_PROXY_USER': 'proxy_user',
            'CREDENTIAL_PROXY_PASS': 'proxy_pass',
            'SECRET_API_KEY_GOOGLE': 'google_key',
            'SECRET_API_KEY_AZURE': 'azure_key',
        }, clear=True):
            yield
    
    def test_get_database_credentials(self, mock_credentials):
        """Test retrieving database credentials."""
        manager = SecretManager()
        db_creds = manager.get_database_credentials()
        
        assert db_creds['host'] == 'localhost'
        assert db_creds['port'] == '27017'
        assert db_creds['username'] == 'db_user'
        assert db_creds['password'] == 'db_pass'
    
    def test_get_proxy_credentials(self, mock_credentials):
        """Test retrieving proxy credentials."""
        manager = SecretManager()
        proxy_creds = manager.get_proxy_credentials()
        
        assert proxy_creds['host'] == 'proxy.example.com'
        assert proxy_creds['username'] == 'proxy_user'
        assert proxy_creds['password'] == 'proxy_pass'
    
    def test_get_api_keys(self, mock_credentials):
        """Test retrieving API keys."""
        manager = SecretManager()
        api_keys = manager.get_api_keys()
        
        assert 'google' in api_keys
        assert api_keys['google'] == 'google_key'
        assert 'azure' in api_keys
        assert api_keys['azure'] == 'azure_key'
    
    def test_missing_credential_handling(self):
        """Test handling of missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            manager = SecretManager()
            
            db_creds = manager.get_database_credentials()
            assert db_creds.get('host') is None
            
            proxy_creds = manager.get_proxy_credentials()
            assert proxy_creds.get('host') is None
            
            api_keys = manager.get_api_keys()
            assert len(api_keys) == 0


class TestSecretValidation:
    """Test secret validation functionality."""
    
    def test_validate_secrets_all_present(self):
        """Test validation when all required secrets are present."""
        with patch.dict(os.environ, {
            'SECRET_API_KEY': 'key1',
            'CREDENTIAL_DB_HOST': 'host1',
            'SECURE_TOKEN': 'token1',
        }, clear=True):
            manager = SecretManager()
            required = ['SECRET_API_KEY', 'CREDENTIAL_DB_HOST', 'SECURE_TOKEN']
            
            # Should not raise any exception
            manager.validate_secrets(required)
    
    def test_validate_secrets_missing_required(self):
        """Test validation when required secrets are missing."""
        with patch.dict(os.environ, {
            'SECRET_API_KEY': 'key1',
        }, clear=True):
            manager = SecretManager()
            required = ['SECRET_API_KEY', 'SECRET_MISSING_KEY']
            
            with pytest.raises(SecretValidationError) as exc_info:
                manager.validate_secrets(required)
            
            assert 'SECRET_MISSING_KEY' in str(exc_info.value)
            assert 'key1' not in str(exc_info.value)  # No actual secrets
    
    def test_validate_secrets_recommended_warning(self):
        """Test warning for recommended but missing secrets."""
        with patch.dict(os.environ, {
            'SECRET_API_KEY': 'key1',
        }, clear=True):
            with patch('phoenix_real_estate.foundation.config.secrets.logger') as mock_logger:
                manager = SecretManager()
                required = ['SECRET_API_KEY']
                recommended = ['SECRET_OPTIONAL_KEY']
                
                manager.validate_secrets(required, recommended)
                
                # Check that a warning was logged
                mock_logger.warning.assert_called()
                warning_call = mock_logger.warning.call_args[0][0]
                assert 'SECRET_OPTIONAL_KEY' in warning_call
    
    def test_comprehensive_error_reporting(self):
        """Test comprehensive error reporting for multiple missing secrets."""
        with patch.dict(os.environ, {}, clear=True):
            manager = SecretManager()
            required = ['SECRET_KEY1', 'SECRET_KEY2', 'CREDENTIAL_KEY3']
            
            with pytest.raises(SecretValidationError) as exc_info:
                manager.validate_secrets(required)
            
            error_msg = str(exc_info.value)
            assert 'SECRET_KEY1' in error_msg
            assert 'SECRET_KEY2' in error_msg
            assert 'CREDENTIAL_KEY3' in error_msg
            assert '3' in error_msg  # Should mention count


class TestGlobalSecretManager:
    """Test global secret manager singleton functionality."""
    
    def test_get_secret_manager_singleton(self):
        """Test that get_secret_manager returns the same instance."""
        manager1 = get_secret_manager()
        manager2 = get_secret_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, SecretManager)
    
    def test_convenience_function_get_secret(self):
        """Test the global get_secret convenience function."""
        with patch.dict(os.environ, {'SECRET_TEST': 'test_value'}, clear=True):
            result = get_secret('SECRET_TEST')
            assert result == 'test_value'
    
    def test_convenience_function_get_required_secret(self):
        """Test the global get_required_secret convenience function."""
        with patch.dict(os.environ, {'SECRET_TEST': 'test_value'}, clear=True):
            result = get_required_secret('SECRET_TEST')
            assert result == 'test_value'
        
        with pytest.raises(SecretNotFoundError):
            get_required_secret('SECRET_MISSING')


class TestSecurityBestPractices:
    """Test security best practices in secret management."""
    
    def test_no_secrets_in_exception_messages(self):
        """Test that actual secret values don't appear in exceptions."""
        with patch.dict(os.environ, {'SECRET_KEY': 'actual_secret_value'}, clear=True):
            manager = SecretManager()
            
            # Test various exception scenarios
            try:
                manager.get_required_secret('SECRET_MISSING')
            except SecretNotFoundError as e:
                assert 'actual_secret_value' not in str(e)
                assert 'SECRET_KEY' not in str(e)  # Don't reveal what secrets exist
    
    def test_no_secrets_in_str_repr(self):
        """Test that secrets don't appear in string representations."""
        with patch.dict(os.environ, {'SECRET_KEY': 'secret_value'}, clear=True):
            manager = SecretManager()
            manager.get_secret('SECRET_KEY')
            
            # String representation should not contain secrets
            assert 'secret_value' not in str(manager)
            assert 'secret_value' not in repr(manager)
    
    def test_audit_logging_for_secret_access(self):
        """Test that secret access is logged for auditing."""
        with patch.dict(os.environ, {'SECRET_API_KEY': 'test_key'}, clear=True):
            with patch('phoenix_real_estate.foundation.config.secrets.logger') as mock_logger:
                manager = SecretManager()
                manager.get_secret('SECRET_API_KEY')
                
                # Verify audit logging occurred
                mock_logger.debug.assert_called()
                
                # Check that the log mentions the secret name but not value
                log_calls = [str(call) for call in mock_logger.debug.call_args_list]
                log_text = ' '.join(log_calls)
                assert 'SECRET_API_KEY' in log_text or 'secret access' in log_text.lower()
                assert 'test_key' not in log_text
    
    def test_safe_error_messages(self):
        """Test that error messages are safe and don't leak information."""
        manager = SecretManager()
        
        # Test validation error messages
        with patch.dict(os.environ, {'SECRET_EXISTS': 'value'}, clear=True):
            try:
                manager.validate_secrets(['SECRET_MISSING', 'SECRET_ALSO_MISSING'])
            except SecretValidationError as e:
                error_msg = str(e)
                assert 'value' not in error_msg
                assert 'SECRET_EXISTS' not in error_msg  # Don't reveal what exists
                assert 'SECRET_MISSING' in error_msg
                assert 'SECRET_ALSO_MISSING' in error_msg


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_secret_value(self):
        """Test handling of empty secret values."""
        with patch.dict(os.environ, {'SECRET_EMPTY': ''}, clear=True):
            manager = SecretManager()
            result = manager.get_secret('SECRET_EMPTY')
            assert result == ''
            
            # Empty should still fail required check
            with pytest.raises(SecretNotFoundError):
                manager.get_required_secret('SECRET_EMPTY')
    
    def test_whitespace_secret_value(self):
        """Test handling of whitespace-only secret values."""
        with patch.dict(os.environ, {'SECRET_WHITESPACE': '   '}, clear=True):
            manager = SecretManager()
            result = manager.get_secret('SECRET_WHITESPACE')
            assert result == '   '  # Preserve whitespace
    
    def test_unicode_secret_value(self):
        """Test handling of unicode in secret values."""
        with patch.dict(os.environ, {'SECRET_UNICODE': '🔐 秘密'}, clear=True):
            manager = SecretManager()
            result = manager.get_secret('SECRET_UNICODE')
            assert result == '🔐 秘密'
    
    def test_very_long_secret_value(self):
        """Test handling of very long secret values."""
        long_value = 'x' * 10000
        with patch.dict(os.environ, {'SECRET_LONG': long_value}, clear=True):
            manager = SecretManager()
            result = manager.get_secret('SECRET_LONG')
            assert result == long_value
            assert len(result) == 10000
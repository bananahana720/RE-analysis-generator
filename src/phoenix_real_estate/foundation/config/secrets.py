"""
Secret management for the Phoenix Real Estate application.

This module provides secure handling of sensitive configuration values
including encryption, decryption, and validation of secrets.
"""

import os
import base64
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field

# Configure logging
logger = logging.getLogger(__name__)


class SecretNotFoundError(Exception):
    """Raised when a required secret is not found."""

    pass


class SecretValidationError(Exception):
    """Raised when secret validation fails."""

    pass


@dataclass
class SecretManager:
    """
    Manages secrets and sensitive configuration values.

    Provides secure storage, retrieval, and validation of secrets with
    support for encryption and automatic decoding of encoded values.
    """

    _secret_key: Optional[str] = None
    _secrets: Dict[str, str] = field(default_factory=dict)

    # Secret prefixes that indicate sensitive data
    SECRET_PREFIXES = ("SECRET_", "SECURE_", "CREDENTIAL_")

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize the SecretManager.

        Args:
            secret_key: Optional encryption key for secret storage
        """
        self._secret_key = secret_key
        self._secrets = {}

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret value.

        Args:
            name: Name of the secret to retrieve
            default: Default value if secret is not found

        Returns:
            The secret value or default if not found
        """
        # Log access for auditing (without revealing the value)
        logger.debug(f"Secret access requested for: {name}")

        # First check stored secrets (bypass prefix check for stored secrets)
        if name in self._secrets:
            value = self._secrets[name]
            return self._decrypt_if_needed(value)

        # Check if this is a secret (has appropriate prefix) for env vars
        if not any(name.startswith(prefix) for prefix in self.SECRET_PREFIXES):
            return None

        # Then check environment variables
        value = os.environ.get(name)
        if value is not None:
            return self._decrypt_if_needed(value)

        return default

    def get_required_secret(self, name: str) -> str:
        """
        Retrieve a required secret value.

        Args:
            name: Name of the secret to retrieve

        Returns:
            The secret value

        Raises:
            SecretNotFoundError: If the secret is not found or is empty
        """
        value = self.get_secret(name)
        if not value:  # None or empty string
            # Don't reveal what secrets exist in error message
            raise SecretNotFoundError(f"Required secret not found: {name}")
        return value

    def _decrypt_if_needed(self, value: str) -> str:
        """
        Decrypt or decode a value if needed.

        Args:
            value: The value to decrypt/decode

        Returns:
            The decrypted/decoded value
        """
        if not value:
            return value

        # Handle base64 encoded values (b64: prefix)
        if value.startswith("b64:"):
            try:
                encoded_part = value[4:]  # Remove 'b64:' prefix
                decoded = base64.b64decode(encoded_part).decode("utf-8")
                return decoded
            except Exception:
                # If decoding fails, return original value
                logger.warning("Failed to decode base64 value")
                return value

        # Handle encrypted values (enc: prefix)
        if value.startswith("enc:") and self._secret_key:
            return self._decrypt_value(value[4:])

        return value

    def _encrypt_value(self, value: str) -> str:
        """
        Encrypt a value using simple XOR encryption (for demonstration).

        Args:
            value: The value to encrypt

        Returns:
            The encrypted value
        """
        if not self._secret_key:
            return value

        # Simple XOR encryption for demonstration
        key_bytes = self._secret_key.encode("utf-8")
        value_bytes = value.encode("utf-8")

        encrypted = bytearray()
        for i, byte in enumerate(value_bytes):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)])

        # Base64 encode the encrypted bytes
        return base64.b64encode(encrypted).decode("utf-8")

    def _decrypt_value(self, encrypted: str) -> str:
        """
        Decrypt a value using simple XOR decryption.

        Args:
            encrypted: The encrypted value (base64 encoded)

        Returns:
            The decrypted value
        """
        if not self._secret_key:
            return encrypted

        try:
            # Base64 decode first
            encrypted_bytes = base64.b64decode(encrypted)
            key_bytes = self._secret_key.encode("utf-8")

            # XOR decrypt
            decrypted = bytearray()
            for i, byte in enumerate(encrypted_bytes):
                decrypted.append(byte ^ key_bytes[i % len(key_bytes)])

            return decrypted.decode("utf-8")
        except Exception:
            logger.warning("Failed to decrypt value")
            return encrypted

    def store_secret(self, name: str, value: str, encrypt: bool = False) -> None:
        """
        Store a secret value.

        Args:
            name: Name of the secret
            value: The secret value
            encrypt: Whether to encrypt the value before storing
        """
        if encrypt and self._secret_key:
            encrypted_value = self._encrypt_value(value)
            self._secrets[name] = f"enc:{encrypted_value}"
        else:
            self._secrets[name] = value

    def get_database_credentials(self) -> Dict[str, Optional[str]]:
        """
        Get database connection credentials.

        Returns:
            Dictionary with database credentials
        """
        return {
            "host": self.get_secret("CREDENTIAL_DB_HOST"),
            "port": self.get_secret("CREDENTIAL_DB_PORT"),
            "username": self.get_secret("CREDENTIAL_DB_USER"),
            "password": self.get_secret("CREDENTIAL_DB_PASS"),
        }

    def get_proxy_credentials(self) -> Dict[str, Optional[str]]:
        """
        Get proxy connection credentials.

        Returns:
            Dictionary with proxy credentials
        """
        return {
            "host": self.get_secret("CREDENTIAL_PROXY_HOST"),
            "username": self.get_secret("CREDENTIAL_PROXY_USER"),
            "password": self.get_secret("CREDENTIAL_PROXY_PASS"),
        }

    def get_api_keys(self) -> Dict[str, str]:
        """
        Get all available API keys.

        Returns:
            Dictionary of API keys by service name
        """
        api_keys = {}

        # Look for API keys in environment
        for key in os.environ:
            if key.startswith("SECRET_API_KEY_"):
                service_name = key.replace("SECRET_API_KEY_", "").lower()
                value = self.get_secret(key)
                if value:
                    api_keys[service_name] = value

        return api_keys

    def validate_secrets(
        self, required: List[str], recommended: Optional[List[str]] = None
    ) -> None:
        """
        Validate that required secrets are present.

        Args:
            required: List of required secret names
            recommended: List of recommended but optional secret names

        Raises:
            SecretValidationError: If any required secrets are missing
        """
        missing_required = []

        for secret_name in required:
            if not self.get_secret(secret_name):
                missing_required.append(secret_name)

        if missing_required:
            count = len(missing_required)
            missing_list = ", ".join(missing_required)
            raise SecretValidationError(f"Missing {count} required secret(s): {missing_list}")

        # Check recommended secrets and log warnings
        if recommended:
            for secret_name in recommended:
                if not self.get_secret(secret_name):
                    logger.warning(f"Recommended secret not found: {secret_name}")

    def __str__(self) -> str:
        """String representation without revealing secrets."""
        return f"SecretManager(secrets_count={len(self._secrets)})"

    def __repr__(self) -> str:
        """Representation without revealing secrets."""
        return self.__str__()


# Global secret manager instance
_secret_manager: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """
    Get the global secret manager instance.

    Returns:
        The global SecretManager instance
    """
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to get a secret using the global manager.

    Args:
        name: Name of the secret to retrieve
        default: Default value if secret is not found

    Returns:
        The secret value or default if not found
    """
    return get_secret_manager().get_secret(name, default)


def get_required_secret(name: str) -> str:
    """
    Convenience function to get a required secret using the global manager.

    Args:
        name: Name of the secret to retrieve

    Returns:
        The secret value

    Raises:
        SecretNotFoundError: If the secret is not found
    """
    return get_secret_manager().get_required_secret(name)

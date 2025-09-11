"""
Field-level encryption for sensitive database fields.

This module provides encryption and decryption functionality for sensitive
data stored in the database, such as API tokens and OAuth credentials.
"""
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class FieldEncryption:
    """Handles encryption and decryption of sensitive database fields."""
    
    _instance: Optional['FieldEncryption'] = None
    _cipher: Optional[Fernet] = None
    
    def __new__(cls) -> 'FieldEncryption':
        """Singleton pattern to ensure single encryption instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize encryption with key from environment."""
        if self._cipher is None:
            encryption_key = os.getenv("FIELD_ENCRYPTION_KEY")
            
            if not encryption_key:
                # For development, generate a key if not set
                # In production, this should always be set
                if os.getenv("ENVIRONMENT", "development") == "development":
                    # Generate a consistent key for development
                    # DO NOT use this in production!
                    salt = b'voltex_dev_salt_do_not_use_in_prod'
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    key = base64.urlsafe_b64encode(kdf.derive(b'development_key'))
                    encryption_key = key.decode()
                else:
                    raise ValueError(
                        "FIELD_ENCRYPTION_KEY environment variable must be set in production. "
                        "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                    )
            
            try:
                # Ensure the key is properly formatted
                if isinstance(encryption_key, str):
                    encryption_key = encryption_key.encode()
                self._cipher = Fernet(encryption_key)
            except Exception as e:
                raise ValueError(f"Invalid FIELD_ENCRYPTION_KEY: {e}")
    
    def encrypt(self, data: Optional[str]) -> Optional[str]:
        """
        Encrypt a string value.
        
        Args:
            data: The string to encrypt
            
        Returns:
            Encrypted string or None if input is None/empty
        """
        if not data:
            return None
        
        try:
            encrypted_bytes = self._cipher.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Encryption failed: {e}")
    
    def decrypt(self, encrypted_data: Optional[str]) -> Optional[str]:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted_data: The encrypted string
            
        Returns:
            Decrypted string or None if input is None/empty
        """
        if not encrypted_data:
            return None
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_bytes = self._cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            # Log error but don't expose details
            raise ValueError("Decryption failed")
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key.
        
        Returns:
            A new Fernet encryption key
        """
        return Fernet.generate_key().decode()


# Create singleton instance
field_encryption = FieldEncryption()
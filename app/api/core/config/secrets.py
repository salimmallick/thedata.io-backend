"""
Secrets management module.
Handles secure storage and retrieval of sensitive configuration data.
"""
import os
import json
import base64
from typing import Dict, Any, Optional
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ..monitoring.instances import metrics

logger = logging.getLogger(__name__)

class SecretsManager:
    """Manages secure storage and retrieval of sensitive configuration data."""
    
    def __init__(self):
        """Initialize the secrets manager."""
        self._fernet = None
        self._initialized = False
        self._secrets_cache: Dict[str, Any] = {}
        self._salt = os.urandom(16)
    
    def initialize(self, master_key: str) -> None:
        """Initialize the secrets manager with a master key."""
        if self._initialized:
            return
            
        try:
            # Generate key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
            self._fernet = Fernet(key)
            self._initialized = True
            
            logger.info("Secrets manager initialized successfully")
            metrics.track_component_health("secrets_manager", True)
            
        except Exception as e:
            logger.error(f"Failed to initialize secrets manager: {str(e)}")
            metrics.track_component_health("secrets_manager", False)
            raise
    
    def _ensure_initialized(self) -> None:
        """Ensure the secrets manager is initialized."""
        if not self._initialized:
            raise RuntimeError("Secrets manager not initialized")
    
    def set_secret(self, key: str, value: str) -> None:
        """Securely store a secret."""
        self._ensure_initialized()
        
        try:
            # Encrypt the value
            encrypted_value = self._fernet.encrypt(value.encode())
            
            # Store in cache
            self._secrets_cache[key] = encrypted_value
            
            # Store in secure storage (implement based on your storage solution)
            self._persist_secret(key, encrypted_value)
            
            logger.info(f"Secret stored successfully: {key}")
            
        except Exception as e:
            logger.error(f"Failed to store secret: {str(e)}")
            metrics.track_error("secret_storage_error", str(e))
            raise
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret."""
        self._ensure_initialized()
        
        try:
            # Try to get from cache first
            encrypted_value = self._secrets_cache.get(key)
            
            # If not in cache, try to load from storage
            if encrypted_value is None:
                encrypted_value = self._load_secret(key)
                if encrypted_value is None:
                    return None
                self._secrets_cache[key] = encrypted_value
            
            # Decrypt and return
            return self._fernet.decrypt(encrypted_value).decode()
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret: {str(e)}")
            metrics.track_error("secret_retrieval_error", str(e))
            return None
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        self._ensure_initialized()
        
        try:
            # Remove from cache
            self._secrets_cache.pop(key, None)
            
            # Remove from storage
            self._delete_persisted_secret(key)
            
            logger.info(f"Secret deleted successfully: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete secret: {str(e)}")
            metrics.track_error("secret_deletion_error", str(e))
            return False
    
    def rotate_master_key(self, new_master_key: str) -> None:
        """Rotate the master encryption key."""
        self._ensure_initialized()
        
        try:
            # Create new encryption key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=100000,
            )
            new_key = base64.urlsafe_b64encode(kdf.derive(new_master_key.encode()))
            new_fernet = Fernet(new_key)
            
            # Re-encrypt all secrets with new key
            for key, encrypted_value in self._secrets_cache.items():
                # Decrypt with old key
                decrypted_value = self._fernet.decrypt(encrypted_value)
                # Encrypt with new key
                new_encrypted_value = new_fernet.encrypt(decrypted_value)
                # Update storage
                self._persist_secret(key, new_encrypted_value)
                # Update cache
                self._secrets_cache[key] = new_encrypted_value
            
            # Update the encryption key
            self._fernet = new_fernet
            
            logger.info("Master key rotated successfully")
            
        except Exception as e:
            logger.error(f"Failed to rotate master key: {str(e)}")
            metrics.track_error("key_rotation_error", str(e))
            raise
    
    def _persist_secret(self, key: str, encrypted_value: bytes) -> None:
        """Persist encrypted secret to secure storage."""
        # Implement based on your storage solution (e.g., Vault, AWS Secrets Manager)
        # For now, we'll use a local encrypted file as an example
        secrets_file = os.path.join(os.path.dirname(__file__), "secrets.enc")
        
        try:
            # Load existing secrets
            secrets = {}
            if os.path.exists(secrets_file):
                with open(secrets_file, "rb") as f:
                    encrypted_data = f.read()
                    if encrypted_data:
                        decrypted_data = self._fernet.decrypt(encrypted_data)
                        secrets = json.loads(decrypted_data)
            
            # Update with new secret
            secrets[key] = base64.b64encode(encrypted_value).decode()
            
            # Save back to file
            encrypted_secrets = self._fernet.encrypt(json.dumps(secrets).encode())
            with open(secrets_file, "wb") as f:
                f.write(encrypted_secrets)
                
        except Exception as e:
            logger.error(f"Failed to persist secret: {str(e)}")
            raise
    
    def _load_secret(self, key: str) -> Optional[bytes]:
        """Load encrypted secret from secure storage."""
        secrets_file = os.path.join(os.path.dirname(__file__), "secrets.enc")
        
        try:
            if not os.path.exists(secrets_file):
                return None
                
            with open(secrets_file, "rb") as f:
                encrypted_data = f.read()
                if not encrypted_data:
                    return None
                    
                decrypted_data = self._fernet.decrypt(encrypted_data)
                secrets = json.loads(decrypted_data)
                
                if key not in secrets:
                    return None
                    
                return base64.b64decode(secrets[key])
                
        except Exception as e:
            logger.error(f"Failed to load secret: {str(e)}")
            return None
    
    def _delete_persisted_secret(self, key: str) -> None:
        """Delete secret from secure storage."""
        secrets_file = os.path.join(os.path.dirname(__file__), "secrets.enc")
        
        try:
            if not os.path.exists(secrets_file):
                return
                
            # Load existing secrets
            with open(secrets_file, "rb") as f:
                encrypted_data = f.read()
                if not encrypted_data:
                    return
                    
                decrypted_data = self._fernet.decrypt(encrypted_data)
                secrets = json.loads(decrypted_data)
            
            # Remove the secret
            secrets.pop(key, None)
            
            # Save back to file
            encrypted_secrets = self._fernet.encrypt(json.dumps(secrets).encode())
            with open(secrets_file, "wb") as f:
                f.write(encrypted_secrets)
                
        except Exception as e:
            logger.error(f"Failed to delete persisted secret: {str(e)}")
            raise

# Create singleton instance
secrets_manager = SecretsManager()

__all__ = ['secrets_manager', 'SecretsManager'] 
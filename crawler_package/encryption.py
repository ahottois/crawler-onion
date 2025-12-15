"""
Module de chiffrement AES-256 pour donnees sensibles.
Chiffre emails, wallets, phones, secrets dans la DB.
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from .logger import Log


class EncryptionConfig:
    """Configuration du chiffrement."""
    
    # Cle AES-256 (32 bytes)
    ENCRYPTION_KEY = os.environ.get('CRAWLER_ENCRYPTION_KEY', '')
    
    # Si pas de cle, en generer une (WARNING: sera perdue au restart)
    if not ENCRYPTION_KEY:
        ENCRYPTION_KEY = secrets.token_hex(32)
        Log.warning("No CRAWLER_ENCRYPTION_KEY set. Generated temporary key.")
    
    # Activer/desactiver le chiffrement
    ENCRYPTION_ENABLED = os.environ.get('CRAWLER_ENCRYPTION_ENABLED', 'false').lower() == 'true'


class AES256Cipher:
    """Chiffrement AES-256-GCM."""
    
    def __init__(self, key: str = None):
        if key:
            self._key = self._derive_key(key)
        else:
            self._key = self._derive_key(EncryptionConfig.ENCRYPTION_KEY)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive une cle de 32 bytes a partir du mot de passe."""
        return hashlib.sha256(password.encode()).digest()
    
    def encrypt(self, plaintext: str) -> str:
        """Chiffre une chaine. Retourne base64(nonce + tag + ciphertext)."""
        if not plaintext:
            return ""
        
        if not EncryptionConfig.ENCRYPTION_ENABLED:
            return plaintext
        
        try:
            # Nonce 12 bytes pour GCM
            nonce = secrets.token_bytes(12)
            
            cipher = Cipher(
                algorithms.AES(self._key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
            
            # Format: nonce (12) + tag (16) + ciphertext
            encrypted = nonce + encryptor.tag + ciphertext
            
            return 'ENC:' + base64.b64encode(encrypted).decode()
            
        except Exception as e:
            Log.error(f"Encryption error: {e}")
            return plaintext
    
    def decrypt(self, encrypted: str) -> str:
        """Dechiffre une chaine."""
        if not encrypted:
            return ""
        
        # Si pas chiffre (pas de prefix ENC:)
        if not encrypted.startswith('ENC:'):
            return encrypted
        
        if not EncryptionConfig.ENCRYPTION_ENABLED:
            return encrypted[4:]  # Retirer prefix
        
        try:
            data = base64.b64decode(encrypted[4:])
            
            nonce = data[:12]
            tag = data[12:28]
            ciphertext = data[28:]
            
            cipher = Cipher(
                algorithms.AES(self._key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext.decode()
            
        except Exception as e:
            Log.error(f"Decryption error: {e}")
            return encrypted
    
    def is_encrypted(self, value: str) -> bool:
        """Verifie si une valeur est chiffree."""
        return value.startswith('ENC:') if value else False


class SensitiveDataEncryptor:
    """Encryptor specifique pour les types de donnees sensibles."""
    
    def __init__(self):
        self.cipher = AES256Cipher()
    
    def encrypt_email(self, email: str) -> str:
        """Chiffre un email."""
        return self.cipher.encrypt(email)
    
    def decrypt_email(self, encrypted: str) -> str:
        """Dechiffre un email."""
        return self.cipher.decrypt(encrypted)
    
    def encrypt_wallet(self, wallet: str) -> str:
        """Chiffre une adresse wallet."""
        return self.cipher.encrypt(wallet)
    
    def decrypt_wallet(self, encrypted: str) -> str:
        """Dechiffre une adresse wallet."""
        return self.cipher.decrypt(encrypted)
    
    def encrypt_phone(self, phone: str) -> str:
        """Chiffre un numero de telephone."""
        return self.cipher.encrypt(phone)
    
    def decrypt_phone(self, encrypted: str) -> str:
        """Dechiffre un numero de telephone."""
        return self.cipher.decrypt(encrypted)
    
    def encrypt_secret(self, secret: str) -> str:
        """Chiffre un secret (API key, password, etc.)."""
        return self.cipher.encrypt(secret)
    
    def decrypt_secret(self, encrypted: str) -> str:
        """Dechiffre un secret."""
        return self.cipher.decrypt(encrypted)
    
    def encrypt_list(self, items: list) -> list:
        """Chiffre une liste d'elements."""
        return [self.cipher.encrypt(item) for item in items]
    
    def decrypt_list(self, items: list) -> list:
        """Dechiffre une liste d'elements."""
        return [self.cipher.decrypt(item) for item in items]
    
    def encrypt_dict(self, data: dict, sensitive_keys: list) -> dict:
        """Chiffre les valeurs des cles sensibles d'un dict."""
        result = data.copy()
        for key in sensitive_keys:
            if key in result and result[key]:
                if isinstance(result[key], list):
                    result[key] = self.encrypt_list(result[key])
                elif isinstance(result[key], str):
                    result[key] = self.cipher.encrypt(result[key])
        return result
    
    def decrypt_dict(self, data: dict, sensitive_keys: list) -> dict:
        """Dechiffre les valeurs des cles sensibles d'un dict."""
        result = data.copy()
        for key in sensitive_keys:
            if key in result and result[key]:
                if isinstance(result[key], list):
                    result[key] = self.decrypt_list(result[key])
                elif isinstance(result[key], str):
                    result[key] = self.cipher.decrypt(result[key])
        return result
    
    def mask_email(self, email: str) -> str:
        """Masque un email pour affichage (a***@b.com)."""
        if not email or '@' not in email:
            return email
        parts = email.split('@')
        return f"{parts[0][0]}***@{parts[1]}"
    
    def mask_phone(self, phone: str) -> str:
        """Masque un telephone (+33 6 ** ** ** **)."""
        if not phone or len(phone) < 6:
            return phone
        return f"{phone[:4]}{'*' * (len(phone) - 6)}{phone[-2:]}"
    
    def mask_wallet(self, wallet: str) -> str:
        """Masque un wallet (bc1q...xyz)."""
        if not wallet or len(wallet) < 10:
            return wallet
        return f"{wallet[:6]}...{wallet[-4:]}"
    
    def mask_secret(self, secret: str) -> str:
        """Masque un secret (*****)."""
        if not secret:
            return secret
        return '*' * min(len(secret), 10)


# Instance globale
encryptor = SensitiveDataEncryptor()

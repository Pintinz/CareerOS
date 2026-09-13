"""Authenticated encryption for OAuth tokens at rest (Phase 8 spec §16).

Deliberately not homemade cryptography: this is a thin wrapper around `cryptography`'s
`MultiFernet`, which is AES-128-CBC + HMAC-SHA256 (authenticated — tampering is detected, not just
hidden). `MultiFernet` encrypts with the first configured key and can decrypt with any of them,
which is what makes key rotation possible: add a new key at the front of
`TOKEN_ENCRYPTION_KEYS`, keep the old one after it until every existing ciphertext has been
re-encrypted (or simply left to expire), then drop it.
"""

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import get_settings


class TokenDecryptionError(Exception):
    """Raised when a stored token can't be decrypted with any configured key — e.g. the key was
    rotated out before this ciphertext was migrated. Callers should treat this as equivalent to a
    missing/invalid token (force reauthorization), never surface the raw error to the client."""


class TokenEncryptionService:
    def __init__(self, keys: list[str] | None = None) -> None:
        settings = get_settings()
        raw_keys = keys if keys is not None else settings.token_encryption_key_list
        if not raw_keys:
            raise RuntimeError("No TOKEN_ENCRYPTION_KEYS configured — cannot handle OAuth tokens safely.")
        self._fernet = MultiFernet([Fernet(key.encode()) for key in raw_keys])

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise TokenDecryptionError("Stored token could not be decrypted with any configured key.") from exc

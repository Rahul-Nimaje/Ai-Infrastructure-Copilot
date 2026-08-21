"""Credential secret resolver.

Real deployments use HashiCorp Vault (docs/04-database-design.md Section 4):
`credentials.vault_path` points at a Vault secret, fetched just-in-time by the
execution engine and never persisted to Postgres.

MVP simplification #3 (see plan): this module implements the same interface
(`store_secret` / `resolve_secret`) against a local, application-managed,
AES-256-GCM-encrypted blob instead of a real Vault round trip. `credentials.
vault_engine = 'local_encrypted'` and `vault_path` becomes a local lookup key
rather than a Vault path. Swapping in real Vault later only means adding a
`hashicorp_vault` branch to `resolve_secret`/`store_secret` — the callers
(execution runner, credential CRUD) never change.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

# In-memory store for MVP: local_encrypted blobs are actually kept in the
# `credentials.encrypted_metadata` JSONB column (never a real secret store),
# so this module only implements the encrypt/decrypt primitives; the caller
# is responsible for persisting/reading `encrypted_metadata["ciphertext"]`.


def _derive_key() -> bytes:
    # Deterministic 32-byte key derived from the configured master key.
    # Fine for MVP local dev; production deployments should use real Vault
    # Transit-backed envelope encryption instead of a static derived key.
    return hashlib.sha256(settings.local_vault_master_key.encode("utf-8")).digest()


def encrypt_secret(plaintext: dict) -> str:
    key = _derive_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    data = json.dumps(plaintext).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, data, associated_data=None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_secret(blob: str) -> dict:
    key = _derive_key()
    aesgcm = AESGCM(key)
    raw = base64.b64decode(blob)
    nonce, ciphertext = raw[:12], raw[12:]
    data = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    return json.loads(data.decode("utf-8"))

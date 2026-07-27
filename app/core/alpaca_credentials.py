"""
Per-user Alpaca API credentials (encrypted at rest in Supabase).

Table: public.alpaca_credentials
  user_id, api_key_id, api_secret_enc, is_paper, updated_at

Secrets are Fernet-encrypted with CREDENTIALS_FERNET_KEY from .env.
Never log api_secret values.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

from app.core.supabase_client import get_supabase

load_dotenv()

logger = logging.getLogger("signal_gate.credentials")

TABLE = "alpaca_credentials"


@dataclass
class AlpacaCredentials:
    user_id: str
    api_key_id: str
    api_secret: str
    is_paper: bool


@dataclass
class AlpacaCredentialStatus:
    linked: bool
    is_paper: Optional[bool] = None
    api_key_masked: Optional[str] = None
    updated_at: Optional[str] = None


def _fernet() -> Fernet:
    raw = (os.getenv("CREDENTIALS_FERNET_KEY") or "").strip()
    if not raw:
        raise RuntimeError(
            "Missing CREDENTIALS_FERNET_KEY in .env — "
            "generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    # Accept raw Fernet key, or derive a stable Fernet key from any passphrase.
    try:
        return Fernet(raw.encode() if isinstance(raw, str) else raw)
    except (ValueError, TypeError):
        digest = hashlib.sha256(raw.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise RuntimeError(
            "Could not decrypt stored Alpaca secret — check CREDENTIALS_FERNET_KEY"
        ) from e


def mask_key_id(api_key_id: str) -> str:
    """Show a short prefix only, e.g. PKAB…WXYZ."""
    key = (api_key_id or "").strip()
    if len(key) <= 8:
        return "••••••••"
    return f"{key[:4]}…{key[-4:]}"


def get_status(user_id: str) -> AlpacaCredentialStatus:
    row = _fetch_row(user_id)
    if not row:
        return AlpacaCredentialStatus(linked=False)
    return AlpacaCredentialStatus(
        linked=True,
        is_paper=bool(row.get("is_paper", True)),
        api_key_masked=mask_key_id(str(row.get("api_key_id") or "")),
        updated_at=row.get("updated_at"),
    )


def load_credentials(user_id: str) -> Optional[AlpacaCredentials]:
    row = _fetch_row(user_id)
    if not row:
        return None
    secret = decrypt_secret(str(row["api_secret_enc"]))
    return AlpacaCredentials(
        user_id=user_id,
        api_key_id=str(row["api_key_id"]),
        api_secret=secret,
        is_paper=bool(row.get("is_paper", True)),
    )


def save_credentials(
    user_id: str,
    *,
    api_key_id: str,
    api_secret: str,
    is_paper: bool,
) -> AlpacaCredentialStatus:
    key_id = api_key_id.strip()
    secret = api_secret.strip()
    if not key_id or not secret:
        raise ValueError("API Key ID and Secret Key are required")

    payload = {
        "user_id": user_id,
        "api_key_id": key_id,
        "api_secret_enc": encrypt_secret(secret),
        "is_paper": bool(is_paper),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # Service-role upsert — never expose secret to clients
    get_supabase().table(TABLE).upsert(payload, on_conflict="user_id").execute()
    logger.info(
        "Saved Alpaca credentials for user %s (paper=%s, key=%s)",
        user_id,
        is_paper,
        mask_key_id(key_id),
    )
    return get_status(user_id)


def delete_credentials(user_id: str) -> bool:
    res = get_supabase().table(TABLE).delete().eq("user_id", user_id).execute()
    deleted = bool(res.data)
    if deleted:
        logger.info("Disconnected Alpaca for user %s", user_id)
    return deleted


def _fetch_row(user_id: str) -> Optional[dict]:
    res = (
        get_supabase()
        .table(TABLE)
        .select("user_id,api_key_id,api_secret_enc,is_paper,updated_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return res.data[0]

"""
User settings — link / disconnect Alpaca credentials.

  GET    /settings/alpaca       status (linked, paper/live, masked key)
  PUT    /settings/alpaca       save (validates with Alpaca first)
  DELETE /settings/alpaca       disconnect (+ wipe this user's chats)
  GET    /settings/alpaca/test  verify stored keys still work
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agent.agent_service import clear_thread_memory
from app.core.alpaca_client import (
    alpaca_auth_error_detail,
    sanitize_credential,
    validate_credentials,
)
from app.core.alpaca_credentials import (
    delete_credentials,
    get_status,
    load_credentials,
    save_credentials,
)
from app.core.auth import AuthUser, get_current_user
from app.core.user_context import trading_user
from app.exits import store as exit_store
from app.routers.chat import delete_all_conversations_for_user, list_conversation_ids

router = APIRouter(prefix="/settings", tags=["settings"])

logger = logging.getLogger("signal_gate.settings")


class AlpacaSettingsBody(BaseModel):
    api_key_id: str = Field(min_length=1)
    api_secret: str = Field(min_length=1)
    is_paper: bool = True


class AlpacaStatusOut(BaseModel):
    linked: bool
    is_paper: Optional[bool] = None
    api_key_masked: Optional[str] = None
    updated_at: Optional[str] = None
    chats_cleared: Optional[bool] = None
    chats_deleted: Optional[int] = None


@router.get("/alpaca", response_model=AlpacaStatusOut)
def get_alpaca_settings(user: AuthUser = Depends(get_current_user)):
    s = get_status(user.id)
    return AlpacaStatusOut(
        linked=s.linked,
        is_paper=s.is_paper,
        api_key_masked=s.api_key_masked,
        updated_at=s.updated_at,
    )


@router.put("/alpaca", response_model=AlpacaStatusOut)
def put_alpaca_settings(
    body: AlpacaSettingsBody,
    user: AuthUser = Depends(get_current_user),
):
    """Validate portfolio via Alpaca; only then encrypt + store. Never save on failure."""
    key_id = sanitize_credential(body.api_key_id)
    secret = sanitize_credential(body.api_secret)
    try:
        # Raises unless GET /v2/account (+ positions) succeeds for this mode.
        validate_credentials(key_id, secret, body.is_paper)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=alpaca_auth_error_detail(body.is_paper, e),
        ) from e

    try:
        s = save_credentials(
            user.id,
            api_key_id=key_id,
            api_secret=secret,
            is_paper=body.is_paper,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save credentials: {e}",
        ) from e

    return AlpacaStatusOut(
        linked=s.linked,
        is_paper=s.is_paper,
        api_key_masked=s.api_key_masked,
        updated_at=s.updated_at,
    )


@router.delete("/alpaca", response_model=AlpacaStatusOut)
async def delete_alpaca_settings(user: AuthUser = Depends(get_current_user)):
    """
    Disconnect Alpaca for this user, then wipe their chats / related state.
    Unlink always runs first so credentials are removed even if chat wipe fails.
    """
    # Snapshot chat ids before wipe (for in-memory agent thread cleanup).
    try:
        thread_ids = list_conversation_ids(user.id)
    except Exception:
        thread_ids = []

    delete_credentials(user.id)

    chats_deleted = 0
    try:
        chats_deleted = delete_all_conversations_for_user(user.id)
        exit_store.delete_all_for_user(user.id)
        await clear_thread_memory(thread_ids)
    except Exception as e:
        logger.exception("Chat wipe failed after Alpaca disconnect for %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Alpaca disconnected, but clearing your chats failed. "
                f"Try again or delete chats manually. ({e})"
            ),
        ) from e

    logger.info(
        "Disconnected Alpaca for user %s; deleted %s conversation(s)",
        user.id,
        chats_deleted,
    )
    return AlpacaStatusOut(
        linked=False,
        chats_cleared=True,
        chats_deleted=chats_deleted,
    )


@router.get("/alpaca/test")
def test_alpaca_connection(user: AuthUser = Depends(get_current_user)):
    creds = load_credentials(user.id)
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Alpaca account linked. Save keys in Settings first.",
        )
    try:
        with trading_user(user.id):
            summary = validate_credentials(
                creds.api_key_id, creds.api_secret, creds.is_paper
            )
        return {"ok": True, **summary}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=alpaca_auth_error_detail(creds.is_paper, e),
        ) from e

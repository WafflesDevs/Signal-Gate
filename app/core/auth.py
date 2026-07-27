"""
Check that the request has a logged-in Supabase user.

Frontend sends:  Authorization: Bearer <access_token>
We ask Supabase if that token is real.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.supabase_client import get_supabase

security = HTTPBearer(auto_error=False)


class AuthUser:
    def __init__(self, id: str, email: str | None):
        self.id = id
        self.email = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")

    try:
        user = get_supabase().auth.get_user(credentials.credentials).user
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
        return AuthUser(id=user.id, email=user.email)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth failed: {e}",
        ) from e

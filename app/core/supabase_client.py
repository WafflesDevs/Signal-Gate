"""
Connect to Supabase.

Put these in your .env:
  SUPABASE_URL=...
  SUPABASE_SERVICE_ROLE_KEY=...   (backend uses this)
  SUPABASE_ANON_KEY=...           (frontend uses this)
"""

import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Keep one client so we don't recreate it every request
_client = None


def get_supabase():
    """Return the Supabase client (service role for the backend)."""
    global _client

    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError(
            "Missing SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env"
        )

    _client = create_client(url, key)
    return _client

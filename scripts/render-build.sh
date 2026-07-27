#!/usr/bin/env bash
# Build Signal Gate for a single Render Web Service (API + SPA).
set -euo pipefail

echo "==> Installing Python dependencies"
pip install -r requirements.txt

echo "==> Ensuring Node.js is available for the Vite build"
export NVM_DIR="${HOME}/.nvm"
if [ ! -s "${NVM_DIR}/nvm.sh" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
fi
# shellcheck disable=SC1091
. "${NVM_DIR}/nvm.sh"
nvm install 20
nvm use 20

# Vite embeds import.meta.env.VITE_* at *build* time from the process environment.
# Render injects Dashboard env vars into the build — they are available here if set.
# If only the server keys are set, copy them so the SPA still gets a correct URL/key.
if [ -z "${VITE_SUPABASE_URL:-}" ] && [ -n "${SUPABASE_URL:-}" ]; then
  export VITE_SUPABASE_URL="${SUPABASE_URL}"
  echo "==> VITE_SUPABASE_URL unset; using SUPABASE_URL for the Vite build"
fi
if [ -z "${VITE_SUPABASE_ANON_KEY:-}" ] && [ -n "${SUPABASE_ANON_KEY:-}" ]; then
  export VITE_SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY}"
  echo "==> VITE_SUPABASE_ANON_KEY unset; using SUPABASE_ANON_KEY for the Vite build"
fi

if [ -z "${VITE_SUPABASE_URL:-}" ] || [ -z "${VITE_SUPABASE_ANON_KEY:-}" ]; then
  echo "ERROR: VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY must be set in Render Environment" >&2
  echo "       before build (same values as SUPABASE_URL / SUPABASE_ANON_KEY)." >&2
  echo "       Vite bakes these into the SPA at build time — runtime-only env is not enough." >&2
  echo "       After adding them: Manual Deploy → Clear build cache & deploy." >&2
  exit 1
fi

echo "==> Vite build env OK (VITE_SUPABASE_URL is set; anon key length=${#VITE_SUPABASE_ANON_KEY})"

echo "==> Building frontend (frontend/dist)"
cd frontend
npm ci
# Explicitly pass through so Vite definitely sees them (already exported above).
VITE_SUPABASE_URL="${VITE_SUPABASE_URL}" \
VITE_SUPABASE_ANON_KEY="${VITE_SUPABASE_ANON_KEY}" \
VITE_API_BASE="${VITE_API_BASE:-}" \
  npm run build
cd ..

echo "==> Build complete"
ls -la frontend/dist

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

echo "==> Building frontend (frontend/dist)"
cd frontend
npm ci
npm run build
cd ..

echo "==> Build complete"
ls -la frontend/dist

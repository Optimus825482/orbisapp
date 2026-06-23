#!/usr/bin/env bash
#
# ORBIS Admin Custom Claim (one-time)
# Tek komutla admin claim atama. VPS'te veya lokalde çalıştır.
#
# Kullanım:
#   bash scripts/set-admin.sh admin@orbisastro.online
#   bash scripts/set-admin.sh admin@orbisastro.online owner@orbisastro.online
#
set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Kullanım: $0 <email1> [email2] [...]"
  echo "Örnek: $0 admin@orbisastro.online"
  exit 1
fi

# Python'u bul
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" &> /dev/null; then
  PYTHON="python"
fi

# Credentials path'i bul (Coolify mount veya lokal)
if [ -z "${FIREBASE_CREDENTIALS_PATH:-}" ]; then
  if [ -f "/app/firebase-credentials.json" ]; then
    export FIREBASE_CREDENTIALS_PATH="/app/firebase-credentials.json"
  elif [ -f "./firebase-credentials.json" ]; then
    export FIREBASE_CREDENTIALS_PATH="./firebase-credentials.json"
  else
    echo "ERROR: Firebase credentials bulunamadı."
    echo "  - /app/firebase-credentials.json"
    echo "  - ./firebase-credentials.json"
    echo "  veya FIREBASE_CREDENTIALS_PATH env set et."
    exit 1
  fi
fi

# firebase-admin kurulu olmalı
"$PYTHON" -c "import firebase_admin" 2>/dev/null || {
  echo "Installing firebase-admin..."
  "$PYTHON" -m pip install --quiet firebase-admin
}

# Email'leri virgülle birleştir ve script'e geçir
EMAILS=$(IFS=,; echo "$*")
echo "════════════════════════════════════════════════════════════"
echo "  ORBIS Admin Claim"
echo "════════════════════════════════════════════════════════════"
echo "Credentials: ${FIREBASE_CREDENTIALS_PATH}"
echo "Emails: ${EMAILS}"
echo ""

"$PYTHON" "$(dirname "$0")/set_admin_claim.py" --email "${EMAILS}"

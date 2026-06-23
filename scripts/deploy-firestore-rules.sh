#!/usr/bin/env bash
#
# ORBIS Firestore Rules + Indexes Deploy
# Bu script lokal makineden çalıştırılır (VPS'te değil). Firebase CLI
# üzerinden rules + composite indexes deploy eder.
#
# Gereksinim:
#   - Node.js + npm
#   - firebase-tools: npm install -g firebase-tools
#   - firebase login (bir kere)
#
# Kullanım:
#   bash scripts/deploy-firestore-rules.sh
#
set -euo pipefail

PROJECT_ID="orbis-ffa9e"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULES_DIR="$(dirname "${SCRIPT_DIR}")/firebase"

echo "════════════════════════════════════════════════════════════"
echo "  ORBIS Firestore Deploy"
echo "════════════════════════════════════════════════════════════"
echo "Project: ${PROJECT_ID}"
echo "Rules dir: ${RULES_DIR}"
echo ""

# 1) Firebase CLI kontrol
if ! command -v firebase &> /dev/null; then
  echo "ERROR: firebase-tools yüklü değil."
  echo "Kurulum: npm install -g firebase-tools"
  exit 1
fi

# 2) Login kontrol
if ! firebase projects:list &> /dev/null; then
  echo "Firebase login gerekli. Çalıştırıyorum..."
  firebase login
fi

# 3) Proje seç
firebase use "${PROJECT_ID}"

# 4) Rules deploy
echo ""
echo "[1/2] Deploying Firestore Rules..."
if [ -f "${RULES_DIR}/firestore.rules" ]; then
  firebase deploy --only firestore:rules --project "${PROJECT_ID}"
  echo "  ✓ Rules deployed"
else
  echo "  ✗ firestore.rules not found at ${RULES_DIR}/firestore.rules"
  exit 1
fi

# 5) Indexes deploy (opsiyonel)
if [ -f "${RULES_DIR}/firestore.indexes.json" ]; then
  echo ""
  echo "[2/2] Deploying Firestore Indexes..."
  firebase deploy --only firestore:indexes --project "${PROJECT_ID}"
  echo "  ✓ Indexes deployed"
else
  echo ""
  echo "[2/2] firestore.indexes.json yok, atlandı."
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Done! Verify:"
echo "  https://console.firebase.google.com/project/${PROJECT_ID}/firestore/rules"
echo "════════════════════════════════════════════════════════════"

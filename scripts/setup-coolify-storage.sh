#!/usr/bin/env bash
#
# ORBIS Coolify Persistent Storage Setup
# Bu script VPS'te çalıştırılır. Coolify uygulaması için /secrets/ dizinini
# hazırlar, JSON dosyalarını koyar ve yetkileri ayarlar.
#
# VPS'te /data/coolify/applications/df6f8aww5jif21e364yd0dtw/secrets/
# dizinine JSON dosyaları yerleştirir. Coolify Directories tab'ında bu
# dizin /app/secrets olarak mount edilir.
#
# Kullanım:
#   1) Lokalden JSON dosyalarını VPS'e scp et:
#      scp firebase-credentials.json user@vps:/tmp/
#      scp ga4-service-account.json user@vps:/tmp/
#   2) VPS'te bu scripti çalıştır:
#      bash setup-coolify-storage.sh
#
set -euo pipefail

# Coolify uygulama dizini (senin app ID'nle değiştir)
APP_ID="${COOLIFY_APP_ID:-df6f8aww5jif21e364yd0dtw}"
APP_DIR="/data/coolify/applications/${APP_ID}"
SECRETS_DIR="${APP_DIR}/secrets"

echo "════════════════════════════════════════════════════════════"
echo "  ORBIS Coolify Secrets Setup"
echo "════════════════════════════════════════════════════════════"
echo "App ID: ${APP_ID}"
echo "Secrets dir: ${SECRETS_DIR}"
echo ""

# 1) Dizin oluştur
if [ ! -d "${SECRETS_DIR}" ]; then
  echo "[1/4] Creating secrets directory..."
  mkdir -p "${SECRETS_DIR}"
  chmod 700 "${SECRETS_DIR}"
  echo "  ✓ Created ${SECRETS_DIR}"
else
  echo "[1/4] Secrets directory already exists: ${SECRETS_DIR}"
fi

# 2) /tmp'deki JSON dosyalarını taşı
echo ""
echo "[2/4] Moving JSON files from /tmp..."
for f in firebase-credentials.json ga4-service-account.json play-service-account.json; do
  if [ -f "/tmp/${f}" ]; then
    if [ -f "${SECRETS_DIR}/${f}" ]; then
      read -p "  ${f} already exists. Overwrite? (y/N) " ans
      if [ "$ans" != "y" ]; then
        echo "  - Skipped ${f}"
        continue
      fi
    fi
    mv "/tmp/${f}" "${SECRETS_DIR}/${f}"
    chmod 600 "${SECRETS_DIR}/${f}"
    echo "  ✓ Moved ${f} (chmod 600)"
  else
    echo "  - /tmp/${f} not found (skipping)"
  fi
done

# 3) Doğrulama
echo ""
echo "[3/4] Verifying files..."
for f in firebase-credentials.json ga4-service-account.json play-service-account.json; do
  if [ -f "${SECRETS_DIR}/${f}" ]; then
    size=$(stat -c%s "${SECRETS_DIR}/${f}")
    perm=$(stat -c%a "${SECRETS_DIR}/${f}")
    echo "  ✓ ${f}: ${size} bytes, perm=${perm}"
  else
    echo "  ✗ ${f}: MISSING (not in /tmp, will fail at runtime)"
  fi
done

# 4) Coolify Directories için talimat
echo ""
echo "[4/4] Coolify UI'da yapman gereken:"
echo ""
echo "  1) Coolify → orbisapp → Configuration → Persistent Storage → Directories"
echo "  2) Add New Row (her dosya için):"
echo ""
echo "     Source Path:  ${SECRETS_DIR}/firebase-credentials.json"
echo "     Dest Path:    /app/firebase-credentials.json"
echo ""
echo "     Source Path:  ${SECRETS_DIR}/ga4-service-account.json"
echo "     Dest Path:    /app/ga4-service-account.json"
echo ""
echo "     Source Path:  ${SECRETS_DIR}/play-service-account.json"
echo "     Dest Path:    /app/play-service-account.json"
echo ""
echo "  3) Save + Redeploy"
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Done!"
echo "════════════════════════════════════════════════════════════"

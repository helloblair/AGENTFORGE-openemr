#!/usr/bin/env bash
# deploy-vultr.sh — One-command setup for the Veris stack on a fresh Vultr VPS.
#
# Usage (on a fresh Ubuntu 22.04+ VPS):
#   curl -sSL https://raw.githubusercontent.com/helloblair/AGENTFORGE-openemr/master/scripts/deploy-vultr.sh | bash
#
# Or clone first and run locally:
#   git clone https://github.com/helloblair/AGENTFORGE-openemr.git /opt/veris
#   cd /opt/veris && bash scripts/deploy-vultr.sh

set -euo pipefail

REPO_URL="https://github.com/helloblair/AGENTFORGE-openemr.git"
INSTALL_DIR="/opt/veris"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║     Veris Healthcare Agent — VPS Deployment      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Install Docker ───────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "==> Installing Docker..."
    apt-get update -qq
    apt-get install -y -qq docker.io docker-compose-plugin git curl jq openssl
    systemctl enable --now docker
    echo "==> Docker installed."
else
    echo "==> Docker already installed."
    # Ensure compose plugin and jq are available
    apt-get install -y -qq docker-compose-plugin jq openssl 2>/dev/null || true
fi

# ── Step 2: Clone repo ──────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "==> Repo already exists at ${INSTALL_DIR}, pulling latest..."
    cd "$INSTALL_DIR"
    git pull --ff-only
else
    echo "==> Cloning repo to ${INSTALL_DIR}..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── Step 3: Configure environment ────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    echo "==> Creating ${ENV_FILE} from template..."
    cp .env.production.example "$ENV_FILE"

    # Auto-detect public IP
    PUBLIC_IP=$(curl -s4 ifconfig.me 2>/dev/null || curl -s4 icanhazip.com 2>/dev/null || echo "YOUR_VPS_IP")
    sed -i "s|DOMAIN=YOUR_VPS_IP|DOMAIN=${PUBLIC_IP}|" "$ENV_FILE"

    echo ""
    echo "  IMPORTANT: Edit ${ENV_FILE} before continuing."
    echo "  At minimum, set:"
    echo "    - ANTHROPIC_API_KEY"
    echo "    - MYSQL_ROOT_PASSWORD"
    echo "    - MYSQL_PASSWORD"
    echo "    - OE_PASS"
    echo ""
    echo "  Run: nano ${ENV_FILE}"
    echo ""
    echo "  Then re-run this script: bash scripts/deploy-vultr.sh"
    exit 0
fi

# Verify required vars are set
# shellcheck disable=SC1090
source "$ENV_FILE"

if [ "${ANTHROPIC_API_KEY:-}" = "sk-ant-..." ] || [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set in ${ENV_FILE}. Edit it and re-run."
    exit 1
fi

if [ "${MYSQL_ROOT_PASSWORD:-}" = "changeme_root" ] || [ -z "${MYSQL_ROOT_PASSWORD:-}" ]; then
    echo "ERROR: MYSQL_ROOT_PASSWORD still set to default. Edit ${ENV_FILE} and re-run."
    exit 1
fi

echo "==> Environment configured. Domain/IP: ${DOMAIN}"

# ── Step 4: Generate self-signed SSL cert ────────────────────────────
CERT_DIR="docker/nginx/certs"
if [ ! -f "${CERT_DIR}/selfsigned.crt" ]; then
    echo "==> Generating self-signed SSL certificate for ${DOMAIN}..."
    mkdir -p "$CERT_DIR"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${CERT_DIR}/selfsigned.key" \
        -out "${CERT_DIR}/selfsigned.crt" \
        -subj "/CN=${DOMAIN}" \
        -addext "subjectAltName=IP:${DOMAIN}" 2>/dev/null
    echo "==> SSL cert generated."
else
    echo "==> SSL cert already exists."
fi

# ── Step 5: Build and start ──────────────────────────────────────────
echo "==> Building and starting all services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

echo "==> Waiting for services to start..."
sleep 10

# ── Step 6: Bootstrap OAuth2 ─────────────────────────────────────────
echo "==> Running OAuth2 bootstrap..."
bash scripts/bootstrap-oauth.sh

# ── Step 7: Seed data ────────────────────────────────────────────────
echo "==> Installing Python dependencies for seeding..."
apt-get install -y -qq python3 python3-pip 2>/dev/null || true
pip3 install --quiet httpx python-dotenv mysql-connector-python 2>/dev/null || true

echo "==> Loading transplant schema and reference data..."
cd agent
MYSQL_HOST="${DOMAIN}" MYSQL_PORT=3306 MYSQL_USER="${MYSQL_USER:-openemr}" \
    MYSQL_PASS="${MYSQL_PASSWORD}" MYSQL_DATABASE="${MYSQL_DATABASE:-openemr}" \
    python3 scripts/load_transplant_data.py || echo "  (May need direct DB access — see below)"

echo "==> Seeding clinical data via REST API..."
python3 -m scripts.seed_clinical_data || echo "  (Seeding may need manual run — see below)"

echo "==> Loading transplant lab results via SQL..."
docker compose -f "/opt/veris/$COMPOSE_FILE" exec -T mariadb \
    mysql -u root -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE:-openemr}" \
    < scripts/seed_transplant_labs.sql || echo "  (Lab seeding may need manual run)"

cd /opt/veris

# ── Step 8: Status summary ───────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║            Deployment Complete!                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Frontend:  https://${DOMAIN}/"
echo "  Agent API: https://${DOMAIN}/api/health"
echo "  OpenEMR:   https://${DOMAIN}:8443/"
echo "  Login:     ${OE_USER:-admin} / ${OE_PASS}"
echo ""
echo "  NOTE: Self-signed cert — browser will show a warning."
echo "        Accept it once to proceed."
echo ""
echo "  Next steps:"
echo "    1. Verify: curl -sk https://${DOMAIN}/api/health"
echo "    2. Create a Vultr snapshot for future restores"
echo "    3. (Optional) Destroy this VPS to save money"
echo ""

#!/usr/bin/env bash
# bootstrap-oauth.sh — Register and enable an OAuth2 client on a fresh OpenEMR instance.
#
# Usage:
#   bash scripts/bootstrap-oauth.sh
#
# Requires: curl, jq, docker compose
# Reads MYSQL_ROOT_PASSWORD and DOMAIN from .env.production

set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
MAX_WAIT=180  # seconds to wait for OpenEMR

# ── Load environment ─────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Copy .env.production.example first."
    exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

OPENEMR_URL="https://${DOMAIN}:8443"

echo "==> Waiting for OpenEMR at ${OPENEMR_URL} (up to ${MAX_WAIT}s)..."

elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    if curl -sk "${OPENEMR_URL}/apis/default/fhir/metadata" >/dev/null 2>&1; then
        echo "==> OpenEMR is ready!"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    echo "    ...waiting (${elapsed}s)"
done

if [ $elapsed -ge $MAX_WAIT ]; then
    echo "ERROR: OpenEMR did not become ready within ${MAX_WAIT}s."
    echo "Check logs: docker compose -f $COMPOSE_FILE logs openemr"
    exit 1
fi

# ── Register OAuth2 client ───────────────────────────────────────────
echo "==> Registering OAuth2 client..."

SCOPES="openid api:oemr api:fhir user/patient.read user/patient.write user/AllergyIntolerance.read user/MedicationRequest.read user/Condition.read user/Practitioner.read user/PractitionerRole.read user/Coverage.read user/Observation.read user/allergy.read user/allergy.write user/medical_problem.read user/medical_problem.write user/medication.read user/medication.write user/encounter.read user/encounter.write user/vital.read user/vital.write user/insurance.read user/insurance.write user/insurance_company.read user/insurance_company.write user/practitioner.read user/practitioner.write user/facility.read user/transplant_criteria.read user/transplant_screening.read user/transplant_screening.write"

RESPONSE=$(curl -sk -X POST "${OPENEMR_URL}/oauth2/default/registration" \
    -H "Content-Type: application/json" \
    -d "{
        \"application_type\": \"private\",
        \"redirect_uris\": [\"${OPENEMR_URL}\"],
        \"post_logout_redirect_uris\": [\"${OPENEMR_URL}\"],
        \"client_name\": \"Veris Healthcare Agent\",
        \"token_endpoint_auth_method\": \"client_secret_post\",
        \"contacts\": [\"agent@veris.health\"],
        \"scope\": \"${SCOPES}\"
    }")

CLIENT_ID=$(echo "$RESPONSE" | jq -r '.client_id // empty')
CLIENT_SECRET=$(echo "$RESPONSE" | jq -r '.client_secret // empty')

if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
    echo "ERROR: OAuth2 registration failed."
    echo "Response: $RESPONSE"
    exit 1
fi

echo "==> Client registered: $CLIENT_ID"

# ── Enable the client via direct SQL ─────────────────────────────────
echo "==> Enabling OAuth2 client in database..."

docker compose -f "$COMPOSE_FILE" exec -T mariadb \
    mysql -u root -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE:-openemr}" \
    -e "UPDATE oauth_clients SET is_enabled = 1 WHERE client_id = '${CLIENT_ID}';"

echo "==> Client enabled."

# ── Write credentials to .env.production ─────────────────────────────
echo "==> Updating ${ENV_FILE} with OAuth2 credentials..."

if grep -q "^OPENEMR_CLIENT_ID=" "$ENV_FILE"; then
    sed -i.bak "s|^OPENEMR_CLIENT_ID=.*|OPENEMR_CLIENT_ID=${CLIENT_ID}|" "$ENV_FILE"
    sed -i.bak "s|^OPENEMR_CLIENT_SECRET=.*|OPENEMR_CLIENT_SECRET=${CLIENT_SECRET}|" "$ENV_FILE"
    rm -f "${ENV_FILE}.bak"
else
    echo "OPENEMR_CLIENT_ID=${CLIENT_ID}" >> "$ENV_FILE"
    echo "OPENEMR_CLIENT_SECRET=${CLIENT_SECRET}" >> "$ENV_FILE"
fi

# ── Restart agent to pick up new credentials ─────────────────────────
echo "==> Restarting agent container..."
docker compose -f "$COMPOSE_FILE" restart agent

echo ""
echo "=== OAuth2 Bootstrap Complete ==="
echo "  Client ID:     ${CLIENT_ID}"
echo "  Client Secret: ${CLIENT_SECRET}"
echo "  Agent restarted with new credentials."
echo ""

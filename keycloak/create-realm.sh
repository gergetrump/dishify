#!/bin/sh
set -e

KCADM="/opt/keycloak/bin/kcadm.sh"
KC="/opt/keycloak/bin/kc.sh"
REALM="dishify"

# ---------------------------------------------------------------------------
# Required env vars:
#   KEYCLOAK_ADMIN, KEYCLOAK_ADMIN_PASSWORD
#   KEYCLOAK_BACKEND_SECRET  — client secret for dishify-backend
#   KEYCLOAK_TEST_USER         — test user username
#   KEYCLOAK_TEST_EMAIL        — test user email
#   KEYCLOAK_TEST_PASSWORD     — test user password
#   IOS_REDIRECT_URI           — optional; default dishify://callback
#   WEB_REDIRECT_URI           — optional; default http://localhost:5173/*
#   KEYCLOAK_PUBLIC_URL        — optional; frontend URL used in OIDC issuer/metadata
# ---------------------------------------------------------------------------

IOS_REDIRECT_URI="${IOS_REDIRECT_URI:-dishify://callback}"
WEB_REDIRECT_URI="${WEB_REDIRECT_URI:-http://localhost:5173/*}"
KEYCLOAK_PUBLIC_URL="${KEYCLOAK_PUBLIC_URL:-http://localhost:9001}"

# Start Keycloak in background
$KC start-dev --http-port=9001 --hostname-url="$KEYCLOAK_PUBLIC_URL" --hostname-strict=false &
KC_PID=$!

echo "Waiting for Keycloak to become ready..."
until $KCADM config credentials \
  --server http://localhost:9001 \
  --realm master \
  --user "$KEYCLOAK_ADMIN" \
  --password "$KEYCLOAK_ADMIN_PASSWORD"; do
  echo "  not ready, retrying..."
  sleep 5
done
echo "Keycloak ready."

# Stop failing the container if any provisioning step errors out.
set +e

client_exists() {
  $KCADM get clients -r "$REALM" -q "clientId=$1" 2>/dev/null | grep -q '"clientId"'
}

get_client_uuid() {
  $KCADM get clients -r "$REALM" -q "clientId=$1" --fields id --format csv --noquotes 2>/dev/null | tail -n1
}

# ---------------------------------------------------------------------------
# 1. Realm
# ---------------------------------------------------------------------------
if ! $KCADM get realms | grep "\"realm\" : \"$REALM\"" > /dev/null; then
  $KCADM create realms \
    -s realm=$REALM \
    -s enabled=true \
    -s registrationAllowed=true \
    -s resetPasswordAllowed=true \
    -s rememberMe=true \
    -s 'attributes.enableUnmanagedAttributes=true'
  echo "Realm '$REALM' created."
else
  echo "Realm '$REALM' already exists."
  $KCADM update realms/$REALM -r master -s 'attributes.enableUnmanagedAttributes=true' 2>/dev/null
fi

# Disable profile/email gates that block password-grant login in dev
for action in VERIFY_PROFILE VERIFY_EMAIL; do
  $KCADM update "authentication/required-actions/${action}" -r $REALM -s enabled=false 2>/dev/null
done

$KCADM update users/profile -r $REALM -f /opt/keycloak/dishify-user-profile.json 2>/dev/null
echo "User profile updated with preference attributes."

# ---------------------------------------------------------------------------
# 2. iOS public client (PKCE)
# ---------------------------------------------------------------------------
if ! client_exists "dishify-ios"; then
  $KCADM create clients -r $REALM \
    -s clientId=dishify-ios \
    -s name="Dishify iOS" \
    -s enabled=true \
    -s publicClient=true \
    -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=false \
    -s protocol=openid-connect \
    -s 'redirectUris=["'"$IOS_REDIRECT_URI"'"]' \
    -s 'webOrigins=["*"]' \
    -s 'attributes.pkce.code.challenge.method=S256'
  echo "Client 'dishify-ios' created."

  IOS_UUID=$(get_client_uuid "dishify-ios")

  $KCADM create clients/$IOS_UUID/protocol-mappers/models -r $REALM \
    -s name=exclusion_restrictions \
    -s protocol=openid-connect \
    -s protocolMapper=oidc-usermodel-attribute-mapper \
    -s 'config."user.attribute"=exclusion_restrictions' \
    -s 'config."claim.name"=exclusion_restrictions' \
    -s 'config."jsonType.label"=String' \
    -s 'config.multivalued=true' \
    -s 'config."access.token.claim"=true' \
    -s 'config."id.token.claim"=true' \
    -s 'config."userinfo.token.claim"=true'

  echo "Protocol mappers added."
else
  echo "Client 'dishify-ios' already exists."
fi

# ---------------------------------------------------------------------------
# 2b. Web public client (PKCE) — React frontend
# ---------------------------------------------------------------------------
if ! client_exists "dishify-web"; then
  $KCADM create clients -r $REALM \
    -s clientId=dishify-web \
    -s name="Dishify Web" \
    -s enabled=true \
    -s publicClient=true \
    -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=true \
    -s protocol=openid-connect \
    -s 'redirectUris=["'"$WEB_REDIRECT_URI"'"]' \
    -s 'webOrigins=["*"]' \
    -s 'attributes.pkce.code.challenge.method=S256'
  echo "Client 'dishify-web' created."
else
  echo "Client 'dishify-web' already exists."
  WEB_UUID=$(get_client_uuid "dishify-web")
  $KCADM update clients/$WEB_UUID -r $REALM -s directAccessGrantsEnabled=true
  echo "Client 'dishify-web' direct access grants enabled."
fi

# ---------------------------------------------------------------------------
# 3. Backend confidential client (service account — writes user attributes)
# ---------------------------------------------------------------------------
if ! client_exists "dishify-backend"; then
  $KCADM create clients -r $REALM \
    -s clientId=dishify-backend \
    -s name="Dishify Backend" \
    -s enabled=true \
    -s publicClient=false \
    -s serviceAccountsEnabled=true \
    -s standardFlowEnabled=false \
    -s directAccessGrantsEnabled=false \
    -s clientAuthenticatorType=client-secret \
    -s secret="$KEYCLOAK_BACKEND_SECRET"

  $KCADM add-roles -r $REALM \
    --uusername service-account-dishify-backend \
    --rolename manage-users \
    --rolename view-users \
    --cclientid realm-management

  echo "Client 'dishify-backend' created."
else
  echo "Client 'dishify-backend' already exists."
  BACKEND_UUID=$(get_client_uuid "dishify-backend")
  $KCADM update clients/$BACKEND_UUID -r $REALM \
    -s directAccessGrantsEnabled=false
  echo "Client 'dishify-backend' updated."
fi

# ---------------------------------------------------------------------------
# 3b. API login client (password grant for user-service)
# ---------------------------------------------------------------------------
if ! client_exists "dishify-api"; then
  $KCADM create clients -r $REALM \
    -s clientId=dishify-api \
    -s name="Dishify API Login" \
    -s enabled=true \
    -s publicClient=false \
    -s serviceAccountsEnabled=false \
    -s standardFlowEnabled=false \
    -s directAccessGrantsEnabled=true \
    -s clientAuthenticatorType=client-secret \
    -s secret="$KEYCLOAK_BACKEND_SECRET"
  echo "Client 'dishify-api' created."
else
  echo "Client 'dishify-api' already exists."
fi

# ---------------------------------------------------------------------------
# 4. Test user (with example attribute values)
# ---------------------------------------------------------------------------
if ! $KCADM get users -r $REALM -q username=$KEYCLOAK_TEST_USER | grep "\"username\" : \"$KEYCLOAK_TEST_USER\"" > /dev/null; then
  $KCADM create users -r $REALM \
    -s username="$KEYCLOAK_TEST_USER" \
    -s email="$KEYCLOAK_TEST_EMAIL" \
    -s enabled=true \
    -s emailVerified=true \
    -s 'requiredActions=[]' \
    -s 'attributes.exclusion_restrictions=["shellfish_allergy","vegetarian"]'

  TEST_USER_ID=$($KCADM get users -r $REALM -q username=$KEYCLOAK_TEST_USER --fields id --format csv | tail -n1 | tr -d '\r"')
  $KCADM set-password -r $REALM --userid "$TEST_USER_ID" --new-password "$KEYCLOAK_TEST_PASSWORD"

  echo "Test user '$KEYCLOAK_TEST_USER' created."
else
  echo "Test user '$KEYCLOAK_TEST_USER' already exists."
fi

# Keep container running
wait $KC_PID

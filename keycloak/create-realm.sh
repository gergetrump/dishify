#!/bin/sh
set -e

KCADM="/opt/keycloak/bin/kcadm.sh"
KC="/opt/keycloak/bin/kc.sh"
REALM="dishify"

# ---------------------------------------------------------------------------
# Required env vars:
#   KEYCLOAK_ADMIN, KEYCLOAK_ADMIN_PASSWORD
#   KEYCLOAK_BACKEND_SECRET       — client secret for dishify-backend
#   KEYCLOAK_USER_SERVICE_SECRET  — client secret for dishify-user-service
#   KEYCLOAK_TEST_USER            — test user username
#   KEYCLOAK_TEST_EMAIL           — test user email
#   KEYCLOAK_TEST_PASSWORD        — test user password
#   FRONTEND_URL                  — origin of the frontend (e.g. http://localhost:4200)
# ---------------------------------------------------------------------------

# Start Keycloak in background
$KC start-dev --http-port=9001 &
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

# ---------------------------------------------------------------------------
# 1. Realm
# ---------------------------------------------------------------------------
if ! $KCADM get realms | grep "\"realm\" : \"$REALM\"" > /dev/null; then
  $KCADM create realms \
    -s realm=$REALM \
    -s enabled=true \
    -s registrationAllowed=true \
    -s resetPasswordAllowed=true \
    -s rememberMe=true
  echo "Realm '$REALM' created."
else
  echo "Realm '$REALM' already exists."
fi

# ---------------------------------------------------------------------------
# 2. Frontend public client (PKCE)
# ---------------------------------------------------------------------------
if ! $KCADM get clients -r $REALM | grep '"clientId" : "dishify-frontend"' > /dev/null; then
  $KCADM create clients -r $REALM \
    -s clientId=dishify-frontend \
    -s name="Dishify Frontend" \
    -s enabled=true \
    -s publicClient=true \
    -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=false \
    -s protocol=openid-connect \
    -s rootUrl="$FRONTEND_URL" \
    -s 'redirectUris=["*"]' \
    -s 'webOrigins=["*"]' \
    -s 'attributes.pkce.code.challenge.method=S256'
  echo "Client 'dishify-frontend' created."

  FRONTEND_UUID=$($KCADM get clients -r $REALM --fields id,clientId | \
    grep -B1 '"clientId" : "dishify-frontend"' | \
    grep '"id"' | sed 's/.*"id" : "\(.*\)".*/\1/')

  # Protocol mapper: exclusion_restrictions (multivalued string array in JWT)
  $KCADM create clients/$FRONTEND_UUID/protocol-mappers/models -r $REALM \
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

  # Protocol mapper: cuisine_preferences (multivalued string array in JWT)
  # Rename this field if needed
  $KCADM create clients/$FRONTEND_UUID/protocol-mappers/models -r $REALM \
    -s name=cuisine_preferences \
    -s protocol=openid-connect \
    -s protocolMapper=oidc-usermodel-attribute-mapper \
    -s 'config."user.attribute"=cuisine_preferences' \
    -s 'config."claim.name"=cuisine_preferences' \
    -s 'config."jsonType.label"=String' \
    -s 'config.multivalued=true' \
    -s 'config."access.token.claim"=true' \
    -s 'config."id.token.claim"=true' \
    -s 'config."userinfo.token.claim"=true'

  echo "Protocol mappers added."
else
  echo "Client 'dishify-frontend' already exists."
fi

# ---------------------------------------------------------------------------
# 3. Backend confidential client (service account — writes user attributes)
# ---------------------------------------------------------------------------
if ! $KCADM get clients -r $REALM | grep '"clientId" : "dishify-backend"' > /dev/null; then
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
fi

# ---------------------------------------------------------------------------
# 3b. User-service confidential client (service account — manages users)
# ---------------------------------------------------------------------------
if ! $KCADM get clients -r $REALM | grep '"clientId" : "dishify-user-service"' > /dev/null; then
  $KCADM create clients -r $REALM \
    -s clientId=dishify-user-service \
    -s name="Dishify User Service" \
    -s enabled=true \
    -s publicClient=false \
    -s serviceAccountsEnabled=true \
    -s standardFlowEnabled=false \
    -s directAccessGrantsEnabled=false \
    -s clientAuthenticatorType=client-secret \
    -s secret="$KEYCLOAK_USER_SERVICE_SECRET"

  $KCADM add-roles -r $REALM \
    --uusername service-account-dishify-user-service \
    --rolename manage-users \
    --rolename view-users \
    --cclientid realm-management

  echo "Client 'dishify-user-service' created."
else
  echo "Client 'dishify-user-service' already exists."
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
    -s 'attributes.exclusion_restrictions=["gluten","dairy"]' \
    -s 'attributes.cuisine_preferences=["italian","asian"]'

  TEST_USER_ID=$($KCADM get users -r $REALM -q username=$KEYCLOAK_TEST_USER --fields id --format csv | tail -n1 | tr -d '\r"')
  $KCADM set-password -r $REALM --userid "$TEST_USER_ID" --new-password "$KEYCLOAK_TEST_PASSWORD"

  echo "Test user '$KEYCLOAK_TEST_USER' created."
else
  echo "Test user '$KEYCLOAK_TEST_USER' already exists."
fi

# Keep container running
wait $KC_PID

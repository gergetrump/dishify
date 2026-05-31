#!/usr/bin/env bash
set -euo pipefail

# Build and push Docker images to GHCR
# Usage: ./build_and_push.sh [TAG] [SHA_TAG]
# Example: ./build_and_push.sh latest abc123

REGISTRY="ghcr.io/cjzbeastmode"
TAG="${1:-latest}"
SHA_TAG="${2:-${GITHUB_SHA:-local-$(date +%s)}}"

# Load environment variables from .env if it exists
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

GHCR_USERNAME="${GHCR_USERNAME:-cjzbeastmode}"
GHCR_TOKEN="${GHCR_TOKEN:-}"

if [[ -z "${GHCR_TOKEN}" ]]; then
  echo "GHCR_TOKEN is not set. Add it to .env or export it before running this script." >&2
  exit 1
fi

echo "🔐 Logging in to GitHub Container Registry..."
echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USERNAME}" --password-stdin >/dev/null

# Array of services: "name context dockerfile"
SERVICES=(
  "moebel services/moebel_service services/moebel_service/Dockerfile"
  "kfz services/kfz_service services/kfz_service/Dockerfile"
  "flug services/flug_service services/flug_service/Dockerfile"
  "hotel services/hotel_service services/hotel_service/Dockerfile"
  "handyvertrag services/handyvertrag_service services/handyvertrag_service/Dockerfile"
  "home-service services/home_service services/home_service/Dockerfile"
  "frontend web-frontend web-frontend/Dockerfile"
)

echo "Building images with tags: ${TAG}, ${SHA_TAG}"
echo ""

FAILED_BUILDS=()

for entry in "${SERVICES[@]}"; do
  # Parse entry: name context dockerfile
  read -r service context dockerfile <<< "$entry"
  image="${REGISTRY}/check24-gendev-${service}"
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔨 Building ${service}"
  echo "   Context: ${context}"
  echo "   Dockerfile: ${dockerfile}"
  echo "   Image: ${image}"
  
  # Build with both tags
  if docker build \
    -f "${dockerfile}" \
    -t "${image}:${SHA_TAG}" \
    -t "${image}:${TAG}" \
    "${context}"; then
    
    echo "Build successful: ${service}"
    
    # Push both tags
    echo "Pushing ${image}:${SHA_TAG}..."
    docker push "${image}:${SHA_TAG}"
    
    echo "Pushing ${image}:${TAG}..."
    docker push "${image}:${TAG}"
    
    echo "Push successful: ${service}"
  else
    echo "Build failed: ${service}"
    FAILED_BUILDS+=("${service}")
  fi
  
  echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ${#FAILED_BUILDS[@]} -eq 0 ]; then
  echo "All builds completed successfully!"
  echo ""
  echo "Images pushed:"
  for entry in "${SERVICES[@]}"; do
    service="${entry%% *}"
    echo "  - ${REGISTRY}/check24-gendev-${service}:${TAG}"
    echo "  - ${REGISTRY}/check24-gendev-${service}:${SHA_TAG}"
  done
  exit 0
else
  echo "Failed builds:"
  for service in "${FAILED_BUILDS[@]}"; do
    echo "  - ${service}"
  done
  exit 1
fi


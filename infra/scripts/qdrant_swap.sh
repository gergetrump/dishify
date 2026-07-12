#!/usr/bin/env bash
# Safely import a third-party Qdrant storage dump onto the Dishify server:
# validate it in an isolated throwaway container before ever touching the
# live qdrant_data volume, then promote (with a rollback path) once it
# checks out.
set -euo pipefail

SSH_KEY="${SSH_KEY:-$HOME/.ssh/dishify_deploy}"
SERVER_IP="${SERVER_IP:-167.233.165.44}"
REMOTE="root@${SERVER_IP}"
SSH_OPTS=(-o StrictHostKeyChecking=no -i "$SSH_KEY")

IMPORT_DIR="/root/qdrant_import"
VOLUME_DIR="/var/lib/docker/volumes/dishify_qdrant_data/_data"
BACKUP_DIR="${VOLUME_DIR}.bak"
TEST_CONTAINER="qdrant-import-test"
TEST_PORT=6334
# Must match the qdrant image pinned in docker-compose.yml.
QDRANT_IMAGE="qdrant/qdrant:v1.12.4"

usage() {
  cat <<EOF
Usage: $0 <command> [args]

Commands:
  validate <path-to-qdrant_volume.tar.gz>
      Stream the tarball to the server and boot a throwaway Qdrant
      container against it on port ${TEST_PORT}, isolated from the live
      stack. Prints collection status/point counts to eyeball.

  inspect
      Re-query the already-running throwaway container's collections.

  promote
      Stop the live qdrant container, move the validated import into place
      as the real volume (previous data kept at ${BACKUP_DIR}), and
      restart. Only run after 'validate' looks right. Asks for confirmation.

  rollback
      Restore the previous volume from ${BACKUP_DIR} (only works if
      promote already ran and the backup still exists).

  cleanup
      Tear down the throwaway test container and remove the scratch import
      dir. Safe to run any time; always run after a successful promote to
      reclaim disk.
EOF
  exit 1
}

remote() {
  ssh "${SSH_OPTS[@]}" "$REMOTE" "$@"
}

cmd_validate() {
  local tarball="${1:-}"
  [ -n "$tarball" ] && [ -f "$tarball" ] || { echo "Usage: $0 validate <path-to-qdrant_volume.tar.gz>" >&2; exit 1; }

  echo "==> Streaming $tarball to ${REMOTE}:${IMPORT_DIR} (no intermediate .tar.gz written on the server)"
  remote "rm -rf '$IMPORT_DIR' && mkdir -p '$IMPORT_DIR'"
  gzip -dc "$tarball" | ssh "${SSH_OPTS[@]}" "$REMOTE" "tar -xf - -C '$IMPORT_DIR'"

  echo "==> Booting throwaway Qdrant ($QDRANT_IMAGE) read-only against the import on port ${TEST_PORT}"
  remote "
    docker rm -f $TEST_CONTAINER >/dev/null 2>&1 || true
    docker run -d --name $TEST_CONTAINER \
      -p ${TEST_PORT}:6333 \
      -v '${IMPORT_DIR}:/qdrant/storage:ro' \
      $QDRANT_IMAGE
  "

  echo "==> Waiting for it to come up..."
  remote "
    for i in \$(seq 1 30); do
      curl -sf http://localhost:${TEST_PORT}/collections >/dev/null && exit 0
      sleep 2
    done
    echo 'Throwaway qdrant did not come up in time' >&2
    exit 1
  "

  cmd_inspect
}

cmd_inspect() {
  echo "==> Collections on throwaway instance (port ${TEST_PORT}):"
  remote "curl -s http://localhost:${TEST_PORT}/collections | python3 -m json.tool"
  echo
  for c in recipes_full recipes_10000; do
    echo "--- $c ---"
    remote "curl -s http://localhost:${TEST_PORT}/collections/$c | python3 -c \"
import json, sys
d = json.load(sys.stdin)
r = d.get('result')
if r:
    print('status:', r['status'], '| points_count:', r['points_count'], '| vector_size:', r['config']['params']['vectors']['size'])
else:
    print(d)
\"" || true
  done
  echo
  echo "Review the numbers above. If they look right: $0 promote"
  echo "Either way, once you're done deciding:      $0 cleanup"
}

cmd_promote() {
  read -r -p "This stops the live qdrant container and swaps its data. Continue? [y/N] " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]] || { echo "Aborted."; exit 1; }

  remote "
    set -euo pipefail
    test -d '$IMPORT_DIR/collections' || { echo 'No validated import at $IMPORT_DIR — run validate first.' >&2; exit 1; }
    docker rm -f $TEST_CONTAINER >/dev/null 2>&1 || true
    docker stop dishify-qdrant
    rm -rf '$BACKUP_DIR'
    mv '$VOLUME_DIR' '$BACKUP_DIR'
    mv '$IMPORT_DIR' '$VOLUME_DIR'
    docker start dishify-qdrant
  "

  echo "==> Waiting for live qdrant to come back up..."
  remote "
    for i in \$(seq 1 30); do
      curl -sf http://localhost:6333/collections >/dev/null && exit 0
      sleep 2
    done
    echo 'Live qdrant did not come back up — run: $0 rollback' >&2
    exit 1
  "

  echo "==> Live recipes_full collection after promote:"
  remote "curl -s http://localhost:6333/collections/recipes_full | python3 -m json.tool"
  echo
  echo "Previous data preserved at ${BACKUP_DIR} on the server."
  echo "Once you're confident, remove it manually to reclaim disk: ssh -i $SSH_KEY $REMOTE rm -rf $BACKUP_DIR"
}

cmd_rollback() {
  remote "
    set -euo pipefail
    test -d '$BACKUP_DIR' || { echo 'No backup found at $BACKUP_DIR' >&2; exit 1; }
    docker stop dishify-qdrant
    rm -rf '$VOLUME_DIR'
    mv '$BACKUP_DIR' '$VOLUME_DIR'
    docker start dishify-qdrant
  "
  echo "Rolled back to the previous data."
}

cmd_cleanup() {
  remote "
    docker rm -f $TEST_CONTAINER >/dev/null 2>&1 || true
    rm -rf '$IMPORT_DIR'
  "
  echo "Removed the throwaway container and scratch import dir."
}

case "${1:-}" in
  validate) shift; cmd_validate "$@" ;;
  inspect) cmd_inspect ;;
  promote) cmd_promote ;;
  rollback) cmd_rollback ;;
  cleanup) cmd_cleanup ;;
  *) usage ;;
esac

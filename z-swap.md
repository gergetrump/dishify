# Qdrant 2M dataset swap — runbook

Goal: get the 2M-point `recipes_full` collection live on the Hetzner server
(cx23, 4GB RAM, no swap) without OOM-killing the rest of the stack
(Postgres, Keycloak, etc).

Server: `167.233.165.44` (root, key `~/.ssh/dishify_deploy`)
Script: `infra/scripts/qdrant_swap.sh`

## Why this is risky

- The dump was indexed with `on_disk: false` for vectors + HNSW → Qdrant
  tries to keep the whole collection resident in RAM. `recipes_full` is
  6.6GB; the server only has ~1.4GB free normally, no swap.
- Fix: convert the collection to `on_disk: true` (mmap from disk) +
  scalar int8 quantization with `always_ram: true` (keeps a ~768MB
  compressed copy in RAM for fast search, full-precision vectors stay on
  disk for rescoring). Standard Qdrant pattern for large dataset / small
  box.

## Status so far

- [x] Docker build cache pruned on server (`docker builder prune -a -f`)
      → disk free went from 9.6GB to 16GB.
- [x] Raw (unconverted) dump already sitting on the server at
      `/root/qdrant_import` (7.0GB, from an earlier `validate` run that
      was never promoted/cleaned up). No need to re-upload from
      `~/Downloads/qdrant_volume.tar.gz`.
- [ ] Swap file
- [ ] In-place conversion to on-disk + quantized
- [ ] Promote
- [ ] Cleanup

## Phase 0 — swap file (safety net)

SSH in once:
```bash
ssh -i ~/.ssh/dishify_deploy root@167.233.165.44
```

On the server:
```bash
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

This doesn't prevent memory pressure, it just means an overflow degrades
(slow/thrashy) instead of triggering the OOM killer on Postgres/Keycloak.

Do this during a low-traffic window — the segment rewrite in Phase 1 is
CPU/disk-I/O heavy on a 2-vCPU box and can cause real-traffic latency
spikes even if nothing gets OOM-killed.

## Phase 1 — convert the already-uploaded dump in place

Still on the server (same session):

```bash
# Writable throwaway container against the raw import (NOT :ro — the
# optimizer needs to rewrite segments on disk).
# --memory caps it so if the old on_disk:false config blows up RAM usage,
# cgroups kill THIS container specifically — not a host-wide OOM lottery
# that could pick Postgres/Keycloak instead.
docker rm -f qdrant-import-test 2>/dev/null
docker run -d --name qdrant-import-test -p 6334:6333 \
  --memory=2g --memory-swap=4g \
  -v /root/qdrant_import:/qdrant/storage \
  qdrant/qdrant:v1.12.4

# Risky moment: first load under the OLD on_disk:false config. Watch it.
watch -n2 free -h
# Ctrl-C once `curl -sf http://localhost:6334/collections` responds.
# If available memory craters and swap thrashes hard, abort:
#   docker stop qdrant-import-test
# and fall back to converting on the Mac instead (see "Fallback" below).
```

Once it's up, convert:
```bash
curl -X PATCH http://localhost:6334/collections/recipes_full \
  -H 'Content-Type: application/json' \
  -d '{"vectors":{"on_disk":true},"hnsw_config":{"on_disk":true},"quantization_config":{"scalar":{"type":"int8","quantile":0.99,"always_ram":true}}}'

watch -n10 'curl -s http://localhost:6334/collections/recipes_full | python3 -m json.tool | grep -E "status|indexed_vectors_count|points_count"'
```

Wait for `status: green`, `optimizer_status: ok`, and
`indexed_vectors_count == points_count`. Then:

```bash
docker stop qdrant-import-test
exit
```

`/root/qdrant_import` is now converted in place and matches what
`promote` expects.

**Do NOT run `qdrant_swap.sh validate` after this** — it starts with
`rm -rf $IMPORT_DIR`, which would wipe the conversion you just did.

## Phase 2 — promote

From your Mac, in the repo:
```bash
./infra/scripts/qdrant_swap.sh promote
```

Stops live `dishify-qdrant`, swaps in `/root/qdrant_import`, keeps the
old volume as `..._data.bak`, restarts.

Verify:
```bash
ssh -i ~/.ssh/dishify_deploy root@167.233.165.44 "free -h; docker stats --no-stream"
```
Watch for a few minutes under real traffic, and run an actual search
through the app to confirm results + latency look right.

## Phase 3 — cleanup

```bash
./infra/scripts/qdrant_swap.sh cleanup
```

Once confident (after a day of normal traffic), reclaim the backup:
```bash
ssh -i ~/.ssh/dishify_deploy root@167.233.165.44 "rm -rf /var/lib/docker/volumes/dishify_qdrant_data/_data.bak"
```

## Rollback

If anything looks wrong after promote:
```bash
./infra/scripts/qdrant_swap.sh rollback
```

## Fallback — convert on the Mac instead

Only needed if Phase 1's in-place conversion looks unsafe on the server
even with swap.

```bash
docker run -d --name qdrant-convert -p 6335:6333 \
  -v ~/Downloads/qdrant_volume:/qdrant/storage \
  qdrant/qdrant:v1.12.4

until curl -sf http://localhost:6335/collections >/dev/null; do sleep 2; done

curl -X PATCH http://localhost:6335/collections/recipes_full \
  -H 'Content-Type: application/json' \
  -d '{"vectors":{"on_disk":true},"hnsw_config":{"on_disk":true},"quantization_config":{"scalar":{"type":"int8","quantile":0.99,"always_ram":true}}}'

# poll until converted (same check as above, port 6335), then:
docker stop qdrant-convert && docker rm qdrant-convert
tar -C ~/Downloads/qdrant_volume -czf ~/Downloads/qdrant_volume_ondisk.tar.gz .

./infra/scripts/qdrant_swap.sh validate ~/Downloads/qdrant_volume_ondisk.tar.gz
# then promote as in Phase 2
```

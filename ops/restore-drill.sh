#!/usr/bin/env bash
# Prove that a backup restores (docs/backups.md). Restores a database dump
# into a throwaway PostGIS container beside the live one, never into the
# live database, prints row counts to compare with the site, and removes
# the container. Run it monthly, and after any change to the backup.
#
#   bash ops/restore-drill.sh                       the newest ~/backups/fisheye-*.dump
#   bash ops/restore-drill.sh path/to/fisheye-….dump
#   bash ops/restore-drill.sh s3://bucket/fisheye/fisheye-20261101-0915.dump
#
# The drill database takes some memory while it runs; on a small server,
# run it when the site is quiet (or on a laptop with Docker).
set -euo pipefail

cd "$(dirname "$0")/.."
if [ -f "$HOME/.fisheye-backup.env" ]; then
  # shellcheck disable=SC1091
  . "$HOME/.fisheye-backup.env"
fi

DIR="${BACKUP_DIR:-$HOME/backups}"
SRC="${1:-$(ls -1t "$DIR"/fisheye-*.dump 2>/dev/null | head -n 1 || true)}"
if [ -z "$SRC" ]; then
  echo "No backup found in $DIR. Run ops/backup.sh first, or pass a file." >&2
  exit 1
fi

NAME="fisheye-restore-drill"
IMAGE="postgis/postgis:16-3.4"  # the same image as docker-compose.yml's db
TMP="$(mktemp -d)"
cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$TMP"
}
trap cleanup EXIT

if [[ "$SRC" == s3://* ]]; then
  aws s3 cp --only-show-errors "$SRC" "$TMP/"
  SRC="$TMP/$(basename "$SRC")"
fi

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" -e POSTGRES_USER=fisheye -e POSTGRES_PASSWORD=drill -e POSTGRES_DB=fisheye "$IMAGE" >/dev/null
for _ in $(seq 1 60); do
  if docker exec "$NAME" pg_isready -U fisheye -d fisheye >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "Restoring $(basename "$SRC") ($(du -h "$SRC" | cut -f1))…"
if ! docker exec -i "$NAME" pg_restore -U fisheye -d fisheye --no-owner < "$SRC"; then
  echo "pg_restore reported errors (above). Read them: a few about objects that already exist are harmless; missing tables are not." >&2
fi

echo
echo "Rows in the restored copy:"
docker exec "$NAME" psql -U fisheye -d fisheye -At -F ' ' -c "
  select 'waterbodies', count(*) from waterbodies
  union all select 'waterbody_species', count(*) from waterbody_species
  union all select 'tackle_shops', count(*) from tackle_shops
  union all select 'users', count(*) from users
  union all select 'catch_pins', count(*) from catch_pins
  union all select 'pin_photos', count(*) from pin_photos"
echo
echo "The same counts on the live site, to compare:"
echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db psql -U fisheye -d fisheye -c 'select count(*) from waterbodies'"

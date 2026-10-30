#!/usr/bin/env bash
# Back up FishEye's database and catch photos (docs/backups.md).
#
#   bash ops/backup.sh                 by hand, from ~/FishEye
#   15 9 * * * cd /home/ubuntu/FishEye && bash ops/backup.sh >> /home/ubuntu/backups/backup.log 2>&1
#
# Writes $BACKUP_DIR/fisheye-<UTC time>.dump (pg_dump's custom format:
# compressed, and restorable table by table) and media-<UTC time>.tar.gz
# (the uploaded photos), copies both to $BACKUP_S3_URI when it is set (a
# backup on the server's own disk dies with that disk), and keeps the last
# $KEEP_DAYS days here. $BACKUP_PING_URL, when set, is called on success and
# with /fail appended on failure (healthchecks.io works that way), so a
# backup that fails or never runs raises an alert.
#
# Settings: the environment, or ~/.fisheye-backup.env (cron doesn't read
# the app's .env, and the backup needs none of its secrets).
set -euo pipefail

cd "$(dirname "$0")/.."
if [ -f "$HOME/.fisheye-backup.env" ]; then
  # shellcheck disable=SC1091
  . "$HOME/.fisheye-backup.env"
fi

DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
DIR="${BACKUP_DIR:-$HOME/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
STAMP="$(date -u +%Y%m%d-%H%M)"
DB_FILE="$DIR/fisheye-$STAMP.dump"
MEDIA_FILE="$DIR/media-$STAMP.tar.gz"

ping_monitor() {
  if [ -n "${BACKUP_PING_URL:-}" ]; then
    curl -fsS -m 10 --retry 3 "${BACKUP_PING_URL}$1" >/dev/null || true
  fi
}
fail() {
  echo "$(date -u +%FT%TZ) backup FAILED: $*" >&2
  rm -f "$DB_FILE.part" "$MEDIA_FILE.part"
  ping_monitor /fail
  exit 1
}
trap 'fail "command on line $LINENO"' ERR

mkdir -p "$DIR"
echo "$(date -u +%FT%TZ) backup start"

# 1. The database. Written to .part first, so a dump cut short is never
#    mistaken for a good one.
$DC exec -T db pg_dump -U fisheye -d fisheye -Fc > "$DB_FILE.part"
[ -s "$DB_FILE.part" ] || fail "the database dump is empty"
mv "$DB_FILE.part" "$DB_FILE"

# 2. The photos, from the backend's media volume.
$DC exec -T backend tar -C /app/media -czf - . > "$MEDIA_FILE.part"
mv "$MEDIA_FILE.part" "$MEDIA_FILE"

# 3. Off the server.
if [ -n "${BACKUP_S3_URI:-}" ]; then
  aws s3 cp --only-show-errors "$DB_FILE" "${BACKUP_S3_URI%/}/"
  aws s3 cp --only-show-errors "$MEDIA_FILE" "${BACKUP_S3_URI%/}/"
else
  echo "warning: BACKUP_S3_URI is not set, so this backup is only on this server" >&2
fi

# 4. Old copies here. S3 keeps its own for as long as its lifecycle rule says.
find "$DIR" -maxdepth 1 -name 'fisheye-*.dump' -mtime +"$KEEP_DAYS" -delete
find "$DIR" -maxdepth 1 -name 'media-*.tar.gz' -mtime +"$KEEP_DAYS" -delete

echo "$(date -u +%FT%TZ) backup done: database $(du -h "$DB_FILE" | cut -f1), photos $(du -h "$MEDIA_FILE" | cut -f1)"
ping_monitor ""

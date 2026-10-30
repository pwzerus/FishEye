# Backups

Nightly, automatic, off the server, and tested. Until this is set up, the
only backups are the ones taken by hand before a deploy, on the same disk
as the database.

- `ops/backup.sh` dumps the database (`pg_dump -Fc`) and the catch photos
  (the backend's media volume), copies both to S3, keeps the last 7 days on
  the server, and pings a monitor so a missed backup raises an alert.
- `ops/restore-drill.sh` restores a dump into a throwaway database next to
  the live one and prints row counts. A backup nobody has restored is a
  hope, not a backup.

Both run on the server from `~/FishEye`, read their settings from
`~/.fisheye-backup.env`, and never touch the live database's data.

## Set up (once)

1. **An S3 bucket**, in the server's region (us-east-2): private, "Block
   all public access" on. Add a lifecycle rule that deletes objects under
   `fisheye/` after 30 days (that is how long backups are kept off the
   server).
2. **Let the server write to it**, without keys on the server: an IAM role
   for EC2 with this policy, attached to the instance (EC2 → the instance →
   Actions → Security → Modify IAM role):

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       { "Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject"], "Resource": "arn:aws:s3:::BUCKET/fisheye/*" },
       { "Effect": "Allow", "Action": "s3:ListBucket", "Resource": "arn:aws:s3:::BUCKET" }
     ]
   }
   ```

3. **The AWS CLI on the server:** `sudo snap install aws-cli --classic`,
   then `aws s3 ls s3://BUCKET/` should answer without asking for keys.
4. **A monitor** (optional, recommended): a free check at healthchecks.io
   with a 1-day period and a 2-hour grace. It emails you when a ping is
   missing or a `/fail` ping arrives.
5. **The settings file** `~/.fisheye-backup.env`:

   ```bash
   BACKUP_S3_URI=s3://BUCKET/fisheye
   BACKUP_PING_URL=https://hc-ping.com/your-check-uuid
   # KEEP_DAYS=7          # copies kept on the server
   # BACKUP_DIR=$HOME/backups
   ```

6. **Run it once by hand** and check S3 has the two files:

   ```bash
   cd ~/FishEye && bash ops/backup.sh
   aws s3 ls s3://BUCKET/fisheye/
   ```

7. **Schedule it** (`crontab -e`), daily at 09:15 UTC (4:15 am in Texas):

   ```
   15 9 * * * cd /home/ubuntu/FishEye && bash ops/backup.sh >> /home/ubuntu/backups/backup.log 2>&1
   ```

8. **Prove it restores:** `bash ops/restore-drill.sh` and compare its row
   counts with the live site. Then put a monthly reminder in your calendar
   to run it again.

## Restoring for real

Only when the live database is lost or damaged, and after taking a fresh
dump of whatever is left (`bash ops/backup.sh`):

```bash
cd ~/FishEye
DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
$DC stop backend frontend                     # nothing writes while it restores
$DC exec -T db pg_restore -U fisheye -d fisheye --clean --if-exists --no-owner < ~/backups/fisheye-YYYYMMDD-HHMM.dump
$DC exec -T backend sh -c 'cd /app/media && tar -xzf -' < ~/backups/media-YYYYMMDD-HHMM.tar.gz   # the photos
$DC start backend frontend
```

`--clean` drops each table before restoring it: it is the step that
replaces the live data, so check the file name twice. A dump from S3 comes
down with `aws s3 cp s3://BUCKET/fisheye/<file> ~/backups/`.

## What this doesn't cover

- The server itself (its disk, Docker, the code): a lost server is rebuilt
  from `docs/deploy-aws.md` and the repository, then restored from S3.
- Point-in-time recovery: at worst, the last day's changes are lost. A
  managed database (RDS) with continuous backups is the step after this.

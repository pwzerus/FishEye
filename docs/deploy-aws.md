# Putting FishEye on the internet (one AWS server)

This runs the same Docker Compose stack as the local setup on a single EC2
server, with Caddy in front serving HTTPS. Files: `docker-compose.prod.yml`
(the production layer) and `Caddyfile`.

**A domain and HTTPS are required, not optional.** Phones only let a page
read the location over HTTPS, so without them "Use my location" doesn't work
at the lake. Buy the domain first: DNS can take hours to reach everyone.

## What it costs (US East, on-demand, October 2026)

| | Monthly |
|---|---|
| `t3.small` server, $0.0208/hour x 730 hours | about $15 |
| 20 GB gp3 disk (EBS) | about $1.60 |
| Public IPv4 address (Elastic IP), $0.005/hour | about $3.60 |
| Data out to the internet | $0: the first 100 GB a month are free, and the map tiles go from MapTiler to the phone, not through the server |
| **Total** | **about $20**, plus about $12 a year for a `.com` |

A stopped server costs only the disk and the IP (about $5 a month). An
Elastic IP that is kept but not attached is still billed: release it when
you delete the server.

**T3 is "burstable".** It runs at 20% of each of its 2 vCPUs for the hourly
price and saves credits while idle; busy moments (building the images)
spend them. It starts in **Unlimited** mode: if the CPU averaged over 24
hours stays at or below 20% there is no extra charge, and above that the
excess costs $0.05 per vCPU-hour. FishEye idles far below 20%. Worst case,
something stuck at 100% for a whole month, is about $58 extra, which the
budget alert below would catch. To rule it out entirely, switch to
**Standard** after the first build (Instances, Actions, Instance settings,
Change credit specification): the CPU is then held at 20% when credits run
out, never billed. Don't start in Standard: T3 gets no launch credits, so
the first build would crawl. Credits are on the instance's Monitoring tab
(`CPUCreditBalance`, `CPUSurplusCreditsCharged`).

## 0. Before you start

- Commit and push everything: the server clones the repository.
- Personal AWS account; turn on a budget alert first (Billing, Budgets,
  monthly cost budget, for example $30).
- Buy the domain (Cloudflare Registrar, Namecheap, Route 53).

## 1. Create the server

Region: US East (Ohio, `us-east-2`) or (N. Virginia, `us-east-1`). Everything
below (server, Elastic IP) must be in the same region. Moving later means a
new server, a database dump and restore, and pointing DNS at the new IP.

EC2, Launch instance:

- **Image**: Ubuntu Server 24.04 LTS.
- **Type**: `t3.small` (2 vCPU, 2 GB RAM). x86, not ARM (`t4g`, `g` in the
  name): the PostGIS image is built for x86. Not `nano`/`micro`: the backend
  with Ask's semantic model needs about 450 MB, the whole stack about 1 GB.
- **Key pair**: create one, keep the `.pem` file safe; it is the only way in.
  On Windows, if ssh says "unprotected private key file", remove every user
  but yourself from the file's Security permissions.
- **Storage**: 20 GB gp3.
- **Security group** (inbound): SSH 22 from *My IP* only; HTTP 80 and HTTPS
  443 from anywhere. The database, API and web ports stay closed.
- **Advanced details, Credit specification**: leave Unlimited (see above).

Then allocate an **Elastic IP** and associate it with the instance, so the
address survives a restart.

## 2. Install Docker

```bash
ssh -i fisheye.pem ubuntu@<ELASTIC_IP>

# Docker's own repository: Ubuntu's packaged Compose is too old for the
# prod file (it needs 2.24+).
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && exit        # log in again afterwards

# 2 GB of RAM is tight while the images build (Next.js, and the semantic
# model being compressed); swap keeps the build from being killed.
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 3. DNS

At the domain's DNS settings add an **A record**: name `@` (and `www` if you
want it), value the Elastic IP. Wait until `nslookup yourdomain.com` shows
that IP before step 5.

## 4. Get the code and configure

```bash
git clone https://github.com/pwzerus/FishEye.git && cd FishEye
git switch demo-integration            # or whichever branch you deploy
```

If the repository is private, clone with a read-only deploy key (GitHub,
repo, Settings, Deploy keys), not your password or a personal token.

Create `.env` next to `docker-compose.yml`. Copy the secret values from
your machine (`backend/.env`, `frontend/.env.local`); never paste them into a
chat or commit them.

```
PUBLIC_URL=https://yourdomain.com
SITE_ADDRESS=yourdomain.com
COOKIE_SECURE=true

# from backend/.env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
ADMIN_API_TOKEN=...

# from frontend/.env.local (baked into the web bundle at build time)
NEXT_PUBLIC_MAP_STYLE_URL=...

# Optional: real AI summaries instead of the demo model (billed per use)
# LLM_PROVIDER=anthropic
# LLM_API_KEY=...
```

Two dashboards must know the new address, or the map is blank and Google
sign-in fails:

- **MapTiler**: the key's Allowed HTTP Origins gets `yourdomain.com`
  (keep `localhost:3000` for development).
- **Google Cloud Console**: the OAuth client's Authorized redirect URIs gets
  `https://yourdomain.com/api/auth/google/callback`.

## 5. Start it

```bash
DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
$DC up --build -d
$DC ps
```

The first build takes 15 to 20 minutes: besides the two images, it fetches
Ask's semantic model (multilingual-e5-small, at the pinned commit) from
Hugging Face and compresses it to int8. The API won't start without it
(ADR 0029), so a failed download shows in `$DC logs backend` rather than as
a quietly weaker search.

Caddy requests the HTTPS certificate on the first visit. If it fails, DNS
isn't pointing here yet or ports 80/443 are closed; `$DC logs caddy` says
which. Check: `curl https://yourdomain.com/health` returns
`{"status":"ok",...}`.

## 6. Load the lakes

The server starts with three demo lakes. The server has internet, so it can
download everything itself. Texas needs TPWD's files from your machine;
Georgia and California can come straight from OpenStreetMap and GBIF, or
from the files you already downloaded (faster, and kinder to those
services).

From your machine (PowerShell, in `F:\FishEye\backend`), copy up what you have:

```
scp -i fisheye.pem -r tpwd_cache tx_osm.json gbif_tx_raw.json ga_osm.json gbif_ga_raw.json ubuntu@<ELASTIC_IP>:~/data/
```

On the server:

```bash
DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
$DC cp ~/data/. backend:/tmp/data

# Texas: OSM, TPWD's verified lakes, OSM again (folds its copies of the
# verified lakes into them), then GBIF records
$DC exec backend python -m app.data_import.osm_waterbody_import --state TX --from-file /tmp/data/tx_osm.json
$DC exec backend python -m app.data_import.tpwd_statewide_import --cache /tmp/data/tpwd_cache
$DC exec backend python -m app.data_import.osm_waterbody_import --state TX --from-file /tmp/data/tx_osm.json
$DC exec backend python -m app.data_import.gbif_occurrence_import --state TX --osm /tmp/data/tx_osm.json --from-file /tmp/data/gbif_tx_raw.json

# Georgia, from the saved files; then Georgia WRD's public access sites and
# fish attractors (two small downloads; drop --fetch to reuse a saved
# ga_wrd_cache copied into /tmp/data)
$DC exec backend python -m app.data_import.osm_waterbody_import --state GA --from-file /tmp/data/ga_osm.json
$DC exec backend python -m app.data_import.ga_wrd_import --fetch --osm /tmp/data/ga_osm.json --cache /tmp/data/ga_wrd_cache
$DC exec backend python -m app.data_import.gbif_occurrence_import --state GA --osm /tmp/data/ga_osm.json --from-file /tmp/data/gbif_ga_raw.json

# California, downloaded here (a large OSM query: if Overpass times out,
# try again later)
$DC exec backend python -m app.data_import.osm_waterbody_import --state CA --save-raw /tmp/data/ca_osm.json
$DC exec backend python -m app.data_import.gbif_occurrence_import --state CA --osm /tmp/data/ca_osm.json --save-raw /tmp/data/gbif_ca_raw.json
```

Each import prints what it placed and what it left out, and is safe to run
again. A state lights up on the national map once it has lakes. Without the
saved files, drop `--from-file ...` and use `--save-raw ...` instead, as for
California; Texas's TPWD pages are fetched with
`python -m app.data_import.tpwd_fetch --out /tmp/data/tpwd_cache` (about
15 minutes), and its boat-ramp file is a manual download (README).

Then back up the database (below), so a mistake never means doing this again.

## 7. Try it on your phone

Over mobile data, not Wi-Fi: use my location, open a state and a lake, read
the plan and the weather, ask a question, sign in. The app has no offline
mode, and lakes often have no signal: open the lake's page before you lose
it, and keep that tab.

## Everyday

```bash
DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# New version
git pull && $DC up --build -d

# Logs
$DC logs -f --tail 100

# Back up the database
$DC exec -T db pg_dump -U fisheye fisheye | gzip > fisheye-$(date +%F).sql.gz
```

Data lives in Docker volumes and survives restarts and rebuilds. Never run
`down -v` on the server: it deletes them. Terminating the instance deletes
its disk too, so back up first.

## What this does not do yet

- **Managed database and backups.** The database is a container on the same
  disk. The plan is RDS PostgreSQL + PostGIS, photos on S3.
- **Email.** No password reset or verification; Google sign-in avoids both.

## Taking it down

Back up, terminate the instance, release the Elastic IP, and remove the
domain's A record. Billing stops when the instance and the IP are gone.

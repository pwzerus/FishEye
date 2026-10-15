# Putting FishEye on the internet (one AWS server)

This runs the same Docker Compose stack as the local setup on a single EC2
server, with Caddy in front. First by IP address, then with a domain name and
HTTPS. Cost: about $15 to $20 a month for the server, plus about $12 a year for
a `.com`. Nothing here needs an API key; the LLM stays the mock provider.

Files: `docker-compose.prod.yml` (the production layer) and `Caddyfile`.

## 1. Create the server

Use a personal AWS account, and turn on a budget alert first
(Billing → Budgets → monthly cost budget, for example $30).

EC2 → Launch instance:

- **Image**: Ubuntu Server 24.04 LTS.
- **Type**: `t3.small` (2 GB RAM). Use x86, not the cheaper ARM `t4g`: the
  PostGIS image is built for x86.
- **Key pair**: create one and keep the `.pem` file safe; it is the only way in.
- **Storage**: 20 GB gp3.
- **Security group** (inbound): SSH 22 from *My IP* only; HTTP 80 and HTTPS 443
  from anywhere. Nothing else: the database, API and web ports stay closed.

Then allocate an **Elastic IP** and attach it, so the address survives a
restart. (EC2 → Elastic IPs. Release it when you delete the server, or it
costs a little.)

## 2. Install Docker

```bash
ssh -i fisheye.pem ubuntu@<ELASTIC_IP>

# Docker's own repository: Ubuntu's packaged Compose is too old for the
# prod file (it needs 2.24+).
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && exit        # log in again afterwards

# 2 GB of RAM is tight while the images build; swap keeps it from being killed.
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 3. Get the code and configure

```bash
git clone https://github.com/pwzerus/FishEye.git && cd FishEye
git switch demo-integration            # or whichever branch you deploy

cat > .env <<'ENV'
PUBLIC_URL=http://<ELASTIC_IP>
SITE_ADDRESS=:80
COOKIE_SECURE=false
ENV
```

If the repository is private, clone with a read-only deploy key (GitHub →
repo → Settings → Deploy keys), not your personal password or token.

## 4. Start it

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

The first build takes a few minutes. Then open `http://<ELASTIC_IP>`. The
browser will say "not secure": that is plain HTTP, fixed in the next step.

Check: `curl http://<ELASTIC_IP>/health` returns `{"status":"ok",...}`.

## 5. A domain and HTTPS

1. Buy a domain (Namecheap, Cloudflare Registrar, Route 53).
2. In its DNS settings add an **A record**: name `@` (and `www` if wanted),
   value the Elastic IP. Wait until `nslookup yourdomain.com` shows that IP.
3. On the server, edit `.env`:

   ```
   PUBLIC_URL=https://yourdomain.com
   SITE_ADDRESS=yourdomain.com
   COOKIE_SECURE=true
   ```

4. Rebuild, because the address is baked into the web bundle:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
   ```

Caddy requests a certificate by itself on the first visit. If it fails, the
usual causes are DNS not pointing here yet, or ports 80/443 closed in the
security group. `docker compose ... logs caddy` says which.

## Load the Texas lakes

The server starts with three demo lakes. Load the rest once (about 20
minutes; the server needs only outbound internet). Copy TPWD's boat-ramp file
up first, from the machine you downloaded it on:

```bash
scp -i fisheye.pem BoatRamps_Public.geojson ubuntu@<ELASTIC_IP>:~/FishEye/
```

Then on the server:

```bash
DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
$DC exec backend python -m app.data_import.osm_waterbody_import --state TX
$DC exec backend python -m app.data_import.tpwd_fetch --out /tmp/tpwd_cache
$DC cp BoatRamps_Public.geojson backend:/tmp/tpwd_cache/
$DC exec backend python -m app.data_import.tpwd_statewide_import --cache /tmp/tpwd_cache
```

The import prints what it placed and what it left out. It is safe to run
again; nothing is duplicated.

## Everyday

```bash
# New version
git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail 100

# Back up the database
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
  pg_dump -U fisheye fisheye | gzip > fisheye-$(date +%F).sql.gz
```

Data lives in Docker volumes and survives restarts and rebuilds. Do not run
`down -v` on the server: it deletes them.

## What this does not do yet

- **Managed database and backups.** The database is a container on the same
  disk. The plan is RDS PostgreSQL + PostGIS, photos on S3.
- **Map key.** The map falls back to OpenStreetMap tiles. If you add a
  MapTiler key, restrict it to your domain in MapTiler's dashboard (it is
  visible in the browser by design).

## Taking it down

Terminate the instance, release the Elastic IP, delete the volume, and
remove the domain's A record. Billing stops when the instance and the IP are
gone.

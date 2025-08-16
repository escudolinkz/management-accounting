# Management Accounting (LXC-safe)

Runs inside Docker CE inside an unprivileged LXC on Proxmox. No privileged containers or cgroup hacks.

## 0) Proxmox LXC requirements
- Create unprivileged LXC (Debian/Ubuntu). Enable nesting.
- Host (Proxmox):
  ```bash
  pct set <CTID> -features nesting=1,keyctl=1
  ```

## 1) Install Docker CE inside the LXC
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

## 2) Get the repo inside the LXC
```bash
# put these files into /opt/management-accounting
cd /opt/management-accounting
cp .env.example .env
mkdir -p volumes/uploads volumes/db volumes/redis volumes/logs
# Permissions for bind mounts
sudo chown -R 1000:1000 volumes/uploads volumes/redis volumes/logs
# Postgres official image runs as uid 999 internally
sudo chown -R 999:999 volumes/db
```

## 3) Start stack
```bash
make up
make migrate
make seed
```
- Web: http://localhost:8080
- API: http://localhost:8000
- Default admin: `admin@example.com` / `admin123` (change in seed or later)

## 4) Backup/Restore
Simple whole-volume backup:
```bash
# backup
cd /opt/management-accounting
sudo tar -czf finance-backup-$(date +%F).tar.gz volumes

# restore
sudo tar -xzf finance-backup-*.tar.gz -C /opt/management-accounting
```

For logical DB backup:
```bash
docker compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > db.sql
# restore
cat db.sql | docker compose exec -T db psql -U $POSTGRES_USER $POSTGRES_DB
```

## 5) Health
```bash
docker compose ps
docker compose logs -f api worker frontend db redis
```

## 6) Security notes
- Max PDF size enforced: 20MB and content-type `application/pdf`.
- All app images run as uid:gid 1000, no extra capabilities.
- Session cookie is HttpOnly + signed; CSRF required on POST.

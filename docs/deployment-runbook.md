# Anjaneya Global Realty — Deployment Runbook

| | |
| --- | --- |
| Domain | anjaneyaglobalrealty.com (+ www) |
| Droplet | `cspaces` — Ubuntu 24.04, 4 GB / 2 vCPU, BLR1 |
| User | `jarvis` |
| App directory | `/home/jarvis/anjaneya` |
| Media | `/home/jarvis/anjaneya/media/` (local filesystem) |
| Backups | `/home/jarvis/backups/` |
| Database | PostgreSQL 16 on the droplet (NOT managed) |
| Cache | Redis on the droplet |

## Architecture

Single droplet, everything on one machine:

```
              ┌─────────── droplet: cspaces ───────────┐
  Internet →  │  nginx  →  unix socket  →  gunicorn     │
   (443/TLS)  │   │                          │ (Django)│
              │   ├─ /static/  (disk)        │         │
              │   └─ /media/   (disk)        ├─ Postgres
              │                              └─ Redis (cache)
              └─────────────────────────────────────────┘
```

- nginx terminates TLS (Let's Encrypt) and reverse-proxies to gunicorn
  over a Unix socket; it also serves `/static/` and `/media/` straight
  from disk.
- gunicorn: 5 `gthread` workers × 2 threads (tuned for 2 vCPU).
- PostgreSQL + Redis run locally — no managed services.
- Nightly cron backup (DB dump + media tarball) → `/home/jarvis/backups/`,
  14-day retention. Also enable DigitalOcean droplet snapshots in the DO
  panel (Droplet → Backups) for one-click whole-machine recovery.

## ⚠️ Known limitation — async email is inert in production

This deployment runs **gunicorn only** — there is no Celery worker or
beat process (deliberate scope decision; see
[`deployment-audit.md`](./deployment-audit.md)).

Consequence: the app's Celery code still runs `send_email_task.delay()`
on every enquiry, which queues a message into Redis — but **nothing
consumes that queue.** So in production:

- Enquiry-notification emails to `ENQUIRY_NOTIFICATION_EMAILS` are
  **not sent.**
- The periodic digest tasks (daily summary, unread-enquiry reminder)
  **never run.**

The site is otherwise fully functional. **Admins must check new
enquiries via `/admin/enquiries/enquiry/`** — the admin dashboard's
"Unread enquiries" card and the `status=new` filter make this quick.

To enable async email later, add `celery -A core worker` (and optionally
`celery -A core beat`) systemd units modelled on `anjaneya.service`,
then `systemctl enable --now` them. No code changes are required.

---

## One-time initial setup

### 1. Configure DNS

Follow [`dns-setup.md`](./dns-setup.md). Verify with `dig` before
continuing — TLS issuance depends on it.

### 2. SSH into the droplet

```bash
ssh jarvis@anjaneyaglobalrealty.com   # or the droplet IP if DNS hasn't propagated
```

### 3. Clone the repo

```bash
cd ~
git clone <repo-url> anjaneya
cd anjaneya
```

### 4. Run provisioning (one time, as root)

```bash
sudo bash deploy/scripts/provision.sh
```

This installs Postgres / Redis / nginx / certbot / Python, creates the
`anjaneya` database + user, sets up the firewall, fail2ban, logrotate,
the sudoers entry, and the nightly backup cron.

**Save the DB password it prints** — also written to
`/root/anjaneya-db-password.txt`.

> If `provision.sh` reports an unexpected Ubuntu version, see
> [`deployment-audit.md`](./deployment-audit.md) §1 for the Python
> package substitution.

### 5. Python environment

```bash
# use the python version provision.sh reported (python3.12 on Ubuntu 24.04)
python3.12 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

### 6. Configure the environment file

```bash
cp .env.production.example .env
nano .env
#   - DB_PASSWORD : paste from /root/anjaneya-db-password.txt
#   - SECRET_KEY  : python -c "import secrets; print(secrets.token_urlsafe(50))"
#   - fill EMAIL_*, DJANGO_ADMINS, SENTRY_DSN (optional)
chmod 600 .env
```

### 7. Create media + static directories

```bash
mkdir -p media staticfiles
chmod 755 media staticfiles
```

### 8. Migrate, collect static, create the admin user

```bash
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
venv/bin/python manage.py createsuperuser
```

### 9. Install the systemd services

```bash
sudo bash deploy/scripts/install_services.sh
```

### 10. Install the nginx site

```bash
sudo bash deploy/scripts/install_nginx.sh
```

### 11. Obtain the TLS certificate

```bash
sudo certbot --nginx \
  -d anjaneyaglobalrealty.com -d www.anjaneyaglobalrealty.com \
  --email admin@anjaneyaglobalrealty.com --agree-tos --non-interactive --redirect
```

### 12. Verify

```bash
curl https://anjaneyaglobalrealty.com/health/
curl https://anjaneyaglobalrealty.com/health/ready/
```

Then open in a browser:
- `https://anjaneyaglobalrealty.com/api/docs/`
- `https://anjaneyaglobalrealty.com/admin/`

### 13. Confirm backups work

```bash
bash deploy/scripts/backup.sh
ls -lh /home/jarvis/backups/db/
ls -lh /home/jarvis/backups/media/
```

---

## Ongoing deploys

```bash
ssh jarvis@anjaneyaglobalrealty.com
cd anjaneya
bash deploy/scripts/deploy.sh
```

`deploy.sh` pulls `main`, installs deps, migrates, collects static,
runs `check --deploy`, reloads gunicorn, and polls `/health/ready/`.

---

## Operations

### Logs
```bash
sudo tail -f /var/log/anjaneya/django.log
sudo tail -f /var/log/anjaneya/django-error.log
sudo tail -f /var/log/anjaneya/gunicorn-error.log
sudo tail -f /var/log/nginx/error.log
tail -f /var/log/anjaneya/backup.log
```

### Restart / reload the app
```bash
sudo systemctl restart anjaneya.service
sudo systemctl reload  anjaneya.service   # graceful, used by deploy.sh
```

### Database access
```bash
sudo -u postgres psql anjaneya
# or
venv/bin/python manage.py dbshell
```

### Manual backup / restore
```bash
bash deploy/scripts/backup.sh
bash deploy/scripts/restore_db.sh /home/jarvis/backups/db/anjaneya-YYYYMMDD-HHMMSS.sql.gz
```

### Disk usage
```bash
df -h
du -sh /home/jarvis/anjaneya/media/
du -sh /home/jarvis/backups/
```

---

## Disaster recovery

### Droplet destroyed
1. Restore the latest DigitalOcean snapshot via the DO panel (if droplet
   snapshots are enabled), **or**
2. Provision a fresh droplet:
   - SSH in, `git clone`, `sudo bash deploy/scripts/provision.sh`
   - Restore the DB: `bash deploy/scripts/restore_db.sh <latest-db-backup>`
   - Restore media: `tar -xzf <latest-media-backup> -C /home/jarvis/anjaneya/`
   - Continue from step 5 of the initial setup.

### Database corrupted
```bash
sudo systemctl stop anjaneya.service
bash deploy/scripts/restore_db.sh /home/jarvis/backups/db/<latest>.sql.gz
# restore_db.sh restarts the service when done
```

### Media files lost
```bash
cd /home/jarvis/anjaneya
tar -xzf /home/jarvis/backups/media/media-<latest>.tar.gz
```

---

## Troubleshooting

### 502 Bad Gateway
```bash
sudo systemctl status anjaneya.service
sudo tail -50 /var/log/anjaneya/gunicorn-error.log
sudo systemctl restart anjaneya.service
```

### Static files 404
```bash
venv/bin/python manage.py collectstatic --noinput
sudo systemctl reload nginx
```

### Media files 404
```bash
ls -la /home/jarvis/anjaneya/media/
# nginx must be able to read the path — jarvis is in the www-data group,
# and provision.sh sets media/ to 755.
```

### Postgres connection issues
```bash
sudo systemctl status postgresql
sudo -u postgres psql -c "\l"    # list databases
sudo -u postgres psql -c "\du"   # list roles
# confirm DB_* values in .env match
```

### Disk filling up
```bash
du -sh /home/jarvis/anjaneya/media/*
du -sh /home/jarvis/backups/*
# old backups auto-purge at 14 days; lower RETENTION_DAYS in backup.sh if needed
# resize the droplet disk via the DO panel if media grows large
```

### TLS certificate renewal
certbot auto-renews via a systemd timer:
```bash
sudo systemctl list-timers | grep certbot
sudo certbot renew --dry-run
```

---

## Rollback

```bash
cd /home/jarvis/anjaneya
git log --oneline -10
git checkout <previous-good-sha>
bash deploy/scripts/deploy.sh
# if the bad deploy ran a migration, restore the DB first:
#   bash deploy/scripts/restore_db.sh <pre-deploy-backup>
```

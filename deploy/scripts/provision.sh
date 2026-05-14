#!/usr/bin/env bash
# Anjaneya Global Realty — one-time droplet provisioning.
# Run as root on the droplet (cspaces, user 'jarvis' already exists):
#   sudo bash deploy/scripts/provision.sh
#
# Installs: Postgres, Redis, nginx, certbot, Python, firewall, fail2ban.
# Creates: the 'anjaneya' database + user (password auto-generated),
#          log + backup directories, logrotate + sudoers + cron entries.

set -euo pipefail

DOMAIN="anjaneyaglobalrealty.com"
EMAIL="admin@anjaneyaglobalrealty.com"   # change to a real mailbox if different

if ! id -u jarvis >/dev/null 2>&1; then
    echo "ERROR: user 'jarvis' must already exist"
    exit 1
fi

# --- Detect Ubuntu version to pick the right Python ------------------------
. /etc/os-release
case "$VERSION_ID" in
    "24.04") PYTHON_PKG="python3.12 python3.12-venv" ; PYTHON_BIN="python3.12" ;;
    "22.04") PYTHON_PKG="python3.10 python3.10-venv" ; PYTHON_BIN="python3.10" ;;
    "20.04") PYTHON_PKG="python3.8 python3.8-venv"   ; PYTHON_BIN="python3.8"  ;;
    *) echo "Unsupported Ubuntu version: $VERSION_ID" ; exit 1 ;;
esac
echo "==> Detected Ubuntu $VERSION_ID — will install $PYTHON_PKG"

echo "==> Updating system"
apt update && apt upgrade -y

echo "==> Installing system packages"
apt install -y \
    $PYTHON_PKG python3-pip \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    git curl ufw fail2ban \
    libpq-dev libmagic1 build-essential \
    htop

echo "==> Ensuring jarvis is in the www-data group"
usermod -aG www-data jarvis

echo "==> Creating directories"
mkdir -p /var/log/anjaneya
chown jarvis:jarvis /var/log/anjaneya
chmod 750 /var/log/anjaneya

mkdir -p /home/jarvis/backups
chown jarvis:jarvis /home/jarvis/backups
chmod 750 /home/jarvis/backups

echo "==> Setting up PostgreSQL"
systemctl enable --now postgresql

# Strong random DB password — printed once and saved to a root-only file.
DB_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)

sudo -u postgres psql <<EOF
CREATE DATABASE anjaneya;
CREATE USER anjaneya WITH PASSWORD '$DB_PASSWORD';
ALTER ROLE anjaneya SET client_encoding TO 'utf8';
ALTER ROLE anjaneya SET default_transaction_isolation TO 'read committed';
ALTER ROLE anjaneya SET timezone TO 'Asia/Kolkata';
GRANT ALL PRIVILEGES ON DATABASE anjaneya TO anjaneya;
\c anjaneya
GRANT ALL ON SCHEMA public TO anjaneya;
EOF

echo "$DB_PASSWORD" > /root/anjaneya-db-password.txt
chmod 600 /root/anjaneya-db-password.txt
echo ""
echo "==> Postgres database 'anjaneya' created."
echo "==> DB_PASSWORD (also saved to /root/anjaneya-db-password.txt):"
echo ""
echo "    $DB_PASSWORD"
echo ""

echo "==> Enabling Redis"
systemctl enable --now redis-server
sed -i 's/^# bind 127.0.0.1.*/bind 127.0.0.1/' /etc/redis/redis.conf || true
systemctl restart redis-server

echo "==> Firewall (ufw)"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "==> fail2ban"
systemctl enable --now fail2ban

echo "==> Nginx rate-limit zones"
if ! grep -q "anjaneya_general" /etc/nginx/nginx.conf; then
    sed -i '/http {/a \    limit_req_zone $binary_remote_addr zone=anjaneya_general:10m rate=30r/s;\n    limit_req_zone $binary_remote_addr zone=anjaneya_enquiry:10m rate=1r/s;' /etc/nginx/nginx.conf
fi

echo "==> Sudoers entry for the deploy script (jarvis: whitelisted commands only)"
cat > /etc/sudoers.d/jarvis-deploy <<'EOF'
jarvis ALL=(ALL) NOPASSWD: /bin/systemctl reload anjaneya.service, /bin/systemctl restart anjaneya.service, /bin/systemctl status anjaneya.service, /bin/systemctl stop anjaneya.service, /bin/systemctl start anjaneya.service, /usr/sbin/nginx -t, /bin/systemctl reload nginx
EOF
chmod 440 /etc/sudoers.d/jarvis-deploy

echo "==> Logrotate config"
cat > /etc/logrotate.d/anjaneya <<'EOF'
/var/log/anjaneya/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 jarvis jarvis
    sharedscripts
    postrotate
        systemctl reload anjaneya.service > /dev/null 2>&1 || true
    endscript
}
EOF

echo "==> Nightly backup cron (DB + media, 3 AM)"
( crontab -u jarvis -l 2>/dev/null | grep -v 'deploy/scripts/backup.sh' ; \
  echo "0 3 * * * /home/jarvis/anjaneya/deploy/scripts/backup.sh >> /var/log/anjaneya/backup.log 2>&1" ) \
  | crontab -u jarvis -

echo ""
echo "==> Provisioning complete on host: $(hostname)"
echo "==> Python binary: $PYTHON_BIN"
echo "==> DB password:   /root/anjaneya-db-password.txt"
echo ""
echo "Next steps (run as jarvis):"
echo "  1.  cd ~ && git clone <repo-url> anjaneya"
echo "  2.  cd anjaneya && $PYTHON_BIN -m venv venv"
echo "  3.  venv/bin/pip install --upgrade pip"
echo "  4.  venv/bin/pip install -r requirements.txt"
echo "  5.  cp .env.production.example .env"
echo "  6.  nano .env   # paste DB_PASSWORD + generate SECRET_KEY"
echo "  7.  chmod 600 .env"
echo "  8.  mkdir -p media staticfiles && chmod 755 media staticfiles"
echo "  9.  venv/bin/python manage.py migrate"
echo " 10.  venv/bin/python manage.py collectstatic --noinput"
echo " 11.  venv/bin/python manage.py createsuperuser"
echo " 12.  sudo bash deploy/scripts/install_services.sh"
echo " 13.  sudo bash deploy/scripts/install_nginx.sh"
echo " 14.  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN \\"
echo "          --email $EMAIL --agree-tos --non-interactive --redirect"

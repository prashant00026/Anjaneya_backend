#!/usr/bin/env bash
# Install + enable the nginx site. Run as root from /home/jarvis/anjaneya:
#   sudo bash deploy/scripts/install_nginx.sh

set -euo pipefail

cp deploy/nginx/anjaneya.conf /etc/nginx/sites-available/anjaneya
ln -sf /etc/nginx/sites-available/anjaneya /etc/nginx/sites-enabled/anjaneya
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

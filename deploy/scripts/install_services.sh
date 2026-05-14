#!/usr/bin/env bash
# Install + start the systemd units. Run as root from /home/jarvis/anjaneya:
#   sudo bash deploy/scripts/install_services.sh

set -euo pipefail

cp deploy/systemd/anjaneya.service /etc/systemd/system/
cp deploy/systemd/anjaneya.socket /etc/systemd/system/

systemctl daemon-reload
systemctl enable --now anjaneya.socket
systemctl enable --now anjaneya.service

systemctl status anjaneya.service --no-pager

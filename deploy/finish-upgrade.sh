#!/usr/bin/bash
# Root-level steps to finish the 20.04 -> 24.04 upgrade and cut the API over to the new venv.
# Run as:  sudo bash deploy/finish-upgrade.sh
# Each section is idempotent. Read before running; the PostgreSQL section is intentionally opt-in.
set -euo pipefail
REPO=/home/administrator/SLUSD-Api
step() { printf '\n==> %s\n' "$*"; }

step "1/7 Base packages for the 3.12 venv"
apt-get update -qq
apt-get install -y -qq python3.12-venv

step "2/7 Docker: replace the focal builds with the noble repo"
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.asc ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y -qq --only-upgrade docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
# ODBC drivers and pgdg already have noble sources; pull their noble builds too.
apt-get install -y -qq --only-upgrade msodbcsql17 msodbcsql18 postgresql-17 postgresql-client-17 postgresql-common libpq5 || true

step "3/7 Cut the API over to the venv (no --reload, hardened unit)"
install -m 0644 "$REPO/deploy/fastapi.service" /etc/systemd/system/fastapi.service
install -m 0644 "$REPO/deploy/data-slusd.service" /etc/systemd/system/data-slusd.service
systemctl daemon-reload

step "4/7 Rotate the JWT signing key (invalidates all issued tokens; clients re-login)"
NEWKEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
sed -i -E "s|^SECRET_KEY\s*=.*|SECRET_KEY = ${NEWKEY}|" "$REPO/.env"
chown administrator:administrator "$REPO/.env"; chmod 600 "$REPO/.env"

step "5/7 Restart services and verify"
systemctl restart fastapi data-slusd
sleep 4
systemctl --no-pager --lines=0 status fastapi data-slusd | grep -E "Active:|fastapi|data-slusd"
curl -fsS -o /dev/null -w "API /openapi.json -> HTTP %{http_code}\n" http://127.0.0.1:8000/openapi.json
curl -fsS -o /dev/null -w "Next.js :3000 -> HTTP %{http_code}\n" http://127.0.0.1:3000/ || true

step "6/7 Remove 20.04-era leftovers that no repo updates any more"
# deadsnakes Python 3.11/3.10 (the API now runs on the system 3.12 venv)
apt-get purge -y -qq 'python3.11*' 'libpython3.11*' 'python3.10-distutils' 'python3.10-lib2to3' || true
rm -f /etc/apt/sources.list.d/deadsnakes-ubuntu-ppa-focal.sources /etc/apt/sources.list.d/*.distUpgrade /etc/apt/sources.list.d/*.save
# OpenSSL 1.1 (EOL 2023) and other orphaned libs
apt-get purge -y -qq libssl1.1 libffi7 libicu66 libicu70 libllvm10 libldap-2.4-2 mime-support || true
# Old kernel
apt-get purge -y -qq 'linux-image-5.15.0-198-generic' 'linux-modules-5.15.0-198-generic' 'linux-modules-extra-5.15.0-198-generic' 'linux-headers-5.15.0-198*' || true
apt-get autoremove -y -qq --purge
apt-get update -qq

step "7/7 Report what is still orphaned"
apt list --installed 2>/dev/null | grep ",local\]" | cut -d/ -f1 | tr '\n' ' '; echo
cat <<'NOTE'

Not done automatically (needs a maintenance decision):
  * PostgreSQL 14 and 16 clusters are still installed alongside 17. Confirm which cluster holds
    live data (pg_lsclusters), dump anything needed, then: apt-get purge postgresql-14 postgresql-16 ...
  * MySQL (0.0.0.0:3306) and PostgreSQL (10.100.4.98:5432) listen on the LAN. If only local apps use
    them, set bind-address / listen_addresses to 127.0.0.1.
  * falcon-sensor, google-cloud-sdk, glow, charm: re-add their noble repos or remove them.
  * Reboot once at the end to land on a clean package set.
NOTE

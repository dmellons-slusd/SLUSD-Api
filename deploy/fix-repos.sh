#!/usr/bin/bash
# Follow-up to finish-upgrade.sh:
#  * point the Microsoft repo at noble so msodbcsql17/18 (used by the API via pyodbc) keep getting updates
#  * drop the leftover PostgreSQL bits (the only database on it, calsaas_early_warning, was discarded)
# Run as:  sudo bash deploy/fix-repos.sh
set -euo pipefail
step() { printf '\n==> %s\n' "$*"; }

step "1/3 Microsoft repo for noble"
install -m 0755 -d /etc/apt/keyrings
[ -f /etc/apt/keyrings/microsoft.asc ] || curl -fsSL https://packages.microsoft.com/keys/microsoft.asc -o /etc/apt/keyrings/microsoft.asc
cat > /etc/apt/sources.list.d/mssql-release.sources <<'SRC'
Types: deb
URIs: https://packages.microsoft.com/ubuntu/24.04/prod
Suites: noble
Components: main
Signed-By: /etc/apt/keyrings/microsoft.asc
SRC
rm -f /etc/apt/sources.list.d/pgdg.sources /etc/apt/sources.list.d/pgdg.list.bak-*
apt-get update -qq
apt-get -s install --only-upgrade msodbcsql17 msodbcsql18 | grep -E "^(Inst|Remv)" || echo "ODBC drivers already current"
ACCEPT_EULA=Y apt-get install -y -qq --only-upgrade msodbcsql17 msodbcsql18

step "2/3 Remove PostgreSQL remnants (dry run shown first)"
apt-get -s purge postgresql-doc postgresql-doc-16 | grep -E "^(Inst|Remv)" || true
apt-get purge -y -qq postgresql-doc postgresql-doc-16 || true
rm -rf /etc/postgresql /var/lib/postgresql /var/log/postgresql
deluser --quiet postgres 2>/dev/null || true
apt-get autoremove -y -qq --purge

step "3/3 Remaining orphaned packages"
apt list --installed 2>/dev/null | grep ",local\]" | cut -d/ -f1 | tr '\n' ' '; echo
echo "Expected: falcon-sensor (self-updating), glow, google-cloud-sdk. Re-add their noble repos or remove them when convenient."

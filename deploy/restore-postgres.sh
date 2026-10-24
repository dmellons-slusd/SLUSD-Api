#!/usr/bin/bash
# Reinstall PostgreSQL 17 from the pgdg *noble* repo and recreate the calsaas_early_warning database.
# Run as:  sudo bash deploy/restore-postgres.sh
# Does NOT restore data. Restore /var/lib/postgresql/17/main from a VM snapshot first if one exists
# (see notes at the end); otherwise re-seed from calsaas_match_site/seeding after this script.
set -euo pipefail
step() { printf '\n==> %s\n' "$*"; }

step "1/4 Point pgdg and Microsoft repos at noble and enable them"
install -m 0755 -d /etc/apt/keyrings
[ -f /etc/apt/keyrings/pgdg.asc ] || curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc -o /etc/apt/keyrings/pgdg.asc
cat > /etc/apt/sources.list.d/pgdg.sources <<'SRC'
Types: deb
URIs: https://apt.postgresql.org/pub/repos/apt
Suites: noble-pgdg
Components: main
Signed-By: /etc/apt/keyrings/pgdg.asc
SRC
[ -f /etc/apt/keyrings/microsoft.asc ] || curl -fsSL https://packages.microsoft.com/keys/microsoft.asc -o /etc/apt/keyrings/microsoft.asc
cat > /etc/apt/sources.list.d/mssql-release.sources <<'SRC'
Types: deb
URIs: https://packages.microsoft.com/ubuntu/24.04/prod
Suites: noble
Components: main
Signed-By: /etc/apt/keyrings/microsoft.asc
SRC
apt-get update -qq

step "2/4 Dry run first, then install PostgreSQL 17 (noble build) and refresh the ODBC drivers"
apt-get -s install postgresql-17 postgresql-client-17 | grep -E "^(Inst|Remv)" | head -20
apt-get install -y -qq postgresql-17 postgresql-client-17
ACCEPT_EULA=Y apt-get install -y -qq --only-upgrade msodbcsql17 msodbcsql18 || true

step "3/4 Cluster status"
pg_lsclusters
# Keep the cluster local-only unless something on the LAN needs it (the old one also listened on 10.100.4.98).
sed -i -E "s|^#?listen_addresses\s*=.*|listen_addresses = 'localhost'|" /etc/postgresql/17/main/postgresql.conf
systemctl restart postgresql@17-main

step "4/4 Recreate the role and empty database for calsaas_match_site (password read from its .env, never printed)"
ENVFILE=/home/administrator/calsaas_match_site/.env
URL=$(sed -nE 's/^DATABASE_URL\s*=\s*"?([^"]*)"?.*/\1/p' "$ENVFILE")
DBUSER=$(printf '%s' "$URL" | sed -E 's#^[a-z]+://([^:@/]+).*#\1#')
DBPASS=$(printf '%s' "$URL" | sed -E 's#^[a-z]+://[^:]+:([^@]*)@.*#\1#')
DBNAME=$(printf '%s' "$URL" | sed -E 's#.*/([^/?]+)(\?.*)?$#\1#')
sudo -u postgres psql -v ON_ERROR_STOP=1 -v u="$DBUSER" -v p="$DBPASS" -v d="$DBNAME" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'u', :'p') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'u') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'d', :'u') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'d') \gexec
SQL
sudo -u postgres psql -l | grep -E "Name|$DBNAME"

cat <<'NOTE'

Next, as administrator (not root), rebuild the schema and data:
  cd /home/administrator/calsaas_match_site
  npx prisma migrate deploy        # or: npx prisma db push   (if there is no migrations/ folder)
  node seeding/seedCredentials.js  # then seedTeachers.js, seedSections.js, in whatever order the README says

If this VM has a VMware snapshot from before 2026-10-22 (or any backup of /var/lib/postgresql/17/main):
  stop postgresql@17-main, replace /var/lib/postgresql/17/main with the snapshot copy (owner postgres:postgres,
  mode 700), start it again, and skip the seeding. That is the only way to get back rows entered through the app.
NOTE

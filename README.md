# URY POS (ERPNext) — full server backup

Complete backup of the Frappe bench that ran on the DigitalOcean droplet `rpos` (167.71.23.137),
taken on **12 Nov 2026** just before the server was wiped and reused for another application.

The bench served one site, `rpos.atlantechglobal` (reachable as `iroas.atlantechglobal.com`),
running Frappe 15 + ERPNext 15 + HRMS 15 + the customised URY restaurant POS app.

> **Keep this repository private.** The database dump contains user accounts with password
> hashes, and `config/site_config.json` contains the old database password.

## What is in here

| Path | Contents |
|---|---|
| `database/20261112_104618-…-database.sql.gz` | Database backup made by `bench backup` (use this one with `bench restore`) |
| `database/rpos_ag-mysqldump-full.sql.gz` | Second, independent `mysqldump` of the same database (874 tables + 7 sequences, with routines/triggers/events) |
| `database/…-files.tar`, `…-private-files.tar` | Public and private uploaded files of the site |
| `database/ROW-COUNTS.txt` | Row counts at backup time, to check a restore against |
| `site/site-rpos.atlantechglobal.tar.gz` | The whole site folder (without logs and old backups) |
| `site/archived-sites.tar.gz` | The bench's `archived/` folder (an older, dropped copy of the site) |
| `apps/ury/` | Full source of the URY app **as it was running**, including the uncommitted CampusBite changes |
| `apps/ury-uncommitted-tracked-changes.patch` | Diff of tracked URY files against commit `d33c60f` of `atlantechglobal-dev/rpos` |
| `apps/frappe-local-changes/` | The one extra file added inside the Frappe app (`demo_cafeteria_setup.py`) |
| `apps/hrms-local-changes/` | Local `yarn.lock` diff in HRMS |
| `apps/APP-VERSIONS.txt` | Git remote, branch and exact commit of every app |
| `config/` | `site_config.json`, `common_site_config.json`, nginx, supervisor and redis configs, `Procfile`, `apps.txt` |
| `scripts/` | One-off helper scripts that were lying in the `frappe` user's home and the bench root |
| `system/` | Python package list, software versions, crontabs, firewall rules |

Frappe, ERPNext and HRMS were unmodified upstream code (apart from the two small items above),
so they are recorded by commit instead of being copied.

## Data at backup time

| | Count |
|---|---|
| Companies | 1 (Atlantech Global) |
| Users | 18 |
| Customers | 18 |
| Employees | 9 |
| Items | 40 |
| Sales Invoices | 63 |
| POS Invoices | 12 |

## Restoring

On a fresh Ubuntu 22.04 server with Frappe bench prerequisites (Python 3.10, Node 18, MariaDB 10.6, Redis, wkhtmltopdf):

```bash
# 1. Bench with the same Frappe version
bench init frappe-bench --frappe-branch version-15
cd frappe-bench

# 2. Apps, at the commits listed in apps/APP-VERSIONS.txt
bench get-app erpnext --branch version-15
bench get-app hrms --branch version-15
# URY: copy apps/ury from this repo into frappe-bench/apps/ury, then
./env/bin/pip install -e apps/ury
echo ury >> sites/apps.txt
cp <this-repo>/apps/frappe-local-changes/frappe/demo_cafeteria_setup.py apps/frappe/frappe/

# 3. Site, restored from the backup
bench new-site rpos.atlantechglobal
bench --site rpos.atlantechglobal install-app erpnext hrms ury
bench --site rpos.atlantechglobal restore \
  <this-repo>/database/20261112_104618-rpos_atlantechglobal-database.sql.gz \
  --with-public-files  <this-repo>/database/20261112_104618-rpos_atlantechglobal-files.tar \
  --with-private-files <this-repo>/database/20261112_104618-rpos_atlantechglobal-private-files.tar
bench --site rpos.atlantechglobal migrate
bench build

# 4. Production setup
sudo bench setup production frappe
```

Then compare the counts in the restored site with `database/ROW-COUNTS.txt`.
`config/nginx.conf` and `config/supervisor.conf` show how the old server was wired, including the
`iroas.atlantechglobal.com` domain mapping.

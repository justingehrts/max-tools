#!/usr/bin/env bash
# Upload the few files that live on HostGator, over FTPS, and check them byte for byte.
#
#   HOSTGATOR_HOST=... HOSTGATOR_USER=... HOSTGATOR_PASSWORD=... tools/deploy_hostgator.sh
#
# Used by .github/workflows/deploy-hostgator.yml (which waits for Justin's approval first) and by tests/test_deploy_hostgator.py.
#
# It touches ONLY the files listed in FILES below. Never the password file (.htaccess in the folder above api/), config.php,
# the token, or anything else on the server. Before overwriting it saves the current server copies to $BACKUP_DIR.
#
# Settings (environment):
#   HOSTGATOR_HOST         server name, e.g. gator1234.hostgator.com  (use the server name shown in cPanel: its certificate matches it)
#   HOSTGATOR_USER         the FTP account made for public_html/max
#   HOSTGATOR_PASSWORD     its password (never printed)
#   HOSTGATOR_REMOTE_DIR   folder to treat as public_html/max; default / (an FTP account limited to that folder starts there)
#   HOSTGATOR_PORT         default 21
#   HOSTGATOR_FTPS         true (default: encrypted, required) | false (only for the local test server)
#   HOSTGATOR_VERIFY_CERT  true (default) | false
#   BACKUP_DIR             default hostgator-backup
set -euo pipefail

: "${HOSTGATOR_HOST:?set HOSTGATOR_HOST}" "${HOSTGATOR_USER:?set HOSTGATOR_USER}" "${HOSTGATOR_PASSWORD:?set HOSTGATOR_PASSWORD}"
REMOTE_DIR="${HOSTGATOR_REMOTE_DIR:-/}"
PORT="${HOSTGATOR_PORT:-21}"
FTPS="${HOSTGATOR_FTPS:-true}"
VERIFY="${HOSTGATOR_VERIFY_CERT:-true}"
BACKUP_DIR="${BACKUP_DIR:-hostgator-backup}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# local path (from the repo root) : path on the server (below REMOTE_DIR). This list IS the whole permission.
FILES=(
  "configurator/dist/index.html:index.html"
  "configurator/api/save.php:api/save.php"
  "configurator/api/lib.php:api/lib.php"
  "configurator/api/.htaccess:api/.htaccess"
)

quote() { local s="${1//\\/\\\\}"; printf '"%s"' "${s//\"/\\\"}"; }   # lftp double-quote escaping

# Run lftp commands (arguments, one command each) with the connection settings; the password never goes on a command line.
ftp() {
  local script; script="$(mktemp)"; chmod 600 "$script"
  {
    echo "set cmd:fail-exit yes"
    echo "set net:max-retries 2"
    echo "set net:timeout 30"
    echo "set net:reconnect-interval-base 3"
    if [ "$FTPS" = "true" ]; then
      echo "set ftp:ssl-allow yes"
      echo "set ftp:ssl-force yes"
      echo "set ftp:ssl-protect-data yes"
      echo "set ftp:ssl-protect-list yes"
      echo "set ssl:verify-certificate $VERIFY"
    else
      echo "set ftp:ssl-allow no"
    fi
    echo "open -p $PORT $(quote "$HOSTGATOR_HOST")"
    echo "user $(quote "$HOSTGATOR_USER") $(quote "$HOSTGATOR_PASSWORD")"
    echo "cd $(quote "$REMOTE_DIR")"
    for c in "$@"; do echo "$c"; done
    echo "bye"
  } > "$script"
  local rc=0; lftp -f "$script" || rc=$?
  rm -f "$script"
  return $rc
}

cd "$ROOT"
case "$BACKUP_DIR" in /*) ;; *) BACKUP_DIR="$ROOT/$BACKUP_DIR" ;; esac     # absolute, so lftp writes where we mean
for pair in "${FILES[@]}"; do
  [ -f "${pair%%:*}" ] || { echo "missing local file: ${pair%%:*}" >&2; exit 2; }
done
if [ "$FTPS" != "true" ]; then echo "WARNING: FTPS is off (test server only)."; fi

echo "1/4 Checking the login and the folder..."
ftp "cls" >/dev/null || { echo "Could not log in or open the folder. Check the host, user, password and remote folder." >&2; exit 3; }

echo "2/4 Saving the current server copies to $BACKUP_DIR/ ..."
mkdir -p "$BACKUP_DIR"
for pair in "${FILES[@]}"; do
  remote="${pair#*:}"; mkdir -p "$BACKUP_DIR/$(dirname "$remote")"
  ftp "get $(quote "$remote") -o $(quote "$BACKUP_DIR/$remote")" >/dev/null 2>&1 \
    && echo "   saved $remote" || echo "   (no existing $remote on the server)"
done

echo "3/4 Uploading..."
ftp "cd api" >/dev/null 2>&1 || ftp "mkdir api"      # create api/ only when it is missing (mkdir on an existing folder is an error)
for pair in "${FILES[@]}"; do
  local_path="${pair%%:*}"; remote="${pair#*:}"
  ftp "put $(quote "$ROOT/$local_path") -o $(quote "$remote")"
  echo "   uploaded $remote ($(wc -c < "$local_path") bytes)"
done

echo "4/4 Checking every file against the repository, byte for byte..."
verify="$(mktemp -d)"; bad=0
for pair in "${FILES[@]}"; do
  local_path="${pair%%:*}"; remote="${pair#*:}"; mkdir -p "$verify/$(dirname "$remote")"
  ftp "get $(quote "$remote") -o $(quote "$verify/$remote")" >/dev/null
  if cmp -s "$local_path" "$verify/$remote"; then echo "   OK   $remote"; else echo "   DIFFERS  $remote" >&2; bad=1; fi
done
rm -rf "$verify"
[ "$bad" = 0 ] || { echo "Upload finished but a file on the server differs from the repository." >&2; exit 4; }
echo "Done. The HostGator copies match the repository."

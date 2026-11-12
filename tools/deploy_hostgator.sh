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
# It logs in twice (a listing, then one session that does all the transfers). Shared hosts often firewall an address that opens
# many connections quickly, so fewer is safer. Step 0 tests the connection with no password at all.
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
#   HOSTGATOR_CMD_TIMEOUT  seconds one FTP session may take before it is cut off and reported (default 120)
set -uo pipefail

: "${HOSTGATOR_HOST:?set HOSTGATOR_HOST}" "${HOSTGATOR_USER:?set HOSTGATOR_USER}" "${HOSTGATOR_PASSWORD:?set HOSTGATOR_PASSWORD}"
REMOTE_DIR="${HOSTGATOR_REMOTE_DIR:-/}"
PORT="${HOSTGATOR_PORT:-21}"
FTPS="${HOSTGATOR_FTPS:-true}"
VERIFY="${HOSTGATOR_VERIFY_CERT:-true}"
BACKUP_DIR="${BACKUP_DIR:-hostgator-backup}"
CMD_TIMEOUT="${HOSTGATOR_CMD_TIMEOUT:-120}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# local path (from the repo root) : path on the server (below REMOTE_DIR). This list IS the whole permission.
FILES=(
  "configurator/dist/index.html:index.html"
  "configurator/api/save.php:api/save.php"
  "configurator/api/lib.php:api/lib.php"
  "configurator/api/.htaccess:api/.htaccess"
)

quote() { local s="${1//\\/\\\\}"; printf '"%s"' "${s//\"/\\\"}"; }   # lftp double-quote escaping

# One lftp session running the given commands (one per argument). The password never goes on a command line. The session has a hard
# time limit; on failure the tail of lftp's own protocol log is printed (lftp shows the password as ****; the exact password is
# also blanked). stdout of lftp is left alone; the protocol log goes to a file.
ftp() {
  local script dbg; script="$(mktemp)"; dbg="$(mktemp)"; chmod 600 "$script" "$dbg"
  {
    echo "set cmd:fail-exit yes"
    echo "set net:max-retries 2"
    echo "set net:timeout 20"
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
  local rc=0
  timeout "$CMD_TIMEOUT" lftp -d -f "$script" </dev/null 2>"$dbg" || rc=$?
  if [ "$rc" != 0 ] && [ "${FTP_SHOW_DEBUG:-1}" != 0 ]; then
    [ "$rc" = 124 ] && echo "   (cut off after ${CMD_TIMEOUT}s: the server stopped answering)" >&2
    echo "   --- last lines of the FTP conversation (password hidden) ---" >&2
    tail -n 30 "$dbg" | while IFS= read -r line; do printf '   %s\n' "${line//"$HOSTGATOR_PASSWORD"/****}"; done >&2
  fi
  rm -f "$script" "$dbg"
  return $rc
}

cd "$ROOT"
case "$BACKUP_DIR" in /*) ;; *) BACKUP_DIR="$ROOT/$BACKUP_DIR" ;; esac     # absolute, so lftp writes where we mean
for pair in "${FILES[@]}"; do
  [ -f "${pair%%:*}" ] || { echo "missing local file: ${pair%%:*}" >&2; exit 2; }
done
if [ "$FTPS" != "true" ]; then echo "WARNING: FTPS is off (test server only)."; fi

# ---------------------------------------------------------------- 0. can we reach the server at all? (no password involved)
echo "0/4 Testing the connection to $HOSTGATOR_HOST:$PORT (no login yet)..."
ip="$(getent hosts "$HOSTGATOR_HOST" 2>/dev/null | awk '{print $1; exit}')"
if [ -z "$ip" ]; then echo "   The name $HOSTGATOR_HOST does not resolve. Check the HOSTGATOR_HOST secret." >&2; exit 6; fi
echo "   address: $ip"
banner="$(timeout 20 bash -c 'exec 3<>"/dev/tcp/$0/$1" && IFS= read -r -t 15 line <&3 && printf "%s" "$line"' "$HOSTGATOR_HOST" "$PORT" 2>/dev/null | tr -d '\r' | cut -c1-100)"
if [ -z "$banner" ]; then
  echo "   NO GREETING from the FTP server within 15 seconds (the connection was refused, dropped or silent)." >&2
  echo "   That is usually the host's firewall blocking this address, or FTP being unavailable. Not a password problem." >&2
  exit 6
fi
echo "   greeting: $banner"
if [ "$FTPS" = "true" ] && command -v openssl >/dev/null 2>&1; then
  tls="$(timeout 25 openssl s_client -starttls ftp -connect "$HOSTGATOR_HOST:$PORT" -servername "$HOSTGATOR_HOST" </dev/null 2>&1 || true)"
  echo "$tls" | grep -E "^subject=|^issuer=|Verification|Verify return code|Protocol  |Protocol:|Cipher is|Cipher    :" | head -6 | sed 's/^/   tls: /'
  if ! echo "$tls" | grep -qE "Cipher is|Cipher    :|Protocol"; then
    echo "   The encryption (TLS) handshake did not complete. FTPS may be unavailable on this host or port." >&2; exit 6
  fi
fi

# ---------------------------------------------------------------- 1. login, where are we, is it the right folder?
echo "1/4 Logging in and looking at the folder..."
listing="$(ftp "pwd" "echo ---" "cls -1")" \
  || { echo "Could not log in or open the folder. Check the host, user, password and remote folder." >&2; exit 3; }
# lftp's pwd prints the whole login URL (password included): keep only the path after the host.
echo "   the account starts in: $(printf '%s\n' "$listing" | sed -n '1p' | sed -E 's#^[A-Za-z]+://[^/]*##; s#^$#/#')"
names="$(printf '%s\n' "$listing" | sed '1,/^---$/d' | sed 's#/$##' | sort | tr '\n' ' ')"
echo "   it contains: ${names:-(nothing)}"
# Refuse to write into the wrong place: an account home or a WordPress folder has these, public_html/max never does.
for bad in public_html mail etc logs tmp wp-config.php wp-content wp-admin wp-includes; do
  case " $names " in *" $bad "*)
    echo "STOPPED before uploading anything: this folder contains '$bad', so it is not public_html/max." >&2
    echo "Fix the FTP account's Directory in cPanel (FTP Accounts > Change Directory) to public_html/max, or set HOSTGATOR_REMOTE_DIR." >&2
    exit 5 ;;
  esac
done
have_api=no; case " $names " in *" api "*) have_api=yes ;; esac

# ---------------------------------------------------------------- 2-4. one session: back up, upload, fetch back
mkdir -p "$BACKUP_DIR"; verify="$(mktemp -d)"
cmds=()
cmds+=("set cmd:fail-exit no")                                  # a file that is not on the server yet is not an error
for pair in "${FILES[@]}"; do
  remote="${pair#*:}"; mkdir -p "$BACKUP_DIR/$(dirname "$remote")"
  cmds+=("get $(quote "$remote") -o $(quote "$BACKUP_DIR/$remote")")
done
cmds+=("set cmd:fail-exit yes")
[ "$have_api" = yes ] || cmds+=("mkdir api")
for pair in "${FILES[@]}"; do
  cmds+=("put $(quote "$ROOT/${pair%%:*}") -o $(quote "${pair#*:}")")
done
for pair in "${FILES[@]}"; do
  remote="${pair#*:}"; mkdir -p "$verify/$(dirname "$remote")"
  cmds+=("get $(quote "$remote") -o $(quote "$verify/$remote")")
done
echo "2/4 Saving the current server copies, 3/4 uploading, 4/4 fetching everything back to compare (one session)..."
ftp "${cmds[@]}" >/dev/null || { echo "The transfer session failed." >&2; rm -rf "$verify"; exit 3; }

echo "2/4 Server copies saved before replacing:"
for pair in "${FILES[@]}"; do
  remote="${pair#*:}"
  if [ -s "$BACKUP_DIR/$remote" ]; then echo "   saved $remote"; else echo "   (no existing $remote on the server)"; rm -f "$BACKUP_DIR/$remote"; fi
done
echo "4/4 Comparing every file with the repository, byte for byte..."
bad=0
for pair in "${FILES[@]}"; do
  local_path="${pair%%:*}"; remote="${pair#*:}"
  if cmp -s "$local_path" "$verify/$remote"; then echo "   OK   $remote ($(wc -c < "$local_path") bytes)"; else echo "   DIFFERS  $remote" >&2; bad=1; fi
done
rm -rf "$verify"
[ "$bad" = 0 ] || { echo "Upload finished but a file on the server differs from the repository." >&2; exit 4; }
echo "Done. The HostGator copies match the repository."

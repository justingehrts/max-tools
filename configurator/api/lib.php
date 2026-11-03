<?php
// Shared code for save.php. Plain functions, no side effects when included.
// Validation mirrors schema/configs.schema.json; both sides are tested against schema/config-test-vectors.json.

declare(strict_types=1);

const MARKET_RE = '/^[a-z0-9][a-z0-9-]{0,39}$/D';   // D: '$' must not match before a trailing newline
const HEX_RE = '/^#[0-9a-fA-F]{6}$/D';
const UTC_RE = '/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/D';
const FFG_COLORS = 7;

/** True if $a is a JSON object (decoded as an associative array that is not a list). */
function is_obj($a): bool { return is_array($a) && ($a === [] || array_keys($a) !== range(0, count($a) - 1)); }

/** Errors for a market id (empty array = fine). $markets: set of known ids (id => true). */
function market_errors($m, array $markets): array {
    if (!is_string($m) || !preg_match(MARKET_RE, $m) || $m === 'default') return ['market' => 'Pick a market from the list.'];
    if (!isset($markets[$m])) return ['market' => 'That market is not in markets.json.'];
    return [];
}

/** Errors for an ffg value: null (= standard colors) or {colors: [7 x #rrggbb]}. */
function ffg_errors($ffg): array {
    if ($ffg === null) return [];
    if (!is_obj($ffg) || array_keys($ffg) !== ['colors']) return ['ffg' => 'Expected {"colors": [...7 colors]} or null.'];
    $c = $ffg['colors'];
    if (!is_array($c) || is_obj($c) || count($c) !== FFG_COLORS) return ['ffg.colors' => 'Exactly 7 colors are needed.'];
    $err = [];
    foreach ($c as $i => $hex) {
        if (!is_string($hex) || !preg_match(HEX_RE, $hex)) $err["ffg.colors[$i]"] = 'Use a color like #a50f15.';
    }
    return $err;
}

/** Validate one configs.json entry the way the build scripts do. Returns errors (empty = valid). */
function config_entry_errors($e, array $markets): array {
    if (!is_obj($e)) return ['entry' => 'not an object'];
    $extra = array_diff(array_keys($e), ['market', 'updatedUtc', 'ffg']);
    if ($extra) return ['entry' => 'unknown field ' . reset($extra)];
    $err = market_errors($e['market'] ?? null, $markets);
    if (array_key_exists('updatedUtc', $e) && (!is_string($e['updatedUtc']) || !preg_match(UTC_RE, $e['updatedUtc']))) $err['updatedUtc'] = 'bad time';
    if (array_key_exists('ffg', $e)) $err += ($e['ffg'] === null ? ['ffg' => 'omit instead of null'] : ffg_errors($e['ffg']));
    return $err;
}

/** Validate a save request body. Returns [clean request or null, errors]. */
function parse_save_request(string $raw, array $markets): array {
    if (strlen($raw) > 4096) return [null, ['body' => 'Request too large.']];
    $req = json_decode($raw, true, 8);
    if (!is_obj($req)) return [null, ['body' => 'Expected a JSON object.']];
    $extra = array_diff(array_keys($req), ['market', 'ffg', 'expectUpdatedUtc']);
    if ($extra) return [null, ['body' => 'Unknown field: ' . reset($extra)]];
    if (!array_key_exists('ffg', $req)) return [null, ['ffg' => 'Missing ffg (use null for the standard colors).']];
    $err = market_errors($req['market'] ?? null, $markets) + ffg_errors($req['ffg']);
    $exp = $req['expectUpdatedUtc'] ?? null;
    if ($exp !== null && (!is_string($exp) || !preg_match(UTC_RE, $exp))) $err['expectUpdatedUtc'] = 'bad time';
    if ($err) return [null, $err];
    if ($req['ffg'] !== null) $req['ffg'] = ['colors' => array_map('strtolower', $req['ffg']['colors'])];
    return [['market' => $req['market'], 'ffg' => $req['ffg'], 'expectUpdatedUtc' => $exp], []];
}

/** Find a market's entry in a decoded configs.json. */
function find_config(array $doc, string $market): ?array {
    foreach ($doc['configs'] ?? [] as $c) if (is_array($c) && ($c['market'] ?? null) === $market) return $c;
    return null;
}

/**
 * Apply a save to a decoded configs.json. Touches only the named market's entry; every other entry is kept exactly
 * as it was (even ones the builders would skip). Returns [new doc, changed?].
 */
function apply_save(array $doc, string $market, ?array $ffg, string $nowUtc): array {
    $old = find_config($doc, $market);
    $keep = array_values(array_filter($doc['configs'] ?? [], fn($c) => !(is_array($c) && ($c['market'] ?? null) === $market)));
    $oldFfg = $old['ffg'] ?? null;
    if ($oldFfg === $ffg) return [$doc, false];                    // nothing to do: no commit, no rebuild
    if ($ffg !== null) $keep[] = ['market' => $market, 'updatedUtc' => $nowUtc, 'ffg' => $ffg];
    usort($keep, fn($a, $b) => strcmp((string)($a['market'] ?? ''), (string)($b['market'] ?? '')));
    $doc['schemaVersion'] = $doc['schemaVersion'] ?? 1;
    $doc['configs'] = $keep;
    return [$doc, true];
}

function json_pretty(array $doc): string {
    $s = json_encode($doc, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    return preg_replace_callback('/^(?: {4})+/m', fn($m) => str_repeat(' ', intdiv(strlen($m[0]), 2)), $s) . "\n";  // 2-space indent like the repo
}

// ---------------------------------------------------------------- GitHub contents API

class GitHubError extends Exception { public int $status; function __construct(string $m, int $s) { parent::__construct($m); $this->status = $s; } }

function gh_request(array $cfg, string $method, string $path, ?array $body = null): array {
    $ch = curl_init(rtrim($cfg['api_base'], '/') . $path);
    $headers = ['Accept: application/vnd.github+json', 'X-GitHub-Api-Version: 2022-11-28', 'User-Agent: max-tools-configurator',
                'Authorization: Bearer ' . $cfg['token']];
    if ($body !== null) { $headers[] = 'Content-Type: application/json'; curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body)); }
    curl_setopt_array($ch, [CURLOPT_CUSTOMREQUEST => $method, CURLOPT_HTTPHEADER => $headers, CURLOPT_RETURNTRANSFER => true,
                            CURLOPT_TIMEOUT => 20, CURLOPT_CONNECTTIMEOUT => 10]);
    $out = curl_exec($ch);
    $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $cerr = curl_error($ch);
    curl_close($ch);
    if ($out === false) throw new GitHubError("network: $cerr", 0);
    $data = json_decode((string)$out, true);
    if ($status < 200 || $status >= 300) throw new GitHubError(is_array($data) ? (string)($data['message'] ?? 'error') : 'error', $status);
    return is_array($data) ? $data : [];
}

/** Read a JSON file from the repo. Returns [decoded, sha]. */
function gh_get_json(array $cfg, string $file): array {
    $r = gh_request($cfg, 'GET', "/repos/{$cfg['owner']}/{$cfg['repo']}/contents/$file?ref=" . rawurlencode($cfg['branch']));
    $doc = json_decode((string)base64_decode((string)($r['content'] ?? ''), true), true);
    if (!is_array($doc)) throw new GitHubError("$file is not valid JSON", 500);
    return [$doc, (string)($r['sha'] ?? '')];
}

function gh_put_file(array $cfg, string $file, string $text, string $sha, string $message): void {
    gh_request($cfg, 'PUT', "/repos/{$cfg['owner']}/{$cfg['repo']}/contents/$file",
               ['message' => $message, 'content' => base64_encode($text), 'sha' => $sha, 'branch' => $cfg['branch']]);
}

// ---------------------------------------------------------------- rate limit (per IP, stored as a salted hash only)

function rate_limited(string $dir, string $ip, string $bucket, int $max, int $window, ?int $now = null): bool {
    $now = $now ?? time();
    if (!is_dir($dir)) @mkdir($dir, 0700, true);
    $f = fopen("$dir/ratelimit.json", 'c+');
    if ($f === false) return false;                                  // never lock people out because of a disk problem
    flock($f, LOCK_EX);
    $all = json_decode((string)stream_get_contents($f), true) ?: [];
    $key = $bucket . ':' . substr(hash('sha256', $ip . '|' . __DIR__), 0, 16);
    foreach ($all as $k => $times) {                                 // forget old entries
        $all[$k] = array_values(array_filter($times, fn($t) => $t > $now - $window));
        if (!$all[$k]) unset($all[$k]);
    }
    $hit = count($all[$key] ?? []) >= $max;
    if (!$hit) $all[$key][] = $now;
    ftruncate($f, 0); rewind($f); fwrite($f, json_encode($all));
    flock($f, LOCK_UN); fclose($f);
    return $hit;
}

function log_line(string $dir, string $line): void {
    @file_put_contents("$dir/save.log", gmdate('Y-m-d\TH:i:s\Z') . " $line\n", FILE_APPEND | LOCK_EX);
}

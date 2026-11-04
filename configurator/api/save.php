<?php
// Configurator endpoint. Lives next to the configurator page, behind the same basic-auth password.
//   GET  save.php?market=columbus-oh   -> that market's saved FFG colors (or null) and when they were saved
//   POST save.php  {"market": "...", "ffg": {"colors": [7 x "#rrggbb"]} | null, "expectUpdatedUtc": "..." | null}
//        -> validates, commits configs.json to GitHub (that commit starts a rebuild), returns the market's URLs.
// The GitHub token never reaches the browser: it is read from a file outside the web folder (see private/config.example.php).

declare(strict_types=1);
require __DIR__ . '/lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function reply(int $status, array $body): void { http_response_code($status); echo json_encode($body, JSON_UNESCAPED_SLASHES); exit; }

// Settings live outside public_html. Default: <home>/maxtools-private/config.php when this file is <home>/public_html/<folder>/api/.
$configFile = getenv('MAXTOOLS_CONFIG') ?: dirname(__DIR__, 3) . '/maxtools-private/config.php';
$cfg = is_file($configFile) ? require $configFile : null;
if (!is_array($cfg)) reply(500, ['ok' => false, 'error' => 'The save service is not set up yet (config file missing).']);
// Say exactly which check failed (the page is behind the password, so naming the server path is fine; the token never is).
$tf = (string)($cfg['token_file'] ?? '');
if ($tf === '') reply(500, ['ok' => false, 'error' => 'The save service is not set up yet: token_file is not set in config.php.']);
if (!@is_file($tf)) reply(500, ['ok' => false, 'error' => "The save service is not set up yet: no token file at $tf (check the path in config.php)."]);
if (!@is_readable($tf)) reply(500, ['ok' => false, 'error' => "The save service is not set up yet: $tf exists but PHP cannot read it (permissions)."]);
$token = trim((string)@file_get_contents($tf));
if ($token === '') reply(500, ['ok' => false, 'error' => "The save service is not set up yet: $tf is empty."]);
$cfg['token'] = $token;
$dataDir = $cfg['data_dir'];
$ip = $_SERVER['REMOTE_ADDR'] ?? '?';
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

// Same-origin only: browsers send Origin on cross-site requests; refuse any that is not this host.
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin !== '' && parse_url($origin, PHP_URL_HOST) !== strtok($_SERVER['HTTP_HOST'] ?? '', ':')) {
    reply(403, ['ok' => false, 'error' => 'Requests must come from the configurator page.']);
}

try {
    [$marketsDoc] = gh_get_json($cfg, 'markets.json');
    $markets = [];
    foreach ($marketsDoc['markets'] ?? [] as $m) if (is_array($m) && is_string($m['id'] ?? null)) $markets[$m['id']] = true;

    if ($method === 'GET') {
        if (rate_limited($dataDir, $ip, 'read', 120, 600)) reply(429, ['ok' => false, 'error' => 'Too many requests. Wait a few minutes.']);
        $m = $_GET['market'] ?? null;
        if ($e = market_errors($m, $markets)) reply(400, ['ok' => false, 'errors' => $e]);
        [$doc] = gh_get_json($cfg, 'configs.json');
        $c = find_config($doc, $m);
        reply(200, ['ok' => true, 'market' => $m, 'ffg' => $c['ffg'] ?? null, 'updatedUtc' => $c['updatedUtc'] ?? null]);
    }

    if ($method !== 'POST') { header('Allow: GET, POST'); reply(405, ['ok' => false, 'error' => 'Use GET or POST.']); }
    if (($_SERVER['HTTP_X_REQUESTED_WITH'] ?? '') !== 'configurator') reply(403, ['ok' => false, 'error' => 'Missing configurator header.']);
    if (stripos($_SERVER['CONTENT_TYPE'] ?? '', 'application/json') !== 0) reply(415, ['ok' => false, 'error' => 'Send JSON.']);
    if (rate_limited($dataDir, $ip, 'save', 10, 600)) reply(429, ['ok' => false, 'error' => 'Too many saves. Wait a few minutes and try again.']);

    [$req, $errors] = parse_save_request((string)file_get_contents('php://input', false, null, 0, 4097), $markets);
    if ($errors) reply(400, ['ok' => false, 'errors' => $errors]);
    $m = $req['market'];

    for ($attempt = 1; ; $attempt++) {
        [$doc, $sha] = gh_get_json($cfg, 'configs.json');
        $current = find_config($doc, $m);
        // Someone else saved this market after the page loaded it: do not overwrite silently.
        if ($req['checkExpected'] && ($current['updatedUtc'] ?? null) !== $req['expectUpdatedUtc']) {
            reply(409, ['ok' => false, 'error' => 'Someone saved this market after you opened the page. Reload to see their colors.',
                        'updatedUtc' => $current['updatedUtc'] ?? null]);
        }
        [$new, $changed] = apply_save($doc, $m, $req['ffg'], gmdate('Y-m-d\TH:i:s\Z'));
        if (!$changed) break;
        try {
            gh_put_file($cfg, 'configs.json', json_pretty($new), $sha, "Update $m (ffg) via configurator");
            break;
        } catch (GitHubError $ex) {
            if ($ex->status === 409 && $attempt === 1) continue;    // the file changed between read and write: retry once
            throw $ex;
        }
    }
    log_line($dataDir, "saved $m " . ($req['ffg'] === null ? 'standard' : 'custom') . ($changed ? '' : ' (unchanged)'));
    $base = rtrim($cfg['pages_base'], '/');
    $urls = [];
    foreach ([1, 3, 6] as $h) $urls["{$h}h"] = "$base/markets/$m/Custom_FFG_{$h}hr.kmz";
    $saved = find_config($new ?? $doc, $m);
    reply(200, ['ok' => true, 'changed' => $changed, 'updatedUtc' => $saved['updatedUtc'] ?? null, 'urls' => $urls,
                'goesLive' => $changed ? 'usually within 5 minutes (at most about 15)' : 'nothing changed']);
} catch (GitHubError $ex) {
    log_line($dataDir, "github error {$ex->status}: {$ex->getMessage()}");
    reply(502, ['ok' => false, 'error' => 'GitHub did not accept the change. Try again in a minute.']);
}

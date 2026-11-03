<?php
// php tests/php/test_lib.php   (exit 1 on failure)
declare(strict_types=1);
require __DIR__ . '/../../configurator/api/lib.php';
$root = dirname(__DIR__, 2);
$fail = 0;
function check(bool $ok, string $what): void { global $fail; if (!$ok) { $fail++; echo "FAIL: $what\n"; } }

$markets = [];
foreach (json_decode(file_get_contents("$root/markets.json"), true)['markets'] as $m) $markets[$m['id']] = true;

// 1. Same cases as the Python validator.
foreach (json_decode(file_get_contents("$root/schema/config-test-vectors.json"), true)['cases'] as $i => $c) {
    $err = config_entry_errors($c['entry'], $markets);
    check(($err === []) === $c['valid'], "vector $i " . json_encode($c['entry']) . ' -> ' . json_encode($err));
}

// 2. Requests.
$seven = array_fill(0, 7, '#A50F15');
[$r, $e] = parse_save_request(json_encode(['market' => 'columbus-oh', 'ffg' => ['colors' => $seven]]), $markets);
check($e === [] && $r['ffg']['colors'][0] === '#a50f15', 'valid request, colors lowercased');
[$r, $e] = parse_save_request(json_encode(['market' => 'columbus-oh', 'ffg' => null]), $markets);
check($e === [] && $r['ffg'] === null, 'null = standard');
[, $e] = parse_save_request(json_encode(['market' => 'columbus-oh']), $markets);           check(isset($e['ffg']), 'ffg required');
[, $e] = parse_save_request(json_encode(['market' => 'columbus-oh', 'ffg' => null, 'x' => 1]), $markets); check(isset($e['body']), 'unknown field');
[, $e] = parse_save_request('[1,2]', $markets);                                            check(isset($e['body']), 'list body');
[, $e] = parse_save_request(str_repeat(' ', 5000), $markets);                              check(isset($e['body']), 'too large');
[, $e] = parse_save_request(json_encode(['market' => 'columbus-oh', 'ffg' => ['colors' => ['#000000', 'x', '#000000', '#000000', '#000000', '#000000', '#000000']]]), $markets);
check(array_keys($e) === ['ffg.colors[1]'], 'field-level error names the bad color');

// 3. Registry update touches only the named market.
$doc = ['schemaVersion' => 1, 'configs' => [['market' => 'seattle-wa', 'ffg' => ['colors' => $seven]], ['market' => 'weird', 'odd' => true]]];
[$new, $ch] = apply_save($doc, 'columbus-oh', ['colors' => $seven], '2026-11-03T00:00:00Z');
check($ch && count($new['configs']) === 3 && $new['configs'][0]['market'] === 'columbus-oh', 'insert, sorted');
check(in_array(['market' => 'weird', 'odd' => true], $new['configs'], true), 'other (even invalid) entries kept as they were');
[$same, $ch] = apply_save($new, 'columbus-oh', ['colors' => $seven], '2026-11-04T00:00:00Z');
check(!$ch && find_config($same, 'columbus-oh')['updatedUtc'] === '2026-11-03T00:00:00Z', 'unchanged save does nothing');
[$back, $ch] = apply_save($new, 'columbus-oh', null, '2026-11-04T00:00:00Z');
check($ch && find_config($back, 'columbus-oh') === null && count($back['configs']) === 2, 'null removes the entry');
check(str_starts_with(json_pretty(['a' => ['b' => 1]]), "{\n  \"a\": {\n    \"b\": 1"), '2-space indent');

// 4. Rate limit.
$dir = sys_get_temp_dir() . '/rl' . getmypid();
$hits = 0; for ($i = 0; $i < 12; $i++) $hits += rate_limited($dir, '1.2.3.4', 'save', 10, 600, 1000) ? 1 : 0;
check($hits === 2, "rate limit after 10 (got $hits)");
check(!rate_limited($dir, '1.2.3.4', 'save', 10, 600, 2000), 'window expires');
check(!rate_limited($dir, '5.6.7.8', 'save', 10, 600, 1000), 'other IPs unaffected');
check(strpos((string)file_get_contents("$dir/ratelimit.json"), '1.2.3.4') === false, 'IP not stored');

echo $fail ? "$fail failure(s)\n" : "PHP lib tests OK\n";
exit($fail ? 1 : 0);

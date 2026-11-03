<?php
// Copy to <home>/maxtools-private/config.php on HostGator (NOT inside public_html).
// <home> is the folder that contains public_html. This file works out <home> by itself (the folder above this one),
// so nothing below needs editing unless you put the token somewhere else.
$home = dirname(__DIR__);
return [
    'token_file' => $home . '/.maxtools_token',          // same token file as the cron job; needs Contents: Read and write
    'owner'      => 'justingehrts',
    'repo'       => 'max-tools',
    'branch'     => 'main',
    'api_base'   => 'https://api.github.com',
    'pages_base' => 'https://justingehrts.github.io/max-tools',
    'data_dir'   => __DIR__ . '/data',                    // rate-limit counters and a short save log (no IP addresses)
];

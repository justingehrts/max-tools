<?php
// Copy to <home>/maxtools-private/config.php on HostGator (NOT inside public_html) and adjust the paths.
// <home> is the folder that contains public_html, e.g. /home2/yourname.
return [
    'token_file' => '/home2/yourname/.maxtools_token',   // same token file as the cron job; needs Contents: Read and write
    'owner'      => 'justingehrts',
    'repo'       => 'max-tools',
    'branch'     => 'main',
    'api_base'   => 'https://api.github.com',
    'pages_base' => 'https://justingehrts.github.io/max-tools',
    'data_dir'   => '/home2/yourname/maxtools-private/data',  // rate-limit counters and a short save log (no IP addresses)
];

<?php
header('Content-Type: application/json');

// Redis
$redis = new Redis();
$redis->connect('127.0.0.1', 6379);

$status_key = 'wilo:pump:status:pins';
$stats_key  = 'wilo:pump:stats:watchdog';

$status_json = $redis->get($status_key);
$stats_raw   = $redis->hGetAll($stats_key);  // Alle Monate als assoc array

if (!$status_json) {
    echo json_encode(['error' => 'No status data']);
    exit;
}

// Parse Status und erweitere um Stats
$status = json_decode($status_json, true);

$stats = [
    "watchdog_resets_per_month" => $stats_raw ?: new stdClass(),
    "total_resets_ever" => array_sum($stats_raw ?: []),
    "last_reset_month"  => $stats_raw ? array_key_first(array_reverse($stats_raw, true)) : null,
    "resets_this_month" => $stats_raw[date('Y-m')] ?? 0
];

$status['STATS'] = $stats;

echo json_encode($status, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
?>

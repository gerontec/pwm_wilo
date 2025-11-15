 cat status_api.php 
<?php
// ######################################################################
// # status_api.php - Ruft den letzten MQTT-Payload aus Redis ab
// ######################################################################

// Setze Content-Type auf JSON
header('Content-Type: application/json');

// Redis Konfiguration
$redis_host = '127.0.0.1';
$redis_port = 6379;
$redis_key  = 'wilo:pump:status:pins'; // Muss dem Schlüssel der Python-Bridge entsprechen

try {
    // 1. Redis-Verbindung herstellen
    $redis = new Redis();
    
    // Stellen Sie sicher, dass die PHP-Redis-Erweiterung installiert ist (php-redis)
    if (!$redis->connect($redis_host, $redis_port)) {
        throw new Exception("Could not connect to Redis server.");
    }
    
    // 2. Wert abrufen
    // Dieser Wert enthält nun automatisch das neue Feld "PumpStatus"
    $json_data = $redis->get($redis_key);

    if ($json_data === false || $json_data === null) {
        // Fehler, wenn der Schlüssel nicht existiert (noch keine Daten vom Pico W empfangen)
        echo json_encode([
            'error' => 'No status data found. Waiting for first MQTT message on heatp/pins.',
            'key' => $redis_key,
            'timestamp' => time()
        ]);
        http_response_code(404);
    } else {
        // 3. JSON-Daten ausgeben (diese sind bereits vom Pico W serialisiert)
        echo $json_data; 
    }
    
} catch (Exception $e) {
    // Fehler bei Redis-Verbindung oder PHP-Erweiterung fehlt
    echo json_encode([
        'error' => 'Backend API Error',
        'message' => $e->getMessage()
    ]);
    http_response_code(500);
}

?>

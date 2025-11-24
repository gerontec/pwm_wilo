#!/usr/bin/python3
import paho.mqtt.client as mqtt
import redis
import time
import sys
import os
import json
from datetime import datetime

# ==================== KONFIGURATION ====================
MQTT_BROKER = "10.8.0.4"
MQTT_PORT = 1883
MQTT_TOPIC = "heatp/pins"
CLIENT_ID = "Wilo_Redis_Bridge"

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_KEY_STATUS = "wilo:pump:status:pins"
REDIS_KEY_STATS = "wilo:pump:stats:watchdog"   # <-- NEU: Zähler pro Monat

r = None

def init_redis():
    global r
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        r.ping()
        print(f"[{os.getpid()}] Redis verbunden.")
        return True
    except Exception as e:
        print(f"[{os.getpid()}] Redis-Verbindung fehlgeschlagen: {e}")
        return False

# ==================== WATCHDOG-RESET ERKENNEN ====================
last_uptime = None

def detect_watchdog_reset(payload_json):
    global last_uptime
    try:
        data = json.loads(payload_json)
        current_uptime = int(data.get("UPTIME", 0))

        # Wenn Uptime < 30 Sekunden UND vorher > 300 Sekunden → klarer Reset!
        if last_uptime is not None and last_uptime > 300 and current_uptime < 30:
            month_key = datetime.now().strftime("%Y-%m")
            print(f"[{os.getpid()}] WATCHDOG RESET ERKANNT! Monat: {month_key}")
            
            # Zähler erhöhen
            current_count = r.hincrby(REDIS_KEY_STATS, month_key, 1)
            print(f"[{os.getpid()}] Reset-Zähler für {month_key}: {current_count}")
        
        last_uptime = current_uptime
    except:
        pass  # Bei kaputtem JSON ignorieren

# ==================== MQTT CALLBACKS ====================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{os.getpid()}] MQTT verbunden → abonniere {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"[{os.getpid()}] MQTT-Verbindung fehlgeschlagen (Code {rc})")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        
        # 1. Normalen Status speichern
        r.set(REDIS_KEY_STATUS, payload)
        
        # 2. Watchdog-Reset erkennen und zählen
        detect_watchdog_reset(payload)
        
    except Exception as e:
        print(f"[{os.getpid()}] Fehler in on_message: {e}")
        init_redis()

# ==================== HAUPTPROGRAMM ====================
if __name__ == '__main__':
    if not init_redis():
        sys.exit(1)

    client = mqtt.Client(client_id=CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[{os.getpid()}] Starte {CLIENT_ID} mit Watchdog-Statistik...")
    client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        print(f"[{os.getpid()}] Beendet.")

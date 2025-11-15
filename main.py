# pwmfeedback.py
# Modul zur Verarbeitung des Wilo-PWM-Feedback-Signals (Pin 5)
# V2.10: Duty Cycle Berechnung basiert auf 75Hz-Nennfrequenz (Fix aus V2.9)
#        + NEU: Hinzufügen einer menschenlesbaren Status-Meldung basierend auf der Wilo-Spezifikation.

from machine import Pin
import utime
import math

# ==================== KONFIGURATION ====================
TACHO_TIMEOUT_MS = 50       
MIN_PULSE_WIDTH_US = 2000   
PIN_FEEDBACK = 5            
NOMINAL_PERIOD_US = 1000000.0 / 75.0 # 13333.33 µs (Nominale 75 Hz Periode)

# Wilo PWM Output Status Mapping (siehe Dokumentation Seite 15 ff.)
# Die Bereiche wurden leicht angepasst, um Rundungsfehler und Grenzfälle robust abzudecken.
STATUS_MAP = [
    # Wichtig: Höchste Priorität/Grenzen zuerst prüfen!
    (lambda d: d >= 97.5, "Interface Damaged / Power OFF (100%)"),
    (lambda d: d >= 92.5, "Permanent Failure (95%) - Pump stopped due to internal error"),
    (lambda d: d >= 82.5 and d <= 92.5, "Abnormal Function Mode (85-90%) - Temporarily stopped/Warning"),
    (lambda d: d > 77.5 and d < 82.5, "Abnormal Running Mode (80%) - Not optimal performance"),
    (lambda d: d >= 5.0 and d <= 77.5, "Normal Operation (5-75%) - Flow/Power feedback"),
    (lambda d: d >= 1.5 and d < 5.0, "Stand-by (2%) - Active stop mode by PWM-Input"),
    (lambda d: d < 1.5, "Interface Damaged / Low Pulse (<2%)"),
]

# ==================== GLOBALE VARIABLEN (IRQ-gesteuert) ====================
last_pin5_time_us = utime.ticks_us()
pin5_high_time_us = 0
pin5_low_time_us = 0
pin5_flank_time_us = 0
last_pulse_time_us = utime.ticks_us() 

# ==================== FLANKENZEIT-MESSUNG CALLBACK (IRQ) ====================

def pin5_callback(pin):
    """
    Speichert die Dauer der HIGH- und LOW-Flanke separat.
    """
    global last_pin5_time_us, pin5_flank_time_us, pin5_high_time_us, pin5_low_time_us, last_pulse_time_us

    current_time_us = utime.ticks_us()
    
    time_diff_us = utime.ticks_diff(current_time_us, last_pin5_time_us)

    if time_diff_us > MIN_PULSE_WIDTH_US:
        if pin.value() == 1:
            pin5_low_time_us = time_diff_us
        else:
            pin5_high_time_us = time_diff_us
            
        pin5_flank_time_us = time_diff_us 
        
        last_pin5_time_us = current_time_us 
        last_pulse_time_us = current_time_us 

# ==================== STATUS-LOGIK ====================

def get_pump_status(duty_cycle):
    """Gibt den menschenlesbaren Status basierend auf dem Wilo Duty Cycle zurück."""
    for check, status in STATUS_MAP:
        if check(duty_cycle):
            return status
    return "UNKNOWN STATUS"


# ==================== INITIALISIERUNG & RÜCKGABE ====================

def init_feedback_pin():
    """Initialisiert den Feedback-Pin und den Interrupt."""
    feedback_pin = Pin(PIN_FEEDBACK, Pin.IN, Pin.PULL_UP)
    feedback_pin.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=pin5_callback)
    return feedback_pin

def get_pump_feedback(current_pin_value):
    """
    Berechnet die Frequenz und den Duty Cycle (konstante 75Hz Periode).
    Gibt ein Dictionary mit den Feedback-Werten zurück.
    """
    now_us = utime.ticks_us()
    time_since_last_pulse_ms = utime.ticks_diff(now_us, last_pulse_time_us) / 1000

    high_time = pin5_high_time_us
    low_time = pin5_low_time_us
    T_us_local = high_time + low_time
    
    # Standardwerte bei Fehler/Timeout
    freq = 0.0
    duty = 0.0
    json_flank_us = 0
    json_high_us = 0
    json_low_us = 0
    status = "TIMEOUT / NO PULSE" # Standard-Status bei Timeout

    if time_since_last_pulse_ms < TACHO_TIMEOUT_MS and T_us_local > 0:
        # 1. Frequenz (gemessen): Nur Diagnose
        freq = 1.0 / (T_us_local * 0.000001)
        
        # 2. Duty Cycle (berechnet): Nutzt die NENN-Periode (FIX)
        duty = (high_time / NOMINAL_PERIOD_US) * 100.0
        duty = min(max(duty, 0.0), 100.0) # Limitierung
        
        # 3. Status ableiten
        status = get_pump_status(duty)

        json_flank_us = pin5_flank_time_us
        json_high_us = high_time
        json_low_us = low_time
            
    # --- RÜCKGABE ---
    return {
        "PIN5": current_pin_value,
        "PIN5_Flank_us": json_flank_us, 
        "PIN5_HIGH_us": json_high_us, 
        "PIN5_LOW_us": json_low_us, 
        "PIN5_Freq_Hz": round(freq, 2), 
        "PumpDuty": round(duty, 2), 
        "PumpStatus": status, # NEUER STATUS-EINTRAG
    }

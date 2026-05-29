# ════════════════════════════════════════
#  demo.py — Demo/simulated data for development
#
#  When no real OBD2 adapter is connected, the app runs in demo mode.
#  This module provides fake vehicle info and simulated live sensor
#  data so the frontend can be developed and tested without hardware.
# ════════════════════════════════════════

import time

# Hardcoded demo vehicle info (shown when no real VIN is available)
DEMO_VIN = "1HGCM82633A004352"
DEMO_VEHICLE = {
    "make": "PORSCHE",
    "model": "911",
    "year": "1975",
    "trim": "Turbo",
    "engine": "3.0",
}


def demo_live_data() -> dict:
    """Generate simulated live sensor data.

    Uses time-based math to create smoothly varying values that
    look like a real running engine. Each sensor oscillates on
    a different period so the gauges don't all move in sync.

    Returns:
        Dict with rpm, speed, coolant, throttle, voltage, fuel_level.
    """
    t = time.time()
    return {
        "rpm":      int(800 + abs(1200 * (0.5 + 0.5 * (t % 4) / 4))),
        "speed":    int(max(0, 45 + 30 * ((t % 8) / 8 - 0.5))),
        "coolant":  int(85 + 10 * ((t % 20) / 20)),
        "throttle": round(15 + 40 * abs((t % 6) / 6 - 0.5), 1),
        "voltage":  round(13.8 + 0.4 * ((t % 3) / 3 - 0.5), 2),
        "fuel_level": 72,
    }

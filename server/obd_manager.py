# ════════════════════════════════════════
#  obd_manager.py — OBD2 connection manager
#
#  Handles connecting to the OBD2 adapter (real or demo),
#  reading live sensor data, and managing diagnostic trouble codes.
#
#  In demo mode (when python-obd is not installed or no adapter
#  is found), it uses simulated data from demo.py instead.
# ════════════════════════════════════════

import random
from typing import Optional

from .dtc_data import DTC_TO_PART, REPAIR_INFO
from .vin import decode_vin
from .demo import DEMO_VIN, DEMO_VEHICLE, demo_live_data

# Try to import the python-obd library. If it's not installed,
# the app runs in demo mode with simulated data.
try:
    import obd
    OBD_AVAILABLE = True
except ImportError:
    OBD_AVAILABLE = False
    print("[OBD2] python-obd not installed — running in DEMO mode")

# Pool of DTC codes to randomly pick from in demo mode
DEMO_DTCS_POOL = list(DTC_TO_PART.keys())


class OBDManager:
    """Manages the OBD2 adapter connection and data retrieval.

    Automatically falls back to demo mode if python-obd is not
    installed or no adapter is detected.
    """

    def __init__(self):
        self.connection: Optional[object] = None
        self.demo_mode = not OBD_AVAILABLE
        self.vin: Optional[str] = None
        self.vehicle_info: Optional[dict] = None
        self.active_dtcs: list[dict] = []

    def connect(self) -> dict:
        """Connect to OBD2 adapter or start demo mode.

        Returns:
            Dict with status, connection info, vehicle data, and DTCs.
        """
        if self.demo_mode:
            self.vin = DEMO_VIN
            self.vehicle_info = DEMO_VEHICLE
            # Randomly pick 0-2 demo DTCs to simulate real diagnostics
            codes = random.sample(DEMO_DTCS_POOL, k=random.randint(0, 2))
            self.active_dtcs = self._build_dtc_list(codes)
            return {
                "status": "connected",
                "demo": True,
                "vin": self.vin,
                "vehicle": self.vehicle_info,
                "dtcs": self.active_dtcs,
            }

        try:
            self.connection = obd.OBD()
            if not self.connection.is_connected():
                return {"status": "error", "message": "No OBD2 adapter found. Check USB connection."}

            # Read VIN from the vehicle's ECU
            vin_resp = self.connection.query(obd.commands["VIN_MESSAGE"])
            self.vin = str(vin_resp.value) if vin_resp.value else "UNKNOWN"
            self.vehicle_info = decode_vin(self.vin)

            # Read active diagnostic trouble codes
            dtc_resp = self.connection.query(obd.commands.GET_DTC)
            codes = [code for code, _ in (dtc_resp.value or [])]
            self.active_dtcs = self._build_dtc_list(codes)

            return {
                "status": "connected",
                "demo": False,
                "vin": self.vin,
                "vehicle": self.vehicle_info,
                "dtcs": self.active_dtcs,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _build_dtc_list(self, codes: list[str]) -> list[dict]:
        """Convert raw DTC codes into rich objects with part/repair info.

        Takes a list of code strings (e.g., ["P0420", "P0335"]) and
        returns a list of dicts with part name, severity, repair cost, etc.
        """
        result = []
        for code in codes:
            info = DTC_TO_PART.get(code, {})
            if info:
                part = info["part"]
                repair = REPAIR_INFO.get(part, {})
                result.append({
                    "code": code,
                    "part": part,
                    "label": info["label"],
                    "severity": info["severity"],
                    "repair_cost": repair.get("cost", "N/A"),
                    "diy": repair.get("diy", False),
                    "repair_time": repair.get("time", "N/A"),
                })
        return result

    def get_live_data(self) -> dict:
        """Read current sensor values from the OBD2 adapter.

        In demo mode, returns simulated data instead.
        """
        if self.demo_mode or not self.connection:
            return demo_live_data()
        try:
            def q(cmd):
                r = self.connection.query(cmd)
                return r.value.magnitude if r.value else 0
            return {
                "rpm":      int(q(obd.commands.RPM)),
                "speed":    int(q(obd.commands.SPEED)),
                "coolant":  int(q(obd.commands.COOLANT_TEMP)),
                "throttle": round(q(obd.commands.THROTTLE_POS), 1),
                "voltage":  round(q(obd.commands.ELM_VOLTAGE), 2),
                "fuel_level": int(q(obd.commands.FUEL_LEVEL)),
            }
        except Exception:
            return demo_live_data()

    def clear_dtcs(self) -> dict:
        """Clear all diagnostic trouble codes.

        On a real adapter, sends the CLEAR_DTC command to the ECU.
        In demo mode, just empties the local list.
        """
        if self.demo_mode:
            self.active_dtcs = []
            return {"status": "ok"}
        try:
            self.connection.query(obd.commands.CLEAR_DTC)
            self.active_dtcs = []
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

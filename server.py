import static
from requests import models
import requests

# hard dependacies
# codes you grab from a website
# 2 options
# keep grabbing
# or just grab it once store


vin = "1HGCM82633A004352"
url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"

r = requests.get(url)
data = r.json()["Results"]

# Extract the fields you need
fields = {item["Variable"]: item["Value"] for item in data}
make  = fields.get("Make")       # e.g. "HONDA"
model = fields.get("Model")      # e.g. "Accord"
year  = fields.get("Model Year") # e.g. "2003"

print(make, model, year)

import asyncio
import json
import os
import random
import time
from pathlib import Path
from typing import Optional

import requests
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Try to import obd; fall back to demo mode if not installed ──────────────
try:
    import obd
    OBD_AVAILABLE = True
except ImportError:
    OBD_AVAILABLE = False
    print("[OBD2] python-obd not installed — running in DEMO mode")

app = FastAPI(title="OBD2 3D Diagnostic")

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# ── DTC → Part name mapping ──────────────────────────────────────────────────
DTC_TO_PART: dict[str, dict] = {
    "P0130": {"part": "O2_Sensor_Front",      "label": "O₂ Sensor (Front)",          "severity": "high"},
    "P0131": {"part": "O2_Sensor_Front",      "label": "O₂ Sensor (Front)",          "severity": "high"},
    "P0136": {"part": "O2_Sensor_Rear",       "label": "O₂ Sensor (Rear)",           "severity": "medium"},
    "P0100": {"part": "MAF_Sensor",           "label": "Mass Airflow Sensor",        "severity": "high"},
    "P0101": {"part": "MAF_Sensor",           "label": "Mass Airflow Sensor",        "severity": "high"},
    "P0102": {"part": "MAF_Sensor",           "label": "Mass Airflow Sensor",        "severity": "medium"},
    "P0120": {"part": "Throttle_Body",        "label": "Throttle Body",              "severity": "high"},
    "P0121": {"part": "Throttle_Body",        "label": "Throttle Body",              "severity": "medium"},
    "P0420": {"part": "Catalytic_Converter",  "label": "Catalytic Converter",        "severity": "medium"},
    "P0430": {"part": "Catalytic_Converter",  "label": "Catalytic Converter",        "severity": "medium"},
    "P0115": {"part": "Coolant_Temp_Sensor",  "label": "Coolant Temp Sensor",        "severity": "medium"},
    "P0116": {"part": "Coolant_Temp_Sensor",  "label": "Coolant Temp Sensor",        "severity": "low"},
    "P0335": {"part": "Crankshaft_Sensor",    "label": "Crankshaft Position Sensor", "severity": "critical"},
    "P0336": {"part": "Crankshaft_Sensor",    "label": "Crankshaft Position Sensor", "severity": "critical"},
    "P0400": {"part": "EGR_Valve",            "label": "EGR Valve",                  "severity": "low"},
    "P0401": {"part": "EGR_Valve",            "label": "EGR Valve",                  "severity": "medium"},
    "P0300": {"part": "Engine_Block",         "label": "Engine (Misfire Detected)",  "severity": "critical"},
    "P0301": {"part": "Engine_Block",         "label": "Cylinder 1 Misfire",         "severity": "critical"},
    "P0171": {"part": "Fuel_Injector",        "label": "Fuel Injector (Lean)",       "severity": "medium"},
    "P0172": {"part": "Fuel_Injector",        "label": "Fuel Injector (Rich)",       "severity": "medium"},
    "P0340": {"part": "Camshaft_Sensor",      "label": "Camshaft Position Sensor",   "severity": "high"},
    "P0011": {"part": "Camshaft_Sensor",      "label": "Camshaft Timing",            "severity": "high"},
}

REPAIR_INFO: dict[str, dict] = {
    "O2_Sensor_Front":      {"cost": "$150–$300",  "diy": True,   "time": "1–2 hrs"},
    "O2_Sensor_Rear":       {"cost": "$120–$250",  "diy": True,   "time": "1 hr"},
    "MAF_Sensor":           {"cost": "$200–$400",  "diy": True,   "time": "30 min"},
    "Throttle_Body":        {"cost": "$300–$600",  "diy": False,  "time": "2–3 hrs"},
    "Catalytic_Converter":  {"cost": "$800–$2000", "diy": False,  "time": "2–4 hrs"},
    "Coolant_Temp_Sensor":  {"cost": "$50–$150",   "diy": True,   "time": "30 min"},
    "Crankshaft_Sensor":    {"cost": "$150–$300",  "diy": False,  "time": "1–3 hrs"},
    "EGR_Valve":            {"cost": "$200–$500",  "diy": False,  "time": "2 hrs"},
    "Engine_Block":         {"cost": "$500–$5000", "diy": False,  "time": "Shop visit"},
    "Fuel_Injector":        {"cost": "$150–$400",  "diy": False,  "time": "2 hrs"},
    "Camshaft_Sensor":      {"cost": "$100–$250",  "diy": True,   "time": "1 hr"},
}

# ── VIN model lookup ─────────────────────────────────────────────────────────
MODEL_LIBRARY: dict[str, str] = {
    # key: "MAKE|MODEL|YEAR_DECADE"  value: glb filename (place in static/models/)
    "default": "2000_Honda_Civic_Type_R",
}

def decode_vin(vin: str) -> dict:
    """Call NHTSA free API to decode a VIN."""
    try:
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"
        r = requests.get(url, timeout=5)
        data = r.json().get("Results", [])
        fields = {item["Variable"]: item["Value"] for item in data}
        return {
            "make":  fields.get("Make", "Unknown"),
            "model": fields.get("Model", "Unknown"),
            "year":  fields.get("Model Year", "Unknown"),
            "trim":  fields.get("Trim", ""),
            "engine": fields.get("Displacement (L)", ""),
        }
    except Exception as e:
        return {"make": "Unknown", "model": "Unknown", "year": "Unknown", "trim": "", "engine": "", "error": str(e)}


# ── Demo data generators ─────────────────────────────────────────────────────
DEMO_VIN = "1HGCM82633A004352"
DEMO_VEHICLE = {"make": "PORSCHE", "model": "911", "year": "1975", "trim": "Turbo", "engine": "3.0"}
DEMO_DTCS_POOL = list(DTC_TO_PART.keys())

_demo_dtcs: list[str] = []
_demo_connected = False


# for constants create a variables for it

def demo_live_data() -> dict:
    t = time.time()
    return {
        "rpm":     int(800 + abs(1200 * (0.5 + 0.5 * (t % 4) / 4))),
        "speed":   int(max(0, 45 + 30 * ((t % 8) / 8 - 0.5))),
        "coolant": int(85 + 10 * ((t % 20) / 20)),
        "throttle": round(15 + 40 * abs((t % 6) / 6 - 0.5), 1),
        "voltage":  round(13.8 + 0.4 * ((t % 3) / 3 - 0.5), 2),
        "fuel_level": 72,
    }


# ── OBD2 connection manager ──────────────────────────────────────────────────
class OBDManager:
    def __init__(self):
        self.connection: Optional[object] = None
        self.demo_mode = not OBD_AVAILABLE
        self.vin: Optional[str] = None
        self.vehicle_info: Optional[dict] = None
        self.active_dtcs: list[dict] = []

    def connect(self) -> dict:
        global _demo_connected
        if self.demo_mode:
            _demo_connected = True
            self.vin = DEMO_VIN
            self.vehicle_info = DEMO_VEHICLE
            # Randomly pick 1-2 demo DTCs
            codes = random.sample(DEMO_DTCS_POOL, k=random.randint(0, 2))
            self.active_dtcs = self._build_dtc_list(codes)
            return {"status": "connected", "demo": True, "vin": self.vin, "vehicle": self.vehicle_info, "dtcs": self.active_dtcs}

        try:
            self.connection = obd.OBD()
            if not self.connection.is_connected():
                return {"status": "error", "message": "No OBD2 adapter found. Check USB connection."}


            # Read VIN
            vin_resp = self.connection.query(obd.commands["VIN_MESSAGE"])
            self.vin = str(vin_resp.value) if vin_resp.value else "UNKNOWN"
            self.vehicle_info = decode_vin(self.vin)

            # Read DTCs
            dtc_resp = self.connection.query(obd.commands.GET_DTC)
            codes = [code for code, _ in (dtc_resp.value or [])]
            self.active_dtcs = self._build_dtc_list(codes)

            return {"status": "connected", "demo": False, "vin": self.vin, "vehicle": self.vehicle_info, "dtcs": self.active_dtcs}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _build_dtc_list(self, codes: list[str]) -> list[dict]:
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
        if self.demo_mode:
            self.active_dtcs = []
            return {"status": "ok"}
        try:
            self.connection.query(obd.commands.CLEAR_DTC)
            self.active_dtcs = []
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


obd_manager = OBDManager()


# ── REST endpoints ────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(html_path.read_text())

@app.post("/api/connect")
async def connect():
    return JSONResponse(obd_manager.connect())

@app.get("/api/vehicle")
async def vehicle():
    return JSONResponse({
        "vin": obd_manager.vin,
        "vehicle": obd_manager.vehicle_info,
        "dtcs": obd_manager.active_dtcs,
    })

@app.post("/api/clear_dtcs")
async def clear_dtcs():
    return JSONResponse(obd_manager.clear_dtcs())

@app.get("/api/dtc_library")
async def dtc_library():
    return JSONResponse(DTC_TO_PART)

@app.get("/api/demo_inject/{code}")
async def demo_inject(code: str):
    """Inject a test DTC for demo/dev purposes."""
    if code in DTC_TO_PART:
        info = DTC_TO_PART[code]
        part = info["part"]
        repair = REPAIR_INFO.get(part, {})
        entry = {
            "code": code,
            "part": part,
            "label": info["label"],
            "severity": info["severity"],
            "repair_cost": repair.get("cost", "N/A"),
            "diy": repair.get("diy", False),
            "repair_time": repair.get("time", "N/A"),
        }
        if not any(d["code"] == code for d in obd_manager.active_dtcs):
            obd_manager.active_dtcs.append(entry)
        return JSONResponse({"status": "injected", "dtc": entry})
    return JSONResponse({"status": "error", "message": "Unknown DTC"}, status_code=400)


# ── WebSocket live data stream ────────────────────────────────────────────────
@app.websocket("/ws/live")
async def live_data(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = obd_manager.get_live_data()
            data["dtcs"] = obd_manager.active_dtcs
            await ws.send_json(data)
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import webbrowser
    print("\n🔧 OBD2 3D Diagnostic App")
    print("   http://localhost:8000\n")
    webbrowser.open("http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
    

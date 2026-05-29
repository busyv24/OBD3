# ════════════════════════════════════════
#  app.py — FastAPI application, routes, and WebSocket
#
#  This is the main entry point for the backend. It:
#  - Creates the FastAPI app
#  - Mounts static files (JS, models, etc.)
#  - Defines REST API endpoints for connecting, reading DTCs, etc.
#  - Runs a WebSocket that streams live sensor data to the frontend
#
#  All business logic lives in other modules (obd_manager, dtc_data, etc.)
#  This file only handles HTTP/WebSocket routing.
# ════════════════════════════════════════

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .dtc_data import DTC_TO_PART, REPAIR_INFO
from .obd_manager import OBDManager

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="OBD2 3D Diagnostic")

# BASE_DIR points to the project root (one level up from server/)
BASE_DIR = Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Single shared OBD manager instance for the whole app
obd_manager = OBDManager()


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main HTML page."""
    html_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(html_path.read_text())


@app.post("/api/connect")
async def connect():
    """Connect to the OBD2 adapter (or start demo mode)."""
    return JSONResponse(obd_manager.connect())


@app.get("/api/vehicle")
async def vehicle():
    """Get current vehicle info and active DTCs."""
    return JSONResponse({
        "vin": obd_manager.vin,
        "vehicle": obd_manager.vehicle_info,
        "dtcs": obd_manager.active_dtcs,
    })


@app.post("/api/clear_dtcs")
async def clear_dtcs():
    """Clear all diagnostic trouble codes."""
    return JSONResponse(obd_manager.clear_dtcs())


@app.get("/api/dtc_library")
async def dtc_library():
    """Return the full DTC code -> part mapping for reference."""
    return JSONResponse(DTC_TO_PART)


@app.get("/api/demo_inject/{code}")
async def demo_inject(code: str):
    """Inject a test DTC for demo/development purposes.

    This lets the frontend be tested without a real OBD2 adapter.
    Only works with codes that exist in DTC_TO_PART.
    """
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
    """Stream live sensor data to the frontend every 250ms.

    The frontend connects to this WebSocket after clicking "Connect".
    Each message is a JSON object with rpm, speed, coolant, etc.
    plus the current list of active DTCs.
    """
    await ws.accept()
    try:
        while True:
            data = obd_manager.get_live_data()
            data["dtcs"] = obd_manager.active_dtcs
            await ws.send_json(data)
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass

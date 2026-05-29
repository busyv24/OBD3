# ════════════════════════════════════════
#  run.py — Application launcher
#
#  This is the entry point you run to start the app:
#    python run.py
#
#  All backend logic lives in the server/ package:
#    server/app.py         — FastAPI routes and WebSocket
#    server/obd_manager.py — OBD2 connection handling
#    server/dtc_data.py    — DTC codes and repair info
#    server/vin.py         — VIN decoding (NHTSA API)
#    server/demo.py        — Simulated data for development
# ════════════════════════════════════════

import uvicorn
import webbrowser


if __name__ == "__main__":
    print("\n🔧 OBD2 3D Diagnostic App")
    print("   http://localhost:8000\n")
    webbrowser.open("http://localhost:8000")
    # "server:app" tells uvicorn to import `app` from the `server` package
    # which is resolved via server/__init__.py -> server/app.py
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)

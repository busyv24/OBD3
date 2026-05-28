# OBD2 3D Diagnostic App

A fullstack Python app that reads live car data via OBD2 and displays
a 3D engine model with highlighted faulty parts.

## Quick Start (macOS)

### 1. Install Python 3.11+
```bash
brew install python@3.11
```

### 2. Create a virtual environment
```bash
cd obd2_app
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python server.py
```
The browser opens automatically at http://localhost:8000

---

## With a Real OBD2 Adapter

1. Plug a USB ELM327 adapter into your Mac and the car's OBD2 port
2. Install the obd library:
   ```bash
   pip install obd
   ```
3. Uncomment `obd>=0.7.1` in requirements.txt
4. Run `python server.py` — click Connect, it will find the adapter automatically

> Tip: If using a Bluetooth ELM327, pair it first in macOS Bluetooth settings,
> then connect via `/dev/tty.OBDII` or similar in the obd library.

---

## Adding Real 3D Models

1. Download a GLB car model from Sketchfab (search "car engine parts named")
2. In Blender, rename meshes to match the part names in `DTC_TO_PART` in server.py
3. Export as GLB → place in `static/models/`
4. Update `MODEL_LIBRARY` in server.py to point to your file

The built-in procedural engine renders immediately without any external files.

---

## Project Structure

```
obd2_app/
├── server.py          ← FastAPI backend, OBD2 logic, WebSocket
├── requirements.txt
├── templates/
│   └── index.html     ← Full frontend (Three.js 3D + UI)
└── static/
    └── models/        ← Place custom .glb files here
```

---

## Demo Mode

Without an OBD2 adapter the app runs in demo mode automatically:
- Simulated live sensor data (RPM, speed, temp, etc.)
- Use the "Inject Test DTC" buttons to trigger fault codes
- The 3D engine highlights the affected part and shows repair info

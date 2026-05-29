// ════════════════════════════════════════
//  obd.js — Server communication (API calls + WebSocket)
//
//  This module handles all communication with the FastAPI backend:
//  - POST /api/connect     — connect to OBD2 adapter (or demo mode)
//  - POST /api/clear_dtcs  — clear fault codes
//  - GET  /api/demo_inject — inject a test DTC for development
//  - WebSocket /ws/live    — real-time streaming of live sensor data
//
//  It imports UI update functions from main.js to refresh the
//  interface when new data arrives from the server.
// ════════════════════════════════════════

import { setStatus, updateVehicle, updateDTCs, updateGauges, toast } from './main.js';
import { showAll, getActiveDTCs, setActiveDTCs } from './scene.js';

// ── Private state ────────────────────────────────────────────────────────────
let isConnected = false;  // Whether we have an active connection
let ws = null;            // WebSocket instance for live data streaming

// ════════════════════════════════════════
//  Connect to car
//  Sends a POST to the server which either:
//  - Connects to a real OBD2 adapter, or
//  - Falls back to demo mode with simulated data
//  Then updates the UI with vehicle info and any DTCs found.
// ════════════════════════════════════════
export async function connectCar() {
  setStatus('connecting', 'Connecting...');
  document.getElementById('scan-overlay').classList.add('active');
  try {
    const r = await fetch('/api/connect', { method: 'POST' });
    const data = await r.json();
    if (data.status === 'connected') {
      isConnected = true;
      // Hide the connect screen, show the 3D view
      document.getElementById('connect-screen').style.display = 'none';
      // Update status pill (green for real, blue for demo)
      setStatus(data.demo ? 'demo' : 'connected', data.demo ? 'Demo Mode' : 'Connected');
      if (data.demo) document.getElementById('demo-badge').style.display = 'block';
      // Display the vehicle's VIN number
      document.getElementById('vin-display').textContent = data.vin || '—';
      // Update left panel with vehicle make/model/year
      updateVehicle(data.vehicle);
      // Display any diagnostic trouble codes found
      updateDTCs(data.dtcs || []);
      // Start receiving live sensor data over WebSocket
      startWebSocket();
    } else {
      setStatus('error', 'Error');
      toast('Connection failed: ' + (data.message || 'Unknown error'));
    }
  } catch(e) {
    setStatus('error', 'Error');
    toast('Server error — is server.py running?');
  }
  document.getElementById('scan-overlay').classList.remove('active');
}

// ════════════════════════════════════════
//  WebSocket live data stream
//  Opens a persistent connection to the server that pushes
//  live sensor data (RPM, speed, coolant temp, etc.) every 250ms.
//  If the connection drops, it automatically reconnects after 2 seconds.
// ════════════════════════════════════════
function startWebSocket() {
  if (ws) ws.close();  // Close existing connection if any
  // Connect to the WebSocket endpoint
  // location.host = hostname:port, so this works on any server
  ws = new WebSocket(`ws://${location.host}/ws/live`);

  ws.onmessage = e => {
    const d = JSON.parse(e.data);
    // Update the gauge displays with new sensor values
    updateGauges(d);
    // Check if the DTC list changed (new codes injected, etc.)
    const activeDTCs = getActiveDTCs();
    if (d.dtcs && JSON.stringify(d.dtcs) !== JSON.stringify(activeDTCs)) {
      updateDTCs(d.dtcs);
    }
  };

  // Auto-reconnect if the WebSocket closes unexpectedly
  ws.onclose = () => {
    if (isConnected) setTimeout(startWebSocket, 2000);
  };
}

// ════════════════════════════════════════
//  Clear DTCs
//  Tells the server to clear all diagnostic trouble codes,
//  then resets the local state and 3D view.
// ════════════════════════════════════════
export async function clearDTCs() {
  await fetch('/api/clear_dtcs', { method: 'POST' });
  setActiveDTCs([]);
  updateDTCs([]);
  showAll();
  toast('Fault codes cleared');
}

// ════════════════════════════════════════
//  main.js — UI updates, glue, and boot
//
//  This is the entry point of the app. It:
//  - Initializes the 3D scene (via scene.js)
//  - Updates all UI elements (gauges, DTC list, vehicle info)
//  - Wires up HTML onclick handlers to module functions
//  - Contains helper functions (toast notifications, DTC descriptions)
//
//  Think of this as the "controller" — it connects the 3D view (scene.js)
//  with the server communication (obd.js) and the HTML interface.
// ════════════════════════════════════════

import {
  initThree,
  highlightPart,
  showAll,
  resetCamera,
  toggleWireframe,
  toggleExplode,
  setSelectedDTC,
  setActiveDTCs,
  getActiveDTCs,
} from './scene.js';

import { connectCar, clearDTCs } from './obd.js';

// ════════════════════════════════════════
//  Toast notification
//  Shows a brief message at the bottom of the screen.
//  Auto-hides after 2.5 seconds.
// ════════════════════════════════════════
let toastTimer;
export function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2500);
}

// ════════════════════════════════════════
//  Status pill
//  Updates the connection status indicator in the top bar.
//  States: 'connecting', 'connected', 'demo', 'error'
// ════════════════════════════════════════
export function setStatus(state, text) {
  const pill = document.getElementById('status-pill');
  pill.className = 'status-pill ' + state;
  document.getElementById('status-text').textContent = text;
}

// ════════════════════════════════════════
//  Vehicle info
//  Updates the left panel with make, model, and year.
// ════════════════════════════════════════
export function updateVehicle(v) {
  if (!v) return;
  document.getElementById('vehicle-make').textContent  = v.make  || '—';
  document.getElementById('vehicle-model').textContent = v.model || '—';
  document.getElementById('vehicle-year').textContent  = v.year  || '—';
}

// ════════════════════════════════════════
//  Live gauge updates
//  Updates the 6 gauge displays with real-time sensor data.
//  Each gauge has a value, a bar fill, and color-coding
//  (normal = blue, warn = orange, danger = red).
// ════════════════════════════════════════
export function updateGauges(d) {
  // Helper: update a single gauge by ID
  // max = the value that represents 100% on the bar
  // warnThresh/dangerThresh = color change thresholds
  const set = (id, val, max, warnThresh, dangerThresh) => {
    document.getElementById('g-' + id).textContent = val;
    const pct = Math.min((val / max) * 100, 100);
    const bar = document.getElementById('b-' + id);
    bar.style.width = pct + '%';
    bar.className = 'gauge-fill' + (val >= dangerThresh ? ' danger' : val >= warnThresh ? ' warn' : '');
  };
  if (d.rpm     !== undefined) set('rpm',     d.rpm,      8000, 5500, 7000);
  if (d.speed   !== undefined) set('speed',   d.speed,    160,  100,  140);
  if (d.coolant !== undefined) set('coolant', d.coolant,  130,   90,  110);
  if (d.throttle!== undefined) set('throttle',d.throttle, 100,   80,   95);
  if (d.voltage !== undefined) set('voltage', d.voltage,   16,   14.5, 15.5);
  if (d.fuel_level!==undefined)set('fuel',   d.fuel_level,100,   20,   10);
}

// ════════════════════════════════════════
//  DTC list
//  Renders the list of diagnostic trouble codes in the left panel.
//  Each DTC becomes a clickable card. The most severe DTC is
//  auto-selected so the 3D view immediately highlights it.
// ════════════════════════════════════════
export function updateDTCs(dtcs) {
  // Sync the shared state in scene.js so flyTo tooltip works
  setActiveDTCs(dtcs);

  const container = document.getElementById('dtc-list-container');
  const noMsg = document.getElementById('no-dtc-msg');
  document.getElementById('dtc-count').textContent = dtcs.length ? `(${dtcs.length})` : '';

  // Remove old DTC cards (but keep the "no DTCs" message element)
  container.querySelectorAll('.dtc-card').forEach(c => c.remove());

  if (!dtcs.length) {
    noMsg.style.display = 'block';
    showAll();  // Reset 3D view when no DTCs
    return;
  }
  noMsg.style.display = 'none';

  // Create a card for each DTC
  dtcs.forEach(dtc => {
    const card = document.createElement('div');
    card.className = 'dtc-card';
    card.dataset.severity = dtc.severity;
    card.dataset.code = dtc.code;
    card.innerHTML = `
      <div class="dtc-code">${dtc.code}</div>
      <div class="dtc-part">${dtc.label}</div>
      <span class="dtc-severity-badge sev-${dtc.severity}">${dtc.severity}</span>
    `;
    card.onclick = () => selectDTC(dtc, card);
    container.appendChild(card);
  });

  // Auto-select the most severe DTC
  const order = ['critical','high','medium','low'];
  const worst = dtcs.sort((a,b) => order.indexOf(a.severity) - order.indexOf(b.severity))[0];
  if (worst) {
    const card = container.querySelector(`[data-code="${worst.code}"]`);
    selectDTC(worst, card);
  }
}

// ════════════════════════════════════════
//  DTC selection
//  When the user clicks a DTC card, this:
//  1. Highlights the card in the list
//  2. Updates the right panel with repair info
//  3. Shows the DTC description
//  4. Updates the location diagram
//  5. Highlights the part in the 3D view
// ════════════════════════════════════════
function selectDTC(dtc, cardEl) {
  setSelectedDTC(dtc);
  // Mark the clicked card as active, deactivate others
  document.querySelectorAll('.dtc-card').forEach(c => c.classList.remove('active'));
  if (cardEl) cardEl.classList.add('active');

  // Right panel — selected fault info
  document.getElementById('selected-code').textContent = dtc.code;
  document.getElementById('selected-part').textContent = dtc.label;

  // Repair info card
  const rc = document.getElementById('repair-card');
  rc.classList.remove('hidden');
  document.getElementById('ri-cost').textContent = dtc.repair_cost || 'N/A';
  document.getElementById('ri-diy').textContent  = dtc.diy ? '✓ Yes' : '✗ No';
  document.getElementById('ri-diy').className = 'repair-val ' + (dtc.diy ? 'diy-yes' : 'diy-no');
  document.getElementById('ri-time').textContent = dtc.repair_time || 'N/A';

  // Description text
  document.getElementById('desc-text').textContent = getDTCDescription(dtc.code);

  // Location diagram dot
  updateLocationDot(dtc.part);

  // 3D highlight — tell scene.js to glow this part
  highlightPart(dtc.part, dtc.severity);
}

// ════════════════════════════════════════
//  DTC descriptions
//  Human-readable explanations of what each fault code means.
//  Falls back to a generic message for codes not in the map.
// ════════════════════════════════════════
function getDTCDescription(code) {
  const map = {
    P0130: "The front oxygen sensor is reporting abnormal voltage. This sensor monitors exhaust gases to help the ECU adjust the air/fuel mixture. A faulty sensor causes poor fuel economy and may trigger a rich or lean condition.",
    P0420: "The catalytic converter efficiency has dropped below the threshold. The rear O2 sensor has detected insufficient conversion of exhaust gases. This is one of the most common check engine codes.",
    P0335: "The crankshaft position sensor is not sending a valid signal. This sensor is critical — without it the ECU cannot determine piston position and the engine may not start or will run poorly.",
    P0300: "A random misfire has been detected across multiple cylinders. This can be caused by bad spark plugs, ignition coils, fuel injectors, or a vacuum leak. Continued driving may damage the catalytic converter.",
    P0100: "The mass airflow sensor signal is outside expected range. The MAF sensor measures incoming air volume to calculate fuel delivery. A dirty or failing MAF causes rough idle, hesitation, and poor performance.",
    P0171: "The engine is running lean — too much air or too little fuel. Common causes include a vacuum leak, dirty MAF sensor, weak fuel pump, or clogged fuel injectors.",
  };
  return map[code] || `Fault code ${code} indicates a problem with the ${code.startsWith('P01') ? 'fuel/air metering' : code.startsWith('P03') ? 'ignition or misfire' : code.startsWith('P04') ? 'emissions system' : 'engine management'} system. Consult a service manual for this vehicle for exact specifications and repair procedures.`;
}

// ════════════════════════════════════════
//  Location diagram
//  Updates the SVG car diagram in the right panel to show
//  a pulsing dot where the affected part is located on the car.
// ════════════════════════════════════════
const LOCATION_DOTS = {
  Engine_Block:         [52, 68],  Crankshaft_Sensor: [60, 75],
  Camshaft_Sensor:      [55, 65],  Throttle_Body:     [50, 62],
  MAF_Sensor:           [45, 60],  Fuel_Injector:     [65, 70],
  Catalytic_Converter:  [145, 80], O2_Sensor_Front:   [120, 78],
  O2_Sensor_Rear:       [165, 80], EGR_Valve:         [70, 65],
  Coolant_Temp_Sensor:  [68, 63],
};

function updateLocationDot(partName) {
  const pos = LOCATION_DOTS[partName] || [120, 70];
  const dot = document.getElementById('loc-dot');
  dot.setAttribute('cx', pos[0]);
  dot.setAttribute('cy', pos[1]);
  dot.setAttribute('opacity', '1');
  document.getElementById('loc-label').textContent = partName.replace(/_/g, ' ');
}

// ════════════════════════════════════════
//  Demo inject buttons
//  Creates the test DTC injection buttons in the right panel.
//  These let you simulate fault codes without a real OBD2 adapter.
// ════════════════════════════════════════
function buildInjectButtons() {
  const grid = document.getElementById('inject-grid');
  const codes = ['P0420','P0130','P0335','P0300','P0100','P0171','P0340','P0115'];
  codes.forEach(code => {
    const b = document.createElement('button');
    b.className = 'inject-btn';
    b.textContent = code;
    b.onclick = async () => {
      const r = await fetch(`/api/demo_inject/${code}`);
      const d = await r.json();
      if (d.status === 'injected') {
        const activeDTCs = getActiveDTCs();
        if (!activeDTCs.find(x => x.code === code)) {
          activeDTCs.push(d.dtc);
          updateDTCs(activeDTCs);
        }
        toast(`Injected ${code}`);
      }
    };
    grid.appendChild(b);
  });
}

// ════════════════════════════════════════
//  Expose functions to HTML onclick handlers
//  ES modules are scoped — functions defined here aren't on the
//  global window object by default. But HTML onclick="fn()" looks
//  for functions on window, so we explicitly assign them.
// ════════════════════════════════════════
window.connectCar = connectCar;
window.clearDTCs = clearDTCs;
window.resetCamera = resetCamera;
window.toggleWireframe = toggleWireframe;
window.toggleExplode = () => toggleExplode(toast);  // Pass toast so scene.js can show messages
window.showAll = showAll;

// ════════════════════════════════════════
//  Boot
//  Initialize the 3D scene and build the demo inject buttons.
//  This runs when the browser loads this module.
// ════════════════════════════════════════
initThree();
buildInjectButtons();

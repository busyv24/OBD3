// ════════════════════════════════════════
//  scene.js — All Three.js / 3D related code
//
//  This module owns everything that touches the 3D viewport:
//  - Scene setup (camera, lights, renderer, controls)
//  - Loading the GLB car model
//  - Part highlighting when a DTC is selected
//  - Camera animations (fly-to, reset)
//  - Visual toggles (wireframe, explode view)
//
//  It exports functions that other modules call,
//  and keeps all Three.js internals private.
// ════════════════════════════════════════

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ── Private state (only this module can access these) ────────────────────────
// These variables are "module-scoped" — no other file can read or modify them
// directly. This prevents accidental changes from other parts of the app.
let scene, camera, renderer, controls, animId;
let engineModel = null;     // The loaded 3D car model
let partMeshes = {};        // Map of part name -> mesh object (for highlighting)
let originalMaterials = {};
let exploded = false;       // Whether explode view is active
let explodeOffsets = {};
let wireframeOn = false;

// ── Shared state ─────────────────────────────────────────────────────────────
// These are needed by multiple modules (main.js, obd.js), so we expose them
// through getter/setter functions. This is a common pattern in ES modules —
// instead of exposing the variable directly, you expose controlled access to it.
let selectedDTC = null;
export function getSelectedDTC() { return selectedDTC; }
export function setSelectedDTC(val) { selectedDTC = val; }

let activeDTCs = [];
export function getActiveDTCs() { return activeDTCs; }
export function setActiveDTCs(val) { activeDTCs = val; }

// ── Part definitions ─────────────────────────────────────────────────────────
// These define the procedural engine parts (name, position, size, color).
// Currently used by highlighting and explode-view logic to know which meshes
// exist and where they belong. These map to the DTC_TO_PART keys in server.py.
const PARTS_DEF = [
  { name:"Engine_Block",         pos:[0,0,0],           size:[1.4,0.9,1.8],  color:0x2a3a4a, label:"Engine Block"             },
  { name:"Crankshaft_Sensor",    pos:[0.71,0.1,0.4],    size:[0.12,0.2,0.15], color:0x334455, label:"Crankshaft Sensor"        },
  { name:"Camshaft_Sensor",      pos:[0,0.46,0.5],      size:[0.14,0.12,0.14],color:0x334455, label:"Camshaft Sensor"          },
  { name:"Throttle_Body",        pos:[0,0.65,0.6],      size:[0.5,0.35,0.4],  color:0x2e4060, label:"Throttle Body"            },
  { name:"MAF_Sensor",           pos:[0,0.72,1.1],      size:[0.18,0.22,0.35],color:0x334455, label:"Mass Airflow Sensor"      },
  { name:"Fuel_Injector",        pos:[0.55,0.3,0],      size:[0.1,0.45,0.6],  color:0x2d4558, label:"Fuel Injectors"           },
  { name:"Catalytic_Converter",  pos:[0,-0.3,-1.2],     size:[0.5,0.4,0.9],   color:0x3a3520, label:"Catalytic Converter"      },
  { name:"O2_Sensor_Front",      pos:[0.26,-0.25,-0.75],size:[0.1,0.1,0.2],   color:0x334444, label:"O2 Sensor (Front)"        },
  { name:"O2_Sensor_Rear",       pos:[0.26,-0.25,-1.65],size:[0.1,0.1,0.2],   color:0x334444, label:"O2 Sensor (Rear)"         },
  { name:"EGR_Valve",            pos:[-0.72,0.25,0.1],  size:[0.22,0.28,0.22],color:0x353525, label:"EGR Valve"                },
  { name:"Coolant_Temp_Sensor",  pos:[-0.55,0.45,-0.3], size:[0.1,0.16,0.1],  color:0x334455, label:"Coolant Temp Sensor"      },
];

// ── Severity color maps ──────────────────────────────────────────────────────
// When a part is highlighted due to a DTC, it glows a color based on severity.
// SEV_COLORS = the main color, EMISSIVE = the glow/emission color.
const SEV_COLORS = {
  critical: 0xff2d55,
  high:     0xff6b35,
  medium:   0xffd700,
  low:      0x00e676,
};

const EMISSIVE = {
  critical: 0xff0033,
  high:     0xff4400,
  medium:   0xcc9900,
  low:      0x00aa44,
};

// ════════════════════════════════════════
//  Scene initialization
//  Called once at boot from main.js. Sets up the entire 3D environment.
// ════════════════════════════════════════
export function initThree() {
  const canvas = document.getElementById('three-canvas');
  const vp = document.getElementById('viewport');

  // Create the scene — this is the "world" that holds all 3D objects
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x090c10);
  scene.fog = new THREE.Fog(0x090c10, 12, 30);  // Fog fades distant objects

  // Camera — the "eye" looking into the scene
  // PerspectiveCamera(fieldOfView, aspectRatio, nearClip, farClip)
  camera = new THREE.PerspectiveCamera(45, vp.clientWidth / vp.clientHeight, 0.01, 100);
  camera.position.set(0, 1.8, 4.5);  // Starting position (x, y, z)

  // Renderer — converts the 3D scene into 2D pixels on the canvas
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));  // Cap at 2x for performance
  renderer.setSize(vp.clientWidth, vp.clientHeight);
  renderer.shadowMap.enabled = true;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;  // Cinematic color mapping
  renderer.toneMappingExposure = 1.1;

  // Lights — without these, everything would be black
  const ambient = new THREE.AmbientLight(0x203050, 1.5);  // Soft overall light
  scene.add(ambient);
  const key = new THREE.DirectionalLight(0x80c8ff, 2);    // Main directional light
  key.position.set(3, 5, 4);
  key.castShadow = true;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x4060a0, 0.8);  // Fill light (opposite side)
  fill.position.set(-3, 2, -3);
  scene.add(fill);
  const rim = new THREE.DirectionalLight(0x00d4ff, 0.4);   // Rim/edge light
  rim.position.set(0, -2, -5);
  scene.add(rim);

  // Grid — the floor grid lines
  const grid = new THREE.GridHelper(20, 40, 0x1e2d3d, 0x1e2d3d);
  grid.position.y = -0.8;
  scene.add(grid);

  // OrbitControls — lets the user click-drag to rotate/zoom the camera
  controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;     // Smooth deceleration when dragging
  controls.dampingFactor = 0.08;
  controls.minDistance = 1;          // Can't zoom closer than 1 unit
  controls.maxDistance = 12;         // Can't zoom further than 12 units
  controls.target.set(0, 0.5, 0);   // Point the camera looks at

  // Resize handler — keeps the 3D view correct when window size changes
  window.addEventListener('resize', onResize);

  // Load the 3D car model and start the render loop
  loadCarModel();
  animate();
}

// ════════════════════════════════════════
//  Model loading
//  Uses GLTFLoader to fetch and display the .glb car model.
//  This is asynchronous — the model loads in the background.
// ════════════════════════════════════════
function loadCarModel() {
  const loader = new GLTFLoader();

  loader.load('/static/models/2000_Honda_Civic_Type_R.glb',
    // onSuccess — called when the model finishes loading
    function(gltf) {
      engineModel = gltf.scene;          // Store reference for other functions
      scene.add(gltf.scene);             // Add to the 3D world so it renders
      document.getElementById('loading').style.display = 'none';  // Hide spinner
    },
    // onProgress — we don't need progress tracking, so undefined
    undefined,
    // onError — if loading fails, log it so we can debug
    function(error) {
      console.error('GLB load error:', error);
    }
  );
}

// ════════════════════════════════════════
//  Animation loop
//  This runs ~60 times per second (every frame). It:
//  1. Updates the orbit controls (smooth damping)
//  2. Auto-rotates the model when no DTC is selected
//  3. Renders the scene to the canvas
// ════════════════════════════════════════
function animate() {
  animId = requestAnimationFrame(animate);  // Schedule next frame
  controls.update();
  // Slow auto-rotate when nothing is selected
  if (!selectedDTC && engineModel) {
    engineModel.rotation.y += 0.002;
  }
  renderer.render(scene, camera);
}

// Called when the browser window resizes — updates camera and renderer to match
function onResize() {
  const vp = document.getElementById('viewport');
  camera.aspect = vp.clientWidth / vp.clientHeight;
  camera.updateProjectionMatrix();  // Must be called after changing aspect
  renderer.setSize(vp.clientWidth, vp.clientHeight);
}

// ════════════════════════════════════════
//  Part highlighting
//  When a DTC is selected, this makes the affected part glow
//  and fades out all other parts so you can focus on the problem.
// ════════════════════════════════════════
export function highlightPart(partName, severity = 'high') {
  if (!engineModel) return;
  engineModel.rotation.y = 0;  // Stop spinning so user can see the part

  scene.traverse(obj => {
    if (!obj.isMesh || !partMeshes[obj.name]) return;
    const mat = obj.material;
    if (obj.name === partName) {
      // Highlight the selected part with severity color + glow
      mat.color.setHex(SEV_COLORS[severity] || 0xff4400);
      mat.emissive.setHex(EMISSIVE[severity] || 0xff2200);
      mat.emissiveIntensity = 0.8;
      mat.opacity = 1.0;
      mat.transparent = false;
    } else {
      // Fade out all other parts
      mat.color.setHex(PARTS_DEF.find(p => p.name === obj.name)?.color || 0x334455);
      mat.emissive.setHex(0x000000);
      mat.emissiveIntensity = 0;
      mat.transparent = true;
      mat.opacity = 0.12;
    }
  });

  // Fly camera to the highlighted part
  const mesh = partMeshes[partName];
  if (mesh) flyTo(mesh);
}

// ════════════════════════════════════════
//  Show all parts
//  Resets all parts to their default appearance (no highlighting).
//  Called when DTCs are cleared or user clicks "show all".
// ════════════════════════════════════════
export function showAll() {
  selectedDTC = null;
  if (!engineModel) return;
  engineModel.rotation.y = 0;
  scene.traverse(obj => {
    if (!obj.isMesh || !partMeshes[obj.name]) return;
    const def = PARTS_DEF.find(p => p.name === obj.name);
    obj.material.color.setHex(def?.color || 0x334455);
    obj.material.emissive.setHex(0x000000);
    obj.material.emissiveIntensity = 0;
    obj.material.transparent = false;
    obj.material.opacity = 1.0;
  });
  document.querySelectorAll('.dtc-card').forEach(c => c.classList.remove('active'));
  document.getElementById('part-tooltip').classList.remove('show');
  resetCamera();
}

// ════════════════════════════════════════
//  Camera fly-to animation
//  Smoothly moves the camera to focus on a specific part.
//  Uses an ease-in-out curve for natural-looking movement.
// ════════════════════════════════════════
function flyTo(mesh) {
  // Calculate the bounding box of the mesh to find its center and size
  const box = new THREE.Box3().setFromObject(mesh);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  const offset = Math.max(size * 3, 2.5);  // How far back the camera should be

  const startPos = camera.position.clone();
  const endPos = center.clone().add(new THREE.Vector3(offset * 0.7, offset * 0.5, offset));
  let t = 0;
  const fly = () => {
    t = Math.min(t + 0.025, 1);
    // Ease-in-out: slow start, fast middle, slow end
    const e = t < 0.5 ? 2*t*t : -1+(4-2*t)*t;
    camera.position.lerpVectors(startPos, endPos, e);  // Interpolate position
    controls.target.lerp(center, e);                    // Interpolate look-at point
    controls.update();
    if (t < 1) requestAnimationFrame(fly);  // Keep animating until done
  };
  fly();

  // Show tooltip with DTC info for this part
  const dtc = activeDTCs.find(d => d.part === mesh.name);
  if (dtc) {
    document.getElementById('tt-code').textContent = dtc.code;
    document.getElementById('tt-name').textContent = dtc.label;
    document.getElementById('part-tooltip').classList.add('show');
  }
}

// ════════════════════════════════════════
//  Camera reset
//  Snaps camera back to the default overview position.
// ════════════════════════════════════════
export function resetCamera() {
  camera.position.set(0, 1.8, 4.5);
  controls.target.set(0, 0.5, 0);
  controls.update();
  document.getElementById('part-tooltip').classList.remove('show');
}

// ════════════════════════════════════════
//  Wireframe toggle
//  Switches all meshes between solid and wireframe rendering.
// ════════════════════════════════════════
export function toggleWireframe() {
  wireframeOn = !wireframeOn;
  scene.traverse(obj => {
    if (obj.isMesh) obj.material.wireframe = wireframeOn;
  });
}

// ════════════════════════════════════════
//  Explode view toggle
//  Spreads all parts outward from center so you can see
//  individual components, or collapses them back together.
//  Takes a toast function as parameter so it can show a message
//  without importing from main.js (avoids circular dependency).
// ════════════════════════════════════════
export function toggleExplode(toast) {
  exploded = !exploded;
  scene.traverse(obj => {
    if (!obj.isMesh || !partMeshes[obj.name]) return;
    const def = PARTS_DEF.find(p => p.name === obj.name);
    if (!def) return;
    const [bx, by, bz] = def.pos;
    // Exploded: move each part 2.2x further from center
    // Collapsed: move back to original position
    const target = exploded
      ? new THREE.Vector3(bx * 2.2, by * 2.2, bz * 2.2)
      : new THREE.Vector3(bx, by, bz);
    let t = 0;
    const from = obj.position.clone();
    const anim = () => {
      t = Math.min(t + 0.04, 1);
      const e = t < 0.5 ? 2*t*t : -1+(4-2*t)*t;
      obj.position.lerpVectors(from, target, e);
      if (t < 1) requestAnimationFrame(anim);
    };
    anim();
  });
  toast(exploded ? 'Exploded view' : 'Collapsed view');
}

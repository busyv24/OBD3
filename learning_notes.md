# OBD3 Project - Learning Notes

## Debugging Session: GLB File Not Working

### Lesson 1: File vs Directory
- A `.glb` file is a single binary file (GL Binary format for 3D models)
- If your `.glb` "file" is actually a directory/folder, the browser can't load it as a 3D model
- When downloading models from sites like Sketchfab, the download is a `.zip` archive that extracts into a folder structure (with `source/`, `textures/`, etc.)
- You need the actual `.glb` file inside that folder, not the folder itself

### Lesson 2: Imported But Never Used
- Just because you import a library (like `GLTFLoader`) doesn't mean it's being used
- Always trace the code path: import -> instantiation -> actual function call
- A good debugging step is to search for where something is actually *called*, not just *imported*

### Lesson 3: Debugging Approach - Follow the Data Path
When a 3D model isn't showing up, trace the full pipeline:
1. **Does the file exist?** Check the actual file on disk (`ls -la`)
2. **Is it being requested?** Check the browser Network tab for the request
3. **Is the loader code actually running?** Search for where the loader is called
4. **Is the path correct?** Compare what the code requests vs where the file actually lives

### Lesson 4: Browser DevTools Are Your Best Friend
- **Console tab**: Shows JavaScript errors (e.g., 404 for missing model files)
- **Network tab**: Shows all HTTP requests — you can see if the GLB file is being fetched and whether it succeeds or fails
- **Sources tab**: You can set breakpoints in JavaScript to see if loader code is ever reached

### Lesson 5: Procedural Geometry vs Loaded Models
- Three.js can create shapes programmatically (BoxGeometry, SphereGeometry, etc.) — this is "procedural"
- It can also load external 3D model files (.glb, .gltf, .obj, etc.) using loaders
- These are two completely different code paths — if your code builds procedural boxes, it will never touch a GLB file

### Lesson 6: GLB is Self-Contained
- GLB (GL Binary) bundles geometry, materials, AND textures into one file
- GLTF (the text version) needs external texture files — GLB does not
- When you download from Sketchfab, the textures folder was used to build the GLB, but you don't need to serve them separately

### Lesson 7: "Make It Work, Make It Right, Make It Fast"
- Fix the bug first, refactor second
- Refactoring while something is broken means you're changing two things at once — if it breaks worse, you won't know which change caused it
- Get to a working state, commit it, THEN reorganize
- This applies everywhere: don't optimize code that doesn't work yet

### Lesson 8: Separation of Concerns (for later)
- A single 900-line HTML file with all JS inline is hard to maintain
- Split JS into separate files by responsibility (e.g., 3D setup, OBD client, UI updates)
- server.py: don't mix top-level script code (lines that run on import) with your FastAPI app definition
- Each file/module should do ONE thing well

### Lesson 9: Dead Code
- `MODEL_LIBRARY` in server.py was defined but never used — that's dead code
- Dead code is confusing because future-you will wonder "is this important?"
- Delete it or use it, don't leave it sitting around

### Lesson 10: ES Modules vs Classic Scripts
- Older Three.js versions used `<script>` tags that put everything on the global `THREE` object
- Modern Three.js (r150+) uses ES modules — you import with `import * as THREE from 'three'`
- The CDN path changes: `examples/js/` (old) -> `examples/jsm/` (new, ES module versions)
- You need a `<script type="importmap">` to tell the browser where to find the modules
- Your main `<script>` tag must have `type="module"` to use `import` statements

### Lesson 11: ES Module Scoping
- Functions in a `<script type="module">` are NOT globally available
- HTML `onclick="myFunction()"` won't find functions defined inside a module
- Fix: explicitly assign them to the window object — `window.myFunction = myFunction`
- This is a common gotcha when migrating from classic scripts to modules

### Lesson 12: Async Loading (Callbacks)
- `GLTFLoader.load()` is asynchronous — it starts a download and returns immediately
- You must use callbacks to handle the result: `loader.load(url, onSuccess, onProgress, onError)`
- The loaded model is at `gltf.scene` inside the success callback
- Always include an error callback — without it, failures are silent and you'll have no idea what went wrong
- Don't put code that depends on the loaded model OUTSIDE the callback — it will run before loading finishes

### Lesson 13: Static File URL Paths
- FastAPI mounts static files at a URL prefix (e.g., `/static`)
- The file at `static/models/car.glb` on disk is served at `/static/models/car.glb` in the browser
- Always use a leading `/` for absolute paths — without it, the browser resolves relative to the current page URL

---

## General Web Dev Debugging Tips
- When something "doesn't work," define what "not working" means: Is it a blank screen? Wrong model? Console error?
- Always check the browser console first (Cmd+Option+J on Mac / Ctrl+Shift+J on Windows)
- Read error messages carefully — they usually tell you exactly what's wrong
- When working with static files in a web server (like FastAPI), the URL path must match the file's actual location in the static directory

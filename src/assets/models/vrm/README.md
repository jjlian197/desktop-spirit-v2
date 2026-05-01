# VRM Models

This folder is the runtime asset directory for the VRM/Three.js renderer.

The app can load:

- `.vrm`
- `.glb`
- `.gltf`

The current desktop sprite is configured to use:

- `src/assets/models/vrm/鸣潮-爱弥斯.glb`

## Current workflow

For Blender-origin models, the most reliable path in this repo is:

1. Keep the original source file here, usually `.blend` or `.pmx`.
2. Export a cleaned `.glb` into this same folder.
3. Point `config.yaml` at the exported `.glb`.
4. Start the app with `pythonw src/main.py`.

## Blend to GLB

This project includes a Blender export helper that:

- relinks missing textures by filename
- simplifies key character materials before export
- exports only the main armature and its child meshes

Command:

```powershell
& 'D:\Program Files (x86)\Blender\blender.exe' -b 'c:\Users\lianj\Python\desktop-spirit-v2-windows\src\assets\models\vrm\your_model.blend' -P 'c:\Users\lianj\Python\desktop-spirit-v2-windows\tools\export_blend_to_glb.py' -- 'c:\Users\lianj\Python\desktop-spirit-v2-windows\src\assets\models\vrm\your_model.glb'
```

## PMX to GLB

This repo also includes a PMX export helper. It expects a checkout of
`blender_mmd_tools` under:

- `.tmp/blender_mmd_tools`

That helper:

- loads `mmd_tools` at runtime
- imports the PMX model in Blender background mode
- exports it as `.glb`

Command:

```powershell
& 'D:\Program Files (x86)\Blender\blender.exe' --factory-startup -b -P 'c:\Users\lianj\Python\desktop-spirit-v2-windows\tools\export_pmx_to_glb.py' -- 'c:\Users\lianj\Python\desktop-spirit-v2-windows\src\assets\models\vrm\your_model.pmx' 'c:\Users\lianj\Python\desktop-spirit-v2-windows\src\assets\models\vrm\your_model.glb'
```

## Notes

- Some original Blender materials in game-style or MMD-style assets do not map
  cleanly to glTF. The export helper rebuilds the key face/body/hair materials
  into simpler realtime-friendly materials before export.
- If the model shape is correct but textures are missing, check whether the
  original `.blend` references textures outside the repo and rerun the export
  helper after placing those textures under this folder tree.

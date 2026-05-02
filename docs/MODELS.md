# Model Setup

## Live2D Models

Live2D provides free sample models for development:

### Download Sample Models

Visit: https://www.live2d.com/en/learn/sample/

Recommended models for Sherry:
- **Hiyori Momose** - Full body, expressions, physics
- **Haru** - Receptionist character, outfit changes
- **Epsilon** - Simple, beginner-friendly
- **Kei** - Motion-sync (lip-sync) support

### Model Structure

After downloading, extract the `runtime` folder contents:

```
src/assets/models/
└── hiyori/
    ├── hiyori.model3.json
    ├── hiyori.moc3
    ├── hiyori.physics3.json
    ├── hiyori.pose3.json
    ├── hiyori.cdi3.json
    ├── textures/
    │   ├── texture_00.png
    │   └── texture_01.png
    ├── motions/
    │   └── hiyori_m01.motion3.json
    └── expressions/
        └── f01.exp3.json
```

### Configuration

Update `config.yaml`:

```yaml
sprite:
  renderer: live2d
  model:
    path: "src/assets/models/hiyori"
    default_expression: "normal"
```

---

## VRM / GLB (3D Models)

3D character models are rendered using Three.js via QWebEngine. This allows Blender-exported characters (VRM, GLB, GLTF) to run as desktop sprites with bone-based gestures, eye tracking, and lip sync.

### Prerequisites

- **Windows**: PyQt6-WebEngine (included in standard PyQt6 install)
- **Blender 3.0+** with VRM Addon (for VRM export) or standard GLB/GLTF export

### Blender Export

Use `tools/export_blend_to_glb.py` to export from Blender with pre-configured material simplification:

```bash
blender -b your_model.blend -P tools/export_blend_to_glb.py -- output.glb
```

Supported formats:
- `glb` — glTF Binary (default, recommended)
- `vrm` — VRM 1.0 (requires VRM Addon for Blender)

The export script:
1. Relinks missing textures from the blend file's directory
2. Simplifies character materials (assigns base color + alpha textures to Principled BSDF)
3. Collects all objects rigged to the primary armature
4. Deletes flat/large Plane meshes used as stages

### Model Directory

Place VRM/GLB files in `src/assets/models/vrm/`:

```
src/assets/models/vrm/
├── your-model.glb
├── another-model.vrm
└── ...
```

### Configuration

In `config.yaml`:

```yaml
sprite:
  renderer: vrm
  vrm:
    path: src/assets/models/vrm/your-model.glb
```

### Bone Naming

The Three.js viewer detects bones by scanning common naming patterns. Models using standard game rigs (e.g., 鸣潮's Bip001 skeleton) are supported automatically.

Detected bones:
| Part | Search Patterns |
|------|-----------------|
| Head | head, _head, Head, Neck (if no head) |
| Neck | neck, _neck, Neck |
| Spine/Chest | spine, chest, Spine, Bip001Spine, Bip001Neck |
| Hips | hips, pelvis, Pelvis, Bip001Pelvis |
| Shoulders | shoulder, Shoulder |
| Upper Arms | upperarm, upper_arm, UpperArm, LUpperArm, RUpperArm |
| Forearms/Elbows | forearm, elbow, Elbow, LForearm, RForearm, Facial_Elbow_a_01_L |
| Wrists/Hands | wrist, hand, Wrist, Hand, LHand, RHand |

### Rendering Features

| Feature | Live2D | VRM/GLB |
|---------|--------|---------|
| Expressions | Yes | Yes (mapped) |
| Motion playback | Yes (motion3.json) | Yes (built-in + procedural) |
| Idle breathing | Yes | Yes |
| Eye tracking | Yes (parametric) | Yes (bone-based) |
| Lip sync | Yes | Yes (ParamMouthOpenY) |
| Background | Color/gradient/image | Color/gradient/image |

### Switching Renderers

Right-click the sprite → **Renderer** submenu:
- **Blender / 3D Model** — loads VRM/GLB models
- **Live2D / 2D Model** — loads Live2D models
- **Blender Model** → submenu lists all `.glb` / `.vrm` / `.gltf` files found in `src/assets/models/vrm/`

Or change `config.yaml` and restart.

---

## Expression Mapping

### Live2D

Expression files use the `.exp3.json` filename (without extension):

| Expression | File |
|------------|------|
| normal | f01.exp3.json |
| happy | f02.exp3.json |
| sad | f03.exp3.json |
| angry | f04.exp3.json |
| surprised | f05.exp3.json |

### VRM / GLB

Expressions are mapped to VRM blend shapes:

| Input Name | VRM Expression |
|------------|---------------|
| normal | neutral |
| happy | happy |
| sad | sad |
| angry | angry |
| love | relaxed |
| blush | happy |
| daze | surprised |
| surprised | surprised |
| sleepy | sleepy |

---

## Troubleshooting

### Live2D model not loading
- Check that `.model3.json` exists
- Verify file paths in config
- Check logs: `~/.sherry/sprite.log`

### VRM textures missing
- Re-export from Blender using `tools/export_blend_to_glb.py`
- Ensure textures are in the same directory as the blend file

### VRM model appears backwards
- Fixed: the viewer automatically corrects orientation for VRM files
- If still backwards, the source model may need rotation in Blender before export

### Stage/plane meshes visible
- The viewer filters out flat, large meshes (likely stage geometry)
- If still visible, check in Blender for objects named `Plane*` and delete them before export

### "Unknown motion: Idle" in logs
- Idle motion is handled by the SpriteBrain idle loop
- For VRM models, Idle is processed by `triggerMotion("idle")` which triggers procedural breathing/sway animation

### VRM idle motion plays when not wanted
- Idle motion is **automatically disabled** for VRM/GLB models
- Controlled by `sprite_brain.py:_detect_idle_motion_enabled()` reading `config.yaml`
- If renderer is `vrm`, Idle motion trigger is skipped (random blink and sigh still occur)

### Performance issues (VRM)
- Reduce model polygon count in Blender before export
- Use GLB instead of VRM for faster loading
- Disable eye tracking in right-click menu if laggy
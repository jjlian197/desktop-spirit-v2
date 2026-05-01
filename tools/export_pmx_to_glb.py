import bpy
import os
import sys
from pathlib import Path


def parse_args(argv):
    if "--" not in argv:
        raise SystemExit("Expected arguments after '--': <input.pmx> <output.glb>")
    args = argv[argv.index("--") + 1 :]
    if len(args) != 2:
        raise SystemExit(
            "Usage: blender -b -P tools/export_pmx_to_glb.py -- <input.pmx> <output.glb>"
        )
    return args[0], args[1]


def register_mmd_tools():
    project_root = Path(__file__).resolve().parents[1]
    addon_root = project_root / ".tmp" / "blender_mmd_tools"
    if not addon_root.exists():
        raise RuntimeError(f"mmd_tools repo not found: {addon_root}")

    sys.path.insert(0, str(addon_root))
    import mmd_tools

    mmd_tools.register()


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def import_pmx(filepath):
    result = bpy.ops.mmd_tools.import_model(
        filepath=filepath,
        types={"MESH", "ARMATURE", "MORPHS"},
        scale=0.08,
        clean_model=False,
        remove_doubles=False,
        log_level="INFO",
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"PMX import failed: {result}")


def export_glb(filepath):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format="GLB",
        use_selection=False,
        export_yup=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_animations=True,
        export_morph=True,
        export_skins=True,
        export_lights=False,
        export_cameras=False,
    )


def main():
    input_path, output_path = parse_args(sys.argv)
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    register_mmd_tools()
    clear_scene()
    import_pmx(input_path)
    export_glb(output_path)
    print(f"Exported GLB to: {output_path}")


if __name__ == "__main__":
    main()

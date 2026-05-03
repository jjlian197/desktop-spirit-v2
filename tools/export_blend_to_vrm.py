import os
import sys
from pathlib import Path

import bpy


class DummyError:
    def __init__(self):
        self.name = ""
        self.severity = 0
        self.message = ""


class DummyErrorCollection(list):
    def clear(self):
        del self[:]

    def add(self):
        item = DummyError()
        self.append(item)
        return item


def parse_args(argv):
    if "--" not in argv:
        raise SystemExit("Expected arguments after '--': <output.vrm>")
    args = argv[argv.index("--") + 1 :]
    if len(args) != 1:
        raise SystemExit(
            "Usage: blender -b <file.blend> -P tools/export_blend_to_vrm.py -- <output.vrm>"
        )
    return args[0]


def enable_vrm_addon():
    project_root = Path(__file__).resolve().parents[1]
    addon_src_root = project_root / ".tmp" / "VRM-Addon-for-Blender" / "src"
    if not addon_src_root.exists():
        raise RuntimeError(f"VRM addon source not found: {addon_src_root}")

    sys.path.insert(0, str(addon_src_root))
    import io_scene_vrm  # noqa: F401

    result = bpy.ops.preferences.addon_enable(module="io_scene_vrm")
    print(f"Addon enable result: {result}")

    from io_scene_vrm.external.io_scene_gltf2_support import export_scene_gltf as original_export_scene_gltf
    from io_scene_vrm.exporter import vrm1_exporter

    def patched_export_scene_gltf(arguments):
        result = original_export_scene_gltf(arguments)
        print(f"glTF export attempt result: {result}")
        if result != {"CANCELLED"}:
            return result

        retries = [
            {
                "export_armature_object_remove": False,
                "export_animations": False,
            },
            {
                "export_armature_object_remove": False,
                "export_animations": False,
                "use_selection": False,
            },
        ]
        for retry in retries:
            for key, value in retry.items():
                setattr(arguments, key, value)
            print(f"Retrying glTF export with: {retry}")
            retry_result = original_export_scene_gltf(arguments)
            print(f"glTF retry result: {retry_result}")
            if retry_result == {"FINISHED"}:
                return retry_result
        return result

    vrm1_exporter.export_scene_gltf = patched_export_scene_gltf


def find_primary_armature():
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    if not armatures:
        raise RuntimeError("No armature found in blend file")
    return max(armatures, key=lambda obj: len(obj.children_recursive))


def uses_armature(obj, armature_obj):
    if obj == armature_obj:
        return True
    if obj.parent == armature_obj:
        return True
    for modifier in getattr(obj, "modifiers", []):
        if modifier.type == "ARMATURE" and getattr(modifier, "object", None) == armature_obj:
            return True
    return False


def select_character_objects(armature_obj):
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    selected = [armature_obj]
    for obj in bpy.data.objects:
        if obj.type == "MESH" and uses_armature(obj, armature_obj):
            obj.select_set(True)
            selected.append(obj)
        elif obj.parent == armature_obj and obj.type == "EMPTY":
            obj.select_set(True)
            selected.append(obj)
    bpy.context.view_layer.objects.active = armature_obj
    print("Selected export objects:")
    for obj in selected:
        print(f"  {obj.type} {obj.name}")


def configure_armature_for_vrm(armature_obj):
    select_character_objects(armature_obj)

    ext = armature_obj.data.vrm_addon_extension
    ext.spec_version = ext.SPEC_VERSION_VRM1
    print(f"Using armature: {armature_obj.name}")
    print(f"Spec version: {ext.spec_version}")

    result = bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically(
        armature_object_name=armature_obj.name
    )
    print(f"Auto human bone assignment: {result}")

    try:
        expr_result = bpy.ops.vrm.assign_vrm1_expressions_automatically(
            armature_object_name=armature_obj.name
        )
        print(f"Auto expression assignment: {expr_result}")
    except Exception as exc:
        print(f"Auto expression assignment failed: {exc}")

    human_bones = ext.vrm1.humanoid.human_bones
    assigned_ok = human_bones.bones_are_correctly_assigned()
    print(f"Human bones correctly assigned: {assigned_ok}")

    if not assigned_ok:
        human_bones.allow_non_humanoid_rig = True
        print("Enabled allow_non_humanoid_rig fallback")

    try:
        t_pose_result = bpy.ops.vrm.make_estimated_humanoid_t_pose(
            armature_name=armature_obj.name
        )
        print(f"Estimated T-pose: {t_pose_result}")
    except Exception as exc:
        print(f"Estimated T-pose failed: {exc}")

    validate_result = bpy.ops.vrm.model_validate(
        armature_object_name=armature_obj.name,
        show_successful_message=False,
    )
    print(f"Model validate: {validate_result}")

    from io_scene_vrm.editor.validation import WM_OT_vrm_validator

    collected_errors = DummyErrorCollection()
    has_errors = WM_OT_vrm_validator.detect_errors(
        bpy.context,
        collected_errors,
        armature_obj.name,
        execute_migration=True,
    )
    print(f"Validator has hard errors: {has_errors}")
    for error in collected_errors:
        print(f"VALIDATION severity={error.severity} message={error.message}")


def export_vrm(output_path):
    from io_scene_vrm.common.preferences import get_preferences
    from io_scene_vrm.exporter.export_scene import _export_vrm

    preferences = get_preferences(bpy.context)
    preferences.export_only_selections = True
    preferences.export_invisibles = False
    preferences.export_lights = False

    active_armature = bpy.context.view_layer.objects.active
    armature_name = active_armature.name if active_armature else ""
    result = _export_vrm(
        Path(output_path),
        preferences,
        bpy.context,
        armature_object_name=armature_name,
    )
    print(f"VRM export result: {result}")
    if "FINISHED" not in result:
        raise RuntimeError(f"VRM export failed: {result}")


def main():
    output_path = os.path.abspath(parse_args(sys.argv))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    enable_vrm_addon()
    armature_obj = find_primary_armature()
    configure_armature_for_vrm(armature_obj)
    export_vrm(output_path)
    print(f"Exported VRM to: {output_path}")


if __name__ == "__main__":
    main()

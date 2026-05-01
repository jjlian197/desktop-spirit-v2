import bpy
import os
import sys
from pathlib import Path


def parse_args(argv):
    if "--" not in argv:
        raise SystemExit("Expected arguments after '--': <output.glb>")
    args = argv[argv.index("--") + 1 :]
    if len(args) != 1:
        raise SystemExit("Usage: blender -b <file.blend> -P tools/export_blend_to_glb.py -- <output.glb>")
    return args[0]


def relink_missing_images():
    blend_path = Path(bpy.data.filepath).resolve()
    search_roots = [blend_path.parent]
    search_roots.extend(p for p in blend_path.parent.iterdir() if p.is_dir())

    def image_basename(filepath, fallback_name):
        if not filepath:
            return fallback_name
        normalized = filepath.replace("\\", "/")
        return normalized.split("/")[-1] or fallback_name

    texture_index = {}
    for root in search_roots:
        for path in root.rglob("*"):
            if path.is_file():
                texture_index.setdefault(path.name.lower(), path)

    relinked = 0
    for image in bpy.data.images:
        raw_path = bpy.path.abspath(image.filepath) if image.filepath else ""
        needs_relink = (not image.has_data) or (raw_path and not os.path.exists(raw_path))
        if not needs_relink:
            continue

        filename = image_basename(image.filepath, image.name)
        match = texture_index.get(filename.lower())
        if not match:
            continue

        image.filepath = str(match)
        try:
            image.reload()
            relinked += 1
        except RuntimeError:
            pass

    print(f"Relinked images: {relinked}")


def find_texture_file(filename):
    blend_path = Path(bpy.data.filepath).resolve()
    for path in blend_path.parent.rglob(filename):
        if path.is_file():
            return path
    return None


def load_image_cached(filepath, cache):
    key = str(filepath).lower()
    if key in cache:
        return cache[key]
    image = bpy.data.images.load(str(filepath), check_existing=True)
    cache[key] = image
    return image


def make_simple_material(name, base_texture, alpha_texture=None, cache=None):
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    tex = nodes.new("ShaderNodeTexImage")
    tex.location = (-250, 120)
    tex.image = load_image_cached(base_texture, cache)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    if alpha_texture is not None:
        alpha = nodes.new("ShaderNodeTexImage")
        alpha.location = (-250, -80)
        alpha.image = load_image_cached(alpha_texture, cache)
        links.new(alpha.outputs["Color"], bsdf.inputs["Alpha"])
        material.blend_method = "CLIP"
        if hasattr(material, "shadow_method"):
            material.shadow_method = "CLIP"
        material.alpha_threshold = 0.1
    else:
        material.blend_method = "OPAQUE"

    return material


def simplify_character_materials():
    cache = {}
    rules = {
        "MI_R2T1AimisiMd10011Face": ("T_R2T1AimisiMd10011Face_D.png", None),
        "MI_R2T1AimisiMd10011Up01": ("T_R2T1AimisiMd10011Up01_D.png", None),
        "MI_R2T1AimisiMd10011Down01": ("T_R2T1AimisiMd10011Down01_D.png", None),
        "MI_R2T1AimisiMd10011Hair": ("T_R2T1AimisiMd10011Hair_D.png", "T_R2T1AimisiMd10011Hair_alpha.png"),
        "MI_R2T1AimisiMd10011Bangs": ("T_R2T1AimisiMd10011Bangs_D.png", "T_R2T1AimisiMd10011Bangs_alpha.png"),
        "MI_R2T1AimisiMd10011Eye": ("T_R2T1AimisiMd10011Eye_D.png", "T_R2T1AimisiMd10011Eye_alpha.png"),
        "MI_R2T1AimisiMd10011Item": ("T_R2T1AimisiMd10011Item_D.png", None),
        "MI_R2T1AimisiMd10011Fx01": ("T_R2T1AimisiMd10011Fx01_D.png", None),
    }

    built = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if obj.name not in rules:
            continue

        base_name, alpha_name = rules[obj.name]
        base_path = find_texture_file(base_name)
        alpha_path = find_texture_file(alpha_name) if alpha_name else None
        if not base_path:
            continue

        if obj.name not in built:
            built[obj.name] = make_simple_material(
                name=f"{obj.name}_Simple",
                base_texture=base_path,
                alpha_texture=alpha_path,
                cache=cache,
            )

        obj.data.materials.clear()
        obj.data.materials.append(built[obj.name])

    print(f"Simplified materials: {len(built)}")


def main():
    output_path = parse_args(sys.argv)
    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    relink_missing_images()
    simplify_character_materials()

    bpy.ops.object.select_all(action="DESELECT")

    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    if armatures:
        primary_armature = max(armatures, key=lambda obj: len(obj.children_recursive))
        export_objects = [primary_armature] + list(primary_armature.children_recursive)
    else:
        export_objects = list(bpy.data.objects)

    for obj in export_objects:
        obj.select_set(True)

    if armatures:
        bpy.context.view_layer.objects.active = primary_armature

    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_tangents=False,
        export_materials="EXPORT",
        export_animations=True,
        export_morph=True,
        export_skins=True,
        export_lights=False,
        export_cameras=False,
    )
    print(f"Exported GLB to: {output_path}")


if __name__ == "__main__":
    main()

import bpy


def main():
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    print(f"ARMATURES {len(armatures)}")
    for arm in armatures:
        print(f"ARMATURE {arm.name}")
        print(f"  children_recursive={len(arm.children_recursive)}")
        if arm.data and hasattr(arm.data, "bones"):
            deform_bones = [bone for bone in arm.data.bones if bone.use_deform]
            print(f"  bones={len(arm.data.bones)} deform_bones={len(deform_bones)}")
            for bone in deform_bones[:20]:
                print(f"    BONE {bone.name}")

        linked_meshes = []
        for obj in bpy.data.objects:
            if obj.type != "MESH":
                continue
            for modifier in getattr(obj, "modifiers", []):
                if modifier.type == "ARMATURE" and getattr(modifier, "object", None) == arm:
                    linked_meshes.append(obj)
                    break

        print(f"  armature_modifier_meshes={len(linked_meshes)}")
        for obj in linked_meshes[:50]:
            parent_name = obj.parent.name if obj.parent else None
            bone_names = {bone.name for bone in arm.data.bones}
            group_names = [group.name for group in obj.vertex_groups]
            matched_groups = [name for name in group_names if name in bone_names]
            print(
                f"    MESH {obj.name} parent={parent_name} "
                f"vertex_groups={len(obj.vertex_groups)} shape_keys="
                f"{len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0} "
                f"matched_groups={len(matched_groups)}"
            )
            if matched_groups:
                print(f"      sample_matched={matched_groups[:10]}")
            else:
                print(f"      sample_groups={group_names[:10]}")


if __name__ == "__main__":
    main()

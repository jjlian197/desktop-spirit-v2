import bpy
for obj in bpy.data.objects:
    if obj.type in {'MESH','ARMATURE','EMPTY','LIGHT'}:
        print(obj.type, obj.name, 'parent=' + (obj.parent.name if obj.parent else 'None'))

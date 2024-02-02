# bl_info = {
#     "name" : "Adjust Bone to Shape",
#     "author" : "Estasleyendoesto",
#     "description" : "Inverse bone alignment to shape using Weights",
#     "blender" : (4, 0, 0),
#     "version" : (1, 0, 0),
#     "location" : "Edit Mode > Sidebar > Item",
#     "warning" : "",
#     "category" : "Rigging"
# }

import bpy
from mathutils import Vector

def filter_object_by_bone(self, obj):
    return (
        obj.type == 'MESH' and 
        obj.parent and 
        obj.parent.type == 'ARMATURE' and 
        obj.parent == bpy.context.active_object
    )

class BoneToShapeProps(bpy.types.PropertyGroup):
    custom_groups: bpy.props.BoolProperty(name="Custom Group", options=set())
    target: bpy.props.PointerProperty(
        type = bpy.types.Object,
        poll = filter_object_by_bone
    )
    vertex_group: bpy.props.StringProperty()
    alignment: bpy.props.EnumProperty(
        items = (
            ('HEAD', "Head", ""),
            ('CENTER', "Center", ""),
            ('TAIL', "Tail", "")
        ),
        default = 'CENTER'
    )
    head: bpy.props.StringProperty()
    tail: bpy.props.StringProperty()

class BoneToShapePanel(bpy.types.Panel):
    bl_label = "Bone to Shape"
    bl_idname = "BONE_PT_bone_to_shape"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"

    @classmethod
    def poll(cls, context):
        return (
            context.object is not None and context.mode == 'EDIT_ARMATURE'
        )
        
    def call_operator(self, layout, bs_props, bone):
        layout.prop(bs_props, 'alignment', expand=True)
        op = layout.operator('bs.to_shape')
        op.bone_name = bone.name
        op.object_name = bs_props.target.name
        op.vertex_group = bs_props.vertex_group
        op.custom_groups = bs_props.custom_groups
        op.alignment = bs_props.alignment
    
    def draw(self, context):
        rig = context.object
        curr_bone = rig.data.edit_bones.active
        bs_props = context.scene.bs_props
        has_group = bs_props.target.vertex_groups.get(curr_bone.name, None)

        layout = self.layout
        box = layout.box()
        row = box.row()
        row.alignment = 'CENTER'
        
        # Rig Info label
        row.label(text=rig.name, icon='ARMATURE_DATA')
        
        if bs_props.target:
            vertex_group = has_group
            if not vertex_group:
                row.alert = True

        # Bone Info label
        row.label(text=curr_bone.name, icon='BONE_DATA')
        
        # No animation
        layout.use_property_decorate = False
        
        # Mesh object search
        box = layout.box()
        box.prop_search(
            bs_props, 'target', context.scene, 'objects', text='Object'
        )
        
        # IF Target exists
        if bs_props.target:
            row = box.row()
            row.alignment = 'RIGHT'
            
            # Groups ON option
            row.prop(bs_props, 'custom_groups', event=False, text='Use Custom Group')
            
            if bs_props.custom_groups:
                box = box.box()
                box.active = False
                if bs_props.target.vertex_groups:
                    box.active = True
                    
                    # Groups search
                    row = box.row()
                    row.prop_search(
                        bs_props, 'vertex_group', bs_props.target, 'vertex_groups', text='Group'
                    )
                else:
                    row = box.row()
                    row.alignment = 'CENTER'
                    
                    # No groups label
                    row.label(text='Mesh object has no vertex groups')
        
        # Operator condition
        if bs_props.custom_groups:
            exists = bs_props.target.vertex_groups.get(bs_props.vertex_group, None)
            if exists:
                # Operator
                self.call_operator(layout, bs_props, curr_bone)
        else:
            if has_group:
                box = layout.box()
                row = box.row()
                row.alignment = 'CENTER'
                # Vertex group info label
                row.label(text=has_group.name, icon='GROUP_VERTEX')
                # Operator
                self.call_operator(layout, bs_props, curr_bone)

class BoneToShapeOP(bpy.types.Operator):
    '''Align bones to shape usign vertex groups'''
    bl_idname = "bs.to_shape"
    bl_label = "Align"

    head: bpy.props.StringProperty()
    tail: bpy.props.StringProperty()
    bone_name: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()
    vertex_group: bpy.props.StringProperty()
    custom_groups: bpy.props.BoolProperty()
    alignment: bpy.props.EnumProperty(
        items = (
            ('HEAD', "Head", ""),
            ('CENTER', "Center", ""),
            ('TAIL', "Tail", "")
        ),
        default = 'CENTER'
    )

    @classmethod
    def poll(cls, context):
        return (
            context.object is not None and context.mode == 'EDIT_ARMATURE'
        )
        
    def calc_center(self, object, group):
        center = [0, 0, 0]
        total_weight = 0
        for vert in object.data.vertices:
            for g in vert.groups:
                if g.group == group.index:
                    center = [c + g.weight * v for c, v in zip(center, object.matrix_world @ vert.co)]
                    total_weight += g.weight
        if total_weight:
            center = [c / total_weight for c in center]

        return center
    
    def center_bone(self, bone, center):
        center = Vector(center)
        bone_center = (bone.head + bone.tail) / 2 # Centro del hueso

        # Direccion del hueso
        bone_dir = bone.tail - bone.head
        bone_dir.normalize()
        
        # Position
        head = center - bone_dir * (bone_center - bone.head).length
        tail = center + bone_dir * (bone.tail - bone_center).length

        return head, tail 

    def execute(self, context):
        bone = context.object.data.edit_bones[self.bone_name]
        object = context.scene.objects[self.object_name]

        if self.custom_groups:
            group = object.vertex_groups[self.vertex_group]
        else:
            group = object.vertex_groups[bone.name]

        # Preserve length
        initial_length = bone.length

        # Alignment
        center = self.calc_center(object, group)

        if self.alignment == 'HEAD':
            bone.head = center
        if self.alignment == 'TAIL':
            bone.tail = center
        if self.alignment == 'CENTER':
            head, tail = self.center_bone(bone, center)
            bone.head = head
            bone.tail = tail

        bone.length = initial_length

        return {'FINISHED'}

def register():
    bpy.utils.register_class(BoneToShapeProps)
    bpy.utils.register_class(BoneToShapeOP)
    bpy.utils.register_class(BoneToShapePanel)

    bpy.types.Scene.bs_props = bpy.props.PointerProperty(type=BoneToShapeProps)

def unregister():
    bpy.utils.unregister_class(BoneToShapeProps)
    bpy.utils.unregister_class(BoneToShapeOP)
    bpy.utils.unregister_class(BoneToShapePanel)
    
    del bpy.types.Scene.bs_props

if __name__ == "__main__":
    register()
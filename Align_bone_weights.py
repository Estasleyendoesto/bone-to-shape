bl_info = {
    "name" : "Bone Weight Alignment",
    "author" : "Estasleyendoesto",
    "description" : "Bone alignment by vertex weights",
    "blender" : (4, 0, 0),
    "version" : (1, 0, 0),
    "location" : "Edit Mode > Sidebar > Item",
    "warning" : "",
    "category" : "Rigging"
}

import bpy
from mathutils import Vector

class AlignBoneByWeightBackup(bpy.types.Operator):
    bl_idname = "bone.weight_alignment_backup"
    bl_label = "Back"
    
    bone_name: bpy.props.StringProperty()
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.mode == 'EDIT_ARMATURE')
                
    def execute(self, context):
        bone = context.object.data.edit_bones[self.bone_name]
        old_bone = context.scene.bone_name_backup
        
        if bone.name == old_bone:
            bone.head = eval(context.scene.bone_head_backup)
            bone.tail = eval(context.scene.bone_tail_backup)
        
        return {'FINISHED'}

class AlignBoneByWeight(bpy.types.Operator):
    """Align bones by Mesh Vertex Group Weights"""
    bl_idname = "bone.weight_alignment"
    bl_label = "Align"
    
    align: bpy.props.EnumProperty(
        items = (
            ('HEAD', "Head", ""),
            ('CENTER', "Center", ""),
            ('TAIL', "Tail", "")
        ),
        default = 'HEAD'
    )
    
    bone_name: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.mode == 'EDIT_ARMATURE')

    def execute(self, context):
        bone = context.object.data.edit_bones[self.bone_name]
        object = context.scene.objects[self.object_name]

        context.scene.bone_name_backup = bone.name
        context.scene.bone_head_backup = str(bone.head.to_tuple())
        context.scene.bone_tail_backup = str(bone.tail.to_tuple())
            
        # Preserve length
        length = bone.length
        
        # Calculate Center     
        group = object.vertex_groups[bone.name]
        center = [0, 0, 0]
        total_weight = 0
        for vert in object.data.vertices:
            for g in vert.groups:
                if g.group == group.index:
                    center = [c + g.weight * v for c, v in zip(center, object.matrix_world @ vert.co)]
                    total_weight += g.weight
                
        if total_weight:
            center = [c / total_weight for c in center]
        
            # Según align
            if self.align == 'HEAD':
                bone.head = center
                
            elif self.align == 'TAIL':
                bone.tail = center
                
            elif self.align == 'CENTER':
                center = Vector(center)
            
                # Calcula el centro del hueso
                bone_center = (bone.head + bone.tail) / 2
                
                # Calcula la dirección del hueso
                bone_dir = bone.tail - bone.head
                bone_dir.normalize()
                
                # Calcula la nueva posición de la cabeza y la cola del hueso
                new_head = center - bone_dir * (bone_center - bone.head).length
                new_tail = center + bone_dir * (bone.tail - bone_center).length
                
                # Alinea el hueso con el centro de los pesos
                bone.head = new_head
                bone.tail = new_tail
                
                self.report({'INFO'}, self.align)
                
            bone.length = length
        else:
            self.report({'ERROR_INVALID_INPUT'}, 'Vertex group has no weights')
        
        return {'FINISHED'}

class WeightAlignmentPanel(bpy.types.Panel):
    bl_label = "Weight Alignment"
    bl_idname = "BONE_PT_bone_weight_alignment"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"

    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.mode == 'EDIT_ARMATURE')

    def draw(self, context):
        rig = context.object
        bone = rig.data.edit_bones.active
        
        layout = self.layout
        box = layout.box()
        row = box.row()
        row.alignment = 'CENTER'
        row.label(text=rig.name, icon='ARMATURE_DATA')
        
        target = context.scene.weight_target_object
        vertex_group = None
        
        bone_icon = 'BONE_DATA'
        row.alert = False
        
        if target:
            vertex_group = target.vertex_groups.get(bone.name, None)
            if not vertex_group:
                bone_icon = 'ERROR'
                row.alert = True
        
        row.label(text=bone.name, icon=bone_icon)
        layout.prop_search(context.scene, "weight_target_object", context.scene, 'objects', text='Object')
        
        if vertex_group:
            box = layout.box()
            row = box.row()
            row.alignment = 'CENTER'
            row.label(text=vertex_group.name, icon='GROUP_VERTEX')
            
            layout.prop(context.scene, "bone_alignment", expand=True)
            props = layout.operator('bone.weight_alignment')
            props.align = context.scene.bone_alignment
            props.bone_name = bone.name
            props.object_name = target.name
            
            props = layout.operator('bone.weight_alignment_backup')
            props.bone_name = bone.name
        
def object_picker_condition(self, obj):
    return (
        obj.type == 'MESH' and 
        obj.parent and 
        obj.parent.type == 'ARMATURE' and 
        obj.parent == bpy.context.active_object
    )
    
def register():
    bpy.utils.register_class(AlignBoneByWeightBackup)
    bpy.utils.register_class(AlignBoneByWeight)
    bpy.utils.register_class(WeightAlignmentPanel)
    
    bpy.types.Scene.bone_alignment = bpy.props.EnumProperty(
        items = (
            ('HEAD', "Head", ""),
            ('CENTER', "Center", ""),
            ('TAIL', "Tail", "")
        ),
        default = 'HEAD'
    )
    
    bpy.types.Scene.weight_target_object = bpy.props.PointerProperty(
        type = bpy.types.Object,
        poll = object_picker_condition
    )
    
    bpy.types.Scene.bone_name_backup = bpy.props.StringProperty()
    bpy.types.Scene.bone_head_backup = bpy.props.StringProperty()
    bpy.types.Scene.bone_tail_backup = bpy.props.StringProperty()

def unregister():
    bpy.utils.unregister_class(AlignBoneByWeightBackup)
    bpy.utils.unregister_class(AlignBoneByWeight)
    bpy.utils.unregister_class(WeightAlignmentPanel)
    
    del bpy.types.Scene.bone_alignment
    del bpy.types.Scene.weight_target_object
    del bpy.types.Scene.bone_name_backup
    del bpy.types.Scene.bone_head_backup
    del bpy.types.Scene.bone_tail_backup

if __name__ == "__main__":
    register()
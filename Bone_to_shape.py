bl_info = {
    "name" : "Adjust Bone to Shape",
    "author" : "Estasleyendoesto",
    "description" : "Inverse bone alignment to shape using Weights",
    "blender" : (4, 0, 0),
    "version" : (1, 0, 0),
    "location" : "Edit Mode > Sidebar > Item",
    "warning" : "",
    "category" : "Rigging"
}

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
    head_group: bpy.props.StringProperty()
    tail_group: bpy.props.StringProperty()
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
    align_bone: bpy.props.BoolProperty(
        default=True,
        options=set()
    )
    preserve_length: bpy.props.BoolProperty(
        options=set(),
        description='Prevents the bone from changing size'
    )
    parent_connect: bpy.props.BoolProperty(
        options=set(), 
        description='Only works if has a parent and related by keep offset'
    )
    head_between: bpy.props.BoolProperty(
        options=set(), 
        description='Aligns the head between two vertex groups'
    )
    tail_between: bpy.props.BoolProperty(
        options=set(), 
        description='Aligns the tail between two vertex groups'
    )

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
        # Align Operator Options props
        col = layout.column(heading='Options')
        col.use_property_decorate = False
        col.use_property_split = True
        col.prop(bs_props, 'align_bone', text='Align Bone')
        col.prop(bs_props, 'preserve_length', text='Preserve Length')
        col.prop(bs_props, 'parent_connect', text='Parent Connect')
        col.prop(bs_props, 'head_between', text='Head Between')
        col.prop(bs_props, 'tail_between', text='Tail Between')

        # Head group
        if bs_props.head_between:
            row = layout.row()
            row.prop_search(
                bs_props, 'head_group', bs_props.target, 'vertex_groups', text='Head Group'
            )

        # Tail group
        if bs_props.tail_between:
            row = layout.row()
            row.prop_search(
                bs_props, 'tail_group', bs_props.target, 'vertex_groups', text='Tail Group'
            )

        # Align Operator
        if bs_props.align_bone:
            layout.prop(bs_props, 'alignment', expand=True)

        op = layout.operator('bs.to_shape')
        op.bone_name = bone.name
        op.object_name = bs_props.target.name
        op.vertex_group = bs_props.vertex_group
        op.custom_groups = bs_props.custom_groups
        op.alignment = bs_props.alignment
        op.align_bone = bs_props.align_bone
        op.preserve_length = bs_props.preserve_length
        op.parent_connect = bs_props.parent_connect
        op.head_between = bs_props.head_between
        op.tail_between = bs_props.tail_between
        op.head_group = bs_props.head_group
        op.tail_group = bs_props.tail_group
    
    def draw(self, context):
        rig = context.object
        curr_bone = rig.data.edit_bones.active
        bs_props = context.scene.bs_props
        bone_has_group = False
        
        if bs_props.target:
            bone_has_group = bs_props.target.vertex_groups.get(curr_bone.name, None)

        layout = self.layout
        box = layout.box()
        row = box.row()
        row.alignment = 'CENTER'
        
        # Rig Info label
        row.label(text=rig.name, icon='ARMATURE_DATA')

        if not bs_props.target:
            row.active = False
        if not bone_has_group:
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
        
        # Operator
        if bs_props.custom_groups:
            exists = False
            if bs_props.target:
                exists = bs_props.target.vertex_groups.get(bs_props.vertex_group, None)
            if exists:
                # Operator
                self.call_operator(layout, bs_props, curr_bone)
        else:
            if bone_has_group:
                box = layout.box()
                row = box.row()
                row.alignment = 'CENTER'
                # Vertex group info label
                row.label(text=bone_has_group.name, icon='GROUP_VERTEX')
                # Operator
                self.call_operator(layout, bs_props, curr_bone)
        

class BoneToShapeOP(bpy.types.Operator):
    '''Align bones to shape usign vertex groups'''
    bl_idname = "bs.to_shape"
    bl_options = {'REGISTER', 'UNDO_GROUPED'}
    bl_label = "Align"

    o_head: bpy.props.StringProperty()
    o_tail: bpy.props.StringProperty()
    bone_name: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()
    vertex_group: bpy.props.StringProperty()
    custom_groups: bpy.props.BoolProperty()
    preserve_length: bpy.props.BoolProperty()
    parent_connect: bpy.props.BoolProperty()
    align_bone: bpy.props.BoolProperty()
    head_between: bpy.props.BoolProperty()
    tail_between: bpy.props.BoolProperty()
    head_group: bpy.props.StringProperty()
    tail_group: bpy.props.StringProperty()
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
    
    def calc_center_between_groups(self, object, group1, group2):
        center1 = self.calc_center(object, group1)
        center2 = self.calc_center(object, group2)
        center_between = [(c1 + c2) / 2 for c1, c2 in zip(center1, center2)]

        return center_between
    
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

        self.o_head = str(bone.head.to_tuple())
        self.o_tail = str(bone.tail.to_tuple())

        # bone.name if not exist vertex_group
        if self.custom_groups:
            group = object.vertex_groups[self.vertex_group]
        else:
            group = object.vertex_groups[bone.name]

        # Preserve length
        initial_length = bone.length

        # Alignment
        if self.align_bone:
            center = self.calc_center(object, group)
            if self.alignment == 'HEAD':
                bone.head = center
            if self.alignment == 'TAIL':
                bone.tail = center
            if self.alignment == 'CENTER':
                head, tail = self.center_bone(bone, center)
                bone.head = head
                bone.tail = tail

        # Head alignment between
        if self.head_between:
            if self.head_group:
                head_group = object.vertex_groups[self.head_group]
                if head_group:
                    pos = self.calc_center_between_groups(object, group, head_group)
                    bone.head = pos

        # Tail alignment between
        if self.tail_between:
            if self.tail_group:
                tail_group = object.vertex_groups[self.tail_group]
                if tail_group:
                    pos = self.calc_center_between_groups(object, group, tail_group)
                    bone.tail = pos

        # Preserver length On
        if self.preserve_length:
            bone.length = initial_length

        # Parent connect
        if self.parent_connect:
            parent = bone.parent
            if parent:
                bone.head = parent.tail

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

"""
#A futuro:
#lanzar rayos en todas las direcciones desde un punto, crear una malla con los puntos de impacto de estos rayos, 
#centrar un vector en esta malla y luego borrar la malla

import bpy
import bmesh
from mathutils import Vector, geometry

# Crea un objeto BMesh para la malla nueva
bm_new = bmesh.new()

# Define el origen del rayo
ray_origin = Vector((0, 0, 0))

# Define la longitud del rayo (30 cm)
ray_length = 0.3

# Lanza los rayos en todas las direcciones y crea la malla nueva
for i in range(360):  # Ajusta este rango según el número de rayos que quieras lanzar
    for j in range(180):
        # Calcula la dirección del rayo
        ray_direction = Vector((i, j, 1)).normalized()

        # Lanza el rayo
        result, location, normal, index = bpy.context.scene.ray_cast(bpy.context.view_layer, ray_origin, ray_direction)

        # Si el rayo intersecta la malla, crea un nuevo vértice en el punto de intersección
        if result:
            vert = bm_new.verts.new(location)

# Calcula el centroide de la malla nueva
centroid = Vector((0, 0, 0))
for vert in bm_new.verts:
    centroid += vert.co
centroid /= len(bm_new.verts)

print("El centroide de la malla nueva es", centroid)

# Borra la malla nueva
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.delete(type='VERT')
bpy.ops.object.mode_set(mode='OBJECT')
"""
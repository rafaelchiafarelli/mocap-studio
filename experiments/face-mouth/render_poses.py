"""Opened on the character .blend, never saved. Arg: poses JSON, output folder, optional subset. Renders each mouth pose close up."""
import json,math,sys
import bpy
from mathutils import Vector
a=sys.argv[sys.argv.index('--')+1:];poses=json.load(open(a[0]));out=a[1];names=a[2].split(',') if len(a)>2 else list(poses)
s=bpy.context.scene
targets=[o for o in bpy.data.objects if o.type=='MESH' and o.data.shape_keys]
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
T=[rig.pose.bones[n] for n in ('tongue','tongue.001','tongue.002')]
for b in T:b.rotation_mode='XYZ'
tm=next(o for o in bpy.data.objects if 'teeth' in o.name and o.type=='MESH').data.materials[0]
bs=next(n for n in tm.node_tree.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled')
for l in list(bs.inputs['Base Color'].links):tm.node_tree.links.remove(l)
bs.inputs['Base Color'].default_value=(0.78,0.72,0.6,1);bs.inputs['Roughness'].default_value=0.25
hc=(rig.data.bones['spine.006'].head_local+rig.data.bones['spine.006'].tail_local)/2
def aim(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
for name,off,power,size in (('Key',(-0.9,-1.1,0.7),60,0.9),('Fill',(1.2,-0.9,0.0),12,1.4),('Rim',(0.5,1.2,0.5),35,0.6)):
    l=bpy.data.lights.new(name,'AREA');l.energy,l.size=power,size;ob=bpy.data.objects.new(name,l);s.collection.objects.link(ob);ob.location=hc+Vector(off);aim(ob,hc)
mouth=Vector((0,-0.14,1.495))
cam=bpy.data.objects.new('C',bpy.data.cameras.new('C'));s.collection.objects.link(cam);cam.data.lens=85;s.camera=cam
s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x,s.render.resolution_y=520,520
cp=bpy.context.preferences.addons['cycles'].preferences;cp.compute_device_type='OPTIX';cp.get_devices()
for d in cp.devices:d.use=d.type=='OPTIX'
s.cycles.device='GPU';s.render.image_settings.file_format='JPEG'
views={'f':(0,-0.42,0.0),'q':(-0.24,-0.36,-0.01)}
for n in names:
    p=poses[n]
    for o in targets:
        for k in o.data.shape_keys.key_blocks:
            if k.name.startswith(('mouth','jaw','tongue')):k.value=p.get(k.name,0.0)
    for i,b in enumerate(T):b.rotation_euler=(math.radians(p.get('tongueUp',0.0)*(22,30,30)[i]),0,0)
    bpy.context.view_layer.update()
    for v,off in views.items():
        cam.location=mouth+Vector(off);aim(cam,mouth)
        s.render.filepath=f"{out}\\{n}_{v}.jpg";bpy.ops.render.render(write_still=True)
    print('RES',n)

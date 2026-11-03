"""Opened on the character .blend. Measures lip gap per jawOpen and eye distance, to scale tracked motion to this face."""
import bpy,json
import numpy as np
body=max((o for o in bpy.data.objects if o.type=='MESH' and o.data.shape_keys),key=lambda o:len(o.data.shape_keys.key_blocks));kb=body.data.shape_keys.key_blocks
for m in body.modifiers:
    if m.type=='SUBSURF':m.show_viewport=False
def pos():
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();me=body.evaluated_get(dg).to_mesh()
    a=np.zeros(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',a);return a.reshape(-1,3).copy()
for k in kb:
    pass
base=pos()
kb['jawOpen'].value=1;j1=pos();kb['jawOpen'].value=0
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');eL=rig.data.bones['eye.L'].head_local;eR=rig.data.bones['eye.R'].head_local
ipd=(eL-eR).length
head=rig.data.bones['spine.006'];z_eye=eL.z
dz=j1[:,2]-base[:,2]
c=np.abs(base[:,0])<0.0015
m=c&(base[:,2]<z_eye-0.05)&(base[:,2]>z_eye-0.13)&(base[:,1]<head.head_local.y-0.04)
idx=np.flatnonzero(m);idx=idx[np.argsort(base[idx,2])]
rows=[(int(i),round(float(base[i,1]),4),round(float(base[i,2]),4),round(float(dz[i]),4)) for i in idx]
print('JSON'+json.dumps({'ipd':ipd,'z_eye':z_eye,'n':len(idx),'rows':rows}))

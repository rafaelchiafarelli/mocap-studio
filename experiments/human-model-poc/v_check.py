import bpy,sys,bmesh,numpy as np
outdir=sys.argv[sys.argv.index('--')+1]
print("=== C")
s=bpy.context.scene; c=bpy.data.objects['CONTROLE_BOCA']; ob=bpy.data.objects
def state(a,t):
    c['abertura']=float(a); c['deslizar_articulacao']=float(t); c.update_tag(); bpy.context.view_layer.update(); s.frame_set(s.frame_current)
    dg=bpy.context.evaluated_depsgraph_get(); return dg
def EV(n,dg):
    e=ob[n].evaluated_get(dg); m=e.to_mesh(); M=np.array(e.matrix_world); k=np.empty(len(m.vertices)*3); m.vertices.foreach_get('co',k); P=k.reshape(-1,3)@M[:3,:3].T+M[:3,3]
    bm=bmesh.new(); bm.from_mesh(m); bm.transform(e.matrix_world); v=abs(bm.calc_volume(signed=True)); bm.free(); e.to_mesh_clear(); return P,v
S0=state(0,1); base={}
for n in ['Lower medial incisor.l','Upper medial incisor.l','Mandible','Temporal bone.l']: base[n]=EV(n,S0)[0].copy()
keys=['Superficial part of masseter.l','Deep part of masseter.l','Temporalis muscle.l','Medial pterygoid muscle.l','Inferior head of lateral pterygoid muscle.l','Depressor labii inferioris.l','Orbicularis oris muscle.l','Zygomaticus major muscle.l','Mentalis muscle.l','Tongue','Lateral temporomandibular ligament.l','Sphenomandibular ligament.l','Stylomandibular ligament.l','Platysma.l','Frontalis muscle.l','Inferior alveolar nerve.l_tubo','Maxilla.l']
rest={k:EV(k,S0) for k in keys if k in ob}
print("missing",[k for k in keys if k not in ob])
for tag,a,t in (('so gira',1,0),('gira+desliza',1,1)):
    dg=state(a,t); L=EV('Lower medial incisor.l',dg)[0]; U=base['Upper medial incisor.l']
    i=base['Lower medial incisor.l'][:,2].argmax()
    print(tag,"incisor drop mm",round((base['Lower medial incisor.l'][i,2]-L[i,2])*1000,1),"back mm",round((L[i,1]-base['Lower medial incisor.l'][i,1])*1000,1),"gap incisors mm",round((U[:,2].min()-L[:,2].max())*1000,1))
    M0=base['Mandible']; M1=EV('Mandible',dg)[0]; top=(M0[:,1]>np.percentile(M0[M0[:,2]>M0[:,2].max()-.015][:,1],60))&(M0[:,2]>M0[:,2].max()-.015)
    d=(M1[top]-M0[top]).mean(0)*1000; print("  condyle shift mm: forward",round(-d[1],1),"up",round(d[2],1))
    from mathutils import kdtree
    T=base['Temporal bone.l']; k=kdtree.KDTree(len(T)); [k.insert(p.tolist(),i) for i,p in enumerate(T)]; k.balance()
    mn=min(k.find(p.tolist())[2] for p in M1[top&(M0[:,0]>0)]); print("  min condyle-temporal distance mm",round(mn*1000,1))
    if t==1:
        for n,(P0,V0) in rest.items():
            P1,V1=EV(n,dg); dd=np.linalg.norm(P1-P0,axis=1)*1000
            print(f"  {n[:44]:44s} moved mean {dd.mean():5.1f} max {dd.max():5.1f} mm  volume {V1/max(V0,1e-12)*100:6.1f}%")
# renders
s.render.engine='BLENDER_WORKBENCH'; s.display.shading.light='STUDIO'; s.display.shading.color_type='OBJECT'; s.display.shading.show_cavity=True; s.render.resolution_x=s.render.resolution_y=700
cam=bpy.data.cameras.new('c'); cam.type='ORTHO'; cam.ortho_scale=.27; co=bpy.data.objects.new('c',cam); s.collection.objects.link(co); s.camera=co; co.location=(.5,-.03,1.53); co.rotation_euler=(np.pi/2,0,np.pi/2)
hide_sup=[o for o in ob if o.type=='MESH' and any(x.name in('Musculos','Lingua') for x in o.users_collection)]
hide_arm=bpy.data.objects.get('Rig')
for tag,a,t in (('a_fechada',0,1),('b_so_gira',1,0),('c_gira_desliza',1,1)):
    state(a,t)
    for o in hide_sup: o.hide_render=False
    s.render.filepath=outdir+'\\full_'+tag+'.png'; bpy.ops.render.render(write_still=True)
    for o in hide_sup: o.hide_render=True
    s.render.filepath=outdir+'\\deep_'+tag+'.png'; bpy.ops.render.render(write_still=True)
print("=== /C")

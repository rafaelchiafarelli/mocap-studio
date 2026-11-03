import bpy,sys,json,math,re,bmesh
import numpy as np
from mathutils import Vector,Matrix,kdtree
a=sys.argv[sys.argv.index('--')+1:]; js,src,out=a
D=json.load(open(js)); meta={i['name']:i for i in D['items']}
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
with bpy.data.libraries.load(src,link=False) as (f,t):
    t.objects=[n for n in f.objects if n in meta]
names={o.name for o in t.objects if o}
scn=bpy.context.scene
col={k:bpy.data.collections.new(v) for k,v in {'bone':'Ossos fixos','jaw':'Mandibula e dentes','muscle':'Musculos','lig':'Ligamentos e disco','tongue':'Lingua','nerve':'Nervos','patch_jaw':'Insercoes na mandibula','patch_fix':'_tmp'}.items()}
for c in col.values(): scn.collection.children.link(c)
color={'bone':(.85,.82,.7,1),'jaw':(.95,.9,.55,1),'muscle':(.72,.2,.18,1),'lig':(.95,.75,.1,1),'tongue':(.9,.45,.55,1),'nerve':(.1,.75,.3,1),'patch_jaw':(.1,.45,.85,1),'patch_fix':(.5,.5,.9,1)}
extra=[o for o in bpy.data.objects if o.name not in names]
objs=[o for o in t.objects if o]
for o in objs:
    o.parent=None; o.matrix_world=Matrix(meta[o.name]['world']); o.hide_viewport=False; o.hide_render=False; o.hide_select=False
    col[meta[o.name]['kind']].objects.link(o); o.color=color[meta[o.name]['kind']]
for o in extra: bpy.data.objects.remove(o)
bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get()
final=[]
for o in objs:
    if o.type=='CURVE' or o.modifiers:
        m=bpy.data.meshes.new_from_object(o.evaluated_get(dg),depsgraph=dg)
        if o.type=='CURVE':
            if not len(m.vertices): print("skip curve",o.name); continue
            n=bpy.data.objects.new(o.name+'_tubo',m); n.matrix_world=o.matrix_world.copy(); n.color=o.color; col['nerve'].objects.link(n); meta[n.name]=dict(meta[o.name]); final.append(n); continue
        o.modifiers.clear(); o.data=m
    else: o.data=o.data.copy()
    final.append(o)
for o in objs:
    if o.type=='CURVE': bpy.data.objects.remove(o)
bpy.context.view_layer.update()
def W(o):
    n=len(o.data.vertices); c=np.empty(n*3); o.data.vertices.foreach_get('co',c); c=c.reshape(-1,3)
    M=np.array(o.matrix_world); return c@M[:3,:3].T+M[:3,3]
def kd(P):
    k=kdtree.KDTree(len(P))
    for i,p in enumerate(P): k.insert(p.tolist(),i)
    k.balance(); return k
def dist(k,P): return np.array([k.find(p.tolist())[2] for p in P])
P={o.name:W(o) for o in final}
by=lambda *ks:[o for o in final if meta[o.name]['kind'] in ks]
K_bone=kd(np.vstack([P[o.name] for o in by('bone')])); K_jaw=kd(np.vstack([P[o.name] for o in by('jaw')]))
def stem(n):
    s=n.split('.')[0].lower()
    for w in('superficial part of ','deep part of ','inferior head of ','superior head of ','orbital part of ','palpebral part of ','anterior belly of ','posterior belly of '): s=s.replace(w,'')
    return s
pat={}
for o in by('patch_jaw','patch_fix'):
    pat.setdefault((stem(o.name),o.name[-1]),{'jaw':[],'fix':[]})['jaw' if meta[o.name]['kind']=='patch_jaw' else 'fix'].append(P[o.name])
arm_d=bpy.data.armatures.new('Rig'); arm=bpy.data.objects.new('Rig',arm_d); scn.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm; arm.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
d=[P[n] for n in ('Articular disc of temporomandibular joint.l','Articular disc of temporomandibular joint.r')]
piv=Vector((0,float((d[0][:,1].mean()+d[1][:,1].mean())/2),float((d[0][:,2].mean()+d[1][:,2].mean())/2)))
for nm,tail in (('Mandibula',.04),('Cranio',.03)):
    b=arm_d.edit_bones.new(nm); b.head=piv; b.tail=piv+Vector((0,0,tail)); b.roll=0
bpy.ops.object.mode_set(mode='OBJECT')
stats={'patch':[], 'prox':[]}
def assign(o,w):
    gj=o.vertex_groups.new(name='Mandibula'); gf=o.vertex_groups.new(name='Cranio')
    for i,x in enumerate(w.tolist()):
        gj.add([i],x,'REPLACE'); gf.add([i],1-x,'REPLACE')
    m=o.modifiers.new('Rig','ARMATURE'); m.object=arm; m.use_vertex_groups=True
def smooth(o,w,it=6):
    if not o.data.edges: return w
    e=np.empty(len(o.data.edges)*2,dtype=int); o.data.edges.foreach_get('vertices',e); e=e.reshape(-1,2); n=len(w)
    for _ in range(it):
        s=np.zeros(n);c=np.zeros(n); np.add.at(s,e[:,0],w[e[:,1]]); np.add.at(s,e[:,1],w[e[:,0]]); np.add.at(c,e[:,0],1); np.add.at(c,e[:,1],1)
        w=np.where(c>0,.5*w+.5*s/np.maximum(c,1),w)
    return w
for o in final:
    k=meta[o.name]['kind']
    if k=='bone' or k=='patch_fix': continue
    Q=P[o.name]
    if k in('jaw','patch_jaw'): assign(o,np.ones(len(Q))); continue
    key=(stem(o.name),o.name[-1]); pp=pat.get(key,{'jaw':[],'fix':[]})
    if pp['jaw']:
        kj=kd(np.vstack(pp['jaw'])); dj=dist(kj,Q); stats['patch'].append(o.name)
        df=dist(kd(np.vstack(pp['fix'])),Q) if pp['fix'] else dist(K_bone,Q)
    else:
        dj=dist(K_jaw,Q); df=dist(K_bone,Q); stats['prox'].append(o.name)
    w=df/(df+dj+1e-6); w=np.clip((w-.08)/.84,0,1); w=w*w*(3-2*w); w[dj>.075]=0
    if not pp['jaw'] and k=='muscle' and 'lateral pterygoid' not in o.name.lower(): w=np.minimum(w,.6)
    assign(o,smooth(o,w))
print("BINDING origin+insertion",len(stats['patch']),"proximity only",len(stats['prox']))
print("origin+insertion:",sorted({n.rsplit('.',1)[0] for n in stats['patch']}))
rm=by('patch_fix'); final=[o for o in final if meta[o.name]['kind']!='patch_fix']
for o in rm: bpy.data.objects.remove(o)
bpy.data.collections.remove(col['patch_fix'])
# calibrate rotation against the measured lower-incisor travel
pmax_f,pmax_d=0.0106,0.0040
ctl=bpy.data.objects.new('CONTROLE_BOCA',None); ctl.empty_display_type='ARROWS'; ctl.empty_display_size=.03; ctl.location=(0,float(piv.y)+.12,float(piv.z)); scn.collection.objects.link(ctl)
inc=P['Lower medial incisor.l']; tip=inc[inc[:,2].argmax()]
def incisor_drop(th):
    y,z=tip[1]-piv.y,tip[2]-piv.z; yr=y*math.cos(th)-z*math.sin(th); zr=y*math.sin(th)+z*math.cos(th)
    return -(zr-(tip[2]-piv.z))+pmax_d*math.sin(math.pi*.85)
lo,hi=0.05,.9
for _ in range(40):
    mid=(lo+hi)/2
    if incisor_drop(mid)<.0418: lo=mid
    else: hi=mid
TH=(lo+hi)/2; print("calibrated rotation deg",round(math.degrees(TH),1))
ctl['abertura']=0.0; ctl['deslizar_articulacao']=1.0
for pn,desc_ in(('abertura','0 fechada, 1 abertura maxima'),('deslizar_articulacao','0 so gira, 1 gira e desliza')):
    ctl.id_properties_ui(pn).update(min=0,max=1,soft_min=0,soft_max=1,description=desc_)
pb=arm.pose.bones['Mandibula']; pb.rotation_mode='XYZ'
def drv(path,idx,expr):
    fc=pb.driver_add(path,idx); dr=fc.driver; dr.type='SCRIPTED'
    for v,p in(('a','abertura'),('t','deslizar_articulacao')):
        x=dr.variables.new(); x.name=v; x.targets[0].id=ctl; x.targets[0].data_path=f'["{p}"]'
    dr.expression=expr
drv('rotation_euler',0,f'a*{TH:.5f}')
drv('location',2,f'a*t*(0.3+0.7*a)*{pmax_f}')   # bone local Z = world -Y (forward)
drv('location',1,f'-t*sin(a*2.67)*{pmax_d}')    # bone local Y = world Z (down)
for s in bpy.data.screens:
    for ar in s.areas:
        if ar.type=='VIEW_3D':
            sp=ar.spaces.active; sp.shading.type='SOLID'; sp.shading.color_type='OBJECT'; sp.shading.show_cavity=True; sp.clip_start=.001; sp.overlay.show_bones=False
            r=sp.region_3d; r.view_location=(0,.0,1.53); r.view_distance=.5; r.view_perspective='PERSP'
            r.view_rotation=(Vector((-.8,.5,0))).to_track_quat('-Z','Y')
        if ar.type=='PROPERTIES':
            try: ar.spaces.active.context='OBJECT'
            except Exception: pass
bpy.context.view_layer.objects.active=ctl; ctl.select_set(True)
for x in bpy.data.objects:
    if x is not ctl: x.select_set(False)
json.dump({'pivot':list(piv),'TH':TH},open(js+'.meta','w'))
bpy.ops.wm.save_as_mainfile(filepath=out,compress=True)
print("BUILD ok",len(bpy.data.objects))

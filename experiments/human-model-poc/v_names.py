import bpy,sys,json,re
from mathutils import Vector
out=sys.argv[sys.argv.index('--')+1]
def colset(prefix):
    r=set()
    def walk(c):
        r.update(c.objects)
        for ch in c.children: walk(ch)
    for c in bpy.context.scene.collection.children:
        if c.name.replace(' ','').startswith(prefix): walk(c)
    return r
bones=colset('1:Skeletal'); musc=colset('4:Muscular')
man=bpy.data.objects['Mandible']; desc=set()
def d(o):
    for c in o.children: desc.add(c); d(c)
d(man)
LIG=re.compile(r'temporomandibular|^stylomandibular|^sphenomandibular')
TON=re.compile(r'^tongue$|glossus')
NER=re.compile(r'(inferior alveolar|lingual|mandibular) nerve|division of mandibular nerve',re.I)
items=[]
for o in bpy.data.objects:
    if o.type=='CURVE':
        if not NER.search(o.name): continue
        items.append({"name":o.name,"kind":"nerve","world":[list(r) for r in o.matrix_world]}); continue
    if o.type!='MESH' or not len(o.data.vertices) or re.search(r'\.[jti]$',o.name): continue
    c=o.matrix_world@(sum((Vector(b) for b in o.bound_box),Vector())/8)
    if c.z<1.32: continue
    patch=bool(re.search(r'\.[oe]\d?[lr]$',o.name))
    jaw=(o==man or o in desc)
    k=None
    if patch: k='patch_jaw' if jaw else 'patch_fix'
    elif o==man or (o in bones and re.match(r'Lower .*(incisor|canine|premolar|molar)',o.name)): k='jaw'
    elif o in bones: k='bone'
    elif LIG.search(o.name.lower()) or o.name.startswith('Articular disc of temporomandibular'): k='lig'
    elif TON.search(o.name.lower()): k='tongue'
    elif o in musc: k='muscle'
    if k: items.append({"name":o.name,"kind":k,"world":[list(r) for r in o.matrix_world]})
json.dump({"items":items},open(out,'w'))
from collections import Counter
print("NAMES",Counter(i['kind'] for i in items))

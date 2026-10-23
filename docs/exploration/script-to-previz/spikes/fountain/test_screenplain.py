import sys
from screenplain.parsers import fountain
sp = fountain.parse(open(sys.argv[1], encoding='utf8'))
for p in sp.paragraphs:
    n = type(p).__name__
    txt = getattr(p,'line',None) or getattr(p,'character',None) or getattr(p,'lines',None)
    print(n, getattr(p,'scene_number',''), str(txt)[:80])

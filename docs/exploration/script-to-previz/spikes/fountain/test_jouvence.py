import sys
from jouvence.parser import JouvenceParser
from jouvence.document import *
doc = JouvenceParser().parse(sys.argv[1])
print("title", doc.title_values)
for s in doc.scenes:
    print("SCENE", repr(s.header))
    for p in s.paragraphs:
        print("   ", type(p).__name__ if not hasattr(p,'type') else p.type, repr(p.text)[:70])

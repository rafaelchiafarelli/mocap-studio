"""Front and side point views of skin and fitted bones, for checking a fit without Blender: python debug_view.py BONES.npz EXPORT.npz OUT.png [xmin xmax ymin ymax zmin zmax]"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from PIL import Image


def draw(img, p, color, sc, ox, oy, h):
    x = ((p[0] - ox) * sc).astype(int)
    y = (h - (p[1] - oy) * sc).astype(int)
    m = (x >= 0) & (y >= 0) & (x < img.shape[1]) & (y < img.shape[0])
    img[y[m], x[m]] = color


def view(bones_npz, skin_npz, out, box=None, h=1400):
    b = np.load(bones_npz)
    skin = np.load(skin_npz)["verts"]
    box = box or [-0.9, 0.9, -0.5, 0.5, -0.02, 1.9]
    sc = h / (box[5] - box[4])
    w1, w2 = int((box[1] - box[0]) * sc), int((box[3] - box[2]) * sc)
    img = np.full((h + 1, w1 + w2 + 20, 3), 255, np.uint8)
    colors = [(200, 50, 40), (30, 90, 200), (20, 150, 70), (170, 90, 200), (220, 140, 20), (20, 160, 170)]
    draw(img, (skin[:, 0], skin[:, 2]), (190, 190, 190), sc, box[0], box[4], h)
    off = box[2] - (w1 + 20) / sc
    draw(img, (skin[:, 1], skin[:, 2]), (190, 190, 190), sc, off, box[4], h)
    names = sorted(k[:-3] for k in b.files if k.endswith("__v"))
    for i, n in enumerate(names):
        v = b[f"{n}__v"]
        v = v[:: max(1, len(v) // 6000)]
        c = colors[hash(n.split("_")[0]) % len(colors)]
        draw(img, (v[:, 0], v[:, 2]), c, sc, box[0], box[4], h)
        draw(img, (v[:, 1], v[:, 2]), c, sc, off, box[4], h)
    Image.fromarray(img).save(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    view(a[0], a[1], a[2], [float(x) for x in a[3:9]] if len(a) >= 9 else None)

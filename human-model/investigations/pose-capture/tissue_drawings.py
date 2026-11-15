"""Drawings of where the tissue's parameters sit, from the real mesh, for Rafael's parameter page (13_parametros_por_regiao.html).

    human-model/hm.sh python human-model/investigations/pose-capture/tissue_drawings.py TECIDOS.npz REST.npz OUT_DIR

TECIDOS.npz should be a mesh built at rest (tissue_mesh.py without pose=), so the cuts are in MPFB's A pose. OUT_DIR gets PNGs
and figuras.json: for each figure, the HTML of the image with its labels (an SVG over it, a leader line from each label to a
point inside its colour), ready to paste into the page.
- mapa_frente / mapa_costas: the skin coloured by group (region), shaded;
- frontal_grupos / frontal_tecidos / frontal_camadas: a cut through the middle of the body, seen from the front, by group,
  by tissue and by tetrahedron size;
- lateral_tecidos: a cut through the left breast and buttock, seen from the left;
- corte_<regiao>: across each region (limbs across their bone), by tissue.
"""
import html
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

GROUPS = ("braco", "antebraco", "tronco", "seio_E", "seio_D", "barriga", "cavidade", "bumbum", "coxa", "perna")
GROUP_NAME = {"braco": "braço", "antebraco": "antebraço", "tronco": "tronco", "seio_E": "seio E", "seio_D": "seio D",
              "barriga": "barriga", "cavidade": "cavidade", "bumbum": "bumbum", "coxa": "coxa", "perna": "perna"}
GROUP_RGB = {"braco": (78, 121, 167), "antebraco": (160, 203, 232), "tronco": (242, 142, 43), "seio_E": (225, 87, 89),
             "seio_D": (255, 157, 154), "barriga": (89, 161, 79), "cavidade": (118, 183, 178), "bumbum": (176, 122, 161),
             "coxa": (237, 201, 72), "perna": (156, 117, 95)}
LABELS = ("pele", "gordura", "musculo", "rigido", "cavidade", "seio")
LABEL_RGB = {"pele": (185, 120, 92), "gordura": (240, 205, 110), "musculo": (205, 95, 85), "rigido": (170, 166, 150),
             "cavidade": (120, 150, 190), "seio": (215, 100, 145)}
LABEL_TEXT = {"pele": "pele: skin_young, fat_density", "gordura": "gordura: fat_young, fat_density",
              "musculo": "músculo: muscle_young, muscle_density", "rigido": "rígido: segue o osso",
              "cavidade": "cavidade: material próprio", "seio": "seio: grupo seio_E / seio_D"}
BAND_MM = (3, 6, 9, 12)
BAND_RGB = ((140, 92, 194), (90, 150, 210), (90, 180, 120), (200, 160, 60))
BG = (255, 255, 255)


def paint_fast(points, classes, colours, size_px, layers, shape):
    """The same, vectorised by layer: layers is a list of index arrays, painted in turn, each as squares of one size."""
    img = np.full((shape[0], shape[1], 3), BG, np.uint8)
    cls_img = -np.ones(shape, np.int64)
    for idx in layers:
        if not len(idx):
            continue
        s = size_px[idx[0]]
        r = int(np.ceil(s / 2))
        base = np.round(points[idx]).astype(int)
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if abs(dx) > s / 2 or abs(dy) > s / 2:
                    continue
                x, y = base[:, 0] + dx, base[:, 1] + dy
                ok = (x >= 0) & (x < shape[1]) & (y >= 0) & (y < shape[0])
                img[y[ok], x[ok]] = colour_table(colours)[classes[idx][ok]]
                cls_img[y[ok], x[ok]] = classes[idx][ok]
    return img, cls_img


def colour_table(colours):
    keys = sorted(colours)
    table = np.zeros((max(keys) + 1, 3), np.uint8)
    for k in keys:
        table[k] = colours[k]
    return table


def anchors(cls_img, min_gap=40):
    """For each class in the image, a pixel well inside it (deepest by distance to its border, so a thin ring's marker sits on
    the ring), kept at least min_gap pixels from the markers already placed, bigger classes first."""
    from scipy import ndimage
    out, placed = {}, []
    classes = [c for c in np.unique(cls_img) if c >= 0]
    classes.sort(key=lambda c: -(cls_img == c).sum())
    for c in classes:
        mask = cls_img == c
        n = int(mask.sum())
        if n < 30:
            continue
        depth = ndimage.distance_transform_edt(mask)
        ys, xs = np.nonzero(mask)
        score = depth[ys, xs].astype(float)
        for (px_, py_) in placed:
            near = np.hypot(xs - px_, ys - py_) < min_gap
            score[near] -= 1000
        k = int(np.argmax(score))
        out[int(c)] = (int(xs[k]), int(ys[k]), n)
        placed.append((xs[k], ys[k]))
    return out


def figure(name, img_w, img_h, labels, caption, folder="13_parametros_imagens", total_w=900, max_h=620, fs=17):
    """The image in an SVG with labels in side margins and leader lines. labels: [(text, x, y)] in image pixels.
    Laid out in display units: the text has a fixed size and the margins fit the longest label; tall images are capped."""
    longest = max([len(t) for t, _, _ in labels] + [4])
    margin = int(fs * 0.56 * longest + 24)
    iw = total_w - 2 * margin
    k = iw / img_w
    if img_h * k > max_h:
        k = max_h / img_h
    dw, dh = img_w * k, img_h * k
    ox = (total_w - dw) / 2
    H = max(dh, fs * 1.6 * (len(labels) / 2 + 1))
    oy = (H - dh) / 2
    left = [l for l in labels if l[1] < img_w / 2]
    right = [l for l in labels if l[1] >= img_w / 2]
    parts = [f'<image href="{folder}/{name}.png" x="{ox:.0f}" y="{oy:.0f}" width="{dw:.0f}" height="{dh:.0f}"/>']
    for side, group in (("L", sorted(left, key=lambda l: l[2])), ("R", sorted(right, key=lambda l: l[2]))):
        n = len(group)
        for j, (text, x, y) in enumerate(group):
            ty = H * (j + 1) / (n + 1)
            ax, ay = ox + x * k, oy + y * k
            tx, anchor = (ox - 14, "end") if side == "L" else (ox + dw + 14, "start")
            lx = tx + (4 if side == "L" else -4)
            parts.append(f'<line x1="{ax:.0f}" y1="{ay:.0f}" x2="{lx:.0f}" y2="{ty - fs * 0.35:.0f}" stroke="currentColor" stroke-width="1.2" opacity="0.65"/>')
            parts.append(f'<circle cx="{ax:.0f}" cy="{ay:.0f}" r="3.5" fill="currentColor"/>')
            parts.append(f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="{anchor}" font-size="{fs}" fill="currentColor">{html.escape(text)}</text>')
    svg = f'<svg viewBox="0 0 {total_w} {H:.0f}" role="img" aria-label="{html.escape(caption)}" style="width:100%;height:auto;color:var(--ink)">{"".join(parts)}</svg>'
    return f'<figure class="fig">{svg}<figcaption>{html.escape(caption)}</figcaption></figure>'


def figure_numbered(name, img_w, img_h, labels, caption, folder="13_parametros_imagens", total_w=900, max_h=560):
    """The image as wide as it fits, a numbered marker on each class, and the numbered list under it: for cards, where side
    labels left the image a sliver."""
    k = min(total_w / img_w, max_h / img_h)
    dw, dh = img_w * k, img_h * k
    ox = (total_w - dw) / 2
    parts = [f'<image href="{folder}/{name}.png" x="{ox:.0f}" y="0" width="{dw:.0f}" height="{dh:.0f}"/>']
    items = []
    for j, (text, x, y) in enumerate(sorted(labels, key=lambda l: (l[2], l[1])), start=1):
        cx, cy = ox + x * k, y * k
        parts.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="17" fill="#fff" stroke="#1f2328" stroke-width="2"/>')
        parts.append(f'<text x="{cx:.0f}" y="{cy + 7:.0f}" text-anchor="middle" font-size="20" font-weight="700" fill="#1f2328">{j}</text>')
        items.append(f"<li>{html.escape(text)}</li>")
    svg = f'<svg viewBox="0 0 {total_w} {dh:.0f}" role="img" aria-label="{html.escape(caption)}" style="width:100%;height:auto">{"".join(parts)}</svg>'
    return f'<figure class="fig">{svg}<figcaption>{html.escape(caption)}</figcaption><ol class="marks">{"".join(items)}</ol></figure>'


def slice_view(cen, band, cls, colours, p0, n, u, v, px, radius=None, pad=0.02):
    """Tetrahedron centres within each band's own half voxel of the plane (p0, n), and within radius of p0 if given (so a
    limb's cut doesn't show the trunk the same plane passes through), seen along n with axes u (right), v (down)."""
    d = (cen - p0) @ n
    sel = np.abs(d) < np.array(BAND_MM)[band] / 2000
    if radius is not None:
        sel &= np.linalg.norm((cen - p0) - np.outer(d, n), axis=1) < radius
    q = cen[sel] - p0
    uu, vv = q @ u, q @ v
    lo_u, lo_v = uu.min() - pad, vv.min() - pad
    w, h = int((uu.max() + pad - lo_u) * px), int((vv.max() + pad - lo_v) * px)
    pts = np.column_stack([(uu - lo_u) * px, (vv - lo_v) * px])
    b = band[sel]
    size = np.array(BAND_MM)[b] / 1000 * px * 1.02
    layers = [np.flatnonzero(b == k) for k in (3, 2, 1, 0)]
    img, cls_img = paint_fast(pts, cls[sel], colours, size, layers, (h, w))
    return img, cls_img


def skin_map(verts, faces, cls, colours, view, px):
    """The skin's vertices seen from the front (view=+1, looking +Y) or back (-1), z-buffered and shaded by the normal."""
    vn = np.zeros_like(verts)
    fn = np.cross(verts[faces[:, 2]] - verts[faces[:, 0]], verts[faces[:, 3]] - verts[faces[:, 1]])
    for k in range(4):
        np.add.at(vn, faces[:, k], fn)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    u = verts[:, 0] * view
    v = -verts[:, 2]
    depth = verts[:, 1] * view
    lo_u, lo_v = u.min() - 0.03, v.min() - 0.03
    w, h = int((u.max() + 0.03 - lo_u) * px), int((v.max() + 0.03 - lo_v) * px)
    shade = 0.72 + 0.28 * np.clip(-vn[:, 1] * view, 0, 1)
    img = np.full((h, w, 3), BG, np.uint8)
    cls_img = -np.ones((h, w), np.int64)
    table = colour_table(colours).astype(float)
    x0, y0 = np.round((u - lo_u) * px).astype(int), np.round((v - lo_v) * px).astype(int)
    # splats with a real depth test: per pixel the nearest vertex wins (painting far to near let the front show through gaps)
    r = 3
    pix, dep, idx = [], [], []
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy > r * r:
                continue
            x, y = x0 + dx, y0 + dy
            ok = (x >= 0) & (x < w) & (y >= 0) & (y < h)
            pix.append(y[ok] * w + x[ok])
            dep.append(depth[ok] + 0.0005 * np.hypot(dx, dy) / r)
            idx.append(np.flatnonzero(ok))
    pix, dep, idx = np.concatenate(pix), np.concatenate(dep), np.concatenate(idx)
    order = np.lexsort((dep, pix))
    first = np.unique(pix[order], return_index=True)[1]
    win_pix, win = pix[order][first], idx[order][first]
    img.reshape(-1, 3)[win_pix] = (table[cls[win]] * shade[win, None]).astype(np.uint8)
    cls_img.reshape(-1)[win_pix] = cls[win]
    return img, cls_img


def save(img, folder, name):
    Image.fromarray(img).save(folder / f"{name}.png", optimize=True)


def main(tissue, rest, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    m, e = np.load(tissue), np.load(rest)
    nodes, tets = m["nodes"].astype(float), m["tets"]
    cen = nodes[tets].mean(axis=1)
    band, label, group = m["tet_band"].astype(int), m["label"].astype(int), m["group"].astype(int)
    names = list(e["bone_names"])
    B = {n: i for i, n in enumerate(names)}
    head, tail = e["bone_head"].astype(float), e["bone_tail"].astype(float)
    gcol = {i: GROUP_RGB[g] for i, g in enumerate(GROUPS)}
    lcol = {i: LABEL_RGB[l] for i, l in enumerate(LABELS)}
    bcol = {i: c for i, c in enumerate(BAND_RGB)}
    soft_group = np.where(label == 3, len(GROUPS), group)  # rigid drawn apart in the group views
    gcol_r = dict(gcol)
    gcol_r[len(GROUPS)] = LABEL_RGB["rigido"]
    figs = {}

    # skin maps by group
    sv, ids = e["sub_verts"].astype(float), m["sub_ids"]
    verts, faces = sv[ids], m["sub_faces"]
    vg = group[m["sub_tet"]]
    for name, view, cap in (("mapa_frente", 1, "A pele por região, de frente"), ("mapa_costas", -1, "A pele por região, de costas")):
        img, ci = skin_map(verts, faces, vg, gcol, view, 420)
        save(img, out, name)
        an = anchors(ci)
        # small patches (a few skin vertices tied into a breast's volume at the nipple) aren't labelled: the skin there is the trunk's
        figs[name] = figure(name, img.shape[1], img.shape[0], [(GROUP_NAME[GROUPS[c]], x, y) for c, (x, y, npx) in an.items() if npx > 400], cap)

    # frontal cut through the middle of the trunk
    y0 = float(np.median(cen[(group == GROUPS.index("tronco")), 1]))
    p0, n, u, v = np.array([0, y0, 0]), np.array([0, 1.0, 0]), np.array([1.0, 0, 0]), np.array([0, 0, -1.0])
    for name, cls, col, text, cap in (
            ("frontal_grupos", soft_group, gcol_r, lambda c: "rígido (osso)" if c == len(GROUPS) else GROUP_NAME[GROUPS[c]],
             "Corte de frente, no meio do corpo: cada cor é uma região (um bloco do tissue_groups.json)"),
            ("frontal_tecidos", label, lcol, lambda c: LABEL_TEXT[LABELS[c]],
             "O mesmo corte por tecido: cada camada usa os parâmetros indicados, com os valores da sua região"),
            ("frontal_camadas", band, bcol, lambda c: f"tetraedros de {BAND_MM[c]} mm",
             "O mesmo corte pelo tamanho dos tetraedros: finos junto da pele, grossos no fundo")):
        img, ci = slice_view(cen, band, cls, col, p0, n, u, v, 420)
        save(img, out, name)
        an = anchors(ci)
        figs[name] = figure(name, img.shape[1], img.shape[0], [(text(c), x, y) for c, (x, y, _) in an.items()], cap)

    # side cut through the left breast and buttock
    xb = float(head[B["breast.L"], 0])
    img, ci = slice_view(cen, band, label, lcol, np.array([xb, 0, 0]), np.array([1.0, 0, 0]), np.array([0, -1.0, 0]), np.array([0, 0, -1.0]), 420)
    save(img, out, "lateral_tecidos")
    an = anchors(ci)
    figs["lateral_tecidos"] = figure_numbered("lateral_tecidos", img.shape[1], img.shape[0], [(LABEL_TEXT[LABELS[c]], x, y) for c, (x, y, _) in an.items()],
                                     "Corte de lado, pelo seio e pela nádega esquerdos (frente à direita)")

    # one cut per region, by tissue
    def limb(bone, t):
        a, b = head[B[bone]], tail[B[bone]]
        nn = (b - a) / np.linalg.norm(b - a)
        uu = np.cross(nn, [0, 1.0, 0])
        uu /= np.linalg.norm(uu)
        return a + t * (b - a), nn, uu, np.cross(nn, uu)
    y_mid = float(np.median(cen[:, 1]))
    zcut = lambda z: (np.array([0, y_mid, z]), np.array([0, 0, 1.0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
    z_hip = (head[B["thigh.L"], 2] + head[B["thigh.R"], 2]) / 2
    cuts = {"braco": (limb("upper_arm.L", 0.5), 1600, 0.09, "Braço esquerdo, atravessado no meio"),
            "antebraco": (limb("forearm.L", 0.45), 2000, 0.07, "Antebraço esquerdo, atravessado no meio"),
            "tronco": (zcut(head[B["spine.004"], 2] + 0.01), 1100, 0.22, "Tronco na altura das axilas, acima dos seios, visto de cima (frente em cima)"),
            "seios": (zcut(head[B["breast.L"], 2]), 1100, 0.22, "Na altura dos seios, visto de cima (frente em cima)"),
            "barriga": (zcut(head[B["spine.001"], 2] + 0.03), 1100, 0.25, "Barriga e cavidade, visto de cima (frente em cima)"),
            "bumbum": (zcut(z_hip - 0.02), 1000, 0.30, "Quadril e nádegas, visto de cima (frente em cima)"),
            "coxa": (limb("thigh.L", 0.45), 1300, 0.12, "Coxa esquerda, atravessada no meio"),
            "perna": (limb("shin.L", 0.35), 1600, 0.09, "Perna esquerda, atravessada na panturrilha")}
    for key, ((pp, nn, uu, vv), px, radius, cap) in cuts.items():
        img, ci = slice_view(cen, band, label, lcol, pp, nn, uu, vv, px, radius)
        name = f"corte_{key}"
        save(img, out, name)
        an = anchors(ci)
        figs[name] = figure_numbered(name, img.shape[1], img.shape[0], [(LABEL_TEXT[LABELS[c]], x, y) for c, (x, y, _) in an.items()], cap)
        bimg, bci = slice_view(cen, band, band, bcol, pp, nn, uu, vv, px, radius)
        save(bimg, out, name + "_camadas")
    (out / "figuras.json").write_text(json.dumps(figs, ensure_ascii=False), encoding="utf-8")
    print("figures", list(figs))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    main(*sys.argv[1:])

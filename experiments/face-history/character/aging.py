"""Seeded aging maps painted from code, no sculpting: a wrinkle height map and an age-tone colour map, in the skin's UV space.

Every texel of the head is rasterised to its 3D position, so wrinkles are placed from the character's real
eye, nose and mouth positions and follow any later change to the recipe's targets.
"""
import struct
import zlib

import bpy
import numpy as np


def _write_png16(path, rgb):
    """16-bit RGB PNG (bottom row first in, as Blender stores it), so bump gradients do not band."""
    h, w, _ = rgb.shape
    data = (np.clip(rgb[::-1], 0, 1) * 65535 + 0.5).astype(">u2")
    raw = b"".join(b"\x00" + data[y].tobytes() for y in range(h))

    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def _position_map(mesh, size, min_z):
    pos = np.zeros((size, size, 3), dtype=np.float32)
    mask = np.zeros((size, size), dtype=bool)
    mesh.calc_loop_triangles()
    uv = np.zeros((len(mesh.loops), 2))
    mesh.uv_layers.active.data.foreach_get("uv", uv.reshape(-1))
    verts = np.array([v.co for v in mesh.vertices])
    for t in mesh.loop_triangles:
        p = verts[list(t.vertices)]
        if p[:, 2].max() < min_z:
            continue
        q = uv[list(t.loops)] * size
        x0, y0 = np.floor(q.min(axis=0)).astype(int)
        x1, y1 = np.ceil(q.max(axis=0)).astype(int) + 1
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, size), min(y1, size)
        if x1 <= x0 or y1 <= y0:
            continue
        a, b, c = q
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
        w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
        val = w0[..., None] * p[0] + w1[..., None] * p[1] + w2[..., None] * p[2]
        pos[y0:y1, x0:x1][inside] = val[inside]
        mask[y0:y1, x0:x1][inside] = True
    return pos, mask


def _line(x, z, pts, width, depth):
    width = width * LINE_WIDTH
    """A crease along a polyline in the frontal (x, z) plane, tapering at both ends."""
    pts = np.asarray(pts)
    best = np.full(x.shape, 1e9)
    along = np.zeros(x.shape)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    total, run = seg.sum(), 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ab = b - a
        t = np.clip(((x - a[0]) * ab[0] + (z - a[1]) * ab[1]) / (ab @ ab), 0, 1)
        d = np.hypot(x - (a[0] + t * ab[0]), z - (a[1] + t * ab[1]))
        closer = d < best
        best[closer] = d[closer]
        along[closer] = (run + t[closer] * seg[i]) / total
        run += seg[i]
    return depth * np.exp(-(best / width) ** 2) * np.sin(np.pi * np.clip(along, 0, 1)) ** 0.6


def _wiggle(x0, x1, z, rng, n=9, amount=0.0012, bow=0.0):
    xs = np.linspace(x0, x1, n)
    zs = z + rng.normal(0, amount, n) + bow * (1 - (2 * (xs - x0) / (x1 - x0) - 1) ** 2)
    return np.stack([xs, zs], axis=1)


def _ray(start, angle, length, rng, n=5, bend=0.12):
    a = np.radians(angle)
    pts, p = [], np.array(start, dtype=float)
    for _ in range(n):
        pts.append(p.copy())
        a += rng.normal(0, bend)
        p = p + np.array([np.cos(a), np.sin(a)]) * length / (n - 1)
    return np.array(pts)


LINE_WIDTH = 1.0


def build_maps(mesh, face, spec, seed, out_dir):
    """`face`: positions measured on the built character. Returns (height image, colour image), both packed."""
    global LINE_WIDTH
    LINE_WIDTH = spec["line_width"]
    size = spec["size"]
    rng = np.random.default_rng(seed)
    pos, mask = _position_map(mesh, size, face["neck_z"])
    x, y, z = pos[..., 0] - face["cx"], pos[..., 1], pos[..., 2]
    front = y < face["cy"] + 0.015
    h = np.zeros(x.shape, dtype=np.float32)
    k = spec["depth"]
    ex, ez, mz, nz, bz = face["eye_x"], face["eye_z"], face["mouth_z"], face["nose_z"], face["brow_z"]
    # forehead lines
    for i, dz in enumerate(np.array(spec["forehead_lines"])):
        h += _line(x, z, _wiggle(-0.056, 0.056, bz + dz, rng, bow=0.002), 0.0013, k * (1.0 - 0.1 * i))
    # frown lines between the brows
    for side in (-1, 1):
        h += _line(x, z, _ray((side * 0.006, bz - 0.006), 90 - side * 8, 0.014, rng), 0.0013, k * 0.6)
    for s in (-1, 1):
        cx_eye = s * ex
        # crow's feet, fanning out from the eye's outer corner
        for ang in spec["crow_angles"]:
            base = 0 if s > 0 else 180
            a = base + (ang if s > 0 else -ang)
            h += _line(x, z, _ray((cx_eye + s * 0.019, ez + ang * 0.00006), a, 0.015, rng), 0.0009, k * 0.7)
        # bags: arcs under the eye
        for dz, d in ((0.011, 0.7), (0.019, 0.5)):
            arc = _wiggle(cx_eye - 0.017, cx_eye + 0.019, ez - dz, rng, amount=0.0006, bow=-0.004)
            h += _line(x, z, arc, 0.0011, k * d)
        # nose-to-mouth fold and the fold below the mouth corner
        h += _line(x, z, [(s * 0.017, nz + 0.002), (s * 0.026, mz + 0.012), (s * 0.033, mz - 0.006)], 0.0021, k * 1.3)
        h += _line(x, z, [(s * 0.027, mz - 0.004), (s * 0.03, mz - 0.03)], 0.0016, k * 0.8)
    # fine vertical lines around the mouth
    for lx in rng.uniform(-0.023, 0.023, spec["lip_lines"]):
        h += _line(x, z, [(lx, mz + 0.004), (lx * 1.05, mz + 0.009 + rng.uniform(0, 0.004))], 0.0006, k * 0.28)
    h *= front
    # neck rings run all the way round
    neck = np.zeros(x.shape, dtype=np.float32)
    for dz in spec["neck_lines"]:
        neck += _line(x, z, _wiggle(-0.08, 0.08, face["chin_z"] + dz, rng, n=7, bow=0.006), 0.0022, k * 0.9)
    h += neck * (z < face["chin_z"])
    # crepe texture: fine cross-hatch, stronger around the eyes and on the neck
    crepe = np.sin(x * 2300 + 2.0 * np.sin(z * 310)) * np.sin(z * 2900 + 2.0 * np.sin(x * 270))
    eye_zone = np.exp(-(((np.abs(x) - ex) / 0.03) ** 2 + ((z - ez) / 0.024) ** 2))
    neck_zone = np.clip((face["chin_z"] - z) / 0.03, 0, 1)
    h -= 0.5 * (crepe * spec["crepe"] * k) * (0.35 + eye_zone + neck_zone)
    height = 0.5 - np.clip(h, -0.5, 0.5)

    # tone: darker creases, age spots, redness on nose and cheeks
    tone = np.ones((size, size, 3), dtype=np.float32)
    tone *= (1 - spec["crease_dark"] * np.clip(h / (k * 1.3), 0, 1))[..., None]
    spots = np.zeros(x.shape, dtype=np.float32)
    for _ in range(spec["spots"]):
        sx, sz, r = rng.uniform(-0.07, 0.07), ez + rng.uniform(-0.055, 0.09), rng.uniform(0.002, 0.006)
        spots += rng.uniform(0.25, 1.0) * np.exp(-(((x - sx) ** 2 + (z - sz) ** 2) / r ** 2))
    spots = np.clip(spots, 0, 1) * front * spec["spot_strength"]
    tone *= np.stack([1 - 0.45 * spots, 1 - 0.62 * spots, 1 - 0.75 * spots], axis=-1)
    red = np.exp(-((x / 0.016) ** 2 + ((z - nz) / 0.02) ** 2)) + 0.6 * np.exp(-(((np.abs(x) - 0.042) / 0.022) ** 2 + ((z - nz) / 0.02) ** 2))
    red = np.clip(red, 0, 1) * front * spec["redness"]
    tone *= np.stack([1 - 0.02 * red, 1 - 0.3 * red, 1 - 0.3 * red], axis=-1)
    height[~mask] = 0.5
    tone[~mask] = 1

    def image(name, rgb, colorspace):
        path = f"{out_dir}\\{name}.png"
        _write_png16(path, rgb)
        img = bpy.data.images.load(path, check_existing=False)
        img.colorspace_settings.name = colorspace
        img.pack()
        return img

    return image("character_wrinkles", np.repeat(height[..., None], 3, axis=2), "Non-Color"), image("character_age_tone", tone, "sRGB")


def apply_maps(group, height_img, tone_img, spec):
    t = group
    bsdf = next(n for n in t.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    tex_h = t.nodes.new("ShaderNodeTexImage"); tex_h.image = height_img
    bump = t.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = spec["bump_distance"]
    bump.inputs["Strength"].default_value = 1.0
    t.links.new(tex_h.outputs[0], bump.inputs["Height"])
    if bsdf.inputs["Normal"].links:
        t.links.new(bsdf.inputs["Normal"].links[0].from_socket, bump.inputs["Normal"])
    t.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    tex_t = t.nodes.new("ShaderNodeTexImage"); tex_t.image = tone_img
    base = bsdf.inputs["Base Color"].links[0].from_socket
    mix = t.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1
    t.links.new(base, mix.inputs["A"])
    t.links.new(tex_t.outputs[0], mix.inputs["B"])
    t.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])

"""Readers for the permissive mesh sources: OpenSim .vtp and .osim (Rajagopal, MIT), the BMF .mat (zlib)."""
import re, xml.etree.ElementTree as ET
import numpy as np


def read_vtp(path):
    """ASCII VTP polygons as (vertices, triangles); larger polygons are fanned."""
    text = open(path, encoding="utf-8", errors="replace").read()
    root = ET.fromstring(text)
    piece = root.find(".//Piece")
    pts = np.array(piece.find("Points/DataArray").text.split(), dtype=float).reshape(-1, 3)
    polys = {d.get("Name"): np.array(d.text.split(), dtype=np.int64) for d in piece.find("Polys").findall("DataArray")}
    tris, start = [], 0
    for end in polys["offsets"]:
        ring = polys["connectivity"][start:end]
        for i in range(1, len(ring) - 1):
            tris.append((ring[0], ring[i], ring[i + 1]))
        start = end
    return pts, np.array(tris, dtype=np.int32)


def bmf_to_model(points):
    """BMF is x forward, y left, z up."""
    p = np.asarray(points, dtype=float)
    return np.column_stack([p[:, 1], -p[:, 0], p[:, 2]])


def opensim_to_model(points):
    """OpenSim is x forward, y up, z right; the model faces -Y with its left on +X."""
    p = np.asarray(points, dtype=float)
    return np.column_stack([-p[:, 2], -p[:, 0], p[:, 1]])


def osim_bodies(path):
    """{body: [mesh file, ...]} and the muscles' path points as read from an .osim file."""
    root = ET.parse(path).getroot()
    bodies = {}
    for b in root.iter("Body"):
        bodies[b.get("name")] = [m.find("mesh_file").text for m in b.iter("Mesh") if m.find("mesh_file") is not None]
    muscles = {}
    for m in root.iter("Millard2012EquilibriumMuscle"):
        pts = []
        for p in m.find("GeometryPath").iter():
            if p.tag.endswith("PathPoint") or p.tag == "ConditionalPathPoint":
                loc = p.find("location")
                sock = p.find("socket_parent_frame")
                if loc is not None and sock is not None:
                    pts.append({"body": sock.text.rsplit("/", 1)[-1], "location": [float(x) for x in loc.text.split()]})
        muscles[m.get("name")] = {"points": pts, "max_force": float(m.find("max_isometric_force").text), "fiber_length": float(m.find("optimal_fiber_length").text), "tendon_length": float(m.find("tendon_slack_length").text)}
    return bodies, muscles


def osim_joints(path):
    """{child body: (parent body, joint translation in the parent)}, the model's static chain."""
    root = ET.parse(path).getroot()
    out = {}
    for joint in root.find(".//JointSet/objects"):
        child, parent = joint.find("socket_child_frame").text, joint.find("socket_parent_frame").text
        frames = {f.get("name"): f for f in joint.iter("PhysicalOffsetFrame")}
        pf, cf = frames[parent], frames[child]
        pbody = pf.find("socket_parent").text.rsplit("/", 1)[-1]
        cbody = cf.find("socket_parent").text.rsplit("/", 1)[-1]
        out[cbody] = (pbody, [float(x) for x in pf.find("translation").text.split()])
    return out


def bmf_bones(mat_path):
    """{bone: {verts, faces, landmarks, socket, condyles}} from the BMF toolkit, in its global frame, metres."""
    import scipy.io as sio
    model = sio.loadmat(mat_path, squeeze_me=True, struct_as_record=False)["model_Original"]
    out = {}
    for b in model:
        v = np.asarray(b.vertices_global, dtype=float)
        f = np.asarray(b.faces, dtype=np.int64) - 1
        out[str(b.BoneName)] = {"verts": v, "faces": f, "landmarks": dict(zip(np.atleast_1d(b.LandmarkNames).tolist(), (np.atleast_1d(b.LandmarkIndices).astype(int) - 1).tolist())) if np.size(b.LandmarkNames) else {}, "socket": np.atleast_1d(b.femoralSocket).astype(int) - 1, "condyles": np.atleast_1d(b.femoralCondyles).astype(int) - 1}
    return out

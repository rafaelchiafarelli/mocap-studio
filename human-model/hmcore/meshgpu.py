"""Point queries against a triangle mesh on the GPU, through Warp's meshes: inside or outside by winding number, and the closest point.
For millions of points, where fit.winding_number on the CPU would take tens of minutes. GPU image only: hm.sh --gpu."""
import numpy as np
import warp as wp

FAR = 100.0  # m: every query looks this far, so every point finds the mesh


@wp.kernel
def _inside(mesh: wp.uint64, points: wp.array(dtype=wp.vec3), out: wp.array(dtype=wp.int8)):
    i = wp.tid()
    q = wp.mesh_query_point_sign_winding_number(mesh, points[i], FAR)
    out[i] = wp.int8(0)
    if q.result and q.sign < 0.0:
        out[i] = wp.int8(1)


@wp.kernel
def _closest(mesh: wp.uint64, points: wp.array(dtype=wp.vec3), dist: wp.array(dtype=float), face: wp.array(dtype=int),
             bary: wp.array(dtype=wp.vec2)):
    i = wp.tid()
    q = wp.mesh_query_point_no_sign(mesh, points[i], FAR)
    if q.result:
        p = wp.mesh_eval_position(mesh, q.face, q.u, q.v)
        dist[i] = wp.length(p - points[i])
        face[i] = q.face
        bary[i] = wp.vec2(q.u, q.v)
    else:
        dist[i] = FAR
        face[i] = -1


class Mesh:
    """A triangle mesh on the GPU. Winding numbers need it closed, and tell inside from outside even across small holes."""

    def __init__(self, verts, tris, device="cuda:0"):
        self.device = device
        self.points = wp.array(np.asarray(verts, np.float32), dtype=wp.vec3, device=device)
        self.indices = wp.array(np.asarray(tris, np.int32).ravel(), dtype=int, device=device)
        self.mesh = wp.Mesh(points=self.points, indices=self.indices, support_winding_number=True)

    def inside(self, points, chunk=2_000_000):
        """True for each point inside the mesh."""
        points = np.asarray(points, np.float32)
        out = np.empty(len(points), bool)
        for s in range(0, len(points), chunk):
            p = wp.array(points[s:s + chunk], dtype=wp.vec3, device=self.device)
            o = wp.zeros(len(p), dtype=wp.int8, device=self.device)
            wp.launch(_inside, len(p), [self.mesh.id, p, o], device=self.device)
            out[s:s + chunk] = o.numpy().astype(bool)
        return out

    def closest(self, points, chunk=2_000_000):
        """Distance to the surface, the closest face, and Warp's barycentric (u, v) on it: the point is u*a + v*b + (1-u-v)*c."""
        points = np.asarray(points, np.float32)
        dist, face, bary = np.empty(len(points)), np.empty(len(points), int), np.empty((len(points), 2))
        for s in range(0, len(points), chunk):
            p = wp.array(points[s:s + chunk], dtype=wp.vec3, device=self.device)
            d = wp.zeros(len(p), dtype=float, device=self.device)
            f = wp.zeros(len(p), dtype=int, device=self.device)
            b = wp.zeros(len(p), dtype=wp.vec2, device=self.device)
            wp.launch(_closest, len(p), [self.mesh.id, p, d, f, b], device=self.device)
            dist[s:s + chunk], face[s:s + chunk], bary[s:s + chunk] = d.numpy(), f.numpy(), b.numpy()
        return dist, face, bary

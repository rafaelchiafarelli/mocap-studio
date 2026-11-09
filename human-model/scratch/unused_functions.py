"""Functions no code or test calls, moved verbatim from their modules on 2026-11-08. Not runnable here: they use their modules' imports."""


# from hmcore/ctbones.py
def principal_length(verts):
    """Extent along the main axis, for long bones."""
    v = verts - verts.mean(axis=0)
    axis = np.linalg.svd(v[:: max(1, len(v) // 5000)], full_matrices=False)[2][0]
    d = v @ axis
    return float(d.max() - d.min())


# from hmcore/retarget.py
def capture_to_model(points):
    """Capture frame to the model's frame, chosen from the data: up from ankles to shoulders; +X the body's left, so the body faces -Y by construction of the first frame."""
    return points


# from hmcore/softtissue.py
def cotan(v, t):
    """Cotangent Laplacian and lumped mass."""
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    def cot(p, q, r):
        x, y = q - p, r - p
        return (x * y).sum(axis=1) / np.maximum(np.linalg.norm(np.cross(x, y), axis=1), 1e-12)
    ca, cb, cc = cot(a, b, c), cot(b, c, a), cot(c, a, b)
    i = np.concatenate([t[:, 1], t[:, 2], t[:, 2], t[:, 0], t[:, 0], t[:, 1]])
    j = np.concatenate([t[:, 2], t[:, 1], t[:, 0], t[:, 2], t[:, 1], t[:, 0]])
    w = 0.5 * np.concatenate([ca, ca, cb, cb, cc, cc])
    w = np.clip(w, 0.0, 5.0)  # negative weights on bad triangles destabilize the solve
    n = len(v)
    W = sp.coo_matrix((w, (i, j)), shape=(n, n)).tocsr()
    L = sp.diags(np.asarray(W.sum(axis=1)).ravel()) - W
    return L, vertex_areas(v, t)


# from hmcore/tsdata.py
def pick_donors(meta, cov, sex, age=(25, 50), n=5):
    """The most complete scans of one sex, without recorded pathology. Coverage is only a filter: a person checks the result."""
    rows = [r for r in meta if r["gender"] == sex and r["age"] and age[0] <= r["age"] <= age[1] and r["pathology"] == "no_pathology"]
    scored = [(whole_body_score(cov.get(r["image_id"], {})), r["image_id"]) for r in rows]
    return [s for s in sorted(scored, reverse=True) if s[0] > 0][:n]

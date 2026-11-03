"""Label volumes to meshes in the model's frame: metres, the body faces -Y, its left is +X, up is +Z."""
import numpy as np


def ras_to_model(points_mm):
    """RAS millimetres to the model's frame; a half turn about Z plus the unit change, so nothing gets mirrored."""
    p = np.asarray(points_mm, dtype=float) / 1000.0
    return np.column_stack([-p[:, 0], -p[:, 1], p[:, 2]])


def largest_component(mask):
    from scipy import ndimage
    labels, n = ndimage.label(mask)
    if n <= 1:
        return mask
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    return labels == counts.argmax()


def mask_to_mesh(mask, affine, sigma=0.7):
    """Marching cubes on the smoothed mask. Returns vertices in the model's frame and faces with outward normals."""
    from scipy import ndimage
    from skimage import measure
    pad = np.pad(mask.astype(np.float32), 2)
    smooth = ndimage.gaussian_filter(pad, sigma)
    verts, faces, _, _ = measure.marching_cubes(smooth, 0.5)
    verts = verts - 2.0
    world = verts @ affine[:3, :3].T + affine[:3, 3]
    out = ras_to_model(world)
    if signed_volume(out, faces) < 0:
        faces = faces[:, ::-1]
    return out.astype(np.float32), faces.astype(np.int32)


def signed_volume(verts, faces):
    a, b, c = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def load_label(path):
    """A NIfTI label as (bool array, affine), reoriented to RAS."""
    import nibabel as nib
    img = nib.as_closest_canonical(nib.load(path))
    return np.asanyarray(img.dataobj) > 0, img.affine


def touches_scan_edge(mask, margin=1):
    """True when the label reaches any face of the volume: the bone is cut, so its size can't be trusted. Arms are usually cut by the sides of the field of view, not the top or bottom."""
    if not mask.any():
        return True
    idx = np.argwhere(mask)
    return bool((idx.min(axis=0) < margin).any() or (idx.max(axis=0) >= np.array(mask.shape) - margin).any())


def principal_length(verts):
    """Extent along the main axis, for long bones."""
    v = verts - verts.mean(axis=0)
    axis = np.linalg.svd(v[:: max(1, len(v) // 5000)], full_matrices=False)[2][0]
    d = v @ axis
    return float(d.max() - d.min())


def split_mandible(skull):
    """The dataset's skull label holds the mandible too. Erosion leaves two seeds (the mandible's body and the cranium), and a watershed on the distance map grows them back until they meet at the thin contact points.
    Returns (cranium mask, mandible mask); the mandible is None when no seed appears."""
    from scipy import ndimage
    from skimage.segmentation import watershed
    labels, _ = ndimage.label(ndimage.binary_erosion(skull, iterations=3))
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    cranium = sizes.argmax()
    z_low = {k: np.argwhere(labels == k)[:, 2].min() for k in np.flatnonzero(sizes > 2000) if k != cranium}
    if not z_low:
        return skull, None
    jaw = min(z_low, key=z_low.get)
    markers = np.zeros(skull.shape, np.int32)
    markers[labels == cranium] = 1
    markers[labels == jaw] = 2
    dist = ndimage.distance_transform_edt(skull)
    grown = watershed(-dist, markers, mask=skull)
    return grown == 1, grown == 2

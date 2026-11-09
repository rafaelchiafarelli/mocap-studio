"""Physical values per tetrahedron: one default per tissue, from data/body_tissue.json, and overrides by tissue and zone (its REGIONS table).
An override changes smoothly between zones, as the fat thickness does: it fades in over SMOOTH_VOXELS cubes at the zone's border. With no overrides the values are the tissue defaults."""
import numpy as np
from scipy import ndimage

SMOOTH_VOXELS = 3
VALUES = ("young", "density", "poisson", "damping")
KEY = {"bone": "MUSCLE", "muscle": "MUSCLE", "fat": "FAT", "skin": "SKIN", "cavity": "CAVITY", "fat_deep": "FAT_DEEP", "gland": "GLAND", "viscera": "VISCERA"}


def defaults(cfg, labels):
    """{label: {young, density, poisson, damping}} from the tissue table: Young and density by tissue, Poisson and damping shared unless a tissue gives its own."""
    out = {}
    for name in labels:
        k = KEY[name]
        out[name] = {"young": cfg[f"{k}_YOUNG"], "density": cfg[f"{k}_DENSITY"], "poisson": cfg.get(f"{k}_POISSON", cfg["POISSON"]), "damping": cfg.get(f"{k}_DAMPING", cfg["DAMPING"])}
    return out


def per_tet(label, zone, voxel_of_tet, vox, table, regions, labels, zones):
    """Arrays per tetrahedron: {young, density, poisson, damping}. label and zone are per tetrahedron, voxel_of_tet its voxel and vox each voxel's grid coordinates.
    regions: {tissue: {zone: {value: number}}}; an override applies to that tissue only."""
    out = {v: np.empty(len(label), float) for v in VALUES}
    for i, name in enumerate(labels):
        for v in VALUES:
            out[v][label == i] = table[name][v]
    for tissue, by_zone in regions.items():
        t = labels.index(tissue)
        m = label == t
        for zone_name, values in by_zone.items():
            weight = _fade(m & (zone == zones.index(zone_name)), m, voxel_of_tet, vox)
            for v, value in values.items():
                out[v][m] += weight[m] * (value - table[tissue][v])
    return out


def _fade(in_zone, in_tissue, voxel_of_tet, vox):
    """1 in the zone's core, fading to 0 over SMOOTH_VOXELS beyond it, on the voxels' grid. Averaged within the tissue only: a layer one or two cubes thick would otherwise lose most of its override to the empty space around it."""
    shape = vox.max(axis=0) + 1
    zone, tissue = np.zeros(shape), np.zeros(shape)
    zone[tuple(vox[voxel_of_tet[in_zone]].T)] = 1.0
    tissue[tuple(vox[voxel_of_tet[in_tissue]].T)] = 1.0
    faded = ndimage.uniform_filter(zone, size=SMOOTH_VOXELS) / np.maximum(ndimage.uniform_filter(tissue, size=SMOOTH_VOXELS), 1e-9)
    return np.clip(faded, 0, 1)[tuple(vox[voxel_of_tet].T)]


def node_values(tets, values, n_nodes):
    """Each node's value: the mean of its tetrahedra's. The solver damps nodes, so a value per tetrahedron becomes one per node."""
    total = np.zeros(n_nodes)
    count = np.zeros(n_nodes)
    np.add.at(total, tets.ravel(), np.repeat(values, 4))
    np.add.at(count, tets.ravel(), 1.0)
    return total / np.maximum(count, 1)

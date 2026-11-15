"""Anny with MPFB 2.0.18's own macro formula, so its parameters are MPFB's sliders.

Anny loads the same MakeHuman targets as MPFB but mixes them differently: gender 0 is male, age has a newborn anchor
(MPFB's 0.5 is Anny's 2/3), height and proportions use two anchors instead of MPFB's three, races are normalised,
and breast targets are scaled by the female weight. Here `phenotype_blendshape_weights` is replaced by MPFB's rules
(`services/targetservice.py`, `_interpolate_macro_components` and `calculate_target_stack_from_macro_info_dict`),
continued in a straight line outside 0..1 as the mpfb_ganho add-on does.

    model = mpfb_anny.model()                       # rig and topology "makehuman": MPFB's 19,158 vertices in its order
    out = mpfb_anny.forward(model, macros, targets) # macros: MPFB names, races included; targets: MPFB target names
"""
import torch
import anny
import anny.models.phenotype as ph

# MPFB's macro.json parts: (lowest, highest, low, high). An empty name is the neutral body.
PARTS = {
    "gender": [(-0.01, 1.01, "female", "male")],
    "age": [(-0.01, 0.1874998, "baby", "child"), (0.1874999, 0.49998, "child", "young"), (0.49999, 1.01, "young", "old")],
    "muscle": [(-0.01, 0.49998, "minmuscle", "averagemuscle"), (0.49999, 1.01, "averagemuscle", "maxmuscle")],
    "weight": [(-0.01, 0.49998, "minweight", "averageweight"), (0.49999, 1.01, "averageweight", "maxweight")],
    "proportions": [(-0.01, 0.4999, "uncommonproportions", ""), (0.5, 1.01, "", "idealproportions")],
    "height": [(-0.01, 0.49, "minheight", ""), (0.51, 1.01, "", "maxheight")],
    "cupsize": [(-0.01, 0.49998, "mincup", "averagecup"), (0.49999, 1.01, "averagecup", "maxcup")],
    "firmness": [(-0.01, 0.4998, "minfirmness", "averagefirmness"), (0.4999, 1.01, "averagefirmness", "maxfirmness")],
}
CUTOFF = 0.01  # set to 0 for a smooth fit
RACES = ("african", "asian", "caucasian")
MACROS = list(PARTS) + list(RACES)
DEFAULTS = {"gender": 0.5, "age": 0.5, "muscle": 0.5, "weight": 0.5, "proportions": 0.5, "height": 0.5, "cupsize": 0.5, "firmness": 0.5,
            "african": 0.33, "asian": 0.33, "caucasian": 0.33}


def mpfb_coefficients(feature, value):
    """{variation: weight tensor}, MPFB's interpolation; outside 0..1 the end segment goes on in a straight line."""
    parts = PARTS[feature]
    out = {}
    for i, (lo, hi, low, high) in enumerate(parts):
        inside = (value > lo) & (value < hi)
        if i == 0:
            inside = inside | (value <= lo)
        if i == len(parts) - 1:
            inside = inside | (value >= hi)
        t = (value - lo) / (hi - lo)
        for name, w in ((low, 1 - t), (high, t)):
            if name:
                out[name] = out.get(name, 0) + torch.where(inside, w, torch.zeros_like(w))
    return out


def mpfb_blendshape_weights(phenotype_parameters, phenotype_labels, anchors, stacked_phenotype_blend_shapes_mask, extrapolate):
    """Drop-in for anny.models.phenotype.phenotype_blendshape_weights, with MPFB's rules."""
    B = phenotype_parameters.shape[0]

    def value(label):
        if label in phenotype_labels:
            return phenotype_parameters[:, phenotype_labels.index(label)]
        return phenotype_parameters.new_full((B,), DEFAULTS[label])

    coeff = {}
    for feature in PARTS:
        coeff.update(mpfb_coefficients(feature, value(feature)))
    for race in RACES:
        coeff[race] = value(race)  # MPFB doesn't normalise races
    zero = phenotype_parameters.new_zeros((B,))
    columns = [key for keys in ph.PHENOTYPE_VARIATIONS.values() for key in keys]
    phens = torch.stack([coeff.get(key, zero) for key in columns], dim=1)
    mask = stacked_phenotype_blend_shapes_mask.clone()
    # MPFB's breast targets aren't scaled by the female weight (targetservice: "there are no male complementary targets")
    cup = [columns.index(k) for k in ph.PHENOTYPE_VARIATIONS["cupsize"]]
    breast_rows = mask[:, cup].sum(1) > 0
    for g in ph.PHENOTYPE_VARIATIONS["gender"]:
        mask[breast_rows, columns.index(g)] = 0
    mask = mask.unsqueeze(0)
    w = torch.prod(phens.unsqueeze(1) * mask + (1 - mask), dim=-1)
    # MPFB keeps a combination only above a weight of 0.01 (calculate_target_stack_from_macro_info_dict's cutoff)
    return torch.where(w.abs() > CUTOFF, w, torch.zeros_like(w)) if CUTOFF else w


ph.phenotype_blendshape_weights = mpfb_blendshape_weights


def model(dtype=torch.float32, device="cpu"):
    m = anny.Anny(topology="makehuman", rig="makehuman", local_changes="all", phenotypes="all",
                  phenotype_blendshapes="original", extrapolate_phenotypes=True)
    return m.to(dtype=dtype, device=device)


def local_changes(m, targets):
    """MPFB target names (…-incr, …-decr, one-way names) to Anny's local changes, where -decr is the -incr label negative.
    Returns (dict, missing names)."""
    labels = set(m.local_change_labels)
    out, missing = {}, []
    for name, v in targets.items():
        if name in labels:
            out[name] = out.get(name, 0) + v
        elif name.endswith("-decr") and name[:-5] + "-incr" in labels:
            out[name[:-5] + "-incr"] = out.get(name[:-5] + "-incr", 0) - v
        else:
            missing.append(name)
    return out, missing


def forward(m, macros, targets=None, pose=None):
    """Vertices (1, 19158, 3) for MPFB macros (races flat or under 'race') and targets."""
    flat = dict(DEFAULTS)
    for k, v in macros.items():
        if k == "race":
            flat.update(v)
        else:
            flat[k] = v
    dev, dt = next(m.buffers()).device, next(m.buffers()).dtype
    t = lambda v: v.reshape(1).to(dev, dt) if torch.is_tensor(v) else torch.tensor([float(v)], device=dev, dtype=dt)
    if pose is None:
        pose = torch.eye(4, device=dev, dtype=dt)[None, None].repeat(1, m.bone_count, 1, 1)
    loc, missing = local_changes(m, targets or {})
    if missing:
        raise KeyError(f"targets Anny doesn't have: {missing}")
    return m(pose_parameters=pose, phenotype_kwargs={k: t(flat[k]) for k in m.phenotype_labels},
             local_changes_kwargs={k: t(v) for k, v in loc.items()})

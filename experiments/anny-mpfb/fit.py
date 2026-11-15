"""Fits MPFB sliders (11 macros and Anny's 256 local targets) and one pose per frame to silhouettes and 2D joints.
Library used by fit_synthetic.py now and by the video fit later. Pure PyTorch: no rasterizer.

Silhouette terms, both in pixels:
- inside: every projected body vertex should fall inside the mask (distance outside the mask, sampled from a distance map);
- cover: every point of the mask's outline should have a projected body vertex near it.
Plus 2D joints, and small pulls of the locals towards 0, the macros towards 0.5 and the pose towards rest.

Camera: a pinhole at distance `dist` in front of the body (looking along +Y in Blender's axes: image x = X, image y = -Z),
focal `f` in pixels. Each frame has its own yaw (the view: 0 front, 90 side, 180 back), set from outside, and its own pose."""
import math
import numpy as np
import torch
import roma
import mpfb_anny

N_BODY = 13380
JOINTS = ["upperleg01.L", "upperleg01.R", "lowerleg01.L", "lowerleg01.R", "foot.L", "foot.R", "upperarm01.L", "upperarm01.R",
          "lowerarm01.L", "lowerarm01.R", "wrist.L", "wrist.R", "neck01", "head"]


class Camera:
    def __init__(self, f=2000.0, dist=10.0, size=(1080, 1920)):
        self.f, self.dist, self.w, self.h = f, dist, size[0], size[1]

    def project(self, pts, yaw_deg, shift):
        """pts (B, N, 3) Blender axes; yaw per frame (B,) degrees, rotates the body about Z; shift (B, 3) body translation."""
        a = torch.deg2rad(yaw_deg)
        c, s = torch.cos(a), torch.sin(a)
        x, y, z = pts[..., 0], pts[..., 1], pts[..., 2]
        xr = c[:, None] * x - s[:, None] * y + shift[:, None, 0]
        yr = s[:, None] * x + c[:, None] * y + shift[:, None, 1]
        zr = z + shift[:, None, 2]
        depth = self.dist + yr  # camera at y = -dist looking along +y
        u = self.f * xr / depth + self.w / 2
        v = -self.f * zr / depth + self.h / 2
        return torch.stack([u, v], -1)


# MPFB's macros with a flat stretch at mid range, where the body doesn't change (macro.json: height 0.49..0.51, proportions 0.4999..0.5).
# The optimiser works on u, which skips it: value = u + half * sign(u - mid), so the gradient is never zero.
GAPS = {"height": (0.49, 0.51), "proportions": (0.4999, 0.5)}


def to_mpfb(labels, u):
    v = u.clone()
    for k, (a, b) in GAPS.items():
        i = labels.index(k)
        v[i] = u[i] + (b - a) / 2 * torch.sign(u[i] - (a + b) / 2)
    return v


def from_mpfb(labels, v):
    u = v.clone()
    for k, (a, b) in GAPS.items():
        i = labels.index(k)
        mid = (a + b) / 2
        u[i] = v[i] - (b - a) / 2 * torch.sign(v[i] - mid) if abs(float(v[i]) - mid) > 1e-9 else mid + 1e-4
    return u


class Shape(torch.nn.Module):
    """Parameters to fit: macros, locals, per-frame pose rotations (rotvecs) and body translation."""

    def __init__(self, m, frames, macros=None, locals_=None, pose_of_frame=None):
        super().__init__()
        self.m = m
        dev, dt = next(m.buffers()).device, next(m.buffers()).dtype
        n_mac, n_loc = len(m.phenotype_labels), len(m.local_change_labels)
        init = torch.tensor([mpfb_anny.DEFAULTS[k] for k in m.phenotype_labels], device=dev, dtype=dt)
        labels = list(m.phenotype_labels)
        self.macros = torch.nn.Parameter(from_mpfb(labels, init if macros is None else macros.clone()))  # u, see GAPS
        self.locals_ = torch.nn.Parameter(torch.zeros(n_loc, device=dev, dtype=dt) if locals_ is None else locals_.clone())
        # Frames seen at the same instant from several cameras share one pose: pose_of_frame[i] is frame i's pose
        self.pose_of_frame = list(range(frames)) if pose_of_frame is None else list(pose_of_frame)
        P = max(self.pose_of_frame) + 1
        self.rot = torch.nn.Parameter(torch.zeros(P, m.bone_count, 3, device=dev, dtype=dt))
        self.shift_p = torch.nn.Parameter(torch.zeros(P, 3, device=dev, dtype=dt))
        self.frames = frames

    @property
    def shift(self):
        return self.shift_p[self.pose_of_frame]

    def pose_matrices(self):
        rot = self.rot[self.pose_of_frame]
        B, J = rot.shape[:2]
        M = torch.eye(4, device=rot.device, dtype=rot.dtype).repeat(B, J, 1, 1)
        M[..., :3, :3] = roma.rotvec_to_rotmat(rot)
        return M

    def effective(self):
        """The macros as MPFB values."""
        return to_mpfb(list(self.m.phenotype_labels), self.macros)

    def forward(self):
        m, B = self.m, self.frames
        mac = self.effective()
        out = m(pose_parameters=self.pose_matrices(),
                phenotype_kwargs={k: mac[i].expand(B) for i, k in enumerate(m.phenotype_labels)},
                local_changes_kwargs={k: self.locals_[i].expand(B) for i, k in enumerate(m.local_change_labels)})
        self.last_rest = out["rest_vertices"]
        return out["vertices"], out["bone_poses"][..., :3, 3]

    def recipe(self):
        mac = {k: round(float(v), 4) for k, v in zip(self.m.phenotype_labels, self.effective())}
        race = {r: mac.pop(r) for r in mpfb_anny.RACES}
        mac["race"] = race
        targets = {}
        for k, v in zip(self.m.local_change_labels, self.locals_.tolist()):
            if abs(v) >= 0.005:
                name = k if v > 0 or not k.endswith("-incr") else k[:-5] + "-decr"
                targets[name] = round(abs(v) if k.endswith("-incr") else v, 4)
        return {"macros": mac, "targets": targets}


def distance_outside(mask):
    """Pixels from each pixel to the mask (0 inside), as a float tensor (H, W). Brute force on a coarse grid, then upsampled."""
    from scipy.ndimage import distance_transform_edt
    return torch.from_numpy(distance_transform_edt(~mask).astype(np.float32))


def outline(mask, n=600, seed=0):
    from scipy.ndimage import binary_erosion
    edge = mask & ~binary_erosion(mask)
    ys, xs = np.nonzero(edge)
    idx = np.random.default_rng(seed).choice(len(xs), size=min(n, len(xs)), replace=False)
    return torch.from_numpy(np.stack([xs[idx], ys[idx]], 1).astype(np.float32))


def sample(img, uv):
    """Bilinear sample of img (H, W) at uv (N, 2) pixels."""
    H, W = img.shape
    g = torch.stack([uv[:, 0] / (W - 1) * 2 - 1, uv[:, 1] / (H - 1) * 2 - 1], -1)[None, None]
    return torch.nn.functional.grid_sample(img[None, None], g, align_corners=True, padding_mode="border")[0, 0, 0]


BODY_WORDS = ("measure-", "hip-", "torso-", "upperarm-", "lowerarm-", "upperleg", "lowerleg", "buttocks-", "stomach-", "breast-", "neck-",
              "l-upperarm", "r-upperarm", "l-lowerarm", "r-lowerarm", "l-upperleg", "r-upperleg", "l-lowerleg", "r-lowerleg", "l-leg", "r-leg", "pelvis-")


def body_local_mask(m):
    """1 for the targets that change the trunk and limbs, 0 for face, ears, hands, feet, genitals."""
    return torch.tensor([1.0 if l.startswith(BODY_WORDS) and not l.startswith(("measure-wrist", "measure-ankle")) else 0.0
                         for l in m.local_change_labels], device=next(m.buffers()).device, dtype=next(m.buffers()).dtype)


def joint_index(m):
    labels = list(m.bone_labels)
    return [labels.index(j) for j in JOINTS]


def fit(m, cam, frames, steps=600, lr=0.02, w_joint=1.0, w_inside=1.0, w_cover=1.0, w_loc=0.02, w_mac=0.001, w_pose=0.01,
        fit_locals=True, local_mask=None, fixed=None, hold_depth=True, stature=None, w_stature=1e5, init_shift=None, log=None):
    """frames: list of dicts with 'yaw' (deg), 'mask' (H, W bool numpy), optionally 'joints' (len(JOINTS), 2) pixels, NaN where unseen,
    'outline' (N, 2) pixels to use instead of the mask's whole outline, and 'pose' (frames of one instant share it).
    fixed: {macro: value} held (e.g. gender 0 for women). stature: metres, the rest body's height, held by a penalty; with it the
    depth can be free (hold_depth False), since the size is known. init_shift: (B, 3) the body's start translation per frame.
    Returns the Shape."""
    dev, dt = next(m.buffers()).device, next(m.buffers()).dtype
    B = len(frames)
    shape = Shape(m, B, pose_of_frame=[f.get("pose", i) for i, f in enumerate(frames)])
    fixed = fixed or {}
    fixed_idx = {list(m.phenotype_labels).index(k): v for k, v in fixed.items()}
    fixed_idx = {i: float(from_mpfb(list(m.phenotype_labels), torch.tensor([0.5] * len(m.phenotype_labels)).index_fill(0, torch.tensor([i]), v))[i]) for i, v in fixed_idx.items()}
    with torch.no_grad():
        for i, v in fixed_idx.items():
            shape.macros[i] = v
    if init_shift is not None:
        with torch.no_grad():
            for b, p in enumerate(shape.pose_of_frame):
                shape.shift_p[p] = torch.as_tensor(init_shift[b], device=dev, dtype=dt)
    yaw = torch.tensor([f["yaw"] for f in frames], device=dev, dtype=dt)
    dmaps = [distance_outside(f["mask"]).to(dev, dt) for f in frames]
    outs = [(torch.as_tensor(f["outline"], dtype=torch.float32) if f.get("outline") is not None else outline(f["mask"], seed=i)).to(dev, dt)
            for i, f in enumerate(frames)]
    joints = [torch.as_tensor(f["joints"], device=dev, dtype=dt) if f.get("joints") is not None else None for f in frames]
    jidx = joint_index(m)
    params = [{"params": [shape.macros], "lr": lr}, {"params": [shape.rot, shape.shift_p], "lr": lr}]
    if fit_locals:
        params.append({"params": [shape.locals_], "lr": lr})
    opt = torch.optim.Adam(params)
    history = []
    for step in range(steps):
        # Coarse to fine: joints and macros first, silhouettes and locals after
        phase = min(1.0, step / (steps * 0.3))
        opt.zero_grad()
        verts, heads = shape()
        uv = cam.project(verts[:, :N_BODY], yaw, shape.shift)
        juv = cam.project(heads[:, jidx], yaw, shape.shift)
        l_in = l_cov = l_j = 0.0
        for b in range(B):
            l_in = l_in + sample(dmaps[b], uv[b]).square().mean()
            l_cov = l_cov + torch.cdist(outs[b], uv[b]).min(1).values.square().mean()
            if joints[b] is not None:
                seen = ~torch.isnan(joints[b][:, 0])
                l_j = l_j + (juv[b][seen] - joints[b][seen]).square().sum(-1).mean()
        l_in, l_cov, l_j = l_in / B, l_cov / B, l_j / B
        reg = w_loc * shape.locals_.square().sum() + w_mac * (shape.macros - 0.5).square().sum() + w_pose * shape.rot.square().sum() / B
        loss = w_joint * l_j + phase * (w_inside * l_in + w_cover * l_cov) + reg
        l_st = 0.0
        if stature is not None:
            z = shape.last_rest[0, :N_BODY, 2]
            l_st = (z.max() - z.min() - stature).square()
            loss = loss + w_stature * l_st
        loss.backward()
        if step < steps * 0.3 and fit_locals:
            shape.locals_.grad = None
        elif local_mask is not None and shape.locals_.grad is not None:
            shape.locals_.grad *= local_mask
        if hold_depth and shape.shift_p.grad is not None:
            shape.shift_p.grad[:, 1] = 0  # depth: a smaller body nearer the camera looks the same; the camera distance is held
        opt.step()
        with torch.no_grad():
            shape.macros.clamp_(-3, 3)
            for i, v in fixed_idx.items():
                shape.macros[i] = v
            shape.locals_.clamp_(-3, 3)
        if step % 50 == 0 or step == steps - 1:
            row = {"step": step, "loss": float(loss), "joint_px": float(l_j) ** 0.5 if joints[0] is not None else None,
                   "inside_px": float(l_in) ** 0.5, "cover_px": float(l_cov) ** 0.5, "stature_err_mm": float(l_st) ** 0.5 * 1000 if stature else None}
            history.append(row)
            if log:
                log(row)
    shape.history = history
    return shape


def masks_from_vertices(uv, faces, size):
    """Silhouette masks (B, H, W) bool by filling each projected face (PIL). uv (B, N, 2) numpy."""
    from PIL import Image, ImageDraw
    W, H = size
    out = []
    for b in range(len(uv)):
        img = Image.new("1", (W, H), 0)
        d = ImageDraw.Draw(img)
        p = uv[b]
        for f in faces:
            d.polygon([tuple(p[i]) for i in f], fill=1)
        out.append(np.array(img, dtype=bool))
    return out

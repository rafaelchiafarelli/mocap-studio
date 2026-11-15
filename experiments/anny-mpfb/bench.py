"""Test 2: speed and GPU memory of Anny-as-MPFB with gradients, as a fit would use it: one shape (11 macros + every local change)
shared by B frames, each with its own pose. experiments/anny-mpfb/run.sh python experiments/anny-mpfb/bench.py OUT.json"""
import json, sys, time
import torch
sys.path.insert(0, "experiments/anny-mpfb")
import mpfb_anny

mpfb_anny.CUTOFF = 0.0
dev = "cuda"
t0 = time.time()
m = mpfb_anny.model(dtype=torch.float32, device=dev)
report = {"build_s": round(time.time() - t0, 1), "device": torch.cuda.get_device_name(0), "locals": len(m.local_change_labels), "bones": m.bone_count, "runs": []}
for B in (1, 8, 32, 64):
    torch.cuda.reset_peak_memory_stats()
    macros = torch.full((len(m.phenotype_labels),), 0.5, device=dev, requires_grad=True)
    locs = torch.zeros((len(m.local_change_labels),), device=dev, requires_grad=True)
    pose = torch.eye(4, device=dev)[None, None].repeat(B, m.bone_count, 1, 1).requires_grad_(True)
    opt = torch.optim.Adam([macros, locs, pose], lr=1e-3)
    def step():
        opt.zero_grad()
        out = m(pose_parameters=pose,
                phenotype_kwargs={k: macros[i].expand(B) for i, k in enumerate(m.phenotype_labels)},
                local_changes_kwargs={k: locs[i].expand(B) for i, k in enumerate(m.local_change_labels)})
        loss = out["vertices"].square().mean()
        loss.backward()
        opt.step()
    for _ in range(3):
        step()
    torch.cuda.synchronize()
    t = time.time()
    n = 20
    for _ in range(n):
        step()
    torch.cuda.synchronize()
    ms = (time.time() - t) / n * 1000
    row = {"frames": B, "ms_per_step": round(ms, 1), "peak_vram_mb": round(torch.cuda.max_memory_allocated() / 2**20)}
    report["runs"].append(row)
    print(row)
json.dump(report, open(sys.argv[1], "w"), indent=1)

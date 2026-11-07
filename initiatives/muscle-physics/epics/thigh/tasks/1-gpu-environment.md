# 1. A GPU environment for soft-tissue simulation

**Asked by Rafael, 2026-11-07.** The thigh experiment runs on the RTX 4080, outside Blender. Before any tissue, this task proves that the project's Docker setup can use the GPU, and measures what a small tetrahedral simulation costs on it.

## Contract

**In:** the RTX 4080 SUPER (16 GB, driver 610.88, seen from WSL by `nvidia-smi`), the existing `human-model/Dockerfile` and `hm.sh`.

**Out:**
- A GPU image for `human-model` with NVIDIA Warp (`warp-lang`, Apache 2.0), pinned with hashes like `requirements.txt`. It lives beside the CPU image: `hmcore`'s tests keep running without a GPU.
- `hm.sh` runs it with `--gpu` (or a sibling script, whichever keeps `hm.sh pytest` unchanged).
- `human-model/tools/gpu_bench.py`: a cube of soft tetrahedra falling on a floor, simulated with XPBD in Warp, at several sizes from 10,000 to 1,000,000 tetrahedra.
- `DEPENDENCIES.md` updated: the GPU image, Warp's version and license, the host's container toolkit.

**Measured, and reported as measured:** milliseconds per simulation step and peak VRAM at each size; the same cube on the CPU at the smallest size, for comparison. Each run's table kept on `G:\mocap-studio-downloads\review\<date>\` with its size in the name.

## Pre-work, needs Rafael

- **Docker can't see the GPU yet:** its only runtime is `runc`. The NVIDIA Container Toolkit has to be installed in WSL, with `sudo`, by Rafael or with his go-ahead. Docker Desktop's own GPU support is the alternative, if that's what runs Docker here.
- **Library: Warp (recommended) or Taichi.** Both Apache 2.0. Warp is maintained by NVIDIA and has tetrahedral soft-body examples; Taichi is the fallback if Warp fails here.

## Dependencies

RTX 4080 driver ≥ 570 (`DEPENDENCIES.md`), Docker in WSL, the container toolkit above. Warp also downloads third-party software of its own: their licenses get checked and recorded.

## Out of scope

Any part of the body. Choosing the simulation method for the thigh beyond XPBD as the starting point.

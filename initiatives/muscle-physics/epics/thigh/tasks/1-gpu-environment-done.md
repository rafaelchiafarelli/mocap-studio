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

## Pre-work, by Rafael

- **Docker can't see the GPU yet:** its only runtime is `runc` (Docker 29.1.3 from Ubuntu's `docker.io`, in WSL Ubuntu 24.04). Rafael runs `sudo human-model/setup_gpu_host.sh` (2026-11-07, as he asked): it installs the NVIDIA Container Toolkit from NVIDIA's repository, registers it with Docker and checks `nvidia-smi` inside a container. The version it prints goes in `DEPENDENCIES.md`.
- **Library: Warp,** agreed 2026-11-07. Apache 2.0, maintained by NVIDIA, with tetrahedral soft-body examples. Taichi (Apache 2.0) is the fallback if Warp fails here.

## Dependencies

RTX 4080 driver ≥ 570 (`DEPENDENCIES.md`), Docker in WSL, the container toolkit above. Warp also downloads third-party software of its own: their licenses get checked and recorded.

## Out of scope

Any part of the body. Choosing the simulation method for the thigh beyond XPBD as the starting point.

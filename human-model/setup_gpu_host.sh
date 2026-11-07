#!/bin/bash
# Lets Docker in WSL use the NVIDIA GPU: installs the NVIDIA Container Toolkit and registers its runtime.
# Run once, with sudo: sudo human-model/setup_gpu_host.sh
# Warp itself isn't installed here: it goes in the GPU image, like every other library (DEPENDENCIES.md).
# Never install an NVIDIA driver inside WSL: the Windows driver provides it (/usr/lib/wsl/lib).
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Run it with sudo: sudo $0" >&2
    exit 1
fi
if [ ! -e /usr/lib/wsl/lib/libcuda.so.1 ]; then
    echo "The Windows NVIDIA driver isn't visible in WSL (/usr/lib/wsl/lib/libcuda.so.1). Stopping." >&2
    exit 1
fi
if ! command -v docker >/dev/null; then
    echo "Docker isn't installed in this WSL. Stopping." >&2
    exit 1
fi

KEYRING=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
LIST=/etc/apt/sources.list.d/nvidia-container-toolkit.list

echo "== 1/4 NVIDIA's package repository"
apt-get update -q
apt-get install -y -q curl gnupg ca-certificates
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor --yes -o "$KEYRING"
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed "s#deb https://#deb [signed-by=$KEYRING] https://#g" > "$LIST"

echo "== 2/4 NVIDIA Container Toolkit"
apt-get update -q
apt-get install -y -q nvidia-container-toolkit

echo "== 3/4 Docker's GPU runtime"
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

echo "== 4/4 Check: the GPU seen from inside a container"
docker run --rm --gpus all ubuntu:24.04 nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv

echo
echo "Done. Installed: $(dpkg-query -W -f='${Package} ${Version}' nvidia-container-toolkit)"
echo "Tell Claude this version, so it goes in DEPENDENCIES.md."

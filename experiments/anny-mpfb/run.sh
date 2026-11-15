#!/bin/sh
# Runs a command in the anny-mpfb image with the GPU, the repository at /repo and G: at /mnt/g. Anny's cache stays on G:.
# experiments/anny-mpfb/run.sh python experiments/anny-mpfb/compare.py
HERE=$(cd "$(dirname "$0")" && pwd)
docker build -q -t mocap-anny-mpfb "$HERE" >/dev/null || exit 1
exec docker run --rm --gpus all --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp \
  -e ANNY_CACHE_DIR=/mnt/g/mocap-studio-downloads/models/anny-mpfb/cache \
  -v "$HERE/../..:/repo" -v /mnt/g:/mnt/g -v /tmp:/tmp -w /repo mocap-anny-mpfb "$@"

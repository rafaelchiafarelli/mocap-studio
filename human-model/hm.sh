#!/bin/sh
# Runs a command in the human-model image, with the repository at /repo and G: at /mnt/g: hm.sh pytest
# hm.sh --gpu runs it in the GPU image instead, with the GPU: hm.sh --gpu python human-model/tools/gpu_bench.py OUT_DIR
# hm.sh --ref runs it in the image with MediaPipe and OpenCV, with C: read-only: hm.sh --ref python human-model/tools/check_reference.py FILE_OR_FOLDER
HERE=$(cd "$(dirname "$0")" && pwd)
IMAGE=mocap-human-model DOCKERFILE=Dockerfile GPU= EXTRA=
if [ "$1" = "--gpu" ]; then
    shift
    IMAGE=mocap-human-model-gpu DOCKERFILE=Dockerfile.gpu GPU="--gpus all"
elif [ "$1" = "--ref" ]; then
    shift
    IMAGE=mocap-human-model-ref DOCKERFILE=Dockerfile.reference EXTRA="-v /mnt/c:/mnt/c:ro"
fi
docker build -q -t "$IMAGE" -f "$HERE/$DOCKERFILE" "$HERE" >/dev/null || exit 1
# Warp caches its compiled kernels under HOME, so /tmp keeps them between runs.
exec docker run --rm $GPU $EXTRA --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp -v "$HERE/..:/repo" -v /mnt/g:/mnt/g -v /tmp:/tmp -w /repo "$IMAGE" "$@"

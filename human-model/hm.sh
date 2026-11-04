#!/bin/sh
# Runs a command in the human-model image, with the repository at /repo and G: at /mnt/g: hm.sh pytest
HERE=$(cd "$(dirname "$0")" && pwd)
docker build -q -t mocap-human-model "$HERE" >/dev/null || exit 1
exec docker run --rm --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp -v "$HERE/..:/repo" -v /mnt/g:/mnt/g -v /tmp:/tmp -w /repo mocap-human-model "$@"

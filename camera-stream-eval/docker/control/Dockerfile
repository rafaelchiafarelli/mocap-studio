# The recorder side of mocap-camera-app's ZeroMQ control channel (scripts/camctl.py): Python 3.12 with the
# runtime deps of mocap-contracts' generated endpoints, from a hash-locked file (DEPENDENCIES.md rule B).
# mocap-contracts itself is mounted from the umbrella's submodule (../mocap-contracts) at run time.
# python:3.12-slim, pinned by digest
FROM python@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f
COPY requirements.lock /tmp/
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock && rm /tmp/requirements.lock
WORKDIR /work

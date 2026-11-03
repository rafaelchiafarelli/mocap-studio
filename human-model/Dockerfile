# Libraries for hmcore and its tests. Blender's own Python runs the scripts in blender/.
FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
COPY requirements.txt /tmp/requirements.txt
RUN pip install --require-hashes --no-deps -r /tmp/requirements.txt
WORKDIR /repo

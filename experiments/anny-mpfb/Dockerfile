# Investigation image: Anny (Apache-2.0, MakeHuman assets CC0) on PyTorch cu128, for fitting MPFB bodies. Run with run.sh.
FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.txt
WORKDIR /repo

"""Packs mpfb_ganho/ and installs it in the Blender on G: from WSL: python3 experiments/mpfb-ganho/install.py
The zip stays on G:, in apps/mpfb-ganho, to install by hand."""
import os, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "human-model"))
from blender_run import BLENDER, win
OUT = "/mnt/g/mocap-studio-downloads/apps/mpfb-ganho"


def main():
    os.makedirs(OUT, exist_ok=True)
    package = os.path.join(HERE, "mpfb_ganho")
    zip_path = os.path.join(OUT, "mpfb_ganho.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(package)):
            if name.endswith((".py", ".toml")):
                z.write(os.path.join(package, name), name)
    code = subprocess.call([BLENDER, "--command", "extension", "install-file", "-r", "user_default", "-e", win(zip_path)])
    if code == 0:
        print("installed", zip_path)
    return code


if __name__ == "__main__":
    sys.exit(main())

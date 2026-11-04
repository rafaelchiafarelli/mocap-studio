"""Packs hm_editor/ and installs it in the Windows Blender from WSL: python3 human-model/install_editor.py
install.json goes in the package, so the add-on can find this repository and start builds. The zip stays on G: too, to install by hand elsewhere."""
import json, os, subprocess, sys, zipfile
from blender_run import BLENDER, win
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/mnt/g/mocap-studio-downloads/apps/hm-editor"


def main():
    os.makedirs(OUT, exist_ok=True)
    package = os.path.join(HERE, "hm_editor")
    zip_path = os.path.join(OUT, "hm_editor.zip")
    config = {"distro": os.environ["WSL_DISTRO_NAME"], "repo": os.path.dirname(HERE)}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(package)):
            if name.endswith((".py", ".toml")):
                z.write(os.path.join(package, name), name)
        z.writestr("install.json", json.dumps(config))
    code = subprocess.call([BLENDER, "--command", "extension", "install-file", "-r", "user_default", "-e", win(zip_path)])
    if code == 0:
        print("installed", zip_path)
    return code


if __name__ == "__main__":
    sys.exit(main())

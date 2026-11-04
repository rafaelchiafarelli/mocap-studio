"""Fetches every source the model is built from into models/ on G:. No Docker needed: python3 -I fetch_sources.py [MODELS_DIR]
Files already there are kept, so it can run again. Licenses: docs/sources-and-validation.md. Fukuchi's and the CT dataset's servers can be slow."""
import json, os, re, subprocess, sys, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from hmcore import remote_zip, tsdata

DONORS = ("s1045", "s0933")  # keep in step with hmcore/bonelib.py
RAW = "https://raw.githubusercontent.com/opensim-org/opensim-models/master"
BMF = "https://github.com/manishsreenivasa/BMFToolkit"
BMF_COMMIT = "e3e781ef166162438273cc1853d6f318482fea67"
FUKUCHI = {"WBDSascii.zip": "https://ndownloader.figshare.com/files/68194516", "WBDSinfo.csv": "https://ndownloader.figshare.com/files/68504641"}
ANSUR = {"ansur_ii_male.csv": "https://tools.openlab.psu.edu/publicData/ANSUR_II_MALE_Public.csv", "ansur_ii_female.csv": "https://tools.openlab.psu.edu/publicData/ANSUR_II_FEMALE_Public.csv"}


def curl(url, dest):
    if os.path.exists(dest):
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    subprocess.check_call(["curl", "-sS", "-L", "--fail", "-A", "Mozilla/5.0", "-o", dest + ".part", url])
    os.replace(dest + ".part", dest)


def main(root):
    labels = tsdata.bone_labels() + [m + s for m in tsdata.MUSCLES for s in ("_left", "_right")]
    ts = os.path.join(root, "totalsegmentator-ct-v2.0.1")
    z = remote_zip.open_zip(tsdata.URL)
    remote_zip.extract(z, ["meta.csv"], ts)
    for donor in DONORS:
        remote_zip.extract(z, [f"{donor}/segmentations/{l}.nii.gz" for l in labels], ts)
        print("donor", donor, flush=True)
    raj = os.path.join(root, "rajagopal-2016")
    curl(f"{RAW}/Models/Rajagopal/Rajagopal2016.osim", os.path.join(raj, "Rajagopal2016.osim"))
    meshes = re.findall(r"<mesh_file>([^<]+)", open(os.path.join(raj, "Rajagopal2016.osim"), encoding="utf-8").read())
    for mesh in sorted(set(meshes)):
        curl(f"{RAW}/Geometry/{mesh}", os.path.join(raj, "Geometry", mesh))
    print("rajagopal", len(set(meshes)), flush=True)
    bmf = os.path.join(root, "bmf-toolkit", "src")
    if not os.path.isdir(bmf):
        subprocess.check_call(["git", "clone", "-q", BMF, bmf])
        subprocess.check_call(["git", "-C", bmf, "checkout", "-q", BMF_COMMIT])
    print("bmf", flush=True)
    for name, url in FUKUCHI.items():
        curl(url, os.path.join(root, "fukuchi-2018", name))
    for name, url in ANSUR.items():
        curl(url, os.path.join(root, "ansur-ii", name))
    print("done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/g/mocap-studio-downloads/models")

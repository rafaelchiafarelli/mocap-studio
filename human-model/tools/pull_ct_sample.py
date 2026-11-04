"""Fetches a per-sex sample of CT labels by byte range for the statistics: python3 -I pull_ct_sample.py OUT_DIR N_PER_SEX
Subjects are the most complete of each sex aged 20-65, excluding recorded trauma. Writes sample.json with the chosen ids."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from hmcore import remote_zip, tsdata
LABELS = ["humerus_left", "humerus_right", "hip_left", "hip_right", "sacrum", "scapula_left", "clavicula_left", "skull", "vertebrae_L3",
          "vertebrae_T6", "rib_left_6", "rib_right_6", "gluteus_maximus_left", "gluteus_medius_left", "iliopsoas_left", "autochthon_left"]
NEED = {"hip_left": 25000, "hip_right": 25000, "sacrum": 12000}  # measures only use labels the scan does not cut


def main(out, n):
    z = remote_zip.open_zip(tsdata.URL)
    meta = tsdata.read_meta(z.read("meta.csv").decode("utf-8-sig"))
    cov = tsdata.coverage(z.infolist())
    chosen = {}
    for sex in "mf":
        rows = [r for r in meta if r["gender"] == sex and r["age"] and 20 <= r["age"] <= 65 and r["pathology"] != "trauma"
                and all(cov.get(r["image_id"], {}).get(k, 0) >= v for k, v in NEED.items())]
        rows.sort(key=lambda r: -sum(cov[r["image_id"]].get(k, 0) for k in ("humerus_left", "hip_left", "clavicula_left", "scapula_left", "skull")))
        chosen[sex] = [r["image_id"] for r in rows[:n]]
        print(sex, "eligible", len(rows), "chosen", len(chosen[sex]), flush=True)
    json.dump(chosen, open(os.path.join(out, "sample.json"), "w"))
    for sex, ids in chosen.items():
        for k, s in enumerate(ids):
            remote_zip.extract(z, [f"{s}/segmentations/{l}.nii.gz" for l in LABELS], out)
            if k % 20 == 0:
                print(sex, k, flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))

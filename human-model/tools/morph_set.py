"""Writes the test individuals: python morph_set.py OUT_DIR. Neutral test people, not characters: parameters per MPFB macro."""
import json, os, sys
BASE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "recipes", "male.json")))
PEOPLE = {
    "slim_tall": {"height": 0.85, "weight": 0.2, "muscle": 0.3, "age": 0.5, "proportions": 0.6},
    "heavy_short": {"height": 0.2, "weight": 0.9, "muscle": 0.4, "age": 0.75, "proportions": 0.4},
    "muscular_young": {"height": 0.55, "weight": 0.55, "muscle": 0.9, "age": 0.5, "proportions": 0.7},
}
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
for sex, gender in (("male", 1.0), ("female", 0.0)):
    for name, macros in PEOPLE.items():
        r = json.loads(json.dumps(BASE))
        r["sex"] = sex
        r["name"] = f"{sex}_{name}"
        r["macros"].update(macros, gender=gender)
        json.dump(r, open(os.path.join(out, r["name"] + ".json"), "w"), indent=1)
        print(r["name"])

"""MPFB's sliders, grouped by body region and labelled for people, and the built model's face muscles. No bpy, so it can be tested."""
import os
from dataclasses import dataclass

# (id, label, group). A section of MPFB's target.json goes to the region of the same id, unless MOVED says otherwise.
REGIONS = [
    ("torso", "Torso and shoulders", "body"),
    ("hip", "Hips, waist and buttocks", "body"),
    ("breast", "Breasts", "body"),
    ("stomach", "Belly", "body"),
    ("arms", "Arms", "body"),
    ("hands", "Hands", "body"),
    ("legs", "Legs", "body"),
    ("feet", "Feet", "body"),
    ("neck", "Neck", "body"),
    ("head", "Head shape", "face"),
    ("forehead", "Forehead", "face"),
    ("eyes", "Eyes", "face"),
    ("eyebrows", "Eyebrows", "face"),
    ("nose", "Nose", "face"),
    ("cheek", "Cheeks", "face"),
    ("mouth", "Mouth and lips", "face"),
    ("chin", "Chin and jaw", "face"),
    ("ears", "Ears", "face"),
    ("asym", "Asymmetry", "face"),
]
SECTION_REGION = {"buttocks": "hip", "pelvis": "hip"}
MOVED = {"measure-hips-circ-decr-incr": "hip", "measure-waist-circ-decr-incr": "hip", "measure-waisttohip-dist-decr-incr": "hip", "measure-bust-circ-decr-incr": "breast"}
# No genitalia in either model (docs/status.md).
LEFT_OUT = {"bulge-decr-incr"}
LEFT_OUT_SECTIONS = {"genitals"}

WORDS = {"horiz": "width", "vert": "height", "circ": "circumference", "dist": "distance", "trans": "position", "rot": "rotation", "scale": "", "measure": "", "lowerarm": "forearm", "upperarm": "upper arm",
         "upperleg": "thigh", "upperlegs": "thigh", "lowerleg": "lower leg", "lowerlegs": "lower leg", "lowerlip": "lower lip", "upperlip": "upper lip", "ext": "outer", "brown": "brow", "cupidsbow": "cupid's bow",
         "napetowaist": "nape to waist", "waisttohip": "waist to hip", "frontchest": "front chest", "invertedtriangular": "inverted triangle", "septumangle": "septum angle", "eyefold": "eye fold", "dorsi": "back"}
REGION_WORDS = {"nose", "eye", "eyebrows", "mouth", "ear", "cheek", "chin", "forehead", "head", "neck", "foot", "hand", "hip", "torso", "breast", "stomach", "buttocks", "asym", "asymm", "pelvis"}
# MPFB has three sliders for each leg segment's height, whose words alone would give them one label.
LABELS = {"measure-upperleg-height-decr-incr": "Thigh height, measure", "upperleg-scale-vert-decr-incr": "Thigh height, scale", "upperlegs-height-decr-incr": "Thigh height, overall",
          "measure-lowerleg-height-decr-incr": "Lower leg height, measure", "lowerleg-scale-vert-decr-incr": "Lower leg height, scale", "lowerlegs-height-decr-incr": "Lower leg height, overall"}
SKIN_ONLY_WORDS = ("muscle", "fat", "buttocks", "breast", "nipple", "bust", "stomach")

# The built model's face muscles: (name, label, what it does), from docs/muscles.md.
FACE_MUSCLES = [
    ("Smile and cheeks", [("zygomaticus_major", "Zygomaticus major", "Pulls the mouth's corner up and out: the smile"), ("zygomaticus_minor", "Zygomaticus minor", "Raises the upper lip's outer part"),
                          ("levator_anguli_oris", "Levator anguli oris", "Raises the corner"), ("risorius", "Risorius", "Pulls the corner sideways"), ("buccinator", "Buccinator", "Presses the cheek in, pulls the corner back")]),
    ("Lips", [("levator_labii_superioris", "Levator labii superioris", "Raises the upper lip"), ("levator_labii_alaeque_nasi", "Levator labii alaeque nasi", "Raises the lip and nose wing"),
              ("orbicularis_oris_upper", "Orbicularis oris, upper", "Purses the upper lip"), ("orbicularis_oris_lower", "Orbicularis oris, lower", "Purses the lower lip")]),
    ("Corners and chin", [("depressor_anguli_oris", "Depressor anguli oris", "Pulls the corner down"), ("depressor_labii_inferioris", "Depressor labii inferioris", "Pulls the lower lip down"),
                          ("mentalis", "Mentalis", "Raises the chin's skin"), ("platysma", "Platysma", "Pulls the lower face and corner down")]),
    ("Brows and nose", [("frontalis_medial", "Frontalis, medial", "Raises the inner brow"), ("frontalis_lateral", "Frontalis, lateral", "Raises the outer brow, with forehead lines"),
                        ("corrugator", "Corrugator", "Pulls the brow in and down"), ("procerus", "Procerus", "Pulls the skin between the brows down"), ("nasalis", "Nasalis", "Narrows the nostril")]),
    ("Eyes", [("orbicularis_oculi_orbital", "Orbicularis oculi, orbital", "Squeezes around the eye, lifts the cheek"), ("orbicularis_oculi_upper_lid", "Upper lid closes", "Closes the upper lid"),
              ("orbicularis_oculi_lower_lid", "Lower lid rises", "Raises the lower lid"), ("levator_palpebrae", "Upper lid opens", "Raises the upper lid")]),
]


@dataclass(frozen=True)
class Slider:
    key: str  # a valid property name
    name: str  # MPFB's name
    label: str
    region: str
    low: str  # what the negative end does; "" when the slider only goes up
    high: str
    sides: tuple  # ("", (negative, positive)), or left and right; negative is None when the slider only goes up
    skin_only: bool

    @property
    def sided(self):
        return len(self.sides) == 2

    def targets(self):
        return [t for _, pair in self.sides for t in pair if t]


def _label(stem, low, high):
    words = stem.split("-")
    if len(words) > 1 and words[0] in REGION_WORDS:
        words = words[1:]
    text = " ".join(w for w in (WORDS.get(w, w) for w in words) if w).strip()
    if low and (low, high) != ("decr", "incr"):
        ends = f"{WORDS.get(low, low)} / {WORDS.get(high, high)}"
        text = f"{text} ({ends})" if text else ends
    return (text or stem).capitalize()


def _slider(section, category):
    name = category["name"]
    region = MOVED.get(name) or SECTION_REGION.get(section, section)
    sided = category.get("has_left_and_right", False)
    opposites = category.get("opposites")
    if opposites:
        side_names = ("left", "right") if sided else ("unsided",)
        pairs = tuple((s[0] if sided else "", (opposites[f"negative-{s}"], opposites[f"positive-{s}"])) for s in side_names)
        neg, pos = [t[2:] if sided else t for t in pairs[0][1]]
        stem = os.path.commonprefix([neg, pos]).rsplit("-", 1)[0]
        low, high = neg[len(stem) + 1:], pos[len(stem) + 1:]
    else:
        pairs = (("l", (None, f"l-{name}")), ("r", (None, f"r-{name}"))) if sided else (("", (None, name)),)
        stem, low, high = name, "", ""
    return Slider("s_" + name.replace("-", "_"), name, LABELS.get(name) or _label(stem, low, high), region, low, high, pairs, any(w in name for w in SKIN_ONLY_WORDS))


def sliders(target_json):
    """Every slider a person may use, from the dict in MPFB's target.json, in region order."""
    out = []
    for section, data in target_json.items():
        if section in LEFT_OUT_SECTIONS:
            continue
        out += [_slider(section, c) for c in data["categories"] if c["name"] not in LEFT_OUT]
    order = [r[0] for r in REGIONS]
    return sorted(out, key=lambda s: (order.index(s.region), s.label))


def search(all_sliders, text):
    """Sliders whose label, MPFB name or region contains every word typed."""
    words = text.lower().split()
    labels = {r[0]: r[1].lower() for r in REGIONS}
    return [s for s in all_sliders if all(w in f"{s.label} {s.name} {labels[s.region]}".lower() for w in words)] if words else []

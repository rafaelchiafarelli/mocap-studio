# The clavicle doesn't reach the scapula's acromion

- **Symptom:** the clavicle's lateral end stops 17 to 20 mm short of the scapula on the neutral woman (left 19.5 mm, right 16.6 mm), where in a person it joins the acromion at the acromioclavicular joint.
- **Where:** `human-model/hmcore/skeleton.py`, shoulder girdle: the clavicle runs from the sternum to a fixed offset from the rig's shoulder (`target_l`), and the scapula is placed from the glenoid; neither looks at the other.
- **Reproduce:** distance from the clavicle's lateral end (`end_centres`) to the nearest scapula vertex in `female.bones.npz` (found on 2026-11-07 while fixing bug 12).
- **Impact:** hidden under the skin; a shoulder that shrugs or reaches would show the two bones moving apart, and the joint has no place to be.
- **Status:** Open. Likely fix: aim the clavicle's lateral end at the placed scapula's acromion.

# 28. The bone test counts the cranium

**Symptom:** the walk's `bone_through_skin` reports `cranium` at 120 to 135 mm in every frame on the new path: the cranium holds the voxels at the neck's cut and lies past it, so the depth figure hides the real bones.
**Where:** `human-model/tools/body_walk.py`, `poking` and the bones listed in `names`.
**How to reproduce:** `body_walk.json` of `t2_neutro`, `ours_bones`.
**Impact:** the depth reported for the walk means nothing on the new path; the list of bones is still right.
**Status:** Open

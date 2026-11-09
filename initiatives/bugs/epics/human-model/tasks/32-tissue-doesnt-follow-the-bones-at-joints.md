# 32. New path: tissue is a shell that doesn't follow the bones

**Symptom:** knees, elbows and shoulders look like spheres, and the limbs between them are thin. Measured on `t2_neutro` against the first shape, diameter in cm: woman's mid-thigh 18.0 to 15.3, just above the knee 10.7 to 13.0; man's just above the knee 11.2 to 16.0, mid-arm 9.4 to 14.9. Lower back +4 cm in both.
**Where:** `human-model/hmcore/outward.py`, `muscle_layer`: one thickness per zone from the bone (`data/muscle_mm_<sex>.json`, medians), so muscle is as thick at the joint as at the belly. `human-model/hmcore/skeleton.py`: with targets the bones aren't narrowed, so the knee's bones are 8.7 to 9.6 cm wide inside a skin 10.7 to 11.2 cm wide.
**Impact:** the neutral bodies don't reproduce their own first shape, so every body is wrong at the joints. Rafael's reading (2026-11-09): muscles don't keep their connection as bones grow or shrink.
On `t5_neutro` (2026-11-09), with muscles attached to the bones: woman above the knee 10.7 to 12.2 cm (was 13.0), mid-thigh 18.0 to 19.1 (was 15.3); man above the knee 11.2 to 12.8 (was 16.0). Lower back +1.4 cm (was +4). Rafael hasn't judged it yet.
**Status:** Open

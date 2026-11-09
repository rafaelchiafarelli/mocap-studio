# 34. New path: the upper arm is too thick

**Symptom:** on `t5_neutro`, the upper arm's middle grows from 10.4 to 16.7 cm across on the woman and 9.4 to 13.3 on the man, while the arm's ends stay close to the first shape.
**Where:** the biceps' and triceps' declared radii and offsets in `human-model/data/muscles.json` (`trunk`), single spindles written by hand; and `human-model/hmcore/outward.py`, `push_needed_on_surface`, which takes the most each triangle asks for.
**How to reproduce:** compare the skin's diameter on `t5_neutro`, `skin/*.skin_fit.npz` against the build's export.
**Impact:** the arms look swollen.
**Status:** Open

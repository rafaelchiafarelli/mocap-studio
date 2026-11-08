# The feet aren't good yet

- **Symptom:** Rafael, looking at the man and the woman on 2026-11-08: "os pés não estão bons mesmo". Measured then: the foot's bones still come through the skin on the inner side (medial cuneiform and first metatarsal 3 to 5 mm on both), and the woman's calcaneus by 6.6 mm. The feet aren't in the simulated body, so their skin and bones only follow the rig.
- **Where:** `human-model/hmcore/skeleton.py`, search `fit_foot` and `FOOT_TISSUE`.
- **Reproduce:** signed depth of the foot's bones in `<name>.bones.npz`, or the section in the Blender file of initiative `fast-review`.
- **Impact:** visible whenever the feet are; a soft foot (initiative `floor-contact`) depends on it.
- **Status:** Open. What exactly is wrong needs Rafael's eye first.

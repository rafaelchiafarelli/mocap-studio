# The foot's bones sit about 2 cm medial of the ankle, through the skin

- **Symptom:** on both neutral bodies, before any push: talus 16.1 mm through the skin on the woman and 17.1 on the man, calcaneus 30.4 and 22.4, navicular 7.4 and 8.8, all on the inner side. The talus's middle lies 2.2 to 2.3 cm medial of the skin's middle at the ankle. The man's talus comes 9.2 mm through in every frame of the walk; the woman's isn't counted, since it lies within the walk's check clearance of the ankle cut.
- **Where:** `human-model/hmcore/skeleton.py`, search `centre_x`: the foot is centred on the ankle joint by the bounding box of the whole foot, not by the talus or the heel.
- **Reproduce:** signed depth and winding number of `talus_L` in `<name>.bones.npz` against the skin. Measured on 2026-11-08 (`models\hm-build\female\`, `models\hm-build\male_2026-11-08_v2_ribs-narrowed\`).
- **Impact:** hidden while the feet stay out of the simulated body, except the man's talus. It will matter for a soft foot on the floor (initiative `floor-contact`).
- **Status:** Open. Likely fix: place the foot with the talus under the ankle joint.

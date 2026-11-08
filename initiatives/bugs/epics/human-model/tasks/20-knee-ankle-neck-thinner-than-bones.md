# MPFB's knee, ankle and neck are thinner than the bones placed in them

- **Symptom:** on the neutral woman at rest, before the skin push, the larynx comes 11.4 mm through the skin, the tibiae 9.9 (at the ankle), the patellae 9.4. The push covers them, and that is what grows the knee 1.3 cm around and the ankle 1.0 (`skin_over_bone.py`, `girths_cm`).
- **Where:** `human-model/hmcore/skeleton.py`: the leg bones are BMF's, one body, joint to joint with thickness to the power 0.7, and the larynx is parametric; none is sized from the skin around it.
- **Reproduce:** `G:\mocap-studio-downloads\review\2026-11-08\skin_v8_pelvis-forward\female.skin_fit.json`.
- **Impact:** knees and ankles a little fuller than the recipe asks for. Moving the bones doesn't help: the patella already lies 1 mm from the femur, and moved back 17.5 mm it went into it; the larynx, moved back, came 5 mm from the vertebrae (`models\hm-build\female_bug10_v1_patella-into-femur_larynx-on-spine\`).
- **Status:** Fixed (2026-11-08) — fixes/0000da/knee-ankle-neck-thinner-than-bones. Bones narrowed to the skin (`fit.slim_to_skin`); the push no longer grows knee or ankle (+0.1 and 0.0 cm against +1.3 and +1.0)

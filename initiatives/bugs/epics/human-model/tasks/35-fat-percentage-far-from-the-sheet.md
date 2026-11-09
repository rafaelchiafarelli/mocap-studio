# 35. New path: the body is about half fat

**Symptom:** on `t5_*`, the fat is 44 to 57% of the simulated mass, against 11 to 36% asked. Muscle is 6.6 to 7.1 litres on the neutral bodies, against 15.6 and 27.7 on the shell of `t1_neutro`.
**Where:** muscle volumes as published (Rajagopal) and declared single spindles, overlapped in one solid, in `human-model/hmcore/muscle_bodies.py`; everything else up to the first shape counts as fat in `human-model/tools/outward_skin.py`. Rafael's decision (2026-11-09) was published volumes, with the percentage reported, knowing it could come out distorted.
**Impact:** the body's soft mass in the walk is mostly fat.
**Status:** Open

# face-character — mocap-studio

**Status:** Planned — starts only if `face-audio` passes. Epics and tasks are
scoped then.

**Goal:** turn the hand-set gain table of `face-audio/test/3` into an
**explicit per-character declaration**: how much each blendshape is amplified
for each character, and which emotion label drives Audio2Face.

**Why its own initiative:** per-character exaggeration is the core idea, and
it must be declared, never inferred by code (standing project principle).
Where it lives is a contract decision.

**Scope:** the declaration's fields and where it lives (alongside the
character data in `session.json`, or a character file in the film root), how
gain is applied (multiply, clamp, curves), and where the emotion label comes
from (by hand first; from the script later, through `mocap-preprod`, which the
MVP keeps frozen).

**Out of scope:** body, video, the MVP shot.

**Initiative gate:** two characters with different profiles, driven by the
same voice clip, read as two different performances to Rafael.

**Cross-repository:** the declaration becomes a `mocap-contracts` task when
its fields are known; applying it is a `mocap-blender` task.

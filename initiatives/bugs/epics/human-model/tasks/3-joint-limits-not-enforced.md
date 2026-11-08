# Joint limits aren't enforced

- **Symptom:** a joint can be posed past its limit.
- **Where:** `human-model/blender/assemble.py`, search `hm_limit_deg`: limits are stored as a bone property, without constraints.
- **Reproduce:** rotate `thigh.L` past 130° by hand.
- **Impact:** body capture and hand posing can break the rule without notice.
- **Status:** Open in part. Hip, knee and ankle are enforced since 2026-11-08 (fixes/0000ec/leg-joint-limits), by a Limit Rotation on the bone's local axis nearest the rest pose's X, at the measured mean plus 10° (`LIMIT_MARGIN_DEG`): the mean isn't a ceiling, and a measured walk came within 1° of it. Shoulder and elbow stay unenforced, their bones lying skewed to that axis (`upper_arm` 0.71, `forearm` 0.77 of it). Likely fix for those: limits on swing and twist.

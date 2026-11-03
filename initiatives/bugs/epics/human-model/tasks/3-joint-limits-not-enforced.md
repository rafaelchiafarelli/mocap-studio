# Joint limits aren't enforced

- **Symptom:** a joint can be posed past its limit.
- **Where:** `human-model/blender/assemble.py`, search `hm_limit_deg`: limits are stored as a bone property, without constraints.
- **Reproduce:** rotate `thigh.L` past 130° by hand.
- **Impact:** body capture and hand posing can break the rule without notice.
- **Status:** Open. Likely fix: Limit Rotation constraints, with axes converted from the rest pose.

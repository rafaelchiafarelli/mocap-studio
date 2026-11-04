## 1. Body input review

- **Type:** review, with a question for Rafael.
- **Depends on:** —
- **Contract:**
  - In: The FreeMoCap test fixture, 60 frames, three cameras (not a recording of ours)
  - Requires: Rafael says what is wrong
  - Delivers: `tools/body_motion.py`, a quality report
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** —

## Result (2026-11-03)

**Open: Rafael hasn't said what's wrong with his body results, and this session couldn't ask.** So it measured what it could. On the fixture, bones that should be rigid change length: thigh 4 to 6%, shin 8 to 11%, foot 13 to 16%, upper arm 6 to 7%, forearm 11%. Median jitter: hip 8.8, ankle 12.8, nose 13.0, wrist 29.0 mm. A better model can't fix that.

**Questions for Rafael:** Is it the shaking, the proportions, feet sliding, joints going the wrong way, or something else? On which recording?

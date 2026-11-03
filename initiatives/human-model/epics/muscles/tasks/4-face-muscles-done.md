## 4. Face muscles

- **Type:** code.
- **Depends on:** `muscles/1`, `references/4`
- **Contract:**
  - In: The rig's face bones as landmarks
  - Requires: Modiolus muscles converge at the mouth's corner
  - Delivers: 15 linear and 6 sphincter or lid muscles per side, each with a FACS action unit list; `hmcore/softtissue.py` turns each into a skin field
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** `tests/test_softtissue.py`

## Result (2026-11-03)

Zygomaticus major and minor, levators, risorius, buccinator, depressors, mentalis, frontalis, corrugator, procerus, nasalis, platysma, orbicularis oris (2) and oculi (3), levator palpebrae. The modiolus has no geometry of its own: its muscles share an insertion near the corner. The first solve tore lips and swelled the chin; uniform weights and a capped bulge fixed that.

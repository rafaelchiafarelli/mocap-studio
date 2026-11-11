# animation-body — epics

The woman only, for now (Rafael, 2026-11-11). The order that matters, and what can run ahead:

1. `clean-body`: a clean MPFB2 woman, at rest and walking. Nothing else starts before it.
2. `pose-corrections`: joints that bend well. Needs epic 1.
3. `fold-catalogue`: the folds and creases. Needs epic 2.
4. `skin-waves`: sway and travelling waves on the skin. Needs epic 1, so it can run beside epics 2 and 3.
5. `foot-impact`: the pulse of each step. Needs epic 4.
6. `compare-references`: the body beside the reference clips, in simple images, closing each round. Needs epic 1, and is run again after each later epic.

**Gate:** Rafael's verdict per layer in epic `compare-references`.

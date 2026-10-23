# face-audio — epics (execution order)

1. **prework** — Can it run here, may we use it, what face it drives (3 tasks)
2. **test** — Voice → Audio2Face → gain → Blender → verdict (4 tasks)

Cross-repository: `test/3` needs one code task in `mocap-blender`
(keyframes CSV → ARKit shape keys, with a per-blendshape gain table). It is
scoped there, following the `mocap-workflow` skill, once `prework` is done.

An epic only merges up into `epics` once all its tasks are `-done` and the suite is green.

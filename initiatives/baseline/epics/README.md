# baseline — epics (execution order)

1. **bootstrap** — Environment (2 tasks)
2. **pipeline** — Per-take execution (2 tasks)
3. **camera-study** — Camera bottleneck study (4 tasks)

An epic only merges up into `epics` once all its tasks are `-done` and the suite is green.

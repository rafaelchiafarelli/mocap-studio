## 1. CLI run-take

- **Depends on:** bootstrap; repositories with a CLI
- **Contract:**
  - In: session + take
  - Requires: calls `mocap-extract` and `mocap-adapt` via subprocess, in order, stopping at the first error
  - Delivers: `mocap run <session> <take>`
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** fake CLIs

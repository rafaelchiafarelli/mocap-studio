## 1. repos.yaml and bootstrap

- **Depends on:** —
- **Contract:**
  - In: —
  - Requires: list of the 6 repositories with pinned version/branch
  - Delivers: `scripts/bootstrap.sh` clones and installs everything into separate venvs
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** shellcheck; dry-run

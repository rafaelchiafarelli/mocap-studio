# face-history — older face test code

**Role:** an archive of earlier experiments. Not run since being copied here, and nothing imports it.

**Entry points:** none. See [README.md](README.md).

**Inputs → Outputs:** see each test in the README. Their inputs aren't in git.

## Files

- `video_test_1/`, `video_test_2/`: `extract_face.py` and `clean_face.py` for MediaPipe; `video_test_2/mapping_config.json` its settings.
- `audio2face/`: `a2f_infer.py`, `a2f_solve.py`, `a2f_merge.py`, their configs, `LICENSE_CHECK.md`, `requirements_used.txt`.
- `dense_face/`: the `stage1_*`, `stage2_*`, `stage3_*` scripts, `preview_frames.py`, `motion_check.py`.
- `character/`: `build.py`, `hair.py`, `aging.py`, `finish_face.py`, `key_face.py`, `motion_test.py`, `render.py`.
- `parrot_on.py`: runs Parrot Lipsync on a character keyed with its upper face.

## Key facts / gotchas

- Film names were replaced when copying, so object names no longer match the original `.blend` files.

## Touchpoints

`experiments/face-mouth/FINDINGS.md`, `initiatives/README.md`.

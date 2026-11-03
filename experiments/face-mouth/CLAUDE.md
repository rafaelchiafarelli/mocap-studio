# face-mouth — repeatable mouth-fader experiment

**Role:** rebuilds the best face result so far from its inputs and checks it against a frozen baseline. An experiment, not pipeline code. Results and how to run it: [FINDINGS.md](FINDINGS.md), [README.md](README.md).

**Entry points:** `run_experiment.py CONFIG.json` from WSL; `mouth_faders/` as a Blender add-on; `cli_faders.py` inside Blender.

**Inputs → Outputs:** a recording, a character `.blend` with ARKit shapes, a take file and `poses.json` → tracking, sounds, channels, `faders.blend`, `metrics.json`, stills, PASS or FAIL.

## Files

- `run_experiment.py`: every stage in order, the bless step and the comparison.
- `recognize_phones.py`: Allosaurus set to Portuguese; restores the saved model if the package has none.
- `overlay_video.py`: tracked points over the recording.
- `osf_to_arkit.py`: tracker log → ARKit channels and head rotation.
- `make_table.py`: every recognizer sound → one of 12 mouth groups.
- `make_data.py`: recognized sounds, known words aligned to their timing, tracked opening, loudness.
- `key_face_head.py`: keys face channels and head, adds audio, video card, lights and camera.
- `build_faders.py`: control object, drivers to shapes and bones, first bake.
- `mouth_faders/`: the add-on: `__init__.py` holds the mouth computation, the panel and presets; `blender_manifest.toml` its metadata.
- `cli_faders.py`: sets faders from the command line.
- `verify_faders.py`: measures the presets, tests a fader, saves curves, renders stills.
- `measure_mouth.py`: measures the lip gap per `jawOpen` and the eye distance on a character.
- `render_poses.py`: renders each pose close up.
- `poses.json`: the 13 mouth poses. `presets/`: fader settings A, B, C. `take_files/`: known words and timing for a recording.
- `face-mouth-experiment.drawio`: the process as a diagram.
- `config.example.json`: template for the local config; real paths stay out of git. `requirements.txt`: pinned versions used.

## Key facts / gotchas

- The tracker log's header doesn't match its rows, so columns are read by position: `overlay_video.py:7`.
- The tracker stores points as (row, column), so head axes are swapped; signs were checked against a recorded head turn: `osf_to_arkit.py:84`.
- The table is written in ASCII because Parrot opens tables with the system encoding: `make_table.py:22`.
- The control object is found by its properties, so older files keep working: `mouth_faders/__init__.py:14`.
- The comparison guards the curves and measures; stills are coarse: `run_experiment.py:11`.
- The take file's folder isn't called `takes/` because the root `.gitignore` ignores that name.
- `requirements.txt` is a local venv, not the Dockerfile that `DEPENDENCIES.md` asks for. It was kept because this is an experiment, and that's a flagged divergence.

## Touchpoints

`initiatives/faces/` (results), `initiatives/human-model/` (next research), `DEPENDENCIES.md` (apps), and the baseline folder on `G:`.

# Mouth faders: how to repeat the experiment

The best face result so far, kept so it can be rebuilt and never quietly lost.
What was tested and learned is in [FINDINGS.md](FINDINGS.md), and the process is
in [the diagram](../../docs/diagrams/face-mouth-experiment.drawio).

## Where everything is

| What | Where | In git? |
|---|---|---|
| Code, poses, presets, take file | This folder | Yes |
| Older test code | [`../face-history/`](../face-history/README.md) | Yes |
| Frozen baseline: recording, character, approved `.blend`, expected results | `G:\mocap-studio-downloads\face\baseline_mouth_faders_2026-11-02\` | **No** |

Recordings and `.blend` files stay out of git: they're large, they show a real
person, and the character belongs to a film. **The baseline is on one drive only,
so back it up.** Check it with `sha256sum -c SHA256SUMS` from inside that folder.

## Open the approved result

Run `G:\mocap-studio-downloads\review\2026-11-02\abrir_faders.bat`, press **N** over
the 3D view and open the **Boca** tab. The add-on is only in the portable Blender.

## Rebuild it from the inputs

From WSL, in this folder, with Python 3.12 and `ffmpeg` installed:

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python run_experiment.py /mnt/g/mocap-studio-downloads/face/baseline_mouth_faders_2026-11-02/config.json

It takes about a minute after the install. It ends with `PASS` or `FAIL` and exit
code 0 or 1. The output goes to the config's `out_dir`, with its own
`abrir_faders.bat`. `--from <stage>` restarts at one stage. For a machine or drive
that isn't this one, copy `config.example.json` and fill in its paths.

Also needed, under `G:\mocap-studio-downloads\apps\`: Blender 5.2.2, with MPFB's
asset packs, and OpenSeeFace v1.20.5. Checksums are in `DEPENDENCIES.md`.

**Checked on 2026-11-02:** a clean venv from `requirements.txt`, rebuilt from the
inputs, matched the approved file exactly in its curves, measures and eight stills.
Worsening two poses on purpose gave `FAIL`, and restoring them gave `PASS`.

## Keeping the distance from what works

1. **Never overwrite the baseline.** The approved `.blend` in its `approved/` folder
   is the reference Rafael judged.
2. **New work is compared with it**, on the same recording, in Rafael's judgement.
3. **Run the check before and after changing this code.** `FAIL` isn't always bad, but
   it means the result moved, and it must be a choice.
4. **Only Rafael moves the reference.** After he approves a better result, make a new
   dated baseline folder and run `run_experiment.py CONFIG.json --bless FILE.blend`.
   Keep the old one.

`PASS` means "the same as the approved result", not "good". Numbers can't judge
performance: the correlation with the video is high partly because setup C uses the
video.

## Use the faders on a new recording

1. Copy `take_files/farol_pipoca_farofa.json` and set a still, neutral window, the words as
   mouth groups, and the markers. `make_data.py` prints how the words aligned; place
   sounds it misses with `anchors`.
2. Point a new config at the recording and a new `out_dir`, and run through `verify`.
   `compare` will fail, because the baseline belongs to another recording.
3. For a different character, measure it first with `measure_mouth.py` and set
   `lip_gap_at_jaw1_m` and `eye_distance_m`. Then check the poses with
   `render_poses.py`, because they were made for one face.

Words as mouth groups are written by hand for now. A general tool that gets them from
the script doesn't exist yet.

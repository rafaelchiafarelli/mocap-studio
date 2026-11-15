# Integration: motion filter (floor, foot contacts, motion gain) into the tissue chain

For the session working on the soft tissue (`tissue_*.py`, `dress_cloth.py` in `investigations/pose-capture/`). Written
2026-11-14 by the session that built the filter. Nothing of yours was touched; the filter is three commits on
`pose-capture` (`b0911c0`, `c7af595`, `19dd595`) and lives in its own files. Integrating it is your call and your
commits.

## What it is

Two programs that work on the capture's landmarks (`.npz`) **before** `drive_capture.py` keys them onto the body. Both
write an `.npz` with the same keys they read, so every step after them runs unchanged.

| Program | Does | Asked by Rafael |
|---|---|---|
| `foot_contacts.py` | Levels the floor and marks when each foot point (ankle, heel, toe) is on the floor, from one frame Rafael marks as "this foot on the floor" (a VLC snapshot or a time). | The floor of a capture is **always level**. The feet need a contact with the floor. |
| `amplify_capture.py` | Motion gain per region (`--hips`, `--trunk`, `--head`, `--arms`, `--legs`, times `--gain`; each 0 to 3), applied only to the intentional band (0.3 to 6 Hz). The pose/travel below and the noise above are kept, and noise has its own `--noise` gain. | The hips barely moved in the capture. Give the motion more travel, set per capture on the command line, not in Blender. |

Details, checks and measured numbers: `investigations/pose-capture/CLAUDE.md` (bullets for both programs and the gotchas on
the floor ramp and the motion measured).

## Where it goes in your chain

Today (per `MELHOR_ATE_AGORA.txt` on G:):

```
06_.../two_cameras.npz → drive_capture.py → 07_movimento_duas_cameras_31-43s.blend → tissue_motion_dump.py → tissue_sim.py …
```

With the filter:

```
06_.../two_cameras.npz
  → foot_contacts.py   (floor levelled, contacts added)
  → amplify_capture.py (optional; all gains 1 = unchanged)
  → drive_capture.py --no-head  → MOTION.blend
  → tissue_motion_dump.py MOTION.blend → tissue_sim.py …
```

The order matters. Contacts are measured **before** the gain, because gain changes speeds and a planted foot could then read
as moving. `amplify_capture.py` copies the `contact` key through.

Commands (from the repo root; `R=/mnt/g/mocap-studio-downloads/review/2026-11-14/pose_capture`,
`V=/mnt/g/mocap-studio-downloads/media_pipe_videos`, `S=human-model/investigations/pose-capture`):

```sh
human-model/hm.sh --ref python $S/foot_contacts.py $R/06_duas_cameras_esqueleto_31-43s/two_cameras.npz OUT_DIR/contatos.npz \
    --pe-no-chao $V/vlcsnap-2026-11-14-21h32m04s141.png:direito --videos $V/20261114_183544.mp4 $V/VID_20261114_183545.mp4
human-model/hm.sh --ref python $S/amplify_capture.py OUT_DIR/contatos.npz OUT_DIR/ganho.npz --hips 2
python3 human-model/blender_run.py --blend $R/02_corpo_com_rig.blend $S/drive_capture.py OUT_DIR/ganho.npz \
    OUT_DIR/movimento.blend OUT_DIR/relatorio_retarget.json --no-head
```

That snapshot is Rafael's mark for this take: right foot, B 37.427 s = A 37.301 s. Passing `37.301:direito` gives the same
result without scanning the videos. Ready-made outputs: `15_chao_e_contatos/contatos.npz` and its
`movimento_nivelado.blend` (levelled, gain 1), and `13_ganho/quadril_2.npz` / `quadril_3.npz` (gain only, **not levelled**,
made before the floor fix).

## Things to know before you switch

1. **The floor ramp is a shear, not a turn.** On this take the still foot points lie on a 9.9° ramp while the body stands
   upright. `foot_contacts.py` takes the ramp out of heights only (`level_shear`). A first version rotated the whole capture
   and leaned the body 9.8° forward; Rafael rejected it (`14_..._ERRADO_*` on G:). Never level by rotating. The ramp is
   measured per take, and its cause, the two-camera calibration in `two_cameras.py`, is still open.
2. **Your mesh was built on frame 1 of 07.** Levelling and gain change the pose at frame 1 slightly (the feet's heights and,
   with gain, every part's angle), so check whether `tissue_mesh.py`'s rest still matches the first frame of the new
   motion, or rebuild.
3. **`drive_capture.py` doesn't read `contact` yet.** The feet are not pinned. With a high hips gain the hips travel further
   (gain 3: 0.75 × 0.92 m against 0.48 × 0.51 m at gain 1, levelled), so feet slide until the next step lands: the planted
   foot held where `contact` says, and leg IK to reach it. It was proposed to Rafael and not started. If you take
   `drive_capture.py` over, say so, so the two sessions don't both change it.
4. **Gain scales what was captured, and the noise slower than 6 Hz along with it.** The pelvis's tilt (1.5° rms) and roll
   (2.7°) are small; gain 3 brings the roll to ~8°. The capture's own noise also drives your tissue, so `--noise 0` (drops
   the band over 6 Hz) may be worth a try on the skin.
5. **Two cameras only** for `foot_contacts.py` (it needs `points_m` and the `two_cameras.json` beside the input).
   `amplify_capture.py` takes either kind.
6. **Checks:** `hm.sh --ref python $S/test_amplify_capture.py` and `$S/test_foot_contacts.py` (synthetic; neither is under
   `tests/`, like `test_two_cameras.py`).

## Files (all in `investigations/pose-capture/`)

- `foot_contacts.py`, `test_foot_contacts.py`
- `amplify_capture.py`, `test_amplify_capture.py`
- `stage_video.py`: gained `--no-frames` (saves the staged `.blend` without rendering).
- `CLAUDE.md`: bullets and gotchas for the above.

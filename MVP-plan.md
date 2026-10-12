# MVP plan: one watchable shot

**Goal:** a rendered shot of about 10 seconds, at 1080p, of a rigged character
performing one dialog beat from the pilot film, driven by our own capture,
with the actor's voice. Rough is fine. The bar is "you can tell what he's
doing and it reads as a performance", not polish.

**Why:** nothing so far has carried real data end to end. This shot is the
first gate that forces a frame to exist. The list of what's broken in it
replaces the current plan.

## Rules for the MVP

- **Frozen until the shot exists:** `mocap-dashboard`, `mocap-preprod`,
  `mocap-audio`, `mocap-sync-fw`, `mocap-adapt`, the hand-off listener
  (`mocap-extract` watch), quality metrics, the camera study, and new
  `.harpia` messages. No new initiatives.
- **One machine.** The processing PC (WSL2, RTX 4080) is also the recorder.
  The take is on disk before the hand-off runs, so a failed hand-off at the
  end of `mocap-capture take` is expected and harmless.
- **Code only where a gap blocks the shot**, as tasks in the owning repository,
  following the `mocap-workflow` skill. Everything else is manual and stays
  manual until the shot shows it's worth automating.
- **Film material stays in the film root.** The beat, takes worth keeping,
  the `.blend` and the render go under `<film-root>/mvp/`. Bulk take data
  stays on the WSL disk (`storage.root`, fast I/O), not under `/mnt/g`.
- **Licenses** as always: commercial-use only, weights and assets included.

## Steps

| # | Step | Who | Done when |
|---|---|---|---|
| 0 | **Prep.** Print the ChArUco board (A4, 100 %, glued flat on rigid backing). Install the camera app on 2–4 devices. A backless stool. A phone to record the voice. Choose the beat. | Rafael | Board measured (100 mm bar = 100 mm), devices stream, beat written in `<film-root>/mvp/shot.md` |
| 1 | **Bench take.** `config.yaml` with every device, one 10 s test take. | together | `mocap-capture report` ok: no big gaps, ~30 fps per camera |
| 2 | **Calibration take** (board walked through the volume), aligned to 30 fps, calibrated with FreeMoCap. | together | Calibration file; board in every camera; reprojection error noted |
| 3 | **Performance takes** of the beat, 3 to 5 of them. Start with a clap that the cameras and the phone both catch. | Rafael acts | One take picked |
| 4 | **3D.** FreeMoCap body (+ hands, best effort) on the picked take, then the FreeMoCap Blender add-on. | session | `.blend` with an animated armature that moves like the actor |
| 5 | **Character.** A rigged human (MPFB2: the add-on is GPL, its assets CC0; verify at download) and the motion retargeted onto it. | together | The character does the beat |
| 6 | **Shot.** Blockout set (bench, lamp, props as primitives), camera, light, voice synced on the clap, EEVEE render. | together | `<film-root>/mvp/shot.mp4` |
| 7 | **Watch it.** Write what's broken, worst first. | Rafael | That list exists. It becomes the next plan. |

## Code gaps: all closed (2026-10-12)

| Gap | Where | Status |
|---|---|---|
| CALIBRATION takes need the declared board | `mocap-capture` baseline board/1 (moved from studio-setup) | done |
| Align one take from the CLI | `mocap-extract` alignment/4 | done |
| ChArUco calibration + ground plane | `mocap-extract` calibration/1, /2 | done; synthetic 3-camera fixture recovers the camera distances within 0.3 % |
| FreeMoCap body and hands 3D | `mocap-extract` body/1 | done; per-camera 2D identical to FreeMoCap's own run |
| Blender: setup, reference scene, character, retarget, shot, CLI | `mocap-blender` initiative `mvp`, epic `shot`, tasks 1–6 | done; FreeMoCap's test recording renders as a 222-frame shot |

The retarget is a simple frame-matching one (`mocap-blender/mocap_blender/retarget.py`):
each bone takes the actor's direction and twist from two landmark vectors, the
hips are scaled by leg length, the ankles are put on the floor, the feet stay flat.

## Runbook

Repositories stay checked out on the branches that carry this work: `mocap-capture`
on `baseline`, `mocap-extract` on `tasks`, `mocap-blender` on `epics` (nothing is
on `dev` yet). Commands below run from `~/workspace/mocap-studio`. Data root:
`~/mocap-data` (short on purpose: Windows paths must stay under 260 characters).

**Step 0, once (you):**

1. **WSL mirrored networking** (WSL2 NAT stalls the tablets' TCP streams; this
   machine is in NAT mode). Create `C:\Users\rafae\.wslconfig` with
   `[wsl2]` and `networkingMode=mirrored`, then `wsl --shutdown` from Windows
   and reopen. Check: `wslinfo --networking-mode` prints `mirrored`.
2. **sshd on localhost**, for the hand-off from `rec/` to `proc/`:
   `sudo apt install -y openssh-server && sudo service ssh start`, then
   `cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys` (make the key with
   `ssh-keygen -t ed25519` if it's missing). Check: `ssh 127.0.0.1 true`.
3. **`~/mocap-data/config.yaml`:** the three tablets' IPs (`SET-TABLET-n-IP`)
   and `measured_square_length_mm` (caliper, one black square).
4. **`~/mocap-data/rec/mvp-1/session.json`:** your height in metres (it's 0,
   which the contract refuses on purpose) and the date of the shoot.
5. **Tablets:** the camera app on all three (`mocap-camera-app/scripts/install-app.sh`).
   Landscape, about 1.2–1.5 m high, around the stool, each seeing the stool and
   the floor around it, **within ~2 m of where the board will move** (the A4 board
   at 1600 px wide; farther than that and corners drop).

**Steps 1–3, takes (you):**

```bash
CAP=mocap-capture/.venv/bin/mocap-capture; CFG=~/mocap-data/config.yaml
$CAP take --config $CFG --session mvp-1 --name bench-1 --type PERFORMANCE   # step 1: 10 s, check the report
$CAP take --config $CFG --session mvp-1 --name cal-1 --type CALIBRATION     # step 2: board flat on the floor at the
                                                                            # stool for 3 s, then 60-90 s slow moves
$CAP take --config $CFG --session mvp-1 --name beat-1 --type PERFORMANCE    # step 3: clap first; beat-2, beat-3, ...
```

Record the voice on the phone at the same time, clap included. If a hand-off
fails, fix it and run `$CAP send --config $CFG --session mvp-1 --take <take>`.

**Steps 2 and 4, extraction (Claude or you):**

```bash
EX=mocap-extract/.venv/bin/mocap-extract; P=~/mocap-data/proc/mvp-1/takes
$EX align $P/cal-1 && $EX calibrate $P/cal-1 --max-error-px 1.0   # prints error per camera and the ground plane
$EX align $P/beat-1 && $EX body $P/beat-1                          # FreeMoCap 3D in beat-1/extract/freemocap/
```

**Steps 5 and 6, Blender (Claude or you):**

```bash
BL=mocap-blender/.venv/bin/mocap-blender; FILM=/mnt/g/TicTac/mvp
$BL reference $P/beat-1                                   # optional: FreeMoCap's own view, to check the capture
$BL character $FILM/character.json ~/mocap-data/proc/mvp-1/antonio.blend
$BL retarget $P/beat-1 ~/mocap-data/proc/mvp-1/antonio.blend
$BL shot $P/beat-1 $FILM/shot.json                        # renders $FILM/shot.mp4
```

Before the final render: put the voice in `$FILM/voice.wav` and set `"audio":
{"path": "voice.wav", "offset_s": …}` in `shot.json` (offset = clap frame / 30
minus the clap's time in the audio). Set `"frames"` to the beat, and move the
stool and the camera to fit the take (`shot.blend` next to the take shows the scene).

## Known limits we accept for the MVP

- **Hands.** 2 MP front cameras won't give usable fingers. Wrists and arms
  only; fingers posed by hand if needed.
- **Face.** No face capture. Frame the shot so lip sync isn't the point
  (wide, profile or three-quarter back), or accept a still mouth.
- **Occlusion.** A seated actor behind a real table loses the lower body. Act
  on a backless stool with no table and add the table in Blender.
- **Cleanup.** No `mocap-adapt` yet: FreeMoCap's own filtering only. Foot
  sliding and jitter go on the step 7 list rather than getting fixed here.
- **Feet.** They stay flat and keep the actor's heading only (MediaPipe's toe
  landmark is too noisy for pitch), and the ankles' lowest contacts are put on
  the floor.

## Gear

| Item | Where |
|---|---|
| ChArUco board, FreeMoCap "5x3 Charuco", 55 mm squares, A4 landscape (detects up to ~2.5 m) | `/mnt/g/mocap-studio-downloads/calibration/charuco-5x3-55mm-A4.pdf` |
| Camera app APK | `mocap-camera-app` (built debug APK) |
| FreeMoCap 1.8.2 | `mocap-extract/.venv` |
| Blender 5.2.2 (portable, MPFB 2.0.18 installed in it), FreeMoCap Blender add-on v2026.04.1041 | `/mnt/g/mocap-studio-downloads/apps/` (`DEPENDENCIES.md`) |
| Recorder config and session template | `~/mocap-data/config.yaml`, `~/mocap-data/rec/mvp-1/session.json` |
| Placeholder character and shot recipe (film material) | `/mnt/g/TicTac/mvp/character.json`, `shot.json` |

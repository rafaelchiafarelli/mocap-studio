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
| 0 | **Prep.** Print the ChArUco board (A0, 100 %, rigid backing). Install the camera app on 2–4 devices. A backless stool. A phone to record the voice. Choose the beat. | Rafael | Board measured (100 mm bar = 100 mm), devices stream, beat written in `<film-root>/mvp/shot.md` |
| 1 | **Bench take.** `config.yaml` with every device, one 10 s test take. | together | `mocap-capture report` ok: no big gaps, ~30 fps per camera |
| 2 | **Calibration take** (board walked through the volume), aligned to 30 fps, calibrated with FreeMoCap. | together | Calibration file; board in every camera; reprojection error noted |
| 3 | **Performance takes** of the beat, 3 to 5 of them. Start with a clap that the cameras and the phone both catch. | Rafael acts | One take picked |
| 4 | **3D.** FreeMoCap body (+ hands, best effort) on the picked take, then the FreeMoCap Blender add-on. | session | `.blend` with an animated armature that moves like the actor |
| 5 | **Character.** A rigged human (MPFB2: the add-on is GPL, its assets CC0; verify at download) and the motion retargeted onto it. | together | The character does the beat |
| 6 | **Shot.** Blockout set (bench, lamp, props as primitives), camera, light, voice synced on the clap, EEVEE render. | together | `<film-root>/mvp/shot.mp4` |
| 7 | **Watch it.** Write what's broken, worst first. | Rafael | That list exists. It becomes the next plan. |

## Code gaps (each one is a task in its own repository)

1. `mocap-extract`: run alignment on one take from the CLI
   (`alignment` + `resample` already exist and just have no command yet).
2. `mocap-extract` calibration/1: ChArUco calibration from the synced
   calibration take (the task file exists).
3. `mocap-extract` body/1: FreeMoCap headless on the synced performance take
   (the task file exists).

Retargeting (step 5) is decided at step 5, after looking at what the add-on's
armature gives us. If it needs code, that's a new task.

## Known limits we accept for the MVP

- **Hands.** 2 MP front cameras won't give usable fingers. Wrists and arms
  only; fingers posed by hand if needed.
- **Face.** No face capture. Frame the shot so lip sync isn't the point
  (wide, profile or three-quarter back), or accept a still mouth.
- **Occlusion.** A seated actor behind a real table loses the lower body. Act
  on a backless stool with no table and add the table in Blender.
- **Cleanup.** No `mocap-adapt` yet: FreeMoCap's own filtering only. Foot
  sliding and jitter go on the step 7 list rather than getting fixed here.

## Gear

| Item | Where |
|---|---|
| ChArUco board, FreeMoCap "5x3 Charuco", 200 mm squares, A0 landscape | `/mnt/g/mocap-studio-downloads/calibration/charuco-5x3-200mm-A0.pdf` |
| Camera app APK | `mocap-camera-app` (built debug APK) |
| FreeMoCap 1.8.2 | `mocap-extract/.venv` |
| Blender 5.2.2, FreeMoCap Blender add-on, MPFB2 | to download into `/mnt/g/mocap-studio-downloads/apps/` (`DEPENDENCIES.md`) |

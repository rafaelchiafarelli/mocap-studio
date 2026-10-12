## 1. Study protocol

- **Depends on:** bootstrap/2
- **Contract:**
  - In: inventory
  - Requires: standardized takes: 10 s T-pose, walking, arm circles, hand gestures close to the torso, fast movement; lighting recorded; decision criteria as confirmed by Rafael (2026-10-12):
    - **Body detection ≥ 90 % of frames per body camera, counted from GO** (the ready-set-go moment in `take.json`, `mocap-capture` live-monitor/ready-check), because the actor may not be in frame when recording starts
    - **Calibration good to 1 cm:** reprojection error below the pixel size of 1 cm at the farthest working distance, and triangulated board geometry within 10 mm (`mocap-capture` studio-setup decision 5)
    - **Sync:** inter-camera timestamp error at most **one shutter (exposure) time** of the take, read from the recorded camera controls. Beyond that, the timestamp strategy itself is rethought
    - **Bones don't jitter:** after the filtering adopted in `mocap-adapt` (research task filtering/0), residual bone-end jitter ≤ 1–3 mm, and bone lengths stable. Jitter is a frequency problem to be filtered, and character models get enough fluidity that what remains reads as natural
  - Delivers: `study/protocol.md`
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** —

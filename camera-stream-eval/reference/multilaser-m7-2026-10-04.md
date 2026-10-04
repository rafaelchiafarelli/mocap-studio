# Reference: Multilaser M7 (M7_WIFI), 2026-10-03/04

The first device evaluated, with the prototype of this tool. Compare a new device's `report.md` against these numbers.

## Device

- Android 13 (SDK 33), 4× ARMv8 cores, 2 GB RAM, Allwinner SoC
- **One camera, front-facing**, 2 MP: YUV/encoder sizes 1600×1200, 640×480, 352×288, 320×240, all with fixed 30 fps
  (`[30,30]`), hardware level `limited`, timestamp source `unknown` (resolved to the monotonic clock)
- Hardware H.264 encoder `c2.allwinner.avc.encoder` (vendor-rated 22–108 fps at 720p; Android reports max 1280×720 and
  20 Mbps, but it really encodes 1600×1200 @ 30 fps); also software `c2.android.avc.encoder` / `OMX.google.h264.encoder`
- SoC: Allwinner A133
- Wi-Fi: 2.4 GHz only in our setup (2457 MHz), RSSI around −30 dBm, link 229–286 Mbps
- Image: soft, heavily denoised; stream is rotated 90° (sensor orientation)

## Results

| test | result |
|---|---|
| Software MJPEG, 640×480 | 30 fps, 12.6 ms/frame encode, 13% CPU |
| Software MJPEG, 1600×1200 | **14.8 fps**: the CPU can't JPEG-encode 2 MP at 30 fps |
| **Hardware H.264, 1600×1200, 8–20 Mbps** | **29.900 fps** real (sensor timestamps), 8–12% CPU, capture→encoded 32 ms |
| Frame interval | median 33.4 ms, p95 33.5 ms, max 33.6 ms when no frames are lost |
| 8 vs 20 Mbps image | no visible difference at 100% crop; the sensor is the limit, not the bitrate |
| Capture→PC latency (Wi-Fi) | min ~32 ms, median 45–60 ms, p95 60–113 ms |
| Clock sync (UDP) | best round trip 2.2–3.2 ms → ±1.1–1.6 ms; offset spread 0.2–0.6 ms |
| Clock drift | −17 to −22 ppm per tablet (about −1.3 ms/min), straight-line, corrected by before/after sync |
| Device wall clock | ~53 s off real time: never use it, use the sensor clock + sync |
| Embedded timestamps | 132 250 / 132 250 frames correct in the 20 min run; survive saving to `.h264` |
| Heat, 20 min at 20 Mbps (on charger) | max 36 °C battery, thermal status 0 |

### Several tablets on one 2.4 GHz access point (PC wired, 1 Gbps)

| run | total | result |
|---|---|---|
| 2 × 20 Mbps, 2 min | 40 Mbps | 0 and 7 frames lost |
| 3 × 20 Mbps, 2 min | 55 Mbps | one tablet lost 12% (bad moment for that tablet) |
| 4 × 10 Mbps, 2 min | 37 Mbps | 3 perfect, 1 lost 11% (was installing a system update) |
| **4 × 20 Mbps, 20 min** | **73.6 Mbps** | **3 tablets: 0–17 lost frames of ~35 880 (≤0.05%)**; the 4th lost 14%, all in the first 10 min while a system update ran, then ~2% |

Cross-camera timing (clock-synced): all cameras ran at exactly 29.900 fps. The phase between two cameras is fixed per
launch (we saw 1–15 ms) and slid by only what their drift difference predicts (e.g. 3.0 ms in 20 min for 2.7 ppm).

## Lessons that became features or defaults

- **Hardware H.264**, not MJPEG.
- **The receiver must run natively**: WSL2's NAT stalled the stream ~3 s every ~35 s (from Windows: max gap 113 ms).
- **Background system updates** wreck a device's numbers for minutes → `run-eval.sh` waits for them; disable auto-updates.
- **Dead batteries** reboot the devices: Wi-Fi adb (port 5555) resets, the app stops → keep devices on chargers; the app
  remembers its settings, so tapping its icon resumes streaming; `./dev wadb <ip>` reconnects without pairing.
- **USB through WSL (usbipd) was flaky** with these tablets (detached on USB resets): use it once, then Wi-Fi adb.
- **Settings over HTTP** (`/control`), so changing bitrate on many devices doesn't need adb.

First run of the finished kit (`./run-eval.sh --quick`, tablet 1, 2026-10-04): **PASS**, 8/8 checks: 1600×1200
@ 29.899 fps, 0 frames lost, capture→PC p95 ~62 ms, sync ±1.1 ms, drift −23 ppm, max 32 °C.

Raw data (CSV, logs, saved streams) from these runs stayed in the prototype folder `../tablet-stream-test/measurements/`.

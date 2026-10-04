# camera-stream-eval

Evaluates an Android device (tablet or phone) as a **live, clock-synchronised mocap camera**: it streams
H.264 over Wi-Fi with the capture time embedded in every frame, and a measuring script on the PC checks
frame rate, losses, gaps, latency, clock sync, heat and image quality. One command produces a report
with a PASS / WARN / FAIL verdict.

This is a decision tool, not the capture pipeline. It answers "is this device good enough, and at which
settings?" before anyone builds a streaming camera source into `mocap-capture`.
Reference results for the first device tested are in [reference/](reference/).

## Quick start

**PC:** Docker, `curl`, Python 3.8+ (standard library only). On Windows + WSL2, run the scripts from WSL
and install **Windows Python** (python.org). The scripts find it on their own. Measuring from inside WSL2
is wrong: WSL's NAT stalls TCP streams for ~3 s every ~35 s, which looks like frame loss.

**Device:** Android 5+, on the same network as the PC (ideally the dedicated capture network), on a charger.
1. Enable Developer options (tap *Build number* 7 times) → **USB debugging**, and on Android 11+ **Wireless debugging**.
2. Disable automatic system updates if the device allows it. A device that installs an update in the background
   loses frames (we measured ~22% loss until the update finished).

**Run** (from this folder):
```bash
./run-eval.sh --quick <device-ip>        # smoke test, ~6 min
./run-eval.sh <device-ip>                # full evaluation, ~25 min (matrix 60 s/step, 10 min soak)
./run-eval.sh --soak 20 <device-ip>      # longer soak
```
How the script reaches the device the first time, from easiest to hardest:
- **The device authorized this PC over USB before** ("Always allow"): just give its IP. The script finds the
  Wireless debugging port by scanning and connects, no pairing needed.
- **First contact over Wi-Fi (Android 11+):** on the device, open Wireless debugging → *Pair device with pairing code*, then
  `./run-eval.sh --pair <ip:pair-port> <code> <device-ip>`.
- **USB:** plug it in and accept the prompt, then `./run-eval.sh usb`. On WSL2 the device must be attached
  first, from Windows: `usbipd bind --busid <id>` (admin, once) and `usbipd attach --wsl --busid <id>`.
  The script then switches the device to Wi-Fi adb (port 5555 until it reboots).

Everything is built inside Docker (JDK 17, Android SDK 34, Gradle 8.7, adb, ffmpeg); nothing is installed on the PC.

## What a run does

| step | what | output (in `results/<model>-<serial>-<time>/`) |
|---|---|---|
| 1-2 | checks prerequisites, builds the Docker image and APK | |
| 3 | connects over Wi-Fi adb | |
| 4 | records device details: Wi-Fi link, battery, update setting, background load | `device-adb.txt` |
| 5 | installs and starts the app; asks it what the cameras/encoders support | `device.json` |
| 6 | waits for background system work (updates, app compilation) to finish | `load.json` |
| 7 | **matrix**: each resolution × bitrate, 60 s each | `steps/mNN-*` |
| 8 | **clock sync** over ~1 min (drift), **image samples**: 10 s of saved video, 3 JPEGs | `clocksync.json`, `samples/` |
| 9 | **soak** at the largest size and bitrate | `steps/soak-*` |
| | **report** | `report.md`, `verdict.json` |

Per step, `*-frames.csv` has one row per frame (sequence, sensor timestamp, capture time on the PC clock,
capture→PC latency); `*-stats.csv` has the device's own counters once per second (camera/encoder fps, CPU,
battery temperature, thermal status); `*-summary.json` has the numbers the report uses.

## Reading the report

The verdict is the worst grade of all checks. Thresholds are in `scripts/report.py` (`THRESHOLDS`):

| check | PASS | why |
|---|---|---|
| capture fps | ≥ 97% of target, measured from sensor timestamps | the camera really delivers the rate |
| lost frames | ≤ 0.5% | holes in the motion data |
| longest gap | ≤ 3.5 frame intervals | a long hole breaks tracking even if average loss is low |
| capture→PC p95 | ≤ 150 ms | live monitoring (not needed for offline processing) |
| embedded timestamps | every frame | frames must carry their capture time |
| clock sync | best round trip ≤ 6 ms (offset known to ±3 ms) | aligning cameras |
| drift | ≤ 100 ppm | corrected anyway; huge drift means an unstable clock |
| soak temperature / thermal status | ≤ 45 °C / ≤ 1 | throttling makes a device drop frames mid-session |

Things the verdict can't judge, which you should check yourself:
- **The sample JPEGs:** focus, noise, motion blur, exposure. A device can PASS every number and still be too soft for hands.
- **Lost frames per 2‑min block in the soak:** a bad start that recovers (background work) is different from a steady problem.
- **The phase between cameras:** run several devices together with `./dev multi`. With synced clocks, each camera's frames
  still start at their own moment (0–16 ms apart at 30 fps); that offset must stay steady during a take.

## Several devices at once

```bash
./dev found                  # every device running the app on the network
./dev ctl all bitrate=10000  # change settings on all of them over HTTP (no adb)
./dev multi 300              # measure all at the same time; compares their clock-synced capture times
```
For reference, on a 2.4 GHz access point, 4 tablets × 20 Mbps (73.6 Mbps total) ran for 20 min with ~0.05% loss on the healthy ones.

## How it works

**App** (`app/src/main/java/dev/mocapstudio/tabletstream/`, package name kept from the first prototype):

| file | role |
|---|---|
| `MainActivity.java` | starts/stops everything; keeps the screen on; remembers settings (tap the icon after a reboot); `/control` and `/info` handlers |
| `CameraStreamer.java` | Camera2: picks the camera, size and fps range; feeds the H.264 encoder's input Surface (or YUV → software JPEG in `mjpeg` mode) |
| `H264Encoder.java` | MediaCodec hardware H.264; adds the timestamp SEI to every frame |
| `TimestampSei.java` | builds the SEI NAL: UUID `MOCAPSTUDIO-TS01` + frame seq + sensor ns + device Unix ns |
| `SensorClock.java` | works out which clock camera timestamps use (monotonic vs boottime) |
| `TimeSyncServer.java` | UDP :8081 time server on the sensor clock (NTP-style) |
| `StreamServer.java` | HTTP :8080: `/stream` (multipart, one part per frame + headers), `/h264.raw` (play with `ffplay -f h264`), `/stats`, `/info`, `/control?width=&height=&fps=&mode=&bitrate=&quality=&facing=` |
| `Stats.java` | per-second counters, battery temperature, thermal status |
| `DeviceInfo.java` | `/info`: cameras, sizes, fps ranges, hardware level, timestamp source, H.264 encoders |

**Timing model:** `capture time on PC clock = sensor_ns + offset`. The offset comes from UDP probes, using the fastest
10% of round trips. `measure.py` syncs before and after each step and interpolates, which removes the device's
clock drift (17–22 ppm on the first tablets). Sanity check: capture→PC latency must never be negative.

**PC scripts** (`scripts/`, standard library only): `measure.py` (one device, one step), `clocksync.py`, `sei.py`
(timestamps out of a saved `.h264`: row N = Nth decoded frame), `multi.py`, `discover.py`, `findadb.py`,
`pick_sizes.py`, `report.py`, `env.sh` (finds the right Python).

`./dev` has every individual step (build, connect, install, launch, logs, ctl, measure); run `./dev` for the list.

## Adapting to a new Android device

Run `./run-eval.sh --quick <ip>` first; `report.md`, `device.json` and `./dev logs` show what doesn't fit.
These are the places that depend on the device, from most to least likely to need a change:

| symptom | where to change |
|---|---|
| **wrong camera** (phones have several back cameras: wide, ultra-wide, tele, plus a "logical" multi-camera) | `CameraStreamer.pickCamera()`: today it takes the first camera with the requested `facing`. Pick by id or focal length (`LENS_INFO_AVAILABLE_FOCAL_LENGTHS`), or handle logical cameras (`REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA`). Add an `id=` key to `/control` in `MainActivity.control()` / `INT_KEYS`/`STRING_KEYS`. |
| **resolution/fps not what was asked** | `CameraStreamer.pickSize()` (closest pixel count among `getOutputSizes(MediaCodec.class)`) and `pickFpsRange()` (prefers a fixed `[fps,fps]`). **60 fps** needs a range with upper 60 in `CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES`; **120+ fps** needs `createConstrainedHighSpeedCaptureSession` in `CameraStreamer.createSession()`. Test sizes come from `scripts/pick_sizes.py` (override with `--resolutions`). |
| **encoder fails, low fps at high resolution, or garbage video** | `H264Encoder.start()`: `createEncoderByType` takes the first AVC encoder; choose by name from `/info` (`MediaCodec.createByCodecName`). Also `KEY_PROFILE`/`KEY_LEVEL`, `KEY_BITRATE_MODE` (CBR helps steady Wi-Fi load), `KEY_I_FRAME_INTERVAL` (1 s now = worst-case recovery after a loss), or switch to HEVC (`MIMETYPE_VIDEO_HEVC`, then `sei.py`/`TimestampSei` need the HEVC NAL header). The SPS/PPS handling is in `H264Encoder.drain()` (`CODEC_CONFIG` buffer or `csd-0/1`). **Don't trust the limits `/info` reports**: the M7 claims its hardware encoder tops out at 1280×720 / 20 Mbps, yet it encodes 1600×1200 at 30 fps. Test, don't filter on them. |
| **motion blur / brightness pumping** (for mocap you want a short, fixed exposure) | Not implemented yet: set `CONTROL_AE_MODE_OFF` + `SENSOR_EXPOSURE_TIME` + `SENSOR_SENSITIVITY`, or `CONTROL_AE_LOCK`, and `CONTROL_AF_MODE`/`LENS_FOCUS_DISTANCE` on the `CaptureRequest.Builder` in `CameraStreamer.createSession()`. Needs `MANUAL_SENSOR` capability (see `hardware_level` in `/info`: `limited` devices may not allow it). Expose them through `/control`. |
| **capture→PC latency negative, or sync drift huge/jumpy** | `SensorClock` (decides monotonic vs boottime from the first frame when `timestamp_source` is `unknown`; a `realtime` source forces boottime). `TimeSyncServer` must read the same clock. |
| **image rotated** | No rotation is applied; the stream is sensor-oriented. Add `SENSOR_ORIENTATION` to `DeviceInfo.cameras()` and record it per device rather than rotating pixels. |
| **app killed / stream stops when the screen dims or after a while** (OEM battery savers: Xiaomi, Samsung, Huawei...) | `MainActivity` keeps the screen on and runs in the foreground only. Disable battery optimisation for the app on the device; if that isn't enough, move the pipeline into a foreground `Service` (Android 14+: `foregroundServiceType="camera"` + `FOREGROUND_SERVICE_CAMERA` permission in `AndroidManifest.xml`). |
| **won't install / crashes on old Android** | `minSdk 21` in `app/build.gradle`. API-level guards are in `Stats.tick()` (thermal API 29+) and `DeviceInfo.encoders()` (`isHardwareAccelerated` 29+). Look at `./dev logs` for `AndroidRuntime` errors. |
| **script can't find the device's IP** | `wlan0` is hard-coded in `run-eval.sh` (step 3, `usb` mode) and `dev` (`ip_of`). Some devices use `wlan1`/`swlan0`. |
| **background-load wait never ends / misses something** | process names in `busy_now()` in `run-eval.sh` (step 6). |
| **device-adb.txt empty in places** | vendor-specific `dumpsys` output in `run-eval.sh` step 4. Only informational; the report doesn't depend on it. |
| **thresholds don't fit the use** (e.g. a device only for slow body capture) | `THRESHOLDS` in `scripts/report.py`; matrix defaults at the top of `run-eval.sh`. |
| **ports 8080/8081 clash** | `MainActivity.PORT` / `SYNC_PORT`, `PORT` in `scripts/env.sh`, `--port` in the Python scripts, `clocksync.measure_offset(port=)`. |

Keep the wire formats unchanged unless every script changes with them. The `/stream` part headers (`X-Kind`,
`X-Frame-Seq`, `X-Timestamp-Ns`, `X-Wall-Ms`), the SEI payload (`TimestampSei` ↔ `scripts/sei.py`) and the UDP sync
reply (`TimeSyncServer` ↔ `scripts/clocksync.py`) are what makes results comparable between devices.

## Known limitations

- Exposure, ISO and focus are automatic (see the table above). Frame timing is steady on the tested tablets, but brightness can change during a take.
- One camera per device at a time; no audio.
- The sensor-timestamp → PC-clock mapping is as good as the clock sync (±1–3 ms on a quiet LAN). It doesn't make cameras
  capture at the same instant. Their frames stay a fixed 0–16 ms apart at 30 fps, measured but not removed.
- Debug-signed APK with a shared test key (`app/debug.keystore`): fine for test devices, not for distribution.

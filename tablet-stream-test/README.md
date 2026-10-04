# tablet-stream-test

Throwaway stress test: can an old Android tablet capture, JPEG-encode and stream
its camera over HTTP at a given resolution/FPS, and for how long before it
throttles? Not part of the mocap-capture baseline (which imports tablet
recordings via `adb pull`).

Everything runs in Docker (`./dev` wraps it): JDK 17, Android SDK 34, Gradle 8.7, adb.

## Connect the tablet

WSL2 doesn't see USB devices by default. Pick one:

- **Wi-Fi, Android 11+:** Developer options → Wireless debugging → "Pair device with pairing code", then
  `./dev pair <ip:pair-port> <code>` and `./dev connect <ip:port>` (the port shown on the Wireless debugging screen).
- **Wi-Fi, older Android:** needs USB once, from Windows: `adb tcpip 5555`, then `./dev connect <tablet-ip>`.
- **USB:** on Windows (admin) `winget install usbipd`, `usbipd list`, `usbipd bind --busid <id>`,
  `usbipd attach --wsl --busid <id>`, then `./dev down && ./dev devices`.

## Run a test

```
./dev build                          # APK
./dev install                        # installs with camera permission granted
./dev launch 1280 720 30 80 back     # width height fps jpeg-quality facing
./dev forward                        # stream at http://localhost:8080/ (works from the Windows browser too)
./dev measure 300                    # 5 min run → measurements/<stamp>-{frames,stats}.csv + summary
```

Over Wi-Fi you can also measure directly against the tablet's IP: `./dev measure 300 <tablet-ip>`
(that tests the Wi-Fi link; `forward` tests the adb link).

## What the numbers mean

| field | meaning |
|---|---|
| `camera_fps` | frames the sensor delivered |
| `encoded_fps` / `dropped_frames` | frames the CPU managed to turn into JPEG / frames it had to skip |
| `client_skipped_frames` | encoded frames a client never got (network too slow) |
| `encode_ms`, `app_cpu_percent` | cost per frame, CPU load of the app |
| `battery_temp_c`, `thermal_status` | heat over time (thermal status only on Android 10+) |
| `X-Timestamp-Ns` (per frame) | sensor timestamp, for jitter between frames |

The tablet can keep up if `encoded_fps ≈ camera_fps ≈ target fps` for the whole run and
the temperature levels off instead of climbing.

## Timestamps and clock sync

- Every H.264 frame carries an SEI NAL (`user_data_unregistered`, UUID `MOCAPSTUDIO-TS01`) with
  frame seq, camera sensor timestamp (ns, tablet monotonic clock) and the tablet's Unix-time
  equivalent. It survives saving the stream: `python3 scripts/sei.py file.h264` → CSV, row N =
  Nth decoded frame.
- UDP port 8081 answers time probes on the sensor clock. `scripts/clocksync.py --host <ip>` gives
  `offset_ns` so that `capture time on PC clock = sensor_ns + offset_ns`, plus drift with `--rounds`.
- `measure.py` syncs before and after the run, interpolates the offset (drift) and reports
  capture→PC latency per frame; a negative latency would mean the sync is wrong.
- Run the receiver natively (Windows/Linux), not inside WSL2: WSL's NAT stalls the stream ~3 s every ~35 s.
  From WSL: `/mnt/c/Python314/python.exe scripts/measure.py --host <ip> --seconds 90 --save-stream`.

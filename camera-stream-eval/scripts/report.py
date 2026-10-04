#!/usr/bin/env python3
"""Turn a run-eval.sh results folder into report.md (+ verdict.json) with PASS / WARN / FAIL per check.

usage: report.py <results-dir>

Thresholds are in THRESHOLDS below; they encode what mocap capture needs from a camera device:
the frame rate it promises, almost no lost frames, short gaps, low enough latency to monitor live,
timestamps that survive, a clock sync good to a few ms, and no thermal throttling over a session.
"""
import csv
import glob
import json
import os
import statistics
import sys

THRESHOLDS = {
    # name: (pass if <=/>= this, warn if <=/>= this, direction)
    "capture_fps_ratio": (0.97, 0.90, "min"),   # real capture rate / requested fps
    "loss_pct": (0.5, 2.0, "max"),              # frames encoded but never received
    "longest_gap_frames": (3.5, 15, "max"),     # longest gap between received frames, in frame intervals
    "latency_ms_p95": (150, 300, "max"),        # capture -> PC, for live monitoring
    "sei_bad": (0, 0, "max"),                   # frames whose embedded timestamp is missing/wrong
    "sync_rtt_ms": (6, 20, "max"),              # best clock-sync round trip; uncertainty is half of it
    "drift_ppm_abs": (100, 300, "max"),         # device clock vs PC clock (corrected, but must be stable)
    "temp_c_max": (45, 50, "max"),              # battery temperature during the soak
    "thermal_status_max": (1, 2, "max"),        # Android thermal status (0 none ... 6 shutdown), Android 10+
}

RANK = {"PASS": 0, "INFO": 0, "WARN": 1, "FAIL": 2}


def grade(name, value):
    if value is None:
        return "INFO"
    ok, warn, direction = THRESHOLDS[name]
    if direction == "max":
        return "PASS" if value <= ok else "WARN" if value <= warn else "FAIL"
    return "PASS" if value >= ok else "WARN" if value >= warn else "FAIL"


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def fmt(v, f="{:.1f}"):
    return f.format(v) if isinstance(v, (int, float)) else "-"


def step_checks(s, fps):
    interval = 1000.0 / fps
    checks = {
        "capture_fps_ratio": s.get("capture_fps", 0) / fps if s.get("capture_fps") else None,
        "loss_pct": s.get("loss_pct"),
        "longest_gap_frames": s["longest_gap_ms"] / interval if s.get("longest_gap_ms") else None,
        "latency_ms_p95": s.get("latency_ms_p95"),
        "sei_bad": s.get("sei_bad"),
    }
    grades = {k: grade(k, v) for k, v in checks.items()}
    if not s.get("frames_received") or s.get("frames_received", 0) < 2:
        grades["no_frames"] = "FAIL"
    if s.get("error"):
        grades["device_error"] = "FAIL"
    return checks, grades


def worst(grades):
    return max(grades, key=lambda g: RANK[g]) if grades else "INFO"


def loss_by_block(frames_csv, block_s=120):
    """Lost-frame % per block of time, to tell a bad start (e.g. background updates) from a steady problem."""
    try:
        with open(frames_csv) as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return []
    if len(rows) < 2:
        return []
    t0 = float(rows[0]["pc_arrival_s"])
    blocks = {}
    prev = None
    for r in rows:
        b = blocks.setdefault(int((float(r["pc_arrival_s"]) - t0) // block_s), [0, 0])
        b[0] += 1
        seq = int(r["seq"])
        if prev is not None and seq > prev + 1:
            b[1] += seq - prev - 1
        prev = seq
    return [100.0 * lost / (got + lost) for _, (got, lost) in sorted(blocks.items())]


def temps_by_block(stats_csv, block_s=120):
    try:
        with open(stats_csv) as f:
            rows = [r for r in csv.DictReader(f) if r.get("battery_temp_c")]
    except OSError:
        return []
    if not rows:
        return []
    t0 = float(rows[0]["pc_time"])
    blocks = {}
    for r in rows:
        blocks.setdefault(int((float(r["pc_time"]) - t0) // block_s), []).append(float(r["battery_temp_c"]))
    return [max(v) for _, v in sorted(blocks.items())]


def main():
    run = sys.argv[1]
    meta = load_json(os.path.join(run, "run.json"), {})
    info = load_json(os.path.join(run, "device.json"), {})
    fps = float(meta.get("fps", 30))
    lines = []
    w = lines.append
    all_grades = []

    w(f"# Camera stream evaluation: {info.get('manufacturer', '?')} {info.get('model', '?')}")
    w("")
    w(f"Run {meta.get('started', '?')} - device {meta.get('device_ip', '?')} - receiver: {meta.get('receiver', '?')}")
    w("")
    w("VERDICT_PLACEHOLDER")
    w("")

    # --- device -------------------------------------------------------------------------------
    w("## Device")
    w("")
    w(f"- **Android** {info.get('android', '?')} (SDK {info.get('sdk', '?')}), SoC `{info.get('soc', '?')}`, "
      f"{info.get('cores', '?')} cores, camera timestamps on the `{info.get('sensor_clock', '?')}` clock")
    for c in info.get("cameras", []):
        sizes = ", ".join(c.get("encoder_sizes", [])[:12])
        w(f"- **Camera {c.get('id')}** ({c.get('facing')}, hardware level `{c.get('hardware_level')}`, "
          f"timestamp source `{c.get('timestamp_source')}`): fps ranges {', '.join(c.get('fps_ranges', []))}; "
          f"encoder sizes {sizes}")
    hw = [e for e in info.get("h264_encoders", []) if e.get("hardware") == "true"]
    for e in info.get("h264_encoders", []):
        w(f"- **H.264 encoder** `{e.get('name')}` ({'hardware' if e.get('hardware') == 'true' else 'software'}), "
          f"up to {e.get('max_size')}, {e.get('bitrate_kbps')} kbps")
    if not hw:
        w("- **WARN: no hardware H.264 encoder reported** - high resolutions will likely not reach the target fps")
        all_grades.append("WARN")
    if not any(c.get("facing") == "back" for c in info.get("cameras", [])):
        w("- note: no back camera; the test used the first camera")
    adb_txt = os.path.join(run, "device-adb.txt")
    if os.path.exists(adb_txt):
        w(f"- More detail (Wi-Fi link, battery, update settings, background load): [device-adb.txt](device-adb.txt)")
    load = load_json(os.path.join(run, "load.json"), {})
    if load:
        busy = load.get("busy_processes") or []
        w(f"- Background load before testing: {'**busy: ' + ', '.join(busy) + '**' if busy else 'idle'}"
          f" (waited {load.get('waited_s', 0)} s)")
        if busy:
            all_grades.append("WARN")
    w("")

    # --- matrix -------------------------------------------------------------------------------
    w("## Test matrix")
    w("")
    w(f"Each step streams for {meta.get('step_seconds', '?')} s at the requested settings; "
      f"target {fps:.0f} fps. The device picks the nearest size it supports (see *actual*).")
    w("")
    w("| step | actual config | capture fps | lost | longest gap | capture->PC p50 / p95 | Mbps | KB/frame "
      "| device CPU | encode latency | verdict |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    steps = sorted(glob.glob(os.path.join(run, "steps", "*-summary.json")))
    soak = None
    for path in steps:
        s = load_json(path, {})
        name = os.path.basename(path)[:-len("-summary.json")]
        checks, grades = step_checks(s, fps)
        v = worst(grades.values())
        all_grades.append(v)
        if name.startswith("soak"):
            soak = (name, s, checks, grades)
        cfg = (s.get("config") or "").replace("camera ", "cam ")
        w(f"| {name} | {cfg} | {fmt(s.get('capture_fps'), '{:.2f}')} | {s.get('frames_lost', '-')} "
          f"({fmt(s.get('loss_pct'), '{:.2f}')}%) | {fmt(s.get('longest_gap_ms'), '{:.0f}')} ms "
          f"| {fmt(s.get('latency_ms_median'), '{:.0f}')} / {fmt(s.get('latency_ms_p95'), '{:.0f}')} ms "
          f"| {fmt(s.get('mbps'))} | {fmt(s.get('kb_per_frame'), '{:.0f}')} | {fmt(s.get('cpu_pct_median'), '{:.0f}')}% "
          f"| {fmt(s.get('encode_latency_ms_median'), '{:.0f}')} ms | **{v}** |")
        bad = [k for k, g in grades.items() if g in ("WARN", "FAIL")]
        if bad:
            w(f"|  | ↳ {', '.join(f'{k}={grades[k]}' for k in bad)} | | | | | | | | | |")
        if s.get("error"):
            w(f"|  | ↳ device error: {s['error']} | | | | | | | | | |")
    w("")

    # --- clock sync ---------------------------------------------------------------------------
    w("## Clock sync")
    w("")
    rounds = load_json(os.path.join(run, "clocksync.json"), [])
    if rounds:
        best = min(r["best_rtt_ms"] for r in rounds)
        t0, o0 = rounds[0]["pc_unix_ns"], rounds[0]["offset_ns"]
        dt = (rounds[-1]["pc_unix_ns"] - t0) / 1e9
        drift_ppm = (rounds[-1]["offset_ns"] - o0) / 1e6 / dt * 1000 if dt > 0 else 0
        # Residual after a straight-line drift fit: how stable the clock relationship is.
        xs = [(r["pc_unix_ns"] - t0) / 1e9 for r in rounds]
        ys = [(r["offset_ns"] - o0) / 1e6 for r in rounds]
        resid = 0.0
        if len(rounds) >= 3:
            mx, my = statistics.mean(xs), statistics.mean(ys)
            sxx = sum((x - mx) ** 2 for x in xs) or 1
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
            resid = max(abs(y - (my + slope * (x - mx))) for x, y in zip(xs, ys))
        g_rtt, g_drift = grade("sync_rtt_ms", best), grade("drift_ppm_abs", abs(drift_ppm))
        all_grades += [g_rtt, g_drift]
        w(f"- {len(rounds)} rounds over {dt:.0f} s. Best round trip **{best:.2f} ms** -> offset known to "
          f"+/-{best / 2:.1f} ms (**{g_rtt}**)")
        w(f"- Device clock drift **{drift_ppm:+.1f} ppm** ({drift_ppm * 60 / 1000:+.2f} ms per minute) (**{g_drift}**); "
          f"largest deviation from a straight-line drift: {resid:.2f} ms")
        w(f"- Device wall clock is off from the PC by {rounds[-1]['tablet_wall_error_ms'] / 1000:+.1f} s "
          f"(irrelevant: frames are timed on the camera clock + this sync)")
    else:
        w("- not measured")
    w("")

    # --- soak ---------------------------------------------------------------------------------
    w("## Soak")
    w("")
    if soak:
        name, s, checks, grades = soak
        g_temp = grade("temp_c_max", s.get("temp_c_max"))
        g_therm = grade("thermal_status_max", s.get("thermal_status_max"))
        all_grades += [g_temp, g_therm]
        w(f"- {name}: {fmt(s.get('duration_s', 0) / 60, '{:.1f}')} min at {s.get('config')}")
        w(f"- Battery temperature {fmt(s.get('temp_c_start'))} -> {fmt(s.get('temp_c_end'))} C, "
          f"max {fmt(s.get('temp_c_max'))} C (**{g_temp}**); thermal status max {s.get('thermal_status_max', 'n/a')} "
          f"(**{g_therm}**); battery {fmt(s.get('battery_start'), '{:.0f}')} -> {fmt(s.get('battery_end'), '{:.0f}')}% "
          f"(charging: {s.get('charging')})")
        lb = loss_by_block(os.path.join(run, "steps", f"{name}-frames.csv"))
        tb = temps_by_block(os.path.join(run, "steps", f"{name}-stats.csv"))
        if lb:
            w(f"- Lost frames per 2-min block: {' '.join(f'{x:.1f}%' for x in lb)}")
        if tb:
            w(f"- Max temperature per 2-min block: {' '.join(f'{x:.1f}' for x in tb)} C")
        w(f"- Clock drift during the soak: {fmt(s.get('drift_ppm'))} ppm")
    else:
        w("- not run")
    w("")

    # --- samples ------------------------------------------------------------------------------
    w("## Image samples")
    w("")
    sdir = os.path.join(run, "samples")
    probe = ""
    try:
        with open(os.path.join(sdir, "ffprobe.txt")) as f:
            probe = f.read().strip()
    except OSError:
        pass
    if probe:
        props = dict(l.split("=", 1) for l in probe.splitlines() if "=" in l)
        sei_rows = 0
        try:
            with open(os.path.join(sdir, "sample-sei.csv")) as f:
                sei_rows = sum(1 for _ in f) - 1
        except OSError:
            pass
        frames = int(props.get("nb_read_frames", 0) or 0)
        g = "PASS" if frames and sei_rows == frames else "FAIL"
        all_grades.append(g)
        w(f"- Saved stream decodes as {props.get('codec_name')} {props.get('profile')} "
          f"{props.get('width')}x{props.get('height')}, {frames} frames; {sei_rows} embedded timestamps "
          f"(**{g}**: every decoded frame must carry one)")
        for jpg in sorted(glob.glob(os.path.join(sdir, "*.jpg"))):
            w(f"- ![{os.path.basename(jpg)}](samples/{os.path.basename(jpg)})")
        w("- Judge these by eye: focus, noise, motion blur, exposure. The numbers above can't.")
    else:
        w("- not captured")
    w("")

    # --- legend -------------------------------------------------------------------------------
    w("## How to read this")
    w("")
    w("| check | PASS | WARN | why it matters |")
    w("|---|---|---|---|")
    why = {
        "capture_fps_ratio": "the camera really delivers the requested rate (from sensor timestamps)",
        "loss_pct": "lost frames are holes in the motion data",
        "longest_gap_frames": "a long hole breaks tracking even if the average loss is low",
        "latency_ms_p95": "live monitoring; not critical for offline processing",
        "sei_bad": "every frame must carry its capture time",
        "sync_rtt_ms": "the clock sync is good to +/- half of this",
        "drift_ppm_abs": "drift is corrected, but huge drift means an unstable clock",
        "temp_c_max": "hot devices throttle and drop frames mid-session",
        "thermal_status_max": "Android's own throttling signal",
    }
    for k, (ok, warn, d) in THRESHOLDS.items():
        op = "<=" if d == "max" else ">="
        w(f"| {k} | {op} {ok} | {op} {warn} | {why[k]} |")
    w("")
    w("FAIL = worse than WARN. Thresholds live in `scripts/report.py` (THRESHOLDS).")

    verdict = worst(all_grades)
    counts = {g: all_grades.count(g) for g in ("PASS", "WARN", "FAIL")}
    text = "\n".join(lines).replace(
        "VERDICT_PLACEHOLDER",
        f"## Verdict: **{verdict}**  ({counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail)")
    with open(os.path.join(run, "report.md"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    with open(os.path.join(run, "verdict.json"), "w") as f:
        json.dump({"verdict": verdict, **counts}, f)
    print(f"verdict: {verdict} ({counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail) -> "
          f"{os.path.join(run, 'report.md')}")


if __name__ == "__main__":
    main()

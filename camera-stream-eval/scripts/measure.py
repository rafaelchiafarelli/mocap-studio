#!/usr/bin/env python3
"""Pull one device's stream for N seconds and record what actually arrived.

Writes into --out-dir (default measurements/), prefix --name (default a timestamp):
  <name>-frames.csv    one row per received frame (seq, sensor timestamp, capture time on the PC clock, latency)
  <name>-stats.csv     the device's /stats once per second (fps, CPU, temperature, ...)
  <name>-summary.json  the key numbers, read by report.py
  <name>.h264          the stream itself, with --save-stream (H.264 mode)
and prints a human-readable summary.

Clock sync (UDP 8081) runs before and after; the offset is interpolated over the run to correct drift.
Standard library only, so it runs with any Python 3.8+ (run it natively, not inside WSL2).

usage: measure.py --host <ip> [--seconds 60] [--out-dir DIR] [--name NAME] [--save-stream]
"""
import argparse
import csv
import json
import os
import socket
import statistics
import threading
import time
import urllib.request

import clocksync
import sei


def read_line(f):
    line = f.readline()
    if not line:
        raise EOFError
    return line.decode("ascii", "replace").strip()


def poll_stats(base, stop, rows):
    while not stop.is_set():
        try:
            with urllib.request.urlopen(base + "/stats", timeout=2) as r:
                j = json.loads(r.read())
            j["pc_time"] = time.time()
            rows.append(j)
        except Exception as e:  # device busy or gone; keep going
            rows.append({"pc_time": time.time(), "poll_error": str(e)})
        stop.wait(1.0)


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]


def sync(host, label):
    try:
        r = clocksync.measure_offset(host, probes=100)
        print(f"clock sync {label}: {clocksync.describe(r)}", flush=True)
        return r
    except Exception as e:
        print(f"clock sync {label} failed: {e}", flush=True)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--out-dir", default="measurements")
    ap.add_argument("--name", default="", help="output file prefix (default: timestamp)")
    ap.add_argument("--save-stream", action="store_true", help="save the H.264 stream (h264 mode)")
    ap.add_argument("--save-every", type=int, default=0, help="MJPEG mode: save every Nth JPEG (0 = none)")
    args = ap.parse_args()

    base = f"http://{args.host}:{args.port}"
    name = args.name or time.strftime("%Y%m%d-%H%M%S")
    os.makedirs(args.out_dir, exist_ok=True)
    out = lambda suffix: os.path.join(args.out_dir, name + suffix)

    sync_before = sync(args.host, "before")

    stop = threading.Event()
    stats_rows = []
    threading.Thread(target=poll_stats, args=(base, stop, stats_rows), daemon=True).start()

    sock = socket.create_connection((args.host, args.port), timeout=5)
    sock.sendall(f"GET /stream HTTP/1.0\r\nHost: {args.host}\r\n\r\n".encode())
    f = sock.makefile("rb")
    while read_line(f):  # response headers
        pass

    frames = []
    keyframes = sei_ok = sei_bad = 0
    raw = open(out(".h264"), "wb") if args.save_stream else None
    t_end = time.time() + args.seconds
    print(f"measuring {base}/stream for {args.seconds:.0f}s ...", flush=True)
    ended_early = ""
    try:
        while time.time() < t_end:
            line = read_line(f)
            if not line.startswith("--"):
                continue
            headers = {}
            while True:
                line = read_line(f)
                if not line:
                    break
                k, _, v = line.partition(":")
                headers[k.strip().lower()] = v.strip()
            n = int(headers["content-length"])
            data = f.read(n)
            arrival = time.time()
            kind = headers.get("x-kind", "jpeg")
            if raw and kind != "jpeg":
                raw.write(data)
            if kind == "config":
                continue
            keyframes += kind == "key"
            seq = int(headers.get("x-frame-seq", -1))
            sensor_ns = int(headers.get("x-timestamp-ns", 0))
            if kind != "jpeg":
                ts = next(sei.find_timestamps(data), None)
                if ts and ts[0] == seq and ts[1] == sensor_ns:
                    sei_ok += 1
                else:
                    sei_bad += 1
            frames.append({"seq": seq, "sensor_ns": sensor_ns, "tablet_wall_ms": int(headers.get("x-wall-ms", 0)),
                           "pc_arrival_s": arrival, "bytes": n})
            if kind == "jpeg" and args.save_every and len(frames) % args.save_every == 0:
                with open(out(f"-{seq:06d}.jpg"), "wb") as img:
                    img.write(data)
    except (EOFError, ConnectionError, socket.timeout) as e:
        ended_early = repr(e)
        print(f"stream ended early: {ended_early}")
    finally:
        stop.set()
        sock.close()
        if raw:
            raw.close()

    sync_after = sync(args.host, "after")

    # Capture time on the PC clock: sensor_ns + offset, offset interpolated between the two syncs (drift).
    def offset_at(t_ns):
        if not sync_before or not sync_after:
            return (sync_before or sync_after or {}).get("offset_ns")
        a, b = sync_before, sync_after
        k = (t_ns - a["pc_unix_ns"]) / max(1, b["pc_unix_ns"] - a["pc_unix_ns"])
        return a["offset_ns"] + k * (b["offset_ns"] - a["offset_ns"])

    for fr in frames:
        off = offset_at(int(fr["pc_arrival_s"] * 1e9))
        if off is None:
            fr["capture_pc_s"] = fr["latency_ms"] = ""
        else:
            fr["capture_pc_s"] = (fr["sensor_ns"] + off) / 1e9
            fr["latency_ms"] = (fr["pc_arrival_s"] - fr["capture_pc_s"]) * 1000

    with open(out("-frames.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["seq", "sensor_ns", "tablet_wall_ms", "pc_arrival_s", "capture_pc_s",
                                           "latency_ms", "bytes"])
        w.writeheader()
        w.writerows(frames)
    with open(out("-stats.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for r in stats_rows for k in r}))
        w.writeheader()
        w.writerows(stats_rows)

    summary = summarize(frames, stats_rows, sync_before, sync_after, keyframes, sei_ok, sei_bad, args.seconds)
    summary["ended_early"] = ended_early
    with open(out("-summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    print_summary(summary)
    print(f"\nwrote {out('-frames.csv')}\n      {out('-stats.csv')}\n      {out('-summary.json')}"
          + (f"\n      {out('.h264')}" if raw else ""))


def summarize(frames, stats_rows, sync_before, sync_after, keyframes, sei_ok, sei_bad, seconds):
    s = {"requested_seconds": seconds, "frames_received": len(frames)}
    good = [r for r in stats_rows if "camera_fps" in r]
    last = good[-1] if good else {}
    for k in ("config", "device", "error", "note", "sensor_clock", "android_sdk", "cores"):
        s[k] = last.get(k)
    s["tablet_dropped"] = last.get("dropped_frames")
    s["slow_sends"] = last.get("slow_writes")
    s["longest_send_ms"] = last.get("max_write_ms")
    if len(frames) < 2:
        return s

    dur = frames[-1]["pc_arrival_s"] - frames[0]["pc_arrival_s"]
    lost = sum(max(0, b["seq"] - a["seq"] - 1) for a, b in zip(frames, frames[1:]))
    sensor_dt = [(b["sensor_ns"] - a["sensor_ns"]) / 1e6 for a, b in zip(frames, frames[1:])]
    med = statistics.median(sensor_dt)
    intervals = sum(max(1, round(d / med)) for d in sensor_dt) if med > 0 else 0
    span_s = (frames[-1]["sensor_ns"] - frames[0]["sensor_ns"]) / 1e9
    s.update({
        "duration_s": dur,
        "fps_at_pc": (len(frames) - 1) / dur if dur > 0 else 0,
        "capture_fps": intervals / span_s if span_s > 0 else 0,  # from sensor timestamps, immune to losses
        "frames_lost": lost,
        "loss_pct": 100.0 * lost / (len(frames) + lost),
        "keyframes": keyframes,
        "frame_interval_ms_median": med,
        "frame_interval_ms_p95": pct(sensor_dt, 95),
        "longest_gap_ms": max(sensor_dt),
        "mbps": sum(fr["bytes"] for fr in frames) * 8 / dur / 1e6 if dur > 0 else 0,
        "kb_per_frame": statistics.mean(fr["bytes"] for fr in frames) / 1024,
        "sei_ok": sei_ok,
        "sei_bad": sei_bad,
    })
    lat = [fr["latency_ms"] for fr in frames if fr["latency_ms"] != ""]
    if lat:
        s.update({"latency_ms_min": min(lat), "latency_ms_median": statistics.median(lat),
                  "latency_ms_p95": pct(lat, 95), "latency_ms_max": max(lat)})
    for label, r in (("before", sync_before), ("after", sync_after)):
        if r:
            s[f"sync_{label}_best_rtt_ms"] = r["best_rtt_ms"]
            s[f"sync_{label}_median_rtt_ms"] = r["median_rtt_ms"]
            s[f"sync_{label}_spread_ms"] = r["offset_spread_ms"]
            s[f"sync_{label}_reply_pct"] = 100.0 * r["replies"] / r["probes"]
            s["device_wall_clock_error_ms"] = r["tablet_wall_error_ms"]
    if sync_before and sync_after:
        dt = (sync_after["pc_unix_ns"] - sync_before["pc_unix_ns"]) / 1e9
        drift = (sync_after["offset_ns"] - sync_before["offset_ns"]) / 1e6
        s["drift_ms"] = drift
        s["drift_ppm"] = drift / dt * 1000 if dt > 0 else 0

    num = lambda k: [float(r[k]) for r in good if r.get(k) not in (None, "")]
    for k, name in (("camera_fps", "camera_fps"), ("encoded_fps", "encoded_fps"), ("app_cpu_percent", "cpu_pct"),
                    ("encode_ms", "encode_latency_ms")):
        v = num(k)[2:] or num(k)  # skip the first seconds (startup)
        if v:
            s[f"{name}_median"] = statistics.median(v)
            s[f"{name}_min"] = min(v)
    temps = num("battery_temp_c")
    if temps:
        s.update({"temp_c_start": temps[0], "temp_c_end": temps[-1], "temp_c_max": max(temps)})
    thermal = num("thermal_status")
    if thermal:
        s["thermal_status_max"] = max(thermal)
    lvl = num("battery_level")
    if lvl:
        s.update({"battery_start": lvl[0], "battery_end": lvl[-1]})
    s["charging"] = last.get("charging")
    return s


def print_summary(s):
    g = lambda k, f="{:.1f}": (f.format(s[k]) if isinstance(s.get(k), (int, float)) else str(s.get(k, "?")))
    print()
    print(f"config            {s.get('config')}")
    print(f"device            {s.get('device')} (SDK {s.get('android_sdk')})")
    if "duration_s" not in s:
        print("not enough frames received")
        return
    print(f"frames received   {s['frames_received']} in {g('duration_s')}s, lost {s['frames_lost']} ({g('loss_pct', '{:.2f}')}%)")
    print(f"capture rate      {g('capture_fps', '{:.3f}')} fps (sensor timestamps); at PC {g('fps_at_pc', '{:.2f}')} fps")
    print(f"frame interval    median {g('frame_interval_ms_median')} ms, p95 {g('frame_interval_ms_p95')}, longest gap {g('longest_gap_ms')}")
    print(f"capture->PC       min {g('latency_ms_min')} ms, median {g('latency_ms_median')}, p95 {g('latency_ms_p95')}, max {g('latency_ms_max')}")
    print(f"clock sync        best rtt {g('sync_before_best_rtt_ms', '{:.2f}')} ms, drift {g('drift_ppm')} ppm")
    if s.get("sei_ok") or s.get("sei_bad"):
        print(f"timestamp SEI     {s['sei_ok']} ok, {s['sei_bad']} missing/mismatched")
    print(f"bitrate           {g('mbps')} Mbps, {g('kb_per_frame', '{:.0f}')} KB/frame")
    print(f"device side       camera {g('camera_fps_median')} fps, encoded {g('encoded_fps_median')} fps, "
          f"dropped {s.get('tablet_dropped')}, CPU {g('cpu_pct_median', '{:.0f}')}%, slow sends {s.get('slow_sends')}")
    print(f"temperature       {g('temp_c_start')} -> {g('temp_c_end')} C (max {g('temp_c_max')}), "
          f"thermal status max {s.get('thermal_status_max', '?')}")


if __name__ == "__main__":
    main()

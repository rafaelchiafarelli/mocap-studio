#!/usr/bin/env python3
"""Pull the tablet's MJPEG stream for N seconds and report what actually arrived.

Writes measurements/<stamp>-frames.csv (one row per frame) and
measurements/<stamp>-stats.csv (the tablet's /stats once per second), then prints a summary.

usage: measure.py [--host 127.0.0.1] [--port 8080] [--seconds 60] [--save-every 0] [--save-stream]

--save-stream writes the H.264 elementary stream to measurements/<stamp>.h264 (h264 mode).
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
        except Exception as e:  # tablet busy or gone; keep going
            rows.append({"pc_time": time.time(), "error": str(e)})
        stop.wait(1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--save-every", type=int, default=0, help="save every Nth JPEG (0 = none)")
    ap.add_argument("--name", default="", help="output file prefix (default: timestamp[-tag])")
    ap.add_argument("--tag", default="", help="suffix for output files (e.g. the device)")
    ap.add_argument("--save-stream", action="store_true", help="save the H.264 stream (h264 mode)")
    args = ap.parse_args()

    base = f"http://{args.host}:{args.port}"
    stamp = time.strftime("%Y%m%d-%H%M%S") + (f"-{args.tag}" if args.tag else "")
    stamp = args.name or stamp
    out_dir = "measurements"
    os.makedirs(out_dir, exist_ok=True)

    def sync(label):
        try:
            r = clocksync.measure_offset(args.host, probes=100)
            print(f"clock sync {label}: {clocksync.describe(r)}")
            return r
        except Exception as e:
            print(f"clock sync {label} failed: {e}")
            return None

    sync_before = sync("before")

    stop = threading.Event()
    stats_rows = []
    poller = threading.Thread(target=poll_stats, args=(base, stop, stats_rows), daemon=True)
    poller.start()

    sock = socket.create_connection((args.host, args.port), timeout=5)
    sock.sendall(f"GET /stream HTTP/1.0\r\nHost: {args.host}\r\n\r\n".encode())
    f = sock.makefile("rb")
    while read_line(f):  # response headers
        pass

    frames = []
    keyframes = 0
    sei_ok = sei_bad = 0
    raw = open(os.path.join(out_dir, f"{stamp}.h264"), "wb") if args.save_stream else None
    t_end = time.time() + args.seconds
    print(f"measuring {base}/stream for {args.seconds:.0f}s ...")
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
            jpeg = f.read(n)
            arrival = time.time()
            kind = headers.get("x-kind", "jpeg")
            if raw and kind != "jpeg":
                raw.write(jpeg)
            if kind == "config":
                continue
            keyframes += kind == "key"
            seq = int(headers.get("x-frame-seq", -1))
            if kind != "jpeg":
                ts = next(sei.find_timestamps(jpeg), None)
                if ts and ts[0] == seq and ts[1] == int(headers.get("x-timestamp-ns", 0)):
                    sei_ok += 1
                else:
                    sei_bad += 1
            frames.append({
                "seq": seq,
                "sensor_ns": int(headers.get("x-timestamp-ns", 0)),
                "tablet_wall_ms": int(headers.get("x-wall-ms", 0)),
                "pc_arrival_s": arrival,
                "bytes": n,
            })
            if kind == "jpeg" and args.save_every and len(frames) % args.save_every == 0:
                with open(os.path.join(out_dir, f"{stamp}-{seq:06d}.jpg"), "wb") as img:
                    img.write(jpeg)
    except (EOFError, ConnectionError, socket.timeout) as e:
        print(f"stream ended early: {e!r}")
    finally:
        stop.set()
        sock.close()
        if raw:
            raw.close()

    sync_after = sync("after")

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

    frames_path = os.path.join(out_dir, f"{stamp}-frames.csv")
    with open(frames_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["seq", "sensor_ns", "tablet_wall_ms", "pc_arrival_s", "capture_pc_s", "latency_ms", "bytes"])
        w.writeheader()
        w.writerows(frames)

    stats_path = os.path.join(out_dir, f"{stamp}-stats.csv")
    keys = sorted({k for r in stats_rows for k in r})
    with open(stats_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(stats_rows)

    if len(frames) < 2:
        print("not enough frames received")
        return

    dur = frames[-1]["pc_arrival_s"] - frames[0]["pc_arrival_s"]
    arrival_dt = [(b["pc_arrival_s"] - a["pc_arrival_s"]) * 1000 for a, b in zip(frames, frames[1:])]
    sensor_dt = [(b["sensor_ns"] - a["sensor_ns"]) / 1e6 for a, b in zip(frames, frames[1:])]
    gaps = sum(max(0, b["seq"] - a["seq"] - 1) for a, b in zip(frames, frames[1:]))
    last = next((r for r in reversed(stats_rows) if "camera_fps" in r), {})

    def pct(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]

    print()
    print(f"config            {last.get('config', '?')}")
    print(f"device            {last.get('device', '?')} (SDK {last.get('android_sdk', '?')})")
    print(f"frames received   {len(frames)} in {dur:.1f}s  -> {(len(frames) - 1) / dur:.2f} fps at PC")
    print(f"keyframes         {keyframes}") if keyframes else None
    print(f"frames skipped    {gaps} (encoded on tablet but never reached the PC)")
    print(f"tablet dropped    {last.get('dropped_frames', '?')} (camera frames the encoder couldn't keep up with)")
    print(f"camera fps        {last.get('camera_fps', '?')}   encoded fps {last.get('encoded_fps', '?')}")
    print(f"arrival interval  median {statistics.median(arrival_dt):.1f} ms, p95 {pct(arrival_dt, 95):.1f}, max {max(arrival_dt):.1f}")
    print(f"sensor interval   median {statistics.median(sensor_dt):.1f} ms, p95 {pct(sensor_dt, 95):.1f}, max {max(sensor_dt):.1f}")
    lat = [fr["latency_ms"] for fr in frames if fr["latency_ms"] != ""]
    if lat:
        print(f"capture->PC       min {min(lat):.1f} ms, median {statistics.median(lat):.1f}, p95 {pct(lat, 95):.1f}, max {max(lat):.1f}"
              "  (negative = clock sync is wrong)")
    if sync_before and sync_after:
        dt = (sync_after["pc_unix_ns"] - sync_before["pc_unix_ns"]) / 1e9
        drift = (sync_after["offset_ns"] - sync_before["offset_ns"]) / 1e6
        print(f"clock drift       {drift:+.2f} ms over {dt:.0f} s ({drift / dt * 1000:+.1f} ppm)")
    if sei_ok or sei_bad:
        print(f"timestamp SEI     {sei_ok} frames match the headers, {sei_bad} missing/mismatched")
    print(f"bitrate           {sum(fr['bytes'] for fr in frames) * 8 / dur / 1e6:.1f} Mbps, {statistics.mean(fr['bytes'] for fr in frames) / 1024:.0f} KB/frame")
    print(f"tablet slow sends {last.get('slow_writes', '?')} (writes blocked >200 ms), longest {last.get('max_write_ms', '?')} ms")
    print(f"encode time       {last.get('encode_ms', '?')} ms/frame (h264: capture->encoded latency)   app CPU {last.get('app_cpu_percent', '?')}% of {last.get('cores', '?')} cores")
    temps = [r["battery_temp_c"] for r in stats_rows if "battery_temp_c" in r]
    if temps:
        print(f"battery temp      {temps[0]:.1f} -> {temps[-1]:.1f} C (max {max(temps):.1f})   thermal status {last.get('thermal_status', '?')}")
    print(f"\nwrote {frames_path}\n      {stats_path}")
    if raw:
        print(f"      {raw.name}")


if __name__ == "__main__":
    main()

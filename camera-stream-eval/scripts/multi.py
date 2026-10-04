#!/usr/bin/env python3
"""Measure several tablets at the same time, then compare their capture times on the PC clock.

usage: multi.py [--hosts 192.168.7.4 192.168.7.5] [--seconds 90] [--save-stream]
       (no --hosts: every tablet discover.py finds)

Each host runs measure.py in parallel (same receiving PC, same network). Afterwards, using the
clock-synced capture times, it reports how far apart the cameras' frames are: for each frame of the
first camera, the nearest frame of every other camera. That's the residual after sync that only
interpolation (or hardware triggering) can remove; at 30 fps it is between 0 and 16.7 ms.
"""
import argparse
import bisect
import csv
import os
import statistics
import subprocess
import sys
import time

import discover

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    with open(path) as f:
        rows = [r for r in csv.DictReader(f) if r["capture_pc_s"]]
    return [float(r["capture_pc_s"]) for r in rows], rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", nargs="+")
    ap.add_argument("--seconds", type=float, default=90)
    ap.add_argument("--save-stream", action="store_true")
    args = ap.parse_args()

    if not args.hosts:
        args.hosts = [ip for ip, _ in discover.discover()]
        print("found: " + " ".join(args.hosts))
        if not args.hosts:
            return

    run = time.strftime("%Y%m%d-%H%M%S")
    names = [f"{run}-{h.split('.')[-1]}" for h in args.hosts]
    procs = []
    for host, name in zip(args.hosts, names):
        cmd = [sys.executable, os.path.join(HERE, "measure.py"), "--host", host,
               "--seconds", str(args.seconds), "--name", name]
        if args.save_stream:
            cmd.append("--save-stream")
        procs.append(subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
    print(f"measuring {len(procs)} tablets for {args.seconds:.0f}s ...", flush=True)
    for host, p in zip(args.hosts, procs):
        out, _ = p.communicate()
        print(f"\n===== {host} =====")
        print("\n".join(l for l in out.splitlines() if l.strip()))

    series = {}
    for host, name in zip(args.hosts, names):
        path = os.path.join("measurements", f"{name}-frames.csv")
        if os.path.exists(path):
            series[host], _ = load(path)
    if len(series) < 2:
        return

    ref_host = args.hosts[0]
    ref = series[ref_host]
    print("\n===== cross-camera (clock-synced capture times) =====")
    total_mbps = 0.0
    for host in args.hosts:
        with open(os.path.join("measurements", f"{names[args.hosts.index(host)]}-frames.csv")) as f:
            rows = list(csv.DictReader(f))
        dur = float(rows[-1]["pc_arrival_s"]) - float(rows[0]["pc_arrival_s"])
        mbps = sum(int(r["bytes"]) for r in rows) * 8 / dur / 1e6
        total_mbps += mbps
        times = series[host]
        # Rate from the sensor clock spacing, so frames lost on the network don't bias it.
        dts = [b - a for a, b in zip(times, times[1:])]
        med = statistics.median(dts)
        intervals = sum(max(1, round(d / med)) for d in dts)
        fps = intervals / (times[-1] - times[0])
        print(f"{host:15s} {len(times)} frames, real capture rate {fps:.3f} fps, {mbps:.1f} Mbps")
    print(f"{'total':15s} {total_mbps:.1f} Mbps into the PC")

    for host in args.hosts[1:]:
        other = series[host]
        deltas = []  # (time, signed ms: other - ref)
        lo, hi = max(ref[0], other[0]), min(ref[-1], other[-1])  # only where both were recording
        for t in (t for t in ref if lo <= t <= hi):
            i = bisect.bisect_left(other, t)
            cands = [other[j] for j in (i - 1, i) if 0 <= j < len(other)]
            nearest = min(cands, key=lambda c: abs(c - t))
            deltas.append((t, (nearest - t) * 1000))
        absd = [abs(d) for _, d in deltas]
        n = len(deltas)
        tenth = max(1, n // 10)
        first = statistics.median(d for _, d in deltas[:tenth])
        last = statistics.median(d for _, d in deltas[-tenth:])
        print(f"\n{host} vs {ref_host}: nearest-frame offset |dt| median {statistics.median(absd):.1f} ms, "
              f"max {max(absd):.1f} ms")
        print(f"  phase at start {first:+.1f} ms, at end {last:+.1f} ms (frames slide relative to each other "
              f"when the two cameras' real rates differ)")


if __name__ == "__main__":
    main()

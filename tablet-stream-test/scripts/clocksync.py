#!/usr/bin/env python3
"""NTP-style offset between this PC's clock and the tablet's camera sensor clock (UDP port 8081).

offset_ns = pc_unix_ns - tablet_sensor_ns, so   capture time on PC clock = sensor_ns + offset_ns.
Taken from the probes with the smallest round trip; uncertainty is +/- rtt/2 of the best probe.

usage: clocksync.py --host 192.168.7.4 [--probes 200] [--rounds 1] [--interval 10]
       (rounds > 1 prints the offset over time, i.e. clock drift)
"""
import argparse
import socket
import statistics
import struct
import time


def measure_offset(host, port=8081, probes=200, spacing_s=0.01):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.25)
    samples = []
    try:
        for i in range(probes):
            token = struct.pack(">Q", i)
            t0_unix = time.time_ns()
            p0 = time.perf_counter_ns()
            sock.sendto(token, (host, port))
            try:
                while True:
                    data, _ = sock.recvfrom(64)
                    if data[:8] == token:
                        break
            except socket.timeout:
                continue
            p1 = time.perf_counter_ns()
            _, sensor_ns, tablet_unix_ns = struct.unpack(">QQQ", data[:24])
            rtt = p1 - p0
            mid_unix = t0_unix + rtt // 2
            samples.append((rtt, mid_unix - sensor_ns, mid_unix - tablet_unix_ns))
            time.sleep(spacing_s)
    finally:
        sock.close()
    if not samples:
        raise RuntimeError(f"no replies from {host}:{port}")
    samples.sort()
    best = samples[: max(3, len(samples) // 10)]  # fastest 10%
    return {
        "pc_unix_ns": time.time_ns(),
        "offset_ns": int(statistics.median(s[1] for s in best)),
        "best_rtt_ms": samples[0][0] / 1e6,
        "median_rtt_ms": statistics.median(s[0] for s in samples) / 1e6,
        "offset_spread_ms": (max(s[1] for s in best) - min(s[1] for s in best)) / 1e6,
        "tablet_wall_error_ms": statistics.median(s[2] for s in best) / 1e6,  # PC minus tablet wall clock
        "replies": len(samples),
        "probes": probes,
    }


def describe(r):
    return (f"offset {r['offset_ns'] / 1e9:.6f} s  rtt best {r['best_rtt_ms']:.2f} ms median {r['median_rtt_ms']:.2f} ms"
            f"  spread {r['offset_spread_ms']:.2f} ms  tablet wall clock off by {r['tablet_wall_error_ms']:+.1f} ms"
            f"  ({r['replies']}/{r['probes']} replies)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=8081)
    ap.add_argument("--probes", type=int, default=200)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--interval", type=float, default=10)
    args = ap.parse_args()

    first = None
    for i in range(args.rounds):
        r = measure_offset(args.host, args.port, args.probes)
        line = describe(r)
        if first is None:
            first = r
        else:
            dt = (r["pc_unix_ns"] - first["pc_unix_ns"]) / 1e9
            drift_ms = (r["offset_ns"] - first["offset_ns"]) / 1e6
            line += f"  drift {drift_ms:+.2f} ms over {dt:.0f} s ({drift_ms / dt * 1000:+.1f} ppm)"
        print(line, flush=True)
        if i < args.rounds - 1:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()

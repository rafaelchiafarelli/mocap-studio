#!/usr/bin/env python3
"""Read the per-frame timestamp SEI (UUID MOCAPSTUDIO-TS01) out of H.264 data.

As a script: dump every timestamp in a saved .h264 file to CSV, in frame (decode) order, so row N
is the timestamp of the Nth frame ffmpeg decodes from that file.

usage: sei.py file.h264 [out.csv]
"""
import csv
import struct
import sys

UUID = b"MOCAPSTUDIO-TS01"


def _unescape(b):
    out = bytearray()
    zeros = 0
    for v in b:
        if zeros >= 2 and v == 3:
            zeros = 0
            continue
        out.append(v)
        zeros = zeros + 1 if v == 0 else 0
    return bytes(out)


def find_timestamps(data):
    """Yield (seq, sensor_ns, tablet_unix_ns) for every timestamp SEI in an Annex-B byte string."""
    i = data.find(b"\x00\x00\x01")
    while i >= 0:
        start = i + 3
        nxt = data.find(b"\x00\x00\x01", start)
        if start < len(data) and data[start] & 0x1F == 6:
            rbsp = _unescape(data[start + 1:nxt if nxt >= 0 else len(data)])
            if len(rbsp) >= 42 and rbsp[0] == 5 and rbsp[1] == 40 and rbsp[2:18] == UUID:
                yield struct.unpack(">QQQ", rbsp[18:42])
        i = nxt


def main():
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else path.rsplit(".", 1)[0] + "-sei.csv"
    with open(path, "rb") as f:
        data = f.read()
    rows = list(find_timestamps(data))
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "seq", "sensor_ns", "tablet_unix_ns"])
        for n, r in enumerate(rows):
            w.writerow([n, *r])
    if rows:
        gaps = sum(1 for a, b in zip(rows, rows[1:]) if b[0] != a[0] + 1)
        span = (rows[-1][1] - rows[0][1]) / 1e9
        print(f"{len(rows)} timestamped frames, seq {rows[0][0]}..{rows[-1][0]}, {gaps} seq gaps, {span:.1f} s -> {out}")
    else:
        print("no timestamp SEI found")


if __name__ == "__main__":
    main()

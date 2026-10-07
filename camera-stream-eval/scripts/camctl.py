#!/usr/bin/env python3
"""The recorder side of mocap-camera-app's control channel, for run-eval.sh --app camera.

ZeroMQ with the generated endpoints of mocap-contracts (camera.harpia, mocap_contracts.transport): a
ControlRequest to the app's control port, its ControlReply on our reply port, CameraStats from its stats
port. Runs in the control image (./dev camctl ...). The ports are local: run-eval.sh forwards the app's
control and stats ports with `adb forward` and our reply port back to the tablet with `adb reverse`, so
the tablet's 127.0.0.1:<reply> reaches us (WSL's NAT keeps the tablet from connecting in otherwise).

  camctl.py info --out device.json                 DeviceInfo, as the eval's device.json (+ "device_info")
  camctl.py stream WxH kbps fps camera-id          apply stream settings; exit 1 unless applied as asked
  camctl.py controls --out controls.json key=value ...   apply camera controls; every result is saved
  camctl.py stats --seconds N --out stats.csv      CameraStats as measure.py's stats rows
  camctl.py streaming [--seconds N]                exit 0 once the app reports encoded frames
  camctl.py v1check file.h264 --json out.json      the stream checked with the mocap-contracts reader

Common: --serial (required except v1check), --control-port 8082, --stats-port 8083, --reply-port 5700.
Every message received is checked with the contract rules (to_json/from_json).
"""

import argparse
import csv
import json
import sys
import time
import uuid

import mocap_contracts as mc
from mocap_contracts import stream_v1

TIMEOUT_MS = 30000


def connect(args):
    import zmq
    from mocap_contracts import transport

    ctx = zmq.Context()
    replies = transport.new_receiver(mc.ControlReply, ctx, f"tcp://127.0.0.1:{args.reply_port}")
    replies.socket.rcvtimeo = TIMEOUT_MS
    requests = transport.new_sender(mc.ControlRequest, ctx, f"tcp://127.0.0.1:{args.control_port}")
    return ctx, requests, replies


def ask(args, **fields):
    """One request, its reply (checked with the contract rules)."""
    ctx, requests, replies = connect(args)
    try:
        rid = uuid.uuid4().hex[:12]
        request = mc.ControlRequest(request_id=rid, serial=args.serial,
                                    reply_endpoint=f"tcp://127.0.0.1:{args.reply_port}",
                                    want_device_info=mc.Flag.Value(fields.pop("want_device_info", "FLAG_OFF")),
                                    **fields)
        requests.send(mc.from_json(mc.ControlRequest, mc.to_json(request)))
        while True:
            reply = replies.recv()
            if reply is None:
                sys.exit(f"camctl: no reply from the app within {TIMEOUT_MS / 1000:.0f} s "
                         f"(is it running, and are the ports forwarded?)")
            if reply.request_id == rid:
                return mc.from_json(mc.ControlReply, mc.to_json(reply))
    finally:
        ctx.destroy(linger=0)


def device_info(args):
    reply = ask(args, want_device_info="FLAG_ON")
    if not reply.HasField("device_info"):
        sys.exit(f"camctl: no device_info in the reply (problems: {list(reply.problems)})")
    return reply.device_info


def cmd_info(args):
    d = device_info(args)
    out = {
        "manufacturer": d.model.split(" ", 1)[0], "model": d.model, "android": d.android_version,
        "serial": d.serial, "app_version": d.app_version,
        "cameras": [{
            "id": c.camera_id,
            "facing": mc.CameraFacing.Name(c.facing).removeprefix("CAMERA_FACING_").lower(),
            "hardware_level": c.hardware_level,
            "timestamp_source": "?",
            "sensor_orientation_deg": c.sensor_orientation_deg,
            "focal_lengths_mm": list(c.focal_lengths_mm),
            "fps_ranges": [f"{r.min_fps}-{r.max_fps}" for r in c.fps_ranges],
            "encoder_sizes": [f"{s.width}x{s.height}" for s in c.sizes],
            "controls": len(c.controls),
        } for c in d.cameras],
        # same rule as the eval app's /info below API 29: Google's software codecs are the non-hardware ones
        "h264_encoders": [{"name": n, "hardware": str(not n.startswith(("OMX.google", "c2.android"))).lower(),
                           "max_size": "?", "bitrate_kbps": "?"} for n in d.h264_encoders],
        "device_info": json.loads(mc.to_json(d)),
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"{d.model}, Android {d.android_version}, cameras "
          + ", ".join(f"{c.camera_id} ({len(c.controls)} controls)" for c in d.cameras))


def cmd_stream(args):
    w, _, h = args.size.partition("x")
    want = mc.StreamSettings(camera_id=args.camera_id, width=int(w), height=int(h), fps=float(args.fps),
                             bitrate_kbps=int(args.kbps), i_frame_interval_s=1.0)
    reply = ask(args, stream=want)
    got = reply.stream_applied if reply.HasField("stream_applied") else None
    applied = f"{got.width}x{got.height} @{got.fps:g} {got.bitrate_kbps} kbps camera {got.camera_id}" if got else "nothing"
    print(f"stream applied: {applied}" + (f"; problems: {list(reply.problems)}" if reply.problems else ""))
    ok = got is not None and not reply.problems and (got.width, got.height, got.bitrate_kbps) == (want.width, want.height, want.bitrate_kbps)
    sys.exit(0 if ok else 1)


def parse_value(cap, text):
    """key=value text as a ControlValue of the capability's type (menus by name or number, lists by commas)."""
    t = mc.ControlValueType.Name(cap.value_type).removeprefix("CONTROL_VALUE_TYPE_")
    if t == "MENU":
        by_name = {o.name.lower(): o.value for o in cap.options}
        return mc.ControlValue(int_value=by_name[text.lower()] if text.lower() in by_name else int(text))
    if t == "INT":
        return mc.ControlValue(int_value=int(text))
    if t == "FLOAT":
        return mc.ControlValue(float_value=float(text))
    if t == "FLAG":
        return mc.ControlValue(flag_value=mc.Flag.Value("FLAG_ON" if text.lower() in ("1", "on", "true") else "FLAG_OFF"))
    if t == "INT_LIST":
        return mc.ControlValue(int_values=[int(x) for x in text.split(",")])
    if t == "FLOAT_LIST":
        return mc.ControlValue(float_values=[float(x) for x in text.split(",")])
    return mc.ControlValue(text_value=text)


def show(v):
    if v.HasField("int_value"):
        return str(v.int_value)
    if v.HasField("float_value"):
        return f"{v.float_value:g}"
    if v.HasField("flag_value"):
        return mc.Flag.Name(v.flag_value).removeprefix("FLAG_")
    if v.HasField("text_value"):
        return v.text_value
    if v.int_values:
        return ",".join(map(str, v.int_values))
    if v.float_values:
        return ",".join(f"{x:g}" for x in v.float_values)
    return "?"


def cmd_controls(args):
    info = device_info(args)
    cam = next((c for c in info.cameras if c.controls and any(k.HasField("current_value") for k in c.controls)),
               info.cameras[0])
    caps = {c.key: c for c in cam.controls}
    settings = []
    for kv in args.settings:
        key, _, text = kv.partition("=")
        if key not in caps:  # sent anyway: the app reports it (UNSUPPORTED / READ_ONLY), nothing is dropped here
            settings.append(mc.ControlSetting(key=key, value=mc.ControlValue(text_value=text)))
        else:
            settings.append(mc.ControlSetting(key=key, value=parse_value(caps[key], text)))
    reply = ask(args, settings=settings)
    rows = []
    for r in reply.results:
        status = mc.ControlStatus.Name(r.status).removeprefix("CONTROL_STATUS_")
        applied = show(r.applied) if r.HasField("applied") else "-"
        print(f"{r.key:42s} {status:12s} requested {show(r.requested):12s} applied {applied:12s} {r.note}")
        rows.append({"key": r.key, "status": status, "requested": show(r.requested), "applied": applied,
                     "note": r.note})
    with open(args.out, "w") as f:
        json.dump({"camera_id": cam.camera_id, "results": rows, "problems": list(reply.problems)}, f, indent=1)


def stats_socket(args):
    import zmq
    from mocap_contracts import transport

    ctx = zmq.Context()
    sub = transport.new_subscriber(mc.CameraStats, ctx, f"tcp://127.0.0.1:{args.stats_port}")
    sub.socket.rcvtimeo = 3000
    return ctx, sub


FIELDS = ["pc_time", "camera_fps", "encoded_fps", "dropped_frames", "app_cpu_percent", "battery_temp_c",
          "thermal_status", "sensor_ns"]


def cmd_stats(args):
    """CameraStats as measure.py's stats rows (the eval app's /stats names), one per second, flushed."""
    ctx, sub = stats_socket(args)
    end = time.time() + args.seconds
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        f.flush()
        while time.time() < end:
            s = sub.recv()
            if s is None or s.serial != args.serial:
                continue
            s = mc.from_json(mc.CameraStats, mc.to_json(s))
            w.writerow({"pc_time": time.time(), "camera_fps": s.camera_fps, "encoded_fps": s.encoder_fps,
                        "dropped_frames": s.dropped_frames, "app_cpu_percent": s.cpu_percent,
                        "battery_temp_c": s.battery_temp_c, "thermal_status": s.thermal_status,
                        "sensor_ns": s.sensor_ns})
            f.flush()
    ctx.destroy(linger=0)


def cmd_streaming(args):
    ctx, sub = stats_socket(args)
    end = time.time() + args.seconds
    try:
        while time.time() < end:
            s = sub.recv()
            if s is not None and s.serial == args.serial and s.encoder_fps > 0:
                print(f"streaming: camera {s.camera_fps:.1f} fps, encoder {s.encoder_fps:.1f} fps")
                return
        sys.exit("camctl: no encoded frames reported")
    finally:
        ctx.destroy(linger=0)


def cmd_v1check(args):
    """The saved stream read with the protocol v1 reference reader: every frame timed, SEIs well formed."""
    with open(args.file, "rb") as f:
        data = f.read()
    out = {"file": args.file, "bytes": len(data)}
    try:
        frames = stream_v1.frames(data)
    except stream_v1.StreamError as e:
        out.update(ok=False, error=str(e))
    else:
        timed = [fr.timestamp for fr in frames if fr.timestamp is not None]
        gaps = stream_v1.seq_gaps(timed)
        untimed = sum(1 for fr in frames if fr.timestamp is None)
        problems = sorted({p for fr in frames for p in fr.problems})
        out.update(ok=bool(frames) and untimed == 0 and not problems, frames=len(frames), timed=len(timed),
                   untimed=untimed, problems=problems,
                   seq_first=timed[0].seq if timed else None, seq_last=timed[-1].seq if timed else None,
                   seq_gaps=len(gaps))
    with open(args.json, "w") as f:
        json.dump(out, f, indent=1)
    print("protocol v1: " + ("OK" if out["ok"] else "NOT OK") + " " + json.dumps({k: v for k, v in out.items() if k != "file"}))
    sys.exit(0 if out["ok"] else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serial", default="")
    ap.add_argument("--control-port", type=int, default=8082)
    ap.add_argument("--stats-port", type=int, default=8083)
    ap.add_argument("--reply-port", type=int, default=5700)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info"); p.add_argument("--out", required=True)
    p = sub.add_parser("stream"); p.add_argument("size"); p.add_argument("kbps"); p.add_argument("fps"); p.add_argument("camera_id")
    p = sub.add_parser("controls"); p.add_argument("--out", required=True); p.add_argument("settings", nargs="+")
    p = sub.add_parser("stats"); p.add_argument("--seconds", type=float, required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("streaming"); p.add_argument("--seconds", type=float, default=30)
    p = sub.add_parser("v1check"); p.add_argument("file"); p.add_argument("--json", required=True)
    args = ap.parse_args()
    if args.cmd != "v1check" and not args.serial:
        ap.error("--serial is required")
    {"info": cmd_info, "stream": cmd_stream, "controls": cmd_controls, "stats": cmd_stats,
     "streaming": cmd_streaming, "v1check": cmd_v1check}[args.cmd](args)


if __name__ == "__main__":
    main()

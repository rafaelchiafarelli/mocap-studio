"""Rebuilds the mouth-fader experiment from its inputs and checks it against the frozen baseline.
    python run_experiment.py CONFIG.json                 every stage, then the comparison
    python run_experiment.py CONFIG.json --from build    start at one stage
    python run_experiment.py CONFIG.json --bless FILE.blend    write the expected results from an approved .blend
Exit code 1 means the result moved away from the baseline. Run it from WSL: Blender and the tracker are Windows programs."""
import argparse, json, os, shutil, subprocess, sys, zipfile
import cv2
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
CORR_TOL, CURVE_TOL = 0.02, 0.02  # the curves and measures are the guard
PIXEL_TOL = 1.0  # a coarse check: the lip tuck going from 0.88 to 0.26 moved a whole frame by only 0.09


def win(p):
    return subprocess.check_output(["wslpath", "-w", p], text=True).strip()


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd)[:220], flush=True)
    return subprocess.run(cmd, check=True, **kw)


def blender(c, blend, script, *args):
    out = subprocess.run([c["blender"], "-b", win(blend), "--python", win(os.path.join(HERE, script)), "--", *args], text=True, capture_output=True, encoding="utf-8", errors="replace")
    lines = [l for l in out.stdout.splitlines() if l.startswith("RESULT") or "Traceback" in l or l.startswith("Error: Python")]
    print("\n".join(l[:300] for l in lines), flush=True)
    if out.returncode or any("Traceback" in l for l in lines):
        print(out.stdout[-3000:]); sys.exit(f"Blender failed on {script}")


class Stages:
    def __init__(self, c):
        self.c = c; self.o = c["out_dir"]; os.makedirs(self.o, exist_ok=True)
        self.take = json.load(open(os.path.join(HERE, c["take"])))
    def path(self, n):
        return os.path.join(self.o, n)
    def track(self):
        run(["./facetracker.exe", "-c", win(self.c["recording"]), "-W", "1920", "-H", "1080", "-F", "30", "--model", "3", "--gaze-tracking", "1", "-s", "1", "--log-data", win(self.path("tracking.csv"))], cwd=self.c["facetracker_dir"], stdout=subprocess.DEVNULL)
        with open(self.path("pts.txt"), "w") as f:
            t = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "packet=pts_time", "-of", "csv=p=0", self.c["recording"]], text=True)
            f.write("\n".join(sorted((x.strip(",") for x in t.split()), key=float)) + "\n")
    def audio(self):
        run(["ffmpeg", "-v", "error", "-y", "-i", self.c["recording"], "-ac", "1", "-ar", "16000", "-f", "s16le", self.path("audio.raw")])
        run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", "16000", "-ac", "1", "-i", self.path("audio.raw"), "-af", "volume=4", self.path("voice.wav")])
    def phones(self):
        run([sys.executable, os.path.join(HERE, "recognize_phones.py"), self.path("voice.wav"), self.path("phones.txt"), self.c["allosaurus_model"]])
    def overlay(self):
        run([sys.executable, os.path.join(HERE, "overlay_video.py"), self.c["recording"], self.path("tracking.csv"), self.path("pts.txt"), self.path("overlay_silent.mp4")])
        run(["ffmpeg", "-v", "error", "-y", "-i", self.path("overlay_silent.mp4"), "-i", self.c["recording"], "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", self.path("overlay.mp4")])
    def channels(self):
        a, b = self.take["rest_window_s"]
        run([sys.executable, os.path.join(HERE, "osf_to_arkit.py"), self.path("tracking.csv"), self.path("pts.txt"), self.path("channels.json"), str(a), str(b), str(self.c["lip_gap_at_jaw1_m"]), str(self.c["eye_distance_m"])], stdout=subprocess.DEVNULL)
        d = json.load(open(self.path("channels.json"))); d["markers"] = self.take["markers"]
        json.dump(d, open(self.path("channels.json"), "w"))
        d["channels"] = {k: v for k, v in d["channels"].items() if k.startswith(("brow", "eye"))}
        json.dump(d, open(self.path("channels_upper.json"), "w"))
    def table(self):
        import allosaurus
        run([sys.executable, "-I", os.path.join(HERE, "make_table.py"), os.path.join(os.path.dirname(allosaurus.__file__), "pretrained", "uni2005", "phone.txt"), self.path("phoneme_table_pt.json")])
    def data(self):
        json.dump(self.take, open(self.path("words.json"), "w"))
        run([sys.executable, os.path.join(HERE, "make_data.py"), self.path("phones.txt"), self.path("phoneme_table_pt.json"), self.path("channels.json"), self.path("pts.txt"), self.path("audio.raw"), os.path.join(HERE, "poses.json"), self.path("words.json"), self.path("mouth_data.json")])
    def install(self):
        z = self.path("mouth_faders.zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
            for n in ("__init__.py", "blender_manifest.toml"):
                f.write(os.path.join(HERE, "mouth_faders", n), n)
        run([self.c["blender"], "--command", "extension", "install-file", "-r", "user_default", "-e", win(z)], stdout=subprocess.DEVNULL)
    def key(self):
        blender(self.c, self.c["character_blend"], "key_face_head.py", win(self.path("channels_upper.json")), win(self.path("overlay.mp4")), win(self.path("voice.wav")), win(self.path("base_upper.blend")))
    def build(self):
        blender(self.c, self.path("base_upper.blend"), "build_faders.py", win(self.path("mouth_data.json")), win(self.path("faders.blend")))
    def preset(self):
        blender(self.c, self.path("faders.blend"), "cli_faders.py", "preset=" + win(os.path.join(HERE, "presets", "C_roteiro_video.json")), "out=" + win(self.path("faders.blend")))
        opener = f'@echo off\r\nstart "" "{win(self.c["blender"])}" "{win(self.path("faders.blend"))}"\r\n'
        open(self.path("abrir_faders.bat"), "w", newline="").write(opener)
    def verify(self):
        verify(self.c, self.path("faders.blend"), self.o)
    def compare(self):
        compare(self.o, self.c["expected_dir"])


ORDER = ["track", "audio", "phones", "overlay", "channels", "table", "data", "install", "key", "build", "preset", "verify", "compare"]


def verify(c, blend, folder):
    still = os.path.join(folder, "stills"); os.makedirs(still, exist_ok=True)
    blender(c, blend, "verify_faders.py", win(os.path.join(HERE, "presets")), win(still) + "\\", win(os.path.join(folder, "metrics.json")))


def compare(folder, expected):
    a = json.load(open(os.path.join(folder, "metrics.json"))); e = json.load(open(os.path.join(expected, "metrics.json")))
    bad = []
    for preset, want in e["presets"].items():
        for m, v in want.items():
            got = a["presets"][preset][m]
            if abs(got - v) > CORR_TOL:
                bad.append(f"{preset} {m}: {got:.3f}, expected {v:.3f}")
    for k, v in e["curves_C"].items():
        n = min(len(v), len(a["curves_C"][k])); dif = float(np.abs(np.array(v[:n]) - np.array(a["curves_C"][k][:n])).max())
        if dif > CURVE_TOL:
            bad.append(f"curve {k}: moved up to {dif:.3f}")
    if a["frames"] != e["frames"]:
        bad.append(f"frames {a['frames']}, expected {e['frames']}")
    if a["missing_images"] != e["missing_images"]:
        bad.append(f"missing images changed: {a['missing_images']}")
    for n in sorted(os.listdir(os.path.join(expected, "stills"))):
        x = cv2.imread(os.path.join(expected, "stills", n)).astype(float); y = cv2.imread(os.path.join(folder, "stills", n)).astype(float)
        dif = float(np.abs(x - y).mean()); print(f"still {n}: mean difference {dif:.2f} of 255")
        if dif > PIXEL_TOL:
            bad.append(f"still {n}: differs by {dif:.2f}")
    print("RESULT presets", {k: round(v["corr_jaw_video"], 3) for k, v in a["presets"].items()})
    if bad:
        print("FAIL: the result moved away from the baseline:\n  " + "\n  ".join(bad)); sys.exit(1)
    print("PASS: matches the baseline")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("config"); ap.add_argument("--from", dest="start", choices=ORDER, default="track"); ap.add_argument("--bless")
    a = ap.parse_args(); c = json.load(open(a.config))
    if a.bless:
        os.makedirs(c["expected_dir"], exist_ok=True); verify(c, a.bless, c["expected_dir"]); print("RESULT expected written to", c["expected_dir"]); return
    st = Stages(c)
    for name in ORDER[ORDER.index(a.start):]:
        print("=== " + name, flush=True); getattr(st, name)()


main()

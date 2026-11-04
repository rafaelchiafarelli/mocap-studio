"""Runs build_model.py in WSL from Windows Blender, in the background, and follows its log. No bpy, so Blender stays free while it runs."""
import json, os, re, subprocess, tempfile

STAGES = ["export", "bones", "muscles", "fields", "assemble"]
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def config():
    """install.json is written by install_editor.py: which WSL distribution and repository this add-on came from."""
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "install.json"), encoding="utf-8") as f:
        return json.load(f)


def wsl_path(path, cfg):
    return subprocess.check_output(["wsl.exe", "-d", cfg["distro"], "-e", "wslpath", "-u", path], text=True, creationflags=NO_WINDOW).strip()


class Build:
    """One running build. The output folder gets a subfolder named after the character, as docs/running.md does."""

    def __init__(self, recipe_path, out_root, name, cfg=None):
        cfg = cfg or config()
        self.name = name
        self.out_dir = os.path.join(out_root, name)
        self.blend = os.path.join(self.out_dir, name + ".blend")
        self.log_path = os.path.join(tempfile.gettempdir(), f"hm_build_{name}.log")
        self.error = None
        out_wsl = wsl_path(self.out_dir, cfg)
        if not out_wsl.startswith(("/mnt/g/", "/tmp/")):
            raise ValueError("The output folder must be on G:, the drive Docker can see")
        cmd = ["wsl.exe", "-d", cfg["distro"], "--cd", cfg["repo"], "-e", "python3", "human-model/build_model.py", wsl_path(recipe_path, cfg), out_wsl]
        self._log = open(self.log_path, "w", encoding="utf-8")
        self.process = subprocess.Popen(cmd, stdout=self._log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)

    def log(self):
        with open(self.log_path, encoding="utf-8", errors="replace") as f:
            return f.read()

    def stage(self):
        found = re.findall(r"^== (\w+)", self.log(), flags=re.M)
        return found[-1] if found else None

    def poll(self):
        """"running", "done" or "failed". A build counts as done only when the file exists."""
        code = self.process.poll()
        if code is None:
            return "running"
        self._log.close()
        if code == 0 and os.path.exists(self.blend):
            return "done"
        lines = [line for line in self.log().splitlines() if line.strip()]
        self.error = lines[-1] if lines else f"exit code {code}"
        return "failed"

    def describe(self):
        stage = self.stage()
        if stage is None:
            return "Starting"
        return f"Stage {STAGES.index(stage) + 1} of {len(STAGES)}: {stage}" if stage in STAGES else stage

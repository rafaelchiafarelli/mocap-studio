"""Runs a script inside the Windows Blender from WSL, turning path arguments into Windows paths.
    python3 blender_run.py [--blend FILE] SCRIPT [ARG ...]
Arguments that start with / become Windows paths. Auto-run scripts stay off."""
import os, subprocess, sys
BLENDER = os.environ.get("HM_BLENDER", "/mnt/g/mocap-studio-downloads/apps/blender/5.2.2/blender-5.2.2-windows-x64/blender.exe")


def win(p):
    return subprocess.check_output(["wslpath", "-w", os.path.abspath(p)], text=True).strip()


def main(argv):
    blend = None
    if argv[0] == "--blend":
        blend, argv = argv[1], argv[2:]
    script, args = argv[0], argv[1:]
    cmd = [BLENDER, "--background", "--disable-autoexec"]
    if blend:
        cmd.append(win(blend))
    cmd += ["--python-exit-code", "1", "--python", win(script), "--"]
    cmd += [win(a) if a.startswith("/") else a for a in args]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

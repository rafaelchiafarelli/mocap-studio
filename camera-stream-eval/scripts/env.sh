# shellcheck shell=bash
# Shared by ./dev and ./run-eval.sh (sourced, not executed).

IMAGE=camera-stream-eval
ADB_CONTAINER=camera-stream-eval-adb
ADB_KEYS_VOLUME=camera-stream-eval-adb-keys
PKG=dev.mocapstudio.tabletstream
APK=app/build/outputs/apk/debug/app-debug.apk
PORT=8080

is_wsl() { grep -qi microsoft /proc/version 2>/dev/null; }

# The measuring Python must run natively on the PC that receives the stream. Under WSL2 that means the
# Windows Python: WSL's NAT stalls TCP streams for ~3 s every ~35 s, which would show up as fake losses.
# Override with PYTHON=/path/to/python.
find_python() {
    if [ -n "${PYTHON:-}" ]; then echo "$PYTHON"; return; fi
    if is_wsl; then
        local p
        for p in $(command -v python.exe 2>/dev/null) /mnt/c/Python3*/python.exe \
                 /mnt/c/Users/*/AppData/Local/Programs/Python/Python3*/python.exe; do
            if [ -x "$p" ] && "$p" -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
                echo "$p"; return
            fi
        done
        echo "WARNING: no Windows Python 3.8+ found; measuring from WSL will show fake ~3 s stalls" >&2
    fi
    command -v python3
}

#!/usr/bin/env bash
# Evaluate one Android device as a streaming mocap camera, end to end, and write a report with a verdict.
#
#   ./run-eval.sh <device-ip>           device reachable over Wi-Fi adb (port 5555 or Wireless debugging)
#   ./run-eval.sh usb                   first device connected over USB (switched to Wi-Fi adb)
#
# See ./run-eval.sh --help and README.md.
set -euo pipefail
cd "$(dirname "$0")"
source scripts/env.sh

FPS=30
RESOLUTIONS=auto
BITRATES="10000 20000"
STEP_SECONDS=60
SOAK_MINUTES=10
SYNC_ROUNDS=7
WAIT_IDLE=300
PAIR_ADDR=; PAIR_CODE=
BUILD=1
OUT=

usage() {
    cat <<EOF
usage: ./run-eval.sh [options] <device-ip | usb>

Builds the app, connects, records the device's capabilities, runs a test matrix (resolution x bitrate),
a clock-sync check, a soak run, saves sample frames, and writes results/<device>-<time>/report.md.

options
  --pair <ip:port> <code>  pair first (Android 11+ Wireless debugging, "Pair device with pairing code")
  --fps <n>                target frame rate (default $FPS)
  --resolutions "<WxH ..>" sizes to test (default auto: largest <=1080p-class, plus largest <=4K)
  --bitrates "<kbps ..>"   H.264 bitrates to test (default "$BITRATES")
  --step-seconds <s>       duration of each matrix step (default $STEP_SECONDS)
  --soak <minutes>         soak duration at the largest size and bitrate (default $SOAK_MINUTES, 0 = skip)
  --quick                  smoke test: 20 s steps, 2 min soak, 3 sync rounds (~6 min)
  --wait-idle <s>          wait up to this long for background updates/compilation to finish (default $WAIT_IDLE)
  --no-build               reuse the existing APK
  --out <dir>              results folder (default results/<model>-<serial>-<time>)

environment: PYTHON=<path> to force the measuring Python (default: native Windows Python under WSL)
EOF
}

die() { echo "ERROR: $*" >&2; exit 1; }
say() { echo; echo "== $*"; }

while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --pair) PAIR_ADDR="$2"; PAIR_CODE="$3"; shift 3 ;;
        --fps) FPS="$2"; shift 2 ;;
        --resolutions) RESOLUTIONS="$2"; shift 2 ;;
        --bitrates) BITRATES="$2"; shift 2 ;;
        --step-seconds) STEP_SECONDS="$2"; shift 2 ;;
        --soak) SOAK_MINUTES="$2"; shift 2 ;;
        --quick) STEP_SECONDS=20; SOAK_MINUTES=2; SYNC_ROUNDS=3; shift ;;
        --wait-idle) WAIT_IDLE="$2"; shift 2 ;;
        --no-build) BUILD=; shift ;;
        --out) OUT="$2"; shift 2 ;;
        -*) die "unknown option $1 (see --help)" ;;
        *) TARGET="$1"; shift ;;
    esac
done
[ -n "${TARGET:-}" ] || { usage; exit 1; }

# ---------------------------------------------------------------------------------------------
say "1/9 prerequisites"
command -v docker >/dev/null || die "docker is required"
command -v curl >/dev/null || die "curl is required"
PY=$(find_python) || true
[ -n "$PY" ] || die "no Python 3.8+ found (set PYTHON=...)"
echo "measuring with: $PY ($("$PY" --version 2>&1 | tr -d '\r'))"
is_wsl && [[ "$PY" != *.exe ]] && echo "WARNING: measuring from inside WSL2 - expect fake ~3 s stalls; install Windows Python"
adb() { ./dev adb "$@"; }
dev_adb() { T="$ADB_T" ./dev adb "$@"; }

if [ -n "$BUILD" ]; then
    say "2/9 build (Docker image + APK)"
    ./dev build
else
    [ -f "$APK" ] || die "no APK at $APK; drop --no-build"
fi

# ---------------------------------------------------------------------------------------------
say "3/9 connect"
./dev up
if [ -n "$PAIR_ADDR" ]; then
    adb pair "$PAIR_ADDR" "$PAIR_CODE"
fi
if [ "$TARGET" = usb ]; then
    serial=$(adb devices | awk 'NR>1 && $2=="device" && $1!~/:/ {print $1; exit}')
    [ -n "$serial" ] || die "no authorized USB device (WSL: 'usbipd attach --wsl --busid <id>' first; accept the prompt on the device)"
    IP=$(T="$serial" ./dev adb shell ip -4 addr show wlan0 | awk '/inet /{sub(/\/.*/,"",$2); print $2}')
    [ -n "$IP" ] || die "device $serial has no Wi-Fi address - connect it to the capture network"
    T="$serial" ./dev tcpip
    sleep 4
    adb connect "$IP:5555"
else
    IP="$TARGET"
    if ! adb connect "$IP:5555" | grep -qE "^(connected|already)"; then
        echo "no adb on $IP:5555, looking for the Wireless debugging port ..."
        ./dev wadb "$IP" || die "can't reach adb on $IP. On the device: Developer options > Wireless debugging (on); first time: --pair <ip:port> <code>"
    fi
fi
ADB_T="$IP:5555"
for _ in $(seq 20); do [ "$(dev_adb get-state 2>/dev/null | tr -d '\r')" = device ] && break; sleep 1; done
[ "$(dev_adb get-state 2>/dev/null | tr -d '\r')" = device ] || die "adb connection to $ADB_T is not ready"

model=$(dev_adb shell getprop ro.product.model | tr -d '\r' | tr ' /' '__')
serial=$(dev_adb shell getprop ro.serialno | tr -d '\r')
STAMP=$(date +%Y%m%d-%H%M%S)
OUT=${OUT:-results/${model}-${serial: -6}-$STAMP}
mkdir -p "$OUT/steps" "$OUT/samples"
echo "device $model ($serial) at $IP -> $OUT"

# ---------------------------------------------------------------------------------------------
say "4/9 device details (adb)"
{
    echo "# getprop"
    for p in ro.product.manufacturer ro.product.model ro.build.version.release ro.build.version.sdk \
             ro.build.fingerprint ro.soc.manufacturer ro.soc.model ro.board.platform ro.hardware; do
        echo "$p=$(dev_adb shell getprop $p | tr -d '\r')"
    done
    echo; echo "# memory"; dev_adb shell grep -E 'MemTotal|MemAvailable' /proc/meminfo
    echo; echo "# wifi (link to the access point)"
    { dev_adb shell dumpsys wifi 2>/dev/null || true; } | grep -m1 'mWifiInfo' \
        | grep -oE '(Wi-Fi standard|RSSI|Link speed|Tx Link speed|Rx Link speed|Frequency): [^,]+' | awk '!seen[$0]++' || true
    echo; echo "# battery"; dev_adb shell dumpsys battery | grep -E 'level|temperature|powered|status' | head -8
    echo; echo "# automatic system updates (1 = disabled)"
    echo "ota_disable_automatic_update=$(dev_adb shell settings get global ota_disable_automatic_update | tr -d '\r')"
    echo; echo "# top (start of run)"; dev_adb shell top -b -n1 | head -14
} > "$OUT/device-adb.txt" 2>&1 || true
sed -n '/# wifi/,/# battery/p' "$OUT/device-adb.txt" | sed '/^#\|^$/d'

# ---------------------------------------------------------------------------------------------
say "5/9 install and start the app"
dev_adb install -r -g "$APK" | tail -1
dev_adb shell am start -S -n "$PKG/.MainActivity" --ei fps "$FPS" --es mode h264 --es facing back >/dev/null
ok=
for _ in $(seq 30); do
    fps_now=$(curl -s --max-time 2 "http://$IP:$PORT/stats" | grep -oE '"encoded_fps":[0-9.]+' | cut -d: -f2 || true)
    [ -n "$fps_now" ] && awk "BEGIN{exit !($fps_now > 0)}" && { ok=1; break; }
    sleep 1
done
[ -n "$ok" ] || die "the app is not streaming (check: ./dev logs; is the screen on?)"
curl -s --max-time 5 "http://$IP:$PORT/info" > "$OUT/device.json"
[ -s "$OUT/device.json" ] || die "no /info from the app"
[ "$RESOLUTIONS" = auto ] && RESOLUTIONS=$("$PY" scripts/pick_sizes.py "$OUT/device.json" "$FPS" | tr -d '\r')  # Windows Python: \r\n
echo "resolutions: $RESOLUTIONS   bitrates: $BITRATES kbps   fps: $FPS"

cat > "$OUT/run.json" <<EOF
{"started": "$STAMP", "device_ip": "$IP", "serial": "$serial", "fps": $FPS,
 "resolutions": "$RESOLUTIONS", "bitrates": "$BITRATES", "step_seconds": $STEP_SECONDS,
 "soak_minutes": $SOAK_MINUTES, "receiver": "$("$PY" -c 'import platform; print(platform.system(), platform.release(), "python", platform.python_version())' | tr -d '\r')"}
EOF

# ---------------------------------------------------------------------------------------------
say "6/9 wait for background load (system updates, app compilation) to settle"
busy_now() {
    { dev_adb shell top -b -n1 2>/dev/null | head -16 \
        | grep -oE 'update_engine|dex2oat[0-9]*|otapreopt|installd|bg_dexopt' || true; } | sort -u | tr '\n' ' '
}
waited=0; busy=$(busy_now)
while [ -n "$busy" ] && [ "$waited" -lt "$WAIT_IDLE" ]; do
    echo "busy: $busy - waiting ($waited/$WAIT_IDLE s)"
    sleep 15; waited=$((waited + 15)); busy=$(busy_now)
done
[ -n "$busy" ] && echo "WARNING: still busy ($busy) - results may be worse than the device can do"
busy_json=$(for b in $busy; do printf '"%s",' "$b"; done | sed 's/,$//')
echo "{\"busy_processes\": [${busy_json}], \"waited_s\": $waited}" > "$OUT/load.json"

measure() {  # name seconds [extra args]
    local name="$1" secs="$2"; shift 2
    "$PY" scripts/measure.py --host "$IP" --seconds "$secs" --out-dir "$OUT/steps" --name "$name" "$@" \
        | grep -E "^(config|frames received|capture rate|capture->PC|bitrate|device side|temperature|stream ended)"
}
configure() {  # WxH kbps - apply, then verify the device restarted with the new bitrate and is streaming
    local w="${1%x*}" h="${1#*x}" try stats
    for try in 1 2 3; do
        if curl -s --max-time 5 "http://$IP:$PORT/control?width=$w&height=$h&fps=$FPS&mode=h264&bitrate=$2" >/dev/null; then
            sleep 8  # pipeline restart + let exposure settle
            stats=$(curl -s --max-time 5 "http://$IP:$PORT/stats" || true)
            if [[ "$stats" == *" $2 kbps"* ]] && ! [[ "$stats" == *'"encoded_fps":0.00'* ]]; then return 0; fi
            echo "settings not applied yet (try $try): $(echo "$stats" | grep -oE '"config":"[^"]*"')"
        else
            echo "no answer from the device (try $try)"
            sleep 3
        fi
    done
    die "device did not accept $1 / $2 kbps"
}

# ---------------------------------------------------------------------------------------------
say "7/9 test matrix ($STEP_SECONDS s per step)"
i=0
for res in $RESOLUTIONS; do
    for br in $BITRATES; do
        i=$((i + 1))
        name=$(printf "m%02d-%s-%sk" "$i" "$res" "$br")
        echo "-- $name"
        configure "$res" "$br"
        measure "$name" "$STEP_SECONDS" || echo "step failed"
    done
done
LAST_RES=$(echo "$RESOLUTIONS" | awk '{print $NF}')
TOP_BR=$(echo "$BITRATES" | tr ' ' '\n' | sort -n | tail -1)

say "8/9 clock sync ($SYNC_ROUNDS rounds) and image samples"
"$PY" scripts/clocksync.py --host "$IP" --rounds "$SYNC_ROUNDS" --interval 10 --json "$OUT/clocksync.json"
configure "$LAST_RES" "$TOP_BR"
"$PY" scripts/measure.py --host "$IP" --seconds 10 --out-dir "$OUT/samples" --name sample --save-stream >/dev/null
"$PY" scripts/sei.py "$OUT/samples/sample.h264" "$OUT/samples/sample-sei.csv"
./dev ffprobe -v error -count_frames -select_streams v:0 \
    -show_entries stream=codec_name,profile,width,height,nb_read_frames -of default=nw=1 \
    "$OUT/samples/sample.h264" > "$OUT/samples/ffprobe.txt"
n=$(grep -oE 'nb_read_frames=[0-9]+' "$OUT/samples/ffprobe.txt" | cut -d= -f2)
for k in 0 $((n / 2)) $((n - 1)); do
    ./dev ffmpeg -v error -i "$OUT/samples/sample.h264" -vf "select=eq(n\,$k)" -frames:v 1 -q:v 2 -y \
        "$OUT/samples/frame-$(printf %04d "$k").jpg"
done
cat "$OUT/samples/ffprobe.txt"

if [ "$SOAK_MINUTES" != 0 ]; then
    say "9/9 soak: $SOAK_MINUTES min at $LAST_RES, $TOP_BR kbps"
    measure "soak-$LAST_RES-${TOP_BR}k" $((SOAK_MINUTES * 60)) || echo "soak failed"
else
    say "9/9 soak skipped"
fi

# ---------------------------------------------------------------------------------------------
say "report"
"$PY" scripts/report.py "$OUT"
echo "open $OUT/report.md   (raw data: steps/, samples/, clocksync.json, device.json, device-adb.txt)"
echo "the app keeps streaming at the last settings; stop it with: T=$ADB_T ./dev adb shell am force-stop $PKG"

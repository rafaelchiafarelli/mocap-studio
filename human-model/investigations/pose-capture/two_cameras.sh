#!/bin/sh
# Joins two videos of one person into a 3D capture: two_cameras.sh A.mp4 B.mp4 OUT_DIR [--height 1.70] [--focal-mm 26] [--offset S] [--fixed-focal]
# OUT_DIR and the videos must be under /mnt/g or /tmp (the reference image mounts those). See two_cameras.py.
# Uses the host's ffmpeg and ffprobe for the sound and the H.264 videos; MediaPipe and the solve run in hm.sh --ref.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
HM="$HERE/../../hm.sh"
A=$(realpath "$1"); B=$(realpath "$2"); OUT=$(realpath -m "$3"); shift 3
mkdir -p "$OUT"
start() { v=$(ffprobe -v error -select_streams "$2" -show_entries stream=start_time -of csv=p=0 "$1" | head -1); echo "${v:-null}"; }
printf '{"a": {"video_start": %s, "audio_start": %s}, "b": {"video_start": %s, "audio_start": %s}}\n' \
    "$(start "$A" v:0)" "$(start "$A" a:0)" "$(start "$B" v:0)" "$(start "$B" a:0)" > "$OUT/meta.json"
# a video without sound gets no .wav; two_cameras.py then needs --offset
[ "$(start "$A" a:0)" = null ] || ffmpeg -v error -y -i "$A" -vn -ac 1 -ar 48000 "$OUT/a.wav"
[ "$(start "$B" a:0)" = null ] || ffmpeg -v error -y -i "$B" -vn -ac 1 -ar 48000 "$OUT/b.wav"
[ -f "$OUT/a.npz" ] || "$HM" --ref python human-model/investigations/pose-capture/capture_pose.py "$A" "$OUT/a.npz" "$OUT/a_mediapipe_mp4v.mp4"
[ -f "$OUT/b.npz" ] || "$HM" --ref python human-model/investigations/pose-capture/capture_pose.py "$B" "$OUT/b.npz" "$OUT/b_mediapipe_mp4v.mp4"
"$HM" --ref python human-model/investigations/pose-capture/two_cameras.py "$OUT/a.npz" "$OUT/b.npz" "$OUT/a.wav" "$OUT/b.wav" "$OUT/meta.json" "$A" "$B" "$OUT" "$@"
for n in a_mediapipe b_mediapipe two_cameras_overlay; do
    src="$OUT/$n.mp4"; [ "$n" = two_cameras_overlay ] || src="$OUT/${n}_mp4v.mp4"
    [ -f "$src" ] && ffmpeg -v error -y -i "$src" -c:v libx264 -pix_fmt yuv420p -crf 20 "$OUT/${n}_h264.mp4"
done
echo "done: $OUT"

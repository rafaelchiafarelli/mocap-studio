#!/bin/sh
# Runs the walking thigh with other values, all the way to the videos: human-model/thigh_run.sh NAME [NAME=value ...]
# Example: human-model/thigh_run.sh v7_damp-20 DAMPING=20
# Writes G:\mocap-studio-downloads\review\<today>\thigh_walk\<NAME>\ and refuses a name that's already there, so nothing is overwritten.
# Defaults are in human-model/data/thigh_tissue.json: edit it to change them for every run. LAYERS and DUMP can be set to use another thigh or walk.
set -e
[ -n "$1" ] || { sed -n 2,5p "$0"; exit 1; }
NAME=$1; shift
HERE=$(cd "$(dirname "$0")" && pwd)
G=/mnt/g/mocap-studio-downloads/review
LAYERS=${LAYERS:-$G/2026-11-07/thigh_v3_section-along-femur/female.thigh_layers.npz}
DUMP=${DUMP:-$G/2026-11-07/thigh_walk/00_female_walk_dump.npz}
OUT=$G/$(date +%F)/thigh_walk/$NAME
[ ! -e "$OUT" ] || { echo "$OUT already exists: pick another name" >&2; exit 1; }
mkdir -p "$OUT"
echo "== 1/3 simulating on the GPU ($*)"
"$HERE/hm.sh" --gpu python human-model/tools/thigh_walk.py "$LAYERS" "$DUMP" "$OUT" "$@" > "$OUT/log.txt" 2>&1 || { tail -20 "$OUT/log.txt"; exit 1; }
echo "== 2/3 baking and rendering in Blender"
python3 "$HERE/blender_run.py" "$HERE/blender/thigh_bake.py" "$OUT/thigh_walk.npz" "$LAYERS" "$DUMP" "$OUT/thigh_walk.blend" "$OUT/frames" > "$OUT/bake_log.txt" 2>&1 || { tail -20 "$OUT/bake_log.txt"; exit 1; }
echo "== 3/3 videos"
for v in compare inside; do
    ffmpeg -loglevel error -y -framerate 24 -i "$OUT/frames/$v/%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 18 "$OUT/${NAME}_$v.mp4"
done
python3 -c "
import json; d = json.load(open('$OUT/thigh_walk.json'))
m = d['skin_motion_in_femur_frame']; b = d['bone_through_skin']
print('peak motion against the femur:', m['ours_peak_mm'], 'mm; settles in', m['after_stop_settles_in_s'], 's after stopping')
print('bone through skin, frames:', b['ours_frames_with_any'], '| ms per frame, median:', d['ms_per_frame']['median'])"
printf "Done: %s\n" "$(wslpath -w "$OUT")"

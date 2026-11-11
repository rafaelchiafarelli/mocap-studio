"""Judges whether photos and videos of a real person are good reference for the human model, and prints why, in Portuguese.

Photos are judged for the body's shape at rest, videos for its motion while walking. A video is split into stretches, each a continuous
run with the whole body in the picture and no camera cut, and each stretch is judged apart; long videos list their best stretches with
start and end. Each check gives ok, atenção or ruim: any ruim makes the photo or stretch RUIM, any atenção ACEITÁVEL, otherwise BOA.
The summary also says which views are missing.

    human-model/hm.sh --ref python human-model/tools/check_reference.py "G:\\referencias" [more files or folders ...] [--todos] [--csv FILE]

--todos lists every stretch of a long video, not only the best ones. --csv writes every stretch to a table, for tools/cut_stretches.py.

Windows paths work, in quotes. Files must be on G: or C:. Every limit below is declared by judgement, not measured against results.
"""
from __future__ import annotations

import csv
import os
import re
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import cv2  # noqa: E402
from mediapipe.python.solutions import face_detection as mp_face  # noqa: E402
from mediapipe.python.solutions import pose as mp_pose  # noqa: E402
from PIL import Image  # noqa: E402

OK, WARN, BAD = "ok", "atenção", "ruim"
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}
UNREADABLE_EXT = {".heic", ".heif", ".avif", ".cr2", ".cr3", ".nef", ".arw", ".dng"}

PHOTO_BODY_PX = (1500, 800)  # body height in pixels: ok from the first, atenção from the second, ruim below
VIDEO_BODY_PX = (1000, 500)
VIDEO_FPS = (59.0, 23.0)  # ok from the first; below the second, ruim. Under 60 and 24 because cameras record at 59.94 and 23.976
VIDEO_SECONDS = (6.0, 2.0)  # a stretch's length: ok from the first; shorter than the second it isn't listed
POSE_HZ = 10.0  # how many frames per second go through the pose model and the other per-frame checks
MAX_GAP_S = 0.5  # longer than this without the whole body ends a stretch
PERSON_JUMP = 0.25  # hips jumping by this share of the body's height, plus one body height per second of gap, means another person
PERSON_SIZE = (0.7, 1.4)  # the body's height against the last sample's, outside which it is another person
CUT_DISTANCE = 0.3  # colour-histogram distance between two frames, from which a jump can be a camera cut
CUT_RATIO = 4.0  # and how many times above the recent frames' distance it must be
BEST_STRETCHES = 15  # how many stretches a long video lists
STEPS = 4  # steps wanted in a walking video
WALK_TRAVEL = (0.5, 0.15)  # under both, the person didn't walk: hips across the picture, and change of apparent size, each over the body's height
CAMERA_SPEED = (0.5, 5.0)  # the background's motion, in % of the body's height per second: ok, then shaking, then moving
BITS_PER_PIXEL = (0.08, 0.03)  # below the first the compression may erase skin detail; below the second it has
DUPLICATE_SHARE = 0.25  # share of repeated frames that means the real frame rate is lower than the file says
CLIPPED = (0.05, 0.15)  # share of the body burnt white; crushed black warns above the second
SIDE_LIGHT = 1.5  # brightness of one half of the body over the other
SHARPNESS = (0.45, 0.25)  # see sharpness(): measured on a real recording and on it blurred on purpose
SKIN_MIN = 0.15  # share of the body with skin colours, under which it is probably clothed
SKIN_TEXTURE = 1.0  # trackable points per 100x100 px of skin, with the body scaled to 1000 px tall
DISTANCE_M = (3.0, 2.0)  # the camera's distance: ok from the first, atenção from the second
ASSUMED_HEIGHT_M = 1.7  # only to estimate that distance
RETOUCH_SOFTWARE = re.compile(r"photoshop|lightroom|facetune|snapseed|gimp|meitu|perfect ?365|pixelmator|capture one|airbrush|remini", re.I)

NOSE, EAR_L, EAR_R, SH_L, SH_R, WR_L, WR_R, HIP_L, HIP_R, KNEE_L, KNEE_R, AN_L, AN_R, HEEL_L, HEEL_R, TOE_L, TOE_R = 0, 7, 8, 11, 12, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32
FEET = (AN_L, AN_R, HEEL_L, HEEL_R, TOE_L, TOE_R)


@dataclass
class Report:
    path: Path
    use: str  # "forma" or "movimento"
    view: str = "?"
    checks: list = field(default_factory=list)
    start: float | None = None  # a video's stretch, in seconds
    end: float | None = None
    body_px: int = 0

    def add(self, level: str, name: str, text: str):
        self.checks.append((level, name, text))

    @property
    def verdict(self) -> str:
        levels = [c[0] for c in self.checks]
        return "RUIM" if BAD in levels else "ACEITÁVEL" if WARN in levels else "BOA"


@dataclass
class Person:
    lm: np.ndarray  # 33 x 4: x and y in the frame's pixels, MediaPipe's relative depth, visibility
    world: np.ndarray  # 33 x 3, metres
    mask: np.ndarray  # bool, the frame's size, the largest piece only
    box: tuple  # x0, y0, x1, y1 of the mask


def wsl_path(raw: str) -> Path:
    m = re.match(r"^([A-Za-z]):[\\/]*(.*)$", raw)
    return Path(f"/mnt/{m[1].lower()}/{m[2].replace(chr(92), '/')}") if m else Path(raw)


def graded(value, limits, higher_is_better=True):
    if higher_is_better:
        return OK if value >= limits[0] else WARN if value >= limits[1] else BAD
    return OK if value <= limits[0] else WARN if value <= limits[1] else BAD


def find_person(pose, bgr, max_side=1280) -> Person | None:
    h, w = bgr.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    small = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else bgr
    r = pose.process(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
    if r.pose_landmarks is None or r.segmentation_mask is None:
        return None
    lm = np.array([[p.x * w, p.y * h, p.z * w, p.visibility] for p in r.pose_landmarks.landmark])
    world = np.array([[p.x, p.y, p.z] for p in r.pose_world_landmarks.landmark])
    raw = (r.segmentation_mask > 0.5).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(raw)
    if n < 2:
        return None
    keep = (labels == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    mask = cv2.resize(keep, (w, h), interpolation=cv2.INTER_NEAREST) > 0
    ys, xs = np.nonzero(mask)
    return Person(lm, world, mask, (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))


def body_height(p: Person) -> int:
    return p.box[3] - p.box[1]


def whole_body_in_frame(p: Person, shape) -> tuple[bool, str]:
    """Head and feet seen, and the mask not cut by the top or the bottom of the picture."""
    h, w = shape[:2]
    margin = 0.005 * h
    if p.box[1] <= margin:
        return False, "a cabeça encosta no topo da imagem"
    if p.box[3] >= h - margin:
        return False, "os pés encostam na base da imagem"
    if p.lm[NOSE, 3] < 0.5:
        seen_head = p.lm[[EAR_L, EAR_R], 3].max() >= 0.5
        if not seen_head:
            return False, "a cabeça não aparece"
    pts = p.lm[list(FEET)]
    inside = (pts[:, 0] >= 0) & (pts[:, 0] < w) & (pts[:, 1] >= 0) & (pts[:, 1] < h)
    if not inside.all() or np.median(pts[:, 3]) < 0.5:
        return False, "os pés não aparecem"
    return True, ""


def view_of(p: Person, bgr, face) -> str:
    """From how wide the shoulders look against the torso; the face decides between front and back."""
    mid_sh = p.lm[[SH_L, SH_R], :2].mean(0)
    mid_hip = p.lm[[HIP_L, HIP_R], :2].mean(0)
    torso = np.linalg.norm(mid_sh - mid_hip) or 1.0
    ratio = np.linalg.norm(p.lm[SH_L, :2] - p.lm[SH_R, :2]) / torso
    if ratio < 0.25:
        return "lado"
    if ratio < 0.55:
        return "3/4"
    h, w = bgr.shape[:2]
    half = int(max(ratio * torso * 0.6, 20))
    cx, cy = p.lm[[NOSE, EAR_L, EAR_R], :2].mean(0).astype(int)
    crop = bgr[max(cy - half, 0):min(cy + half, h), max(cx - half, 0):min(cx + half, w)]
    if crop.size == 0:
        return "frente/costas"
    crop = cv2.resize(crop, (256, 256), interpolation=cv2.INTER_AREA if crop.shape[0] > 256 else cv2.INTER_CUBIC)
    return "frente" if face.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)).detections else "costas"


def body_crop(bgr, p: Person, tall=1000):
    """The body's box and mask, shrunk to `tall` pixels high when larger, so sharpness and texture don't depend on the camera's resolution."""
    x0, y0, x1, y1 = p.box
    crop, mask = bgr[y0:y1, x0:x1], p.mask[y0:y1, x0:x1].astype(np.uint8)
    if y1 - y0 > tall:
        s = tall / (y1 - y0)
        crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        mask = cv2.resize(mask, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_NEAREST)
    return crop, mask > 0


def sharpness(bgr, p: Person) -> float:
    """The strongest fine detail on the body against its contrast: the 99.5th percentile of the Laplacian over the 99th-1st percentile of brightness."""
    crop, mask = body_crop(bgr, p)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
    inner = cv2.dilate(mask.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    values = gray[inner]
    if values.size < 100:
        return 0.0
    contrast = max(float(np.percentile(values, 99) - np.percentile(values, 1)), 1.0)
    return float(np.percentile(np.abs(cv2.Laplacian(gray, cv2.CV_32F))[inner], 99.5) / contrast)


def skin_mask(bgr):
    y, cr, cb = cv2.split(cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb))
    return (cr >= 133) & (cr <= 180) & (cb >= 77) & (cb <= 135) & (y >= 30)


def skin_share(bgr, p: Person) -> float:
    return float(skin_mask(bgr)[p.mask].mean())


def skin_texture(bgr, p: Person) -> float | None:
    """Points a tracker could hold, per 100x100 px of skin. None when too little skin shows."""
    crop, mask = body_crop(bgr, p)
    skin = skin_mask(crop) & cv2.erode(mask.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    area = int(skin.sum())
    if area < 5000:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    pts = cv2.goodFeaturesToTrack(gray, 2000, 0.02, 8, mask=skin.astype(np.uint8) * 255)
    return 0.0 if pts is None else len(pts) / (area / 1e4)


def check_sharpness(r: Report, value: float, what: str = ""):
    level = graded(value, SHARPNESS)
    note = {OK: "boa", WARN: "um pouco suave: dobras rasas podem sumir", BAD: "borrada ou tremida"}[level]
    r.add(level, "nitidez", f"{note} ({value:.2f}; boa a partir de {SHARPNESS[0]}{what})")


def check_skin(r: Report, share: float):
    if share < SKIN_MIN:
        r.add(WARN, "pele visível", f"cerca de {share:.0%} do corpo: a roupa pode esconder a forma")
    else:
        r.add(OK, "pele visível", f"cerca de {share:.0%} do corpo")


def angle(a, b):
    c = np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-6)
    return float(np.degrees(np.arccos(np.clip(c, -1, 1))))


def check_pose(r: Report, p: Person):
    """Standing straight, knees straight, and, seen from the front or back, arms a little away from the body."""
    lm = p.lm[:, :2]
    mid_sh, mid_hip = lm[[SH_L, SH_R]].mean(0), lm[[HIP_L, HIP_R]].mean(0)
    lean = angle(mid_sh - mid_hip, np.array([0.0, -1.0]))
    knee = min(angle(lm[HIP_L] - lm[KNEE_L], lm[AN_L] - lm[KNEE_L]), angle(lm[HIP_R] - lm[KNEE_R], lm[AN_R] - lm[KNEE_R]))
    if lean > 25 or knee < 130:
        r.add(BAD, "pose", f"o corpo não está em pé e reto (tronco inclinado {lean:.0f}°, joelho a {knee:.0f}°)")
    elif lean > 10 or knee < 160:
        r.add(WARN, "pose", f"pouco reta (tronco inclinado {lean:.0f}°, joelho a {knee:.0f}°)")
    else:
        r.add(OK, "pose", f"em pé e reta (tronco inclinado {lean:.0f}°, joelho a {knee:.0f}°)")
    if r.view in ("frente", "costas", "frente/costas"):
        arms = [angle(lm[w] - lm[s], lm[h] - lm[s]) for w, s, h in ((WR_L, SH_L, HIP_L), (WR_R, SH_R, HIP_R))]
        if min(arms) < 8:
            r.add(WARN, "braços", f"colados ao corpo (ângulo {min(arms):.0f}°): escondem a linha da cintura e do quadril")
        elif max(arms) > 50:
            r.add(WARN, "braços", f"muito abertos ou erguidos ({max(arms):.0f}°): mudam ombro e seio")
        else:
            r.add(OK, "braços", f"um pouco afastados ({min(arms):.0f}° a {max(arms):.0f}°)")


def check_light(r: Report, bgr, p: Person):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    values = gray[p.mask]
    burnt, black = float((values >= 250).mean()), float((values <= 5).mean())
    r.add(graded(burnt, CLIPPED, higher_is_better=False), "exposição", f"{burnt:.0%} do corpo estourado de branco")
    if black > CLIPPED[1]:  # never ruim: black clothes look the same as lost shadows
        r.add(WARN, "sombras", f"{black:.0%} do corpo totalmente preto: sombra sem detalhe, ou roupa preta")
    if r.view in ("frente", "costas", "frente/costas"):
        mid = (p.box[0] + p.box[2]) // 2
        left, right = p.mask.copy(), p.mask.copy()
        left[:, mid:], right[:, :mid] = False, False
        if left.any() and right.any():
            ratio = max(gray[left].mean(), gray[right].mean()) / max(min(gray[left].mean(), gray[right].mean()), 1.0)
            if ratio > SIDE_LIGHT:
                r.add(WARN, "luz", f"um lado do corpo {ratio:.1f}x mais claro: sombra forte confunde dobras")
            else:
                r.add(OK, "luz", "equilibrada entre os dois lados")


def check_metadata(r: Report, path: Path, frame_shape, body_px: int):
    """Retouching software and, when the photo says its lens, how far the camera was."""
    try:
        exif = Image.open(path).getexif()
    except OSError:
        return
    if not exif:
        r.add(WARN, "metadados", "a foto não diz câmera nem lente: pode ter sido editada ou baixada da internet")
        return
    software = str(exif.get(305, ""))
    if RETOUCH_SOFTWARE.search(software):
        r.add(WARN, "retoque", f"salva por {software}: o corpo pode ter sido alterado")
    focal = exif.get_ifd(0x8769).get(41989)
    if focal:
        h, w = frame_shape[:2]
        side_mm = 36.0 * h / max(h, w)
        distance = ASSUMED_HEIGHT_M * float(focal) * h / (side_mm * body_px)
        level = graded(distance, DISTANCE_M)
        note = {OK: "boa", WARN: "perto: a perspectiva altera as proporções", BAD: "muito perto: a perspectiva distorce o corpo"}[level]
        r.add(WARN if level == BAD else level, "distância", f"cerca de {distance:.1f} m (lente {focal} mm, supondo {ASSUMED_HEIGHT_M} m de altura): {note}")


def judge_photo(path: Path, pose, face) -> Report:
    r = Report(path, "forma")
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        r.add(BAD, "leitura", "não consegui abrir este arquivo")
        return r
    p = find_person(pose, bgr)
    if p is None:
        r.add(BAD, "pessoa", "não encontrei uma pessoa na imagem")
        return r
    r.view = view_of(p, bgr, face)
    whole, why = whole_body_in_frame(p, bgr.shape)
    r.add(OK if whole else BAD, "corpo inteiro", "da cabeça aos pés" if whole else why)
    px = body_height(p)
    r.add(graded(px, PHOTO_BODY_PX), "resolução", f"o corpo ocupa {px} pixels de altura (ideal: {PHOTO_BODY_PX[0]} ou mais)")
    check_sharpness(r, sharpness(bgr, p))
    check_pose(r, p)
    check_light(r, bgr, p)
    check_skin(r, skin_share(bgr, p))
    check_metadata(r, path, bgr.shape, px)
    return r


def count_steps(times, distance) -> int:
    """Ankle separation swings once per step: counts its rises through its own middle, ignoring swings of under 10 cm."""
    if len(distance) < 8:
        return 0
    uniform = np.arange(times[0], times[-1], 1 / POSE_HZ)
    y = np.interp(uniform, times, distance)
    y = np.convolve(y, np.ones(3) / 3, mode="same")
    if np.percentile(y, 95) - np.percentile(y, 5) < 0.10:
        return 0
    above = y > np.median(y)
    return int(np.sum(above[1:] & ~above[:-1]))


def camera_motion(prev_gray, gray, prev_mask, h_body) -> float | None:
    """The background's displacement between two frames, in % of the body's height. None when the background has too few points to follow."""
    allowed = (cv2.dilate(prev_mask.astype(np.uint8), np.ones((31, 31), np.uint8)) == 0).astype(np.uint8) * 255
    pts = cv2.goodFeaturesToTrack(prev_gray, 300, 0.01, 10, mask=allowed)
    if pts is None or len(pts) < 20:
        return None
    moved, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, gray, pts, None)
    good = status.ravel() == 1
    if good.sum() < 20:
        return None
    return float(np.linalg.norm(np.median((moved - pts)[good].reshape(-1, 2), axis=0)) / h_body * 100)


@dataclass
class Stretch:
    """What was seen in a continuous run with the whole body in the picture."""
    times: list = field(default_factory=list)
    body: list = field(default_factory=list)
    sharp: list = field(default_factory=list)
    skin: list = field(default_factory=list)
    texture: list = field(default_factory=list)
    views: list = field(default_factory=list)
    ankle: list = field(default_factory=list)
    hip_x: list = field(default_factory=list)
    speeds: list = field(default_factory=list)
    prev: tuple | None = None  # grey frame, mask and time of the last sample


@dataclass
class FileFacts:
    """What holds for the whole video file."""
    fps: float
    true_fps: float
    repeated: float
    irregular: float
    declared: float
    bits_per_pixel: float | None


def stamp(seconds: float) -> str:
    return f"{int(seconds // 60):02d}:{seconds % 60:04.1f}"


def add_sample(st: Stretch, t: float, bgr, p: Person, face):
    st.times.append(t)
    st.body.append(body_height(p))
    st.sharp.append(sharpness(bgr, p))
    if len(st.sharp) % 5 == 1:
        st.skin.append(skin_share(bgr, p))
        tex = skin_texture(bgr, p)
        if tex is not None:
            st.texture.append(tex)
        st.views.append(view_of(p, bgr, face))
    st.ankle.append(float(np.linalg.norm(p.world[AN_L] - p.world[AN_R])))
    st.hip_x.append(float(p.lm[[HIP_L, HIP_R], 0].mean()))
    s = min(1.0, 640 / max(bgr.shape[:2]))
    gray = cv2.cvtColor(cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    small_mask = cv2.resize(p.mask.astype(np.uint8), (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    if st.prev is not None:
        moved = camera_motion(st.prev[0], gray, st.prev[1], st.body[-1] * s)
        if moved is not None:
            st.speeds.append(moved / max(t - st.prev[2], 1e-3))
    st.prev = (gray, small_mask, t)


def same_person(st: Stretch, p: Person, t: float, last: float) -> bool:
    """Models replace each other without a camera cut: a stretch ends if the body jumps or changes size from one sample to the next."""
    px = body_height(p)
    hip = float(p.lm[[HIP_L, HIP_R], 0].mean())
    return abs(hip - st.hip_x[-1]) <= (PERSON_JUMP + (t - last)) * px and PERSON_SIZE[0] <= px / st.body[-1] <= PERSON_SIZE[1]


def add_frame_rate_checks(r: Report, f: FileFacts):
    level = graded(f.true_fps, VIDEO_FPS)
    note = {OK: "suficiente para ver o impacto do passo", WARN: "serve para o balanço; o impacto do passo não aparece", BAD: "pouco para qualquer medida de movimento"}[level]
    text = f"{f.fps:.0f} quadros por segundo: {note}"
    if f.repeated > DUPLICATE_SHARE:
        text = f"o arquivo diz {f.fps:.0f}, mas {f.repeated:.0%} dos quadros são repetidos, então são cerca de {f.true_fps:.0f}: {note}"
    r.add(level, "quadros por segundo", text)
    if f.irregular > 0.05:
        r.add(WARN, "ritmo dos quadros", f"{f.irregular:.0%} dos intervalos fora do ritmo: quadros perdidos ou taxa variável")


def judge_stretch(path: Path, st: Stretch, facts: FileFacts) -> Report:
    r = Report(path, "movimento", start=st.times[0], end=st.times[-1])
    add_frame_rate_checks(r, facts)
    duration = r.end - r.start
    r.add(graded(duration, VIDEO_SECONDS), "duração", f"{duration:.1f} s com o corpo inteiro")
    px = int(np.median(st.body))
    r.body_px = px
    r.add(graded(px, VIDEO_BODY_PX), "resolução", f"o corpo ocupa {px} pixels de altura (ideal: {VIDEO_BODY_PX[0]} ou mais)")
    check_sharpness(r, float(np.median(st.sharp)), "; inclui o borrão de movimento")

    if len(st.speeds) >= 3:
        speed = float(np.median(st.speeds))
        level = graded(speed, CAMERA_SPEED, higher_is_better=False)
        note = {OK: "parada", WARN: "tremendo um pouco", BAD: "em movimento: bom para olhar, ruim para medir"}[level]
        r.add(OK if level == OK else WARN, "câmera", f"{note} (fundo anda {speed:.1f}% da altura do corpo por segundo)")
    else:
        r.add(WARN, "câmera", "o fundo não tem detalhes suficientes para saber se a câmera ficou parada")

    steps = count_steps(np.array(st.times), np.array(st.ankle))
    across = float(np.percentile(st.hip_x, 95) - np.percentile(st.hip_x, 5)) / px
    closer = float(np.percentile(st.body, 95) - np.percentile(st.body, 5)) / px
    camera_still = len(st.speeds) >= 3 and float(np.median(st.speeds)) <= CAMERA_SPEED[1]  # a camera following the walk keeps the body in the same place
    if camera_still and across < WALK_TRAVEL[0] and closer < WALK_TRAVEL[1]:
        r.add(WARN, "caminhada", f"a pessoa quase não sai do lugar: não parece caminhada, a não ser em esteira ({steps} oscilações dos pés)")
    else:
        r.add(OK if steps >= STEPS else WARN, "caminhada", f"cerca de {steps} passos detectados (ideal: {STEPS} ou mais)")

    if facts.bits_per_pixel is not None:
        level = graded(facts.bits_per_pixel, BITS_PER_PIXEL)
        note = {OK: "boa", WARN: "alta: pode apagar detalhes da pele", BAD: "muito alta: detalhes da pele perdidos"}[level]
        r.add(level, "compressão", f"{facts.bits_per_pixel:.2f} bits por pixel: {note}")

    check_skin(r, float(np.median(st.skin)) if st.skin else 0.0)
    if st.texture:
        value = float(np.median(st.texture))
        if value < SKIN_TEXTURE:
            r.add(WARN, "marcas na pele", f"{value:.1f} pontos rastreáveis por área: pele lisa, o rastreamento pode escorregar")
        else:
            r.add(OK, "marcas na pele", f"{value:.1f} pontos rastreáveis por área")
    if st.views:
        r.view = max(set(st.views), key=st.views.count)
    return r


def read_error(path: Path, text: str) -> list[Report]:
    r = Report(path, "movimento")
    r.add(BAD, "leitura", text)
    return [r]


def judge_video(path: Path, pose, face) -> list[Report]:
    """One report per stretch, in the video's order."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return read_error(path, "não consegui abrir este vídeo")
    declared = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    every = max(1, int(round((declared or 30.0) / POSE_HZ)))
    if declared and total / declared > 120:
        print(f"{path.name}: {total / declared / 60:.0f} min de vídeo, leva alguns minutos...", file=sys.stderr)

    stamps, repeats, compared, cuts, people, why_not = [], 0, 0, 0, 0, {}
    stretches: list[Stretch] = []
    current, last_whole = None, None
    prev_tiny, prev_hist, pending, recent = None, None, None, deque(maxlen=30)
    index, shape = -1, None

    def close():
        nonlocal current
        if current is not None and current.times:
            stretches.append(current)
        current = None

    while cap.grab():
        index += 1
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        stamps.append(t)
        ok, bgr = cap.retrieve()
        if not ok:
            continue
        shape = bgr.shape
        small = cv2.resize(bgr, (160, 90), interpolation=cv2.INTER_AREA)
        tiny = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if prev_tiny is not None:
            compared += 1
            repeats += int(np.mean(cv2.absdiff(tiny, prev_tiny)) < 0.05)
        prev_tiny = tiny
        hist = cv2.calcHist([cv2.cvtColor(small, cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 16], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        if pending is not None:
            # A camera flash is one bright frame and the picture comes back: only a jump that stays is a cut.
            if cv2.compareHist(pending, hist, cv2.HISTCMP_BHATTACHARYYA) >= CUT_DISTANCE / 2:
                cuts += 1
                close()
                last_whole = None
                pose.reset()
            pending = None
        elif prev_hist is not None:
            jump = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
            if jump > CUT_DISTANCE and jump > CUT_RATIO * (np.mean(recent) if recent else 0.02):
                pending, prev_hist = prev_hist, hist
                continue
            recent.append(jump)
        prev_hist = hist
        if index % every:
            continue
        p = find_person(pose, bgr)
        whole, why = whole_body_in_frame(p, bgr.shape) if p is not None else (False, "a pessoa some")
        if whole:
            if current is not None and (t - last_whole > MAX_GAP_S or not same_person(current, p, t, last_whole)):
                if t - last_whole <= MAX_GAP_S:
                    people += 1
                close()
            if current is None:
                current = Stretch()
            add_sample(current, t, bgr, p, face)
            last_whole = t
        else:
            why_not[why] = why_not.get(why, 0) + 1
            if current is not None:
                current.prev = None
                if t - last_whole > MAX_GAP_S:
                    close()
    close()
    cap.release()

    if len(stamps) < 2 or shape is None:
        return read_error(path, "o vídeo não tem quadros que eu consiga ler")
    gaps = np.diff(np.array(stamps))
    gaps = gaps[gaps > 0]
    if gaps.size == 0:
        return read_error(path, "o vídeo não informa o tempo dos quadros")
    fps = 1.0 / float(np.median(gaps))
    repeated = repeats / compared if compared else 0.0
    h, w = shape[:2]
    facts = FileFacts(fps, fps * (1 - repeated) if repeated > DUPLICATE_SHARE else fps, repeated,  # a few equal frames are a still moment, not a lower rate
                      float(np.mean(np.abs(gaps - np.median(gaps)) > 0.5 * np.median(gaps))), declared,
                      path.stat().st_size * 8 / (total * w * h) if total else None)

    kept = [st for st in stretches if st.times[-1] - st.times[0] >= VIDEO_SECONDS[1]]
    if not kept:
        r = Report(path, "movimento")
        add_frame_rate_checks(r, facts)
        why = max(why_not, key=why_not.get) if why_not else "o corpo não aparece inteiro"
        r.add(BAD, "corpo inteiro", f"nenhum trecho de {VIDEO_SECONDS[1]:.0f} s ou mais com o corpo inteiro; o mais comum: {why}")
        return [r]
    reports = [judge_stretch(path, st, facts) for st in kept]
    print(f"\n{path.name}: {stamp(stamps[-1])} de vídeo, {cuts + 1} tomada(s), {people} troca(s) de pessoa sem corte, {len(reports)} trecho(s) com o corpo inteiro ({len(stretches) - len(kept)} curtos demais, descartados)")
    return reports


def expand(args) -> list[Path]:
    files = []
    for raw in args:
        path = wsl_path(raw)
        if path.is_dir():
            files += sorted(f for f in path.rglob("*") if f.is_file() and f.suffix.lower() in PHOTO_EXT | VIDEO_EXT | UNREADABLE_EXT)
        elif path.is_file():
            files.append(path)
        else:
            print(f"Não encontrei: {raw}  (o arquivo precisa estar no G: ou no C:)")
    return files


def title(r: Report) -> str:
    return r.path.name if r.start is None else f"{r.path.name} {stamp(r.start)} a {stamp(r.end)}"


def print_report(r: Report):
    print(f"\n{title(r)}: {r.verdict}  (para {r.use}; vista: {r.view})")
    for level, name, text in sorted(r.checks, key=lambda c: (BAD, WARN, OK).index(c[0])):
        print(f"  [{level:7}] {name}: {text}")


def rank(r: Report):
    """Fewest problems first, then the longest stretch with the largest body."""
    levels = [c[0] for c in r.checks]
    return (levels.count(BAD), levels.count(WARN), -(r.end - r.start) * min(1.0, r.body_px / VIDEO_BODY_PX[0]))


def print_stretches(reports: list[Report], show_all: bool):
    ordered = sorted(reports, key=rank)
    print(f"  Trechos, do melhor para o pior ({'todos' if show_all or len(ordered) <= BEST_STRETCHES else f'os {BEST_STRETCHES} melhores de {len(ordered)}'}):")
    for r in ordered if show_all else ordered[:BEST_STRETCHES]:
        problems = ", ".join(c[1] for c in r.checks if c[0] != OK) or "nenhum aviso"
        print(f"  {stamp(r.start)} a {stamp(r.end)}  {r.verdict:9}  {r.end - r.start:5.1f} s  {r.view:7}  corpo {r.body_px:4d} px  {problems}")
    print_report(ordered[0])


def print_summary(reports: list[Report]):
    usable = [r for r in reports if r.verdict != "RUIM"]
    photos = {r.view for r in usable if r.use == "forma"}
    videos = {r.view for r in usable if r.use == "movimento"}
    print("\nResumo")
    print(f"  Fotos e trechos: {sum(r.verdict == 'BOA' for r in reports)} bom/boa(s), {sum(r.verdict == 'ACEITÁVEL' for r in reports)} aceitável(is), {sum(r.verdict == 'RUIM' for r in reports)} ruim(ns).")
    missing = [v for v in ("frente", "lado", "costas") if v not in photos]
    print("  Fotos: as três vistas estão cobertas." if not missing else f"  Fotos: faltam {', '.join(missing)}.")
    missing = [v for v in ("lado", "costas") if v not in videos]
    print("  Vídeos: lado e costas estão cobertos." if not missing else f"  Vídeos: faltam {', '.join(missing)}.")
    print("\nO que este programa não vê: retoque sem registro no arquivo, roupa justa contra roupa larga, altura da câmera, mais de uma pessoa na cena e se o movimento é mesmo caminhada. Isso fica para o seu olho.")


def main(args) -> int:
    show_all = "--todos" in args
    args = [a for a in args if a != "--todos"]
    table, writer = None, None
    if "--csv" in args:
        at = args.index("--csv")
        table = open(wsl_path(args[at + 1]), "w", newline="", encoding="utf-8")
        writer = csv.writer(table)
        writer.writerow(["video", "start_s", "end_s", "verdict", "view", "body_px", "warnings"])
        args = args[:at] + args[at + 2:]
    if not args:
        print(__doc__)
        return 2
    files = expand(args)
    if not files:
        print("Nenhuma foto ou vídeo para avaliar.")
        return 1
    reports = []
    with mp_pose.Pose(static_image_mode=True, model_complexity=1, enable_segmentation=True) as photo_pose, \
            mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face:
        for path in files:
            suffix = path.suffix.lower()
            if suffix in VIDEO_EXT:
                with mp_pose.Pose(static_image_mode=False, model_complexity=1, enable_segmentation=True, smooth_segmentation=True) as video_pose:
                    found = judge_video(path, video_pose, face)
                if found[0].start is not None:
                    print_stretches(found, show_all)
                    if writer:
                        for r in found:
                            writer.writerow([r.path, f"{r.start:.3f}", f"{r.end:.3f}", r.verdict, r.view, r.body_px, "; ".join(c[1] for c in r.checks if c[0] != OK)])
                        table.flush()
                else:
                    print_report(found[0])
                reports += found
                continue
            if suffix in PHOTO_EXT:
                r = judge_photo(path, photo_pose, face)
            else:
                r = Report(path, "forma")
                r.add(BAD, "formato", f"não leio {suffix}: exporte como JPG ou PNG" if suffix in UNREADABLE_EXT else f"formato {suffix} desconhecido")
            print_report(r)
            reports.append(r)
    print_summary(reports)
    if table:
        table.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

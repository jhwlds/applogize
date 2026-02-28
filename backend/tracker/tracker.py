import argparse
import json
import math
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import cv2
import mediapipe as mp

from mediapipe.tasks.python import BaseOptions  # type: ignore
from mediapipe.tasks.python import vision  # type: ignore


# ---------------------------------------------------------------------
# Landmark indices / connections (no mp.solutions dependency)
# ---------------------------------------------------------------------

# FaceMesh landmark indices (MediaPipe canonical numbering).
# These are used for look-away scoring (eye bbox + iris center) and highlighting.
FACE_LEFT_EYE_IDX: Set[int] = {
    33,
    7,
    163,
    144,
    145,
    153,
    154,
    155,
    133,
    173,
    157,
    158,
    159,
    160,
    161,
    246,
}
FACE_RIGHT_EYE_IDX: Set[int] = {
    263,
    249,
    390,
    373,
    374,
    380,
    381,
    382,
    362,
    398,
    384,
    385,
    386,
    387,
    388,
    466,
}
# MediaPipe canonical iris indices:
# - Right iris: 468..472
# - Left iris: 473..477
FACE_LEFT_IRIS_IDX: Set[int] = {473, 474, 475, 476, 477}
FACE_RIGHT_IRIS_IDX: Set[int] = {468, 469, 470, 471, 472}

# Hand landmark connections (MediaPipe canonical 21-point hand skeleton).
HAND_CONNECTIONS: List[Tuple[int, int]] = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
]


# ---------------------------------------------------------------------
# Models (download-on-demand)
# ---------------------------------------------------------------------

FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
HAND_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)


def _ensure_file(path: str, url: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    try:
        print(f"[tracker] downloading model -> {path}", file=sys.stderr)
        urllib.request.urlretrieve(url, path)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "Failed to download model.\n"
            f"- url: {url}\n"
            f"- path: {path}\n"
            "Try downloading it manually to that path."
        ) from e


# ---------------------------------------------------------------------
# Scoring + stability (ported from face-recognition/main.js)
# ---------------------------------------------------------------------

SCORE_TAU_MS = 120.0

LOOK_EYE_T = 0.2
LOOK_EYE_MAX = 0.55
LOOK_HEAD_T = 0.1
LOOK_HEAD_MAX = 0.35
LOOK_ON = 0.42
LOOK_OFF = 0.28

# When using calibration (baseline subtraction), we score based on delta from baseline.
# Deltas are much smaller than absolute eye_raw magnitudes.
LOOK_EYE_DELTA_T = 0.03
LOOK_EYE_DELTA_MAX = 0.22

# Head-turn guard (do NOT add head into score; only reduce false positives).
# If head yaw proxy rises, make iris-only lookaway less sensitive.
HEAD_GUARD_T = 0.08
HEAD_GUARD_MAX = 0.28
HEAD_DAMP = 0.85
HEAD_DELTA_T_BOOST = 0.10

# Auto-calibration: assume user starts by looking at the camera.
CALIBRATION_WARMUP_MS = 250.0
CALIBRATION_DURATION_MS = 1100.0

# Landmark-based smile fallback (when blendshapes are missing/weak).
# Mouth corners: 61(left), 291(right). Lip center: 13(upper), 14(lower).
# Uses "corner raise" (corners go up relative to mouth center), normalized by mouth width.
SMILE_MOUTH_UP_T = 0.035
SMILE_MOUTH_UP_MAX = 0.11

# Smile sensitivity shaping:
# - deadzone removes small neutral-model bias (prevents "always slightly smiling")
# - gamma makes low scores less influential while keeping strong smiles responsive
SMILE_DEADZONE = 0.30
SMILE_GAMMA = 2.0

# Geometry fallback can be noisy, especially before calibration baseline is ready.
SMILE_GEOM_WEIGHT_PRECALIB = 0.55

# Landmark-based sadness (frown) fallback:
# "Corner drop" (corners go down relative to mouth center), normalized by mouth width.
SAD_MOUTH_DOWN_T = 0.015
SAD_MOUTH_DOWN_MAX = 0.07

# Sadness sensitivity shaping (same idea as smile).
SAD_DEADZONE = 0.12
SAD_GAMMA = 1.15

# Geometry fallback can be noisy, especially before calibration baseline is ready.
SAD_GEOM_WEIGHT_PRECALIB = 0.7

DIALOG_HOLD_MS = 350.0
DIALOG_MIN_SHOW_MS = 900.0

# Two-hand heart gesture (heuristic; normalized by hand scale).
# Definition (per project spec):
# - two thumbs touch each other
# - each thumb stays far from its own 4 fingertips
# - within each hand, the 4 fingertips are clustered together
# - across hands, the two 4-fingertip clusters touch/overlap
HEART_THUMB_TOUCH_T = 0.24
HEART_THUMB_FAR_T = 0.68
HEART_THUMB_FAR_MAX = 1.20
HEART_FOUR_CLUSTER_MAX_SPREAD_T = 0.55
HEART_FOUR_GROUP_TOUCH_T = 0.70
HEART_FOUR_CROSS_TIP_TOUCH_T = 0.55
HEART_ON = 0.55
HEART_OFF = 0.35


@dataclass(frozen=True)
class HeartParams:
    thumb_touch_t: float = HEART_THUMB_TOUCH_T
    thumb_far_t: float = HEART_THUMB_FAR_T
    thumb_far_max: float = HEART_THUMB_FAR_MAX
    four_cluster_max_spread_t: float = HEART_FOUR_CLUSTER_MAX_SPREAD_T
    four_group_touch_t: float = HEART_FOUR_GROUP_TOUCH_T
    four_cross_tip_touch_t: float = HEART_FOUR_CROSS_TIP_TOUCH_T
    on_t: float = HEART_ON
    off_t: float = HEART_OFF


def heart_params_from_sensitivity(sensitivity: float) -> HeartParams:
    """
    sensitivity > 1.0 => easier heart detection
    sensitivity < 1.0 => stricter heart detection
    """
    s = float(sensitivity)
    if not math.isfinite(s):
        s = 1.0
    s = max(0.5, min(2.5, s))
    inv = 1.0 / max(1e-6, s)
    return HeartParams(
        thumb_touch_t=float(HEART_THUMB_TOUCH_T) * s,
        thumb_far_t=float(HEART_THUMB_FAR_T) * inv,
        thumb_far_max=float(HEART_THUMB_FAR_MAX),
        four_cluster_max_spread_t=float(HEART_FOUR_CLUSTER_MAX_SPREAD_T) * s,
        four_group_touch_t=float(HEART_FOUR_GROUP_TOUCH_T) * s,
        four_cross_tip_touch_t=float(HEART_FOUR_CROSS_TIP_TOUCH_T) * s,
        on_t=float(HEART_ON) * inv,
        off_t=float(HEART_OFF) * inv,
    )


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def ema_alpha(dt_ms: float, tau_ms: float) -> float:
    dt = max(0.0, float(dt_ms))
    tau = max(1.0, float(tau_ms))
    return 1.0 - math.exp(-dt / tau)


def blendshapes_to_map(categories: Sequence[Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for c in categories or []:
        key = getattr(c, "category_name", None) or getattr(c, "categoryName", None)
        if not key:
            continue
        score = getattr(c, "score", 0.0)
        try:
            out[str(key)] = float(score)
        except Exception:  # noqa: BLE001
            out[str(key)] = 0.0
    return out


def get_cat(cat: Dict[str, float], key: str) -> float:
    v = cat.get(key, 0.0)
    try:
        return float(v)
    except Exception:  # noqa: BLE001
        return 0.0


def compute_smile(cat: Dict[str, float]) -> float:
    l = get_cat(cat, "mouthSmileLeft")
    r = get_cat(cat, "mouthSmileRight")
    return clamp01((l + r) * 0.5)


def compute_sadness(cat: Dict[str, float]) -> float:
    l = get_cat(cat, "mouthFrownLeft")
    r = get_cat(cat, "mouthFrownRight")
    return clamp01((l + r) * 0.5)


def shape_smile_score(x: float) -> float:
    x = clamp01(x)
    dz = clamp01(SMILE_DEADZONE)
    if x <= dz:
        return 0.0
    y = (x - dz) / max(1e-6, (1.0 - dz))
    g = max(0.1, float(SMILE_GAMMA))
    try:
        return clamp01(float(y) ** g)
    except Exception:  # noqa: BLE001
        return clamp01(y)


def shape_sadness_score(x: float) -> float:
    x = clamp01(x)
    dz = clamp01(SAD_DEADZONE)
    if x <= dz:
        return 0.0
    y = (x - dz) / max(1e-6, (1.0 - dz))
    g = max(0.1, float(SAD_GAMMA))
    try:
        return clamp01(float(y) ** g)
    except Exception:  # noqa: BLE001
        return clamp01(y)


def mouth_smile_metric(landmarks: Sequence[Any]) -> float:
    # "Corner raise" metric (smile tends to lift mouth corners).
    left = safe_point(landmarks, 61)
    right = safe_point(landmarks, 291)
    upper = safe_point(landmarks, 13)
    lower = safe_point(landmarks, 14)
    if left is None or right is None or upper is None or lower is None:
        return 0.0
    w = dist2d(left, right)
    if not math.isfinite(w):
        return 0.0
    w = max(1e-6, float(w))
    center_y = (float(upper.y) + float(lower.y)) * 0.5
    corners_y = (float(left.y) + float(right.y)) * 0.5
    up = (center_y - corners_y) / w
    return max(0.0, float(up)) if math.isfinite(up) else 0.0


def compute_smile_geom(landmarks: Sequence[Any], baseline: float = 0.0) -> float:
    m = mouth_smile_metric(landmarks)
    if m <= 0.0:
        return 0.0
    m_adj = max(0.0, float(m) - float(baseline))
    return clamp01((m_adj - SMILE_MOUTH_UP_T) / (SMILE_MOUTH_UP_MAX - SMILE_MOUTH_UP_T))


def mouth_sad_metric(landmarks: Sequence[Any]) -> float:
    # "Corner drop" metric (sadness/frown tends to lower mouth corners).
    left = safe_point(landmarks, 61)
    right = safe_point(landmarks, 291)
    upper = safe_point(landmarks, 13)
    lower = safe_point(landmarks, 14)
    if left is None or right is None or upper is None or lower is None:
        return 0.0
    w = dist2d(left, right)
    if not math.isfinite(w):
        return 0.0
    w = max(1e-6, float(w))
    center_y = (float(upper.y) + float(lower.y)) * 0.5
    corners_y = (float(left.y) + float(right.y)) * 0.5
    down = (corners_y - center_y) / w
    return max(0.0, float(down)) if math.isfinite(down) else 0.0


def compute_sad_geom(landmarks: Sequence[Any], baseline: float = 0.0) -> float:
    m = mouth_sad_metric(landmarks)
    if m <= 0.0:
        return 0.0
    m_adj = max(0.0, float(m) - float(baseline))
    return clamp01((m_adj - SAD_MOUTH_DOWN_T) / (SAD_MOUTH_DOWN_MAX - SAD_MOUTH_DOWN_T))


def safe_point(landmarks: Sequence[Any], idx: int) -> Optional[Any]:
    if not landmarks:
        return None
    if idx < 0 or idx >= len(landmarks):
        return None
    p = landmarks[idx]
    if p is None:
        return None
    x = getattr(p, "x", None)
    y = getattr(p, "y", None)
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    return p


def hypot2(a: float, b: float) -> float:
    return math.sqrt(a * a + b * b)


def dist2d(a: Any, b: Any) -> float:
    if a is None or b is None:
        return 0.0
    ax, ay = getattr(a, "x", None), getattr(a, "y", None)
    bx, by = getattr(b, "x", None), getattr(b, "y", None)
    if not isinstance(ax, (int, float)) or not isinstance(ay, (int, float)):
        return 0.0
    if not isinstance(bx, (int, float)) or not isinstance(by, (int, float)):
        return 0.0
    return hypot2(float(ax) - float(bx), float(ay) - float(by))


def is_finger_extended(hand_landmarks: Sequence[Any], tip_idx: int, pip_idx: int, k: float = 1.12) -> bool:
    wrist = safe_point(hand_landmarks, 0)
    tip = safe_point(hand_landmarks, tip_idx)
    pip = safe_point(hand_landmarks, pip_idx)
    if wrist is None or tip is None or pip is None:
        return False
    return dist2d(wrist, tip) > dist2d(wrist, pip) * float(k)


def is_finger_folded(hand_landmarks: Sequence[Any], tip_idx: int, pip_idx: int, k: float = 1.03) -> bool:
    wrist = safe_point(hand_landmarks, 0)
    tip = safe_point(hand_landmarks, tip_idx)
    pip = safe_point(hand_landmarks, pip_idx)
    if wrist is None or tip is None or pip is None:
        return False
    return dist2d(wrist, tip) < dist2d(wrist, pip) * float(k)


def palm_center(hand_landmarks: Sequence[Any]) -> Optional[Dict[str, float]]:
    wrist = safe_point(hand_landmarks, 0)
    index_mcp = safe_point(hand_landmarks, 5)
    mid_mcp = safe_point(hand_landmarks, 9)
    pinky_mcp = safe_point(hand_landmarks, 17)
    if wrist is None or index_mcp is None or mid_mcp is None or pinky_mcp is None:
        return None
    return {
        "x": (float(wrist.x) + float(index_mcp.x) + float(mid_mcp.x) + float(pinky_mcp.x)) * 0.25,
        "y": (float(wrist.y) + float(index_mcp.y) + float(mid_mcp.y) + float(pinky_mcp.y)) * 0.25,
    }


def compute_hand_gestures(hand_landmarks: Sequence[Any]) -> Dict[str, bool]:
    index_ext = is_finger_extended(hand_landmarks, 8, 6, 1.12)
    middle_ext = is_finger_extended(hand_landmarks, 12, 10, 1.12)
    ring_ext = is_finger_extended(hand_landmarks, 16, 14, 1.12)
    pinky_ext = is_finger_extended(hand_landmarks, 20, 18, 1.12)
    thumb_ext = is_finger_extended(hand_landmarks, 4, 3, 1.18)

    extended_count = sum([index_ext, middle_ext, ring_ext, pinky_ext, thumb_ext])
    open_palm = extended_count >= 4

    thumb_tip = safe_point(hand_landmarks, 4)
    thumb_mcp = safe_point(hand_landmarks, 2)
    center = palm_center(hand_landmarks)
    wrist = safe_point(hand_landmarks, 0)
    mid_mcp = safe_point(hand_landmarks, 9)
    scale = dist2d(wrist, mid_mcp) if (wrist is not None and mid_mcp is not None) else 1.0
    scale = max(1e-6, scale)

    others_folded = (
        is_finger_folded(hand_landmarks, 8, 6, 1.05)
        and is_finger_folded(hand_landmarks, 12, 10, 1.05)
        and is_finger_folded(hand_landmarks, 16, 14, 1.05)
        and is_finger_folded(hand_landmarks, 20, 18, 1.05)
    )

    thumb_up_y = False
    if thumb_tip is not None and thumb_mcp is not None:
        thumb_up_y = float(thumb_tip.y) < float(thumb_mcp.y) - 0.035
        if center is not None:
            thumb_up_y = thumb_up_y and float(thumb_tip.y) < float(center["y"]) - 0.02

    thumb_far_from_palm = False
    if thumb_tip is not None and center is not None:
        thumb_far_from_palm = (hypot2(float(thumb_tip.x) - float(center["x"]), float(thumb_tip.y) - float(center["y"])) / scale) > 0.75

    thumbs_up = bool(thumb_ext and others_folded and thumb_up_y and thumb_far_from_palm)
    return {"openPalm": bool(open_palm), "thumbsUp": bool(thumbs_up)}


def _hand_scale(hand_landmarks: Sequence[Any]) -> float:
    wrist = safe_point(hand_landmarks, 0)
    mid_mcp = safe_point(hand_landmarks, 9)
    s = dist2d(wrist, mid_mcp) if (wrist is not None and mid_mcp is not None) else 0.0
    return max(1e-6, float(s) if math.isfinite(float(s)) else 1e-6)


def _xy(p: Any) -> Optional[Tuple[float, float]]:
    if p is None:
        return None
    if isinstance(p, dict):
        x = p.get("x", None)
        y = p.get("y", None)
    else:
        x = getattr(p, "x", None)
        y = getattr(p, "y", None)
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    fx, fy = float(x), float(y)
    if not (math.isfinite(fx) and math.isfinite(fy)):
        return None
    return fx, fy


def _dist2d_any(a: Any, b: Any) -> float:
    aa = _xy(a)
    bb = _xy(b)
    if aa is None or bb is None:
        return 0.0
    ax, ay = aa
    bx, by = bb
    return hypot2(ax - bx, ay - by)


def _center_xy(hand_landmarks: Sequence[Any], tip_indices: Sequence[int]) -> Optional[Dict[str, float]]:
    sx = 0.0
    sy = 0.0
    n = 0
    for idx in tip_indices:
        p = safe_point(hand_landmarks, int(idx))
        if p is None:
            continue
        sx += float(p.x)
        sy += float(p.y)
        n += 1
    if n == 0:
        return None
    return {"x": sx / float(n), "y": sy / float(n)}


def _max_pairwise_spread(hand_landmarks: Sequence[Any], tip_indices: Sequence[int]) -> float:
    pts: List[Any] = []
    for idx in tip_indices:
        p = safe_point(hand_landmarks, int(idx))
        if p is not None:
            pts.append(p)
    if len(pts) < 2:
        return 0.0
    m = 0.0
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            m = max(m, _dist2d_any(pts[i], pts[j]))
    return float(m)


def compute_two_hand_heart_score(
    hands: Sequence[Sequence[Any]],
    params: Optional[HeartParams] = None,
    require_both_touch: bool = True,
) -> float:
    """
    Heuristic for a two-hand heart (thumbs touch; other 4 fingertips clustered and touching across hands).
    Returns a confidence score in [0, 1].
    """
    if hands is None or len(hands) < 2:
        return 0.0
    p = params or HeartParams()

    best = 0.0
    n = min(4, len(hands))  # keep it bounded
    for i in range(n):
        for j in range(i + 1, n):
            h1 = hands[i]
            h2 = hands[j]

            # Required points
            t1 = safe_point(h1, 4)
            t2 = safe_point(h2, 4)
            w1 = safe_point(h1, 0)
            w2 = safe_point(h2, 0)
            if t1 is None or t2 is None or w1 is None or w2 is None:
                continue

            # Normalize by average hand scale.
            scale = (_hand_scale(h1) + _hand_scale(h2)) * 0.5
            d_thumb = _dist2d_any(t1, t2) / scale

            # Also ensure hands are not wildly separated.
            d_wrist = _dist2d_any(w1, w2) / scale
            if d_wrist > 2.7:
                continue

            # 4-fingertip clusters (exclude thumb): index, middle, ring, pinky tips.
            four = [8, 12, 16, 20]
            c1 = _center_xy(h1, four)
            c2 = _center_xy(h2, four)
            if c1 is None or c2 is None:
                continue

            # Thumb should be far from own 4-fingertip cluster.
            d_thumb_far_1 = _dist2d_any(t1, c1) / scale
            d_thumb_far_2 = _dist2d_any(t2, c2) / scale

            # 4 fingertips should be clustered (within each hand).
            spread_1 = _max_pairwise_spread(h1, four) / scale
            spread_2 = _max_pairwise_spread(h2, four) / scale

            # Across hands, 4-fingertip clusters should touch/overlap.
            d_four_centers = _dist2d_any(c1, c2) / scale
            min_cross_tip = float("inf")
            for a_idx in four:
                pa = safe_point(h1, int(a_idx))
                if pa is None:
                    continue
                for b_idx in four:
                    pb = safe_point(h2, int(b_idx))
                    if pb is None:
                        continue
                    min_cross_tip = min(min_cross_tip, _dist2d_any(pa, pb) / scale)
            if not math.isfinite(min_cross_tip):
                continue

            # Hard requirements from spec.
            if d_thumb > p.thumb_touch_t:
                continue
            if d_thumb_far_1 < p.thumb_far_t or d_thumb_far_2 < p.thumb_far_t:
                continue
            if spread_1 > p.four_cluster_max_spread_t or spread_2 > p.four_cluster_max_spread_t:
                continue
            if require_both_touch:
                if d_four_centers > p.four_group_touch_t:
                    continue
                if min_cross_tip > p.four_cross_tip_touch_t:
                    continue
            else:
                if d_four_centers > p.four_group_touch_t and min_cross_tip > p.four_cross_tip_touch_t:
                    continue

            # Score components
            s_thumb_touch = clamp01(1.0 - float(d_thumb) / float(p.thumb_touch_t))
            s_thumb_far = clamp01(
                min(
                    (float(d_thumb_far_1) - float(p.thumb_far_t)) / max(1e-6, (float(p.thumb_far_max) - float(p.thumb_far_t))),
                    (float(d_thumb_far_2) - float(p.thumb_far_t)) / max(1e-6, (float(p.thumb_far_max) - float(p.thumb_far_t))),
                )
            )
            s_cluster = clamp01(1.0 - max(float(spread_1), float(spread_2)) / float(p.four_cluster_max_spread_t))
            s_touch_centers = clamp01(1.0 - float(d_four_centers) / float(p.four_group_touch_t))
            s_touch_tips = clamp01(1.0 - float(min_cross_tip) / float(p.four_cross_tip_touch_t))
            s_touch = min(s_touch_centers, s_touch_tips) if require_both_touch else max(s_touch_centers, s_touch_tips)

            score = float(min(s_thumb_touch, s_thumb_far, s_cluster, s_touch))
            best = max(best, score)

    return clamp01(best)


def connection_indices(connections: Iterable[Tuple[int, int]]) -> Set[int]:
    s: Set[int] = set()
    for a, b in connections or []:
        s.add(int(a))
        s.add(int(b))
    return s


def bbox_from_indices(landmarks: Sequence[Any], indices: Set[int]) -> Optional[Dict[str, float]]:
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")
    count = 0
    for idx in indices:
        p = safe_point(landmarks, idx)
        if p is None:
            continue
        x, y = float(p.x), float(p.y)
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)
        count += 1
    if count == 0:
        return None
    return {"minX": min_x, "minY": min_y, "maxX": max_x, "maxY": max_y}


def center_from_indices(landmarks: Sequence[Any], indices: Set[int]) -> Optional[Dict[str, float]]:
    sx = 0.0
    sy = 0.0
    n = 0
    for idx in indices:
        p = safe_point(landmarks, idx)
        if p is None:
            continue
        sx += float(p.x)
        sy += float(p.y)
        n += 1
    if n == 0:
        return None
    return {"x": sx / n, "y": sy / n}


def look_away_mag_for_eye(landmarks: Sequence[Any], eye_indices: Set[int], iris_indices: Set[int]) -> float:
    eye_box = bbox_from_indices(landmarks, eye_indices)
    iris_center = center_from_indices(landmarks, iris_indices)
    if eye_box is None or iris_center is None:
        return 0.0

    mid_x = (eye_box["minX"] + eye_box["maxX"]) * 0.5
    mid_y = (eye_box["minY"] + eye_box["maxY"]) * 0.5
    half_w = max(1e-6, (eye_box["maxX"] - eye_box["minX"]) * 0.5)
    half_h = max(1e-6, (eye_box["maxY"] - eye_box["minY"]) * 0.5)

    dx = (iris_center["x"] - mid_x) / half_w
    dy = (iris_center["y"] - mid_y) / half_h
    mag = math.sqrt(dx * dx + dy * dy)
    return mag if math.isfinite(mag) else 0.0


def head_yaw_proxy(landmarks: Sequence[Any]) -> float:
    # Same indices as JS: nose tip(1), left eye outer(33), right eye outer(263)
    n = safe_point(landmarks, 1)
    l = safe_point(landmarks, 33)
    r = safe_point(landmarks, 263)
    if n is None or l is None or r is None:
        return 0.0

    d_l = hypot2(float(n.x) - float(l.x), float(n.y) - float(l.y))
    d_r = hypot2(float(n.x) - float(r.x), float(n.y) - float(r.y))
    yaw_2d = abs(d_l - d_r) / (d_l + d_r + 1e-6)

    yaw_z = 0.0
    lz = getattr(l, "z", None)
    rz = getattr(r, "z", None)
    if isinstance(lz, (int, float)) and isinstance(rz, (int, float)):
        eye_dx = abs(float(l.x) - float(r.x)) + 1e-6
        yaw_z = abs(float(lz) - float(rz)) / eye_dx

    return max(yaw_z, yaw_2d * 1.25)


def look_away_scores_from_raw(eye_raw: float, head_raw: float) -> Dict[str, float]:
    eye_score = clamp01((float(eye_raw) - LOOK_EYE_T) / (LOOK_EYE_MAX - LOOK_EYE_T))
    head_score = clamp01((float(head_raw) - LOOK_HEAD_T) / (LOOK_HEAD_MAX - LOOK_HEAD_T))
    # User preference: ignore head/face movement, use iris-only eye score.
    return {"lookAwayScore": eye_score, "eyeScore": eye_score, "headScore": head_score}


def compute_look_away_eye_only(
    landmarks: Sequence[Any],
    left_eye_idx: Set[int],
    right_eye_idx: Set[int],
    left_iris_idx: Set[int],
    right_iris_idx: Set[int],
) -> Dict[str, float]:
    if not landmarks:
        return {"lookAwayScore": 0.0, "eyeRaw": 0.0, "leftMag": 0.0, "rightMag": 0.0}
    left_mag = float(look_away_mag_for_eye(landmarks, left_eye_idx, left_iris_idx))
    right_mag = float(look_away_mag_for_eye(landmarks, right_eye_idx, right_iris_idx))
    eye_raw = max(left_mag, right_mag)  # more sensitive to single-eye movement
    eye_score = clamp01((eye_raw - LOOK_EYE_T) / (LOOK_EYE_MAX - LOOK_EYE_T))
    return {"lookAwayScore": float(eye_score), "eyeRaw": float(eye_raw), "leftMag": left_mag, "rightMag": right_mag}


def compute_look_away_combined(
    landmarks: Sequence[Any],
    left_eye_idx: Set[int],
    right_eye_idx: Set[int],
    left_iris_idx: Set[int],
    right_iris_idx: Set[int],
) -> Dict[str, float]:
    if not landmarks:
        return {"lookAwayScore": 0.0, "eyeScore": 0.0, "headScore": 0.0, "eyeRaw": 0.0, "headRaw": 0.0}

    left_mag = look_away_mag_for_eye(landmarks, left_eye_idx, left_iris_idx)
    right_mag = look_away_mag_for_eye(landmarks, right_eye_idx, right_iris_idx)
    # Averaging reduces single-eye jitter spikes.
    eye_raw = (float(left_mag) + float(right_mag)) * 0.5
    head_raw = float(head_yaw_proxy(landmarks))
    scores = look_away_scores_from_raw(eye_raw, head_raw)
    return {**scores, "eyeRaw": eye_raw, "headRaw": head_raw}


def update_looking_away_bool(prev: bool, look_away_score: float) -> bool:
    if prev:
        return look_away_score > LOOK_OFF
    return look_away_score > LOOK_ON


def update_heart_bool(prev: bool, heart_score: float, params: Optional[HeartParams] = None) -> bool:
    p = params or HeartParams()
    if prev:
        return float(heart_score) > float(p.off_t)
    return float(heart_score) > float(p.on_t)


def pick_dialog_line(face_present: bool, looking_away: bool, smile: float) -> str:
    if not face_present:
        return "I can't see your face…"
    if looking_away:
        return "Why are you looking away? Are you ignoring me?"
    if smile > 0.55:
        return "You're smiling? I'm angry right now."
    return "Apologize properly."


def pick_dialog_line_with_hand(
    face_present: bool,
    looking_away: bool,
    smile: float,
    hand_present: bool,
    open_palm: bool,
    thumbs_up: bool,
    heart: bool,
) -> str:
    if hand_present:
        if heart:
            return "A heart… Okay. Keep your eyes on me."
        if thumbs_up:
            return "A thumbs up? You think that's enough?"
        if open_palm:
            return "Okay… I hear you. Keep your eyes on me."
    return pick_dialog_line(face_present, looking_away, smile)


@dataclass
class DialogState:
    current: str = "Apologize properly."
    since_ms: float = 0.0
    candidate: Optional[str] = None
    candidate_since_ms: float = 0.0


def update_dialog_stably(now_ms: float, next_line: str, dstate: DialogState) -> str:
    if dstate.current == next_line:
        dstate.candidate = None
        return dstate.current

    if dstate.candidate != next_line:
        dstate.candidate = next_line
        dstate.candidate_since_ms = now_ms
        return dstate.current

    candidate_held = now_ms - dstate.candidate_since_ms
    current_shown = now_ms - dstate.since_ms
    if candidate_held >= DIALOG_HOLD_MS or current_shown >= DIALOG_MIN_SHOW_MS:
        dstate.current = next_line
        dstate.since_ms = now_ms
        dstate.candidate = None
    return dstate.current


# ---------------------------------------------------------------------
# Rendering helpers (OpenCV)
# ---------------------------------------------------------------------


def _to_px(p: Any, w: int, h: int) -> Tuple[int, int]:
    return int(float(p.x) * w), int(float(p.y) * h)


def draw_connections(
    frame_bgr,
    landmarks: Sequence[Any],
    connections: Iterable[Tuple[int, int]],
    color: Tuple[int, int, int],
    thickness: int,
) -> None:
    h, w = frame_bgr.shape[:2]
    for a, b in connections or []:
        pa = safe_point(landmarks, int(a))
        pb = safe_point(landmarks, int(b))
        if pa is None or pb is None:
            continue
        ax, ay = _to_px(pa, w, h)
        bx, by = _to_px(pb, w, h)
        cv2.line(frame_bgr, (ax, ay), (bx, by), color, thickness, cv2.LINE_AA)


def draw_points_by_indices(
    frame_bgr,
    landmarks: Sequence[Any],
    indices: Iterable[int],
    color: Tuple[int, int, int],
    radius: int = 2,
) -> None:
    h, w = frame_bgr.shape[:2]
    for idx in indices:
        p = safe_point(landmarks, int(idx))
        if p is None:
            continue
        x, y = _to_px(p, w, h)
        cv2.circle(frame_bgr, (x, y), int(radius), color, -1, cv2.LINE_AA)


def draw_face_points(frame_bgr, landmarks: Sequence[Any], color: Tuple[int, int, int] = (200, 200, 200)) -> None:
    # Lightweight point cloud (keeps tracker usable without FACEMESH connection tables).
    h, w = frame_bgr.shape[:2]
    for p in landmarks:
        x = getattr(p, "x", None)
        y = getattr(p, "y", None)
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue
        cv2.circle(frame_bgr, (int(float(x) * w), int(float(y) * h)), 1, color, -1, cv2.LINE_AA)


def put_hud_lines(frame_bgr, lines: List[str], origin: Tuple[int, int] = (12, 28)) -> None:
    x, y = origin
    for i, line in enumerate(lines):
        yy = y + i * 22
        cv2.putText(frame_bgr, line, (x, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (10, 10, 10), 3, cv2.LINE_AA)
        cv2.putText(frame_bgr, line, (x, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (245, 245, 245), 1, cv2.LINE_AA)


def put_dialog(frame_bgr, text: str) -> None:
    h, w = frame_bgr.shape[:2]
    pad = 14
    box_h = 64
    y0 = h - box_h - pad
    overlay = frame_bgr.copy()
    cv2.rectangle(overlay, (pad, y0), (w - pad, h - pad), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.45, frame_bgr, 0.55, 0, frame_bgr)

    cv2.putText(
        frame_bgr,
        text,
        (pad + 14, h - pad - 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------


@dataclass
class SmoothedSignals:
    smile: float = 0.0
    sadness: float = 0.0
    look_away_score: float = 0.0
    looking_away: bool = False
    hand_present: bool = False
    open_palm: bool = False
    thumbs_up: bool = False
    heart_score: float = 0.0
    heart: bool = False


@dataclass
class CalibrationState:
    ready: bool = False
    start_ms: float = 0.0
    eye_sum: float = 0.0
    head_sum: float = 0.0
    mouth_sum: float = 0.0
    mouth_down_sum: float = 0.0
    n: int = 0
    eye0: float = 0.0
    head0: float = 0.0
    mouth0: float = 0.0
    mouth_down0: float = 0.0

    def reset(self, now_ms: float) -> None:
        self.ready = False
        self.start_ms = float(now_ms)
        self.eye_sum = 0.0
        self.head_sum = 0.0
        self.mouth_sum = 0.0
        self.mouth_down_sum = 0.0
        self.n = 0
        self.eye0 = 0.0
        self.head0 = 0.0
        self.mouth0 = 0.0
        self.mouth_down0 = 0.0

    def update(self, now_ms: float, eye_raw: float, head_raw: float, mouth_up: float, mouth_down: float) -> None:
        if self.ready:
            return
        if self.start_ms <= 0.0:
            self.reset(now_ms)
        elapsed = float(now_ms) - float(self.start_ms)
        if elapsed < CALIBRATION_WARMUP_MS:
            return
        if elapsed > (CALIBRATION_WARMUP_MS + CALIBRATION_DURATION_MS):
            if self.n > 0:
                self.eye0 = self.eye_sum / float(self.n)
                self.head0 = self.head_sum / float(self.n)
                self.mouth0 = self.mouth_sum / float(self.n)
                self.mouth_down0 = self.mouth_down_sum / float(self.n)
                self.ready = True
            return
        if (
            math.isfinite(eye_raw)
            and math.isfinite(head_raw)
            and math.isfinite(mouth_up)
            and math.isfinite(mouth_down)
        ):
            self.eye_sum += float(eye_raw)
            self.head_sum += float(head_raw)
            self.mouth_sum += float(mouth_up)
            self.mouth_down_sum += float(mouth_down)
            self.n += 1


def _get_face_landmarks(face_result: Any) -> List[List[Any]]:
    v = getattr(face_result, "face_landmarks", None) or getattr(face_result, "faceLandmarks", None)
    return list(v) if v else []


def _get_face_blendshapes(face_result: Any) -> List[Any]:
    v = getattr(face_result, "face_blendshapes", None) or getattr(face_result, "faceBlendshapes", None)
    return list(v) if v else []


def _get_hand_landmarks(hand_result: Any) -> List[List[Any]]:
    for attr in ("hand_landmarks", "handLandmarks", "landmarks", "hand_landmarks_list", "handLandmarksList"):
        v = getattr(hand_result, attr, None)
        if v:
            return list(v)
    return []


def run(args: argparse.Namespace) -> int:
    # NOTE: some environments ship `mediapipe.tasks` without `mp.solutions`.
    # We therefore avoid `mp.solutions.*` and rely on canonical landmark indices.
    left_eye_idx = FACE_LEFT_EYE_IDX
    right_eye_idx = FACE_RIGHT_EYE_IDX
    left_iris_idx = FACE_LEFT_IRIS_IDX
    right_iris_idx = FACE_RIGHT_IRIS_IDX

    models_dir = os.path.join(os.path.dirname(__file__), "models")
    face_model_path = os.path.join(models_dir, "face_landmarker.task")
    hand_model_path = os.path.join(models_dir, "hand_landmarker.task")

    _ensure_file(face_model_path, FACE_MODEL_URL)
    if not args.no_hand:
        _ensure_file(hand_model_path, HAND_MODEL_URL)

    face_options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=face_model_path),
        running_mode=vision.RunningMode.VIDEO,
        output_face_blendshapes=True,
        num_faces=1,
    )
    face_landmarker = vision.FaceLandmarker.create_from_options(face_options)

    hand_landmarker = None
    if not args.no_hand:
        try:
            hand_options = vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=hand_model_path),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=2,
            )
            hand_landmarker = vision.HandLandmarker.create_from_options(hand_options)
        except Exception as e:  # noqa: BLE001
            print("[tracker] HandLandmarker failed to load; continuing without hands.", e, file=sys.stderr)
            hand_landmarker = None

    cam_index = int(args.camera)
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        # macOS often needs explicit AVFoundation backend + camera permission grant.
        try:
            cap.release()
        except Exception:  # noqa: BLE001
            pass
        cap = cv2.VideoCapture(cam_index, cv2.CAP_AVFOUNDATION)

    if not cap.isOpened():
        hint = ""
        if sys.platform == "darwin":
            hint = (
                "\n\nmacOS camera permission hint:\n"
                "- System Settings -> Privacy & Security -> Camera\n"
                "- Enable camera access for the app you run from (Terminal/iTerm/Cursor/VSCode)\n"
                "- Then fully quit & relaunch that app and retry.\n"
            )
        raise RuntimeError(f"Failed to open camera index {cam_index}.{hint}")

    if args.width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(args.width))
    if args.height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(args.height))

    smoothed = SmoothedSignals()
    calib = CalibrationState()
    dialog = DialogState(current="Apologize properly.", since_ms=time.perf_counter() * 1000.0)
    prev_ms = time.perf_counter() * 1000.0

    last_hand_run_ms = 0.0
    hand_interval_ms = float(args.hand_interval_ms)
    cached_hand_result = None

    json_enabled = bool(args.json)
    last_json_ms = 0.0
    json_interval_ms = 1000.0 / max(1.0, float(args.json_rate_hz))

    output_file = getattr(args, "output_file", None)
    screenshot_dir = getattr(args, "screenshot_dir", None)
    screenshot_count = 0
    if screenshot_dir:
        out_dir = os.path.abspath(os.path.expanduser(screenshot_dir))
        if os.path.isdir(out_dir):
            for f in os.listdir(out_dir):
                m = re.match(r"pose_(\d+)\.png", f, re.I)
                if m:
                    screenshot_count = max(screenshot_count, int(m.group(1)))
    last_screenshot_ms = 0.0
    SCREENSHOT_COOLDOWN_MS = 3000.0
    smile_count = 0
    heart_detected_once = False
    gesture = "—"  # fallback if loop exits before assignment
    smile_was_above = False
    SMILE_EVENT_THRESHOLD = 0.50
    SMILE_EVENT_RESET = 0.35
    last_output_write_ms = 0.0
    OUTPUT_WRITE_INTERVAL_MS = 500.0  # write smile_count to file every 0.5s

    debug = bool(args.debug)
    heart_params = heart_params_from_sensitivity(float(getattr(args, "heart_sensitivity", 1.0)))

    window_name = args.window_title
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            ok, frame_bgr = cap.read()
            if not ok or frame_bgr is None:
                break

            if args.mirror:
                frame_bgr = cv2.flip(frame_bgr, 1)

            now_ms = time.perf_counter() * 1000.0
            dt_ms = now_ms - prev_ms
            prev_ms = now_ms

            # Mediapipe Tasks expects SRGB input.
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            timestamp_ms = int(now_ms)

            face_result = face_landmarker.detect_for_video(mp_image, timestamp_ms)

            if hand_landmarker is not None and (now_ms - last_hand_run_ms) >= hand_interval_ms:
                last_hand_run_ms = now_ms
                cached_hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)

            face_landmarks_list = _get_face_landmarks(face_result)
            blendshapes_list = _get_face_blendshapes(face_result)
            hand_landmarks_list = _get_hand_landmarks(cached_hand_result) if cached_hand_result is not None else []

            # Raw signals
            face_present = len(face_landmarks_list) > 0
            hand_present = len(hand_landmarks_list) > 0

            raw_smile = 0.0
            raw_sadness = 0.0
            raw_look_away = 0.0
            dbg_eye_raw = 0.0
            dbg_eye_adj = 0.0
            dbg_left_mag = 0.0
            dbg_right_mag = 0.0
            dbg_lm_n = 0
            dbg_iris_ok = False
            dbg_head_raw = 0.0
            dbg_head_factor = 0.0
            if face_present:
                lm = face_landmarks_list[0]

                # look-away (auto-calibrated)
                dbg_lm_n = len(lm) if lm is not None else 0
                dbg_iris_ok = (safe_point(lm, 468) is not None) and (safe_point(lm, 473) is not None)
                dbg_head_raw = float(head_yaw_proxy(lm))
                dbg_head_factor = clamp01(
                    (dbg_head_raw - HEAD_GUARD_T) / max(1e-6, (HEAD_GUARD_MAX - HEAD_GUARD_T))
                )
                look = compute_look_away_eye_only(lm, left_eye_idx, right_eye_idx, left_iris_idx, right_iris_idx)
                eye_raw = float(look.get("eyeRaw", 0.0))
                dbg_eye_raw = eye_raw
                dbg_left_mag = float(look.get("leftMag", 0.0))
                dbg_right_mag = float(look.get("rightMag", 0.0))
                head_raw = 0.0
                mr_up = mouth_smile_metric(lm)
                mr_down = mouth_sad_metric(lm)
                calib.update(now_ms, eye_raw, head_raw, mr_up, mr_down)

                if calib.ready:
                    eye_adj = max(0.0, eye_raw - calib.eye0)
                    dbg_eye_adj = eye_adj
                    eff_t = LOOK_EYE_DELTA_T + HEAD_DELTA_T_BOOST * float(dbg_head_factor)
                    eff_den = max(1e-6, (LOOK_EYE_DELTA_MAX - eff_t))
                    eye_score_delta = clamp01((float(eye_adj) - float(eff_t)) / float(eff_den))
                    raw_look_away = float(eye_score_delta)
                else:
                    raw_look_away = float(look.get("lookAwayScore", 0.0))

                # If head is turned, dampen the iris-only score (reduces false positives on head turns).
                raw_look_away = float(raw_look_away) * (1.0 - float(HEAD_DAMP) * float(dbg_head_factor))

                # smile: blendshapes if present + geometry fallback
                smile_bs = 0.0
                if blendshapes_list:
                    categories = getattr(blendshapes_list[0], "categories", None) or []
                    cat = blendshapes_to_map(categories)
                    smile_bs = compute_smile(cat)
                smile_geom = compute_smile_geom(lm, baseline=(calib.mouth0 if calib.ready else 0.0))
                geom_w = 1.0 if calib.ready else float(SMILE_GEOM_WEIGHT_PRECALIB)
                raw_smile = max(float(smile_bs), float(smile_geom) * geom_w)
                raw_smile = shape_smile_score(raw_smile)

                # sadness (mouth corners down): blendshapes + geometry fallback
                sad_bs = 0.0
                if blendshapes_list:
                    categories = getattr(blendshapes_list[0], "categories", None) or []
                    cat = blendshapes_to_map(categories)
                    sad_bs = compute_sadness(cat)
                sad_geom = compute_sad_geom(lm, baseline=(calib.mouth_down0 if calib.ready else 0.0))
                sad_w = 1.0 if calib.ready else float(SAD_GEOM_WEIGHT_PRECALIB)
                raw_sad = max(float(sad_bs), float(sad_geom) * sad_w)
                raw_sadness = shape_sadness_score(raw_sad)

            raw_open_palm = False
            raw_thumbs_up = False
            raw_heart_score = 0.0
            if hand_present:
                for hlm in hand_landmarks_list:
                    g = compute_hand_gestures(hlm)
                    raw_open_palm = raw_open_palm or bool(g["openPalm"])
                    raw_thumbs_up = raw_thumbs_up or bool(g["thumbsUp"])
                raw_heart_score = compute_two_hand_heart_score(
                    hand_landmarks_list,
                    params=heart_params,
                    require_both_touch=not bool(getattr(args, "heart_touch_either", False)),
                )

            # Smooth + hysteresis
            a = ema_alpha(dt_ms, SCORE_TAU_MS)
            smoothed.smile = clamp01(smoothed.smile + a * (raw_smile - smoothed.smile))
            smoothed.sadness = clamp01(smoothed.sadness + a * (raw_sadness - smoothed.sadness))

            # Smile event counting (for output_file / Ren'Py integration)
            if output_file:
                if smile_was_above and smoothed.smile < SMILE_EVENT_RESET:
                    smile_was_above = False
                elif not smile_was_above and smoothed.smile >= SMILE_EVENT_THRESHOLD:
                    smile_count += 1
                    smile_was_above = True
            smoothed.look_away_score = clamp01(smoothed.look_away_score + a * (raw_look_away - smoothed.look_away_score))
            smoothed.looking_away = update_looking_away_bool(smoothed.looking_away, smoothed.look_away_score)
            smoothed.hand_present = bool(hand_present)
            smoothed.open_palm = bool(hand_present and raw_open_palm)
            smoothed.thumbs_up = bool(hand_present and raw_thumbs_up)
            smoothed.heart_score = clamp01(smoothed.heart_score + a * (float(raw_heart_score) - smoothed.heart_score))
            smoothed.heart = bool(hand_present and update_heart_bool(smoothed.heart, smoothed.heart_score, params=heart_params))
            if smoothed.heart:
                heart_detected_once = True

            next_dialog = pick_dialog_line_with_hand(
                face_present,
                smoothed.looking_away,
                smoothed.smile,
                smoothed.hand_present,
                smoothed.open_palm,
                smoothed.thumbs_up,
                smoothed.heart,
            )
            dialog_line = update_dialog_stably(now_ms, next_dialog, dialog)

            # Capture raw frame before any overlay (no HUD, no face mesh, no hand lines)
            capture_frame = frame_bgr.copy() if screenshot_dir else None

            # Drawing
            if args.draw_face and face_present:
                for lm in face_landmarks_list:
                    draw_face_points(frame_bgr, lm, (200, 200, 200))
                    draw_points_by_indices(frame_bgr, lm, right_eye_idx, (48, 48, 255), radius=2)
                    draw_points_by_indices(frame_bgr, lm, left_eye_idx, (48, 255, 48), radius=2)
                    draw_points_by_indices(frame_bgr, lm, right_iris_idx, (0, 0, 255), radius=3)
                    draw_points_by_indices(frame_bgr, lm, left_iris_idx, (0, 255, 0), radius=3)

            if args.draw_hand and hand_present:
                for hlm in hand_landmarks_list:
                    draw_connections(frame_bgr, hlm, HAND_CONNECTIONS, (255, 209, 0), 2)

            gesture = "—"
            if smoothed.heart:
                gesture = "TWO_HAND_HEART"
            elif smoothed.thumbs_up:
                gesture = "THUMBS_UP"
            elif smoothed.open_palm:
                gesture = "OPEN_PALM"

            # Auto-capture on "funny" poses (with cooldown)
            if (
                screenshot_dir
                and capture_frame is not None
                and (now_ms - last_screenshot_ms) >= SCREENSHOT_COOLDOWN_MS
            ):
                funny = (
                    (smoothed.look_away_score > 0.7 and gesture != "—")
                    or smoothed.smile > 0.85
                    or smoothed.sadness > 0.8
                )
                if funny:
                    try:
                        out_dir = os.path.abspath(os.path.expanduser(screenshot_dir))
                        os.makedirs(out_dir, exist_ok=True)
                        screenshot_count += 1
                        path = os.path.join(out_dir, f"pose_{screenshot_count:03d}.png")
                        if cv2.imwrite(path, capture_frame):
                            last_screenshot_ms = now_ms
                            print(f"[tracker] Screenshot: {path}", file=sys.stderr)
                    except Exception as e:  # noqa: BLE001
                        print(f"[tracker] Screenshot failed: {e}", file=sys.stderr)

            hud_lines = [
                f"Smile: {smoothed.smile:.2f}" + (f"  Events: {smile_count}" if output_file else ""),
                f"Sad: {smoothed.sadness:.2f}",
                f"LookAway: {smoothed.look_away_score:.2f}  LookingAway: {'YES' if smoothed.looking_away else 'NO'}",
                f"Hand: {'YES' if smoothed.hand_present else 'NO'}  Gesture: {gesture}  Heart: {smoothed.heart_score:.2f}",
            ]
            if debug:
                hud_lines.append(
                    f"Calib: {'READY' if calib.ready else '...'}  eye0={calib.eye0:.3f} head0={calib.head0:.3f} mouthUp0={calib.mouth0:.2f} mouthDown0={calib.mouth_down0:.2f}"
                )
                hud_lines.append(
                    f"EyeRaw: {dbg_eye_raw:.3f}  EyeAdj: {dbg_eye_adj:.3f}  L/R: {dbg_left_mag:.3f}/{dbg_right_mag:.3f}  LM:{dbg_lm_n}  IrisOK:{'Y' if dbg_iris_ok else 'N'}"
                )
                hud_lines.append(f"HeadRaw: {dbg_head_raw:.3f}  HeadFactor: {dbg_head_factor:.2f}")
                hud_lines.append(f"JSON: {'ON' if json_enabled else 'OFF'}  (toggle: j)   Debug: ON (toggle: d)")
                hud_lines.append("Quit: q/esc   Recalibrate: c")
            put_hud_lines(frame_bgr, hud_lines)
            put_dialog(frame_bgr, dialog_line)

            # Periodic write of smile_count to output file (so Ren'Py can read after pkill)
            if output_file and (now_ms - last_output_write_ms) >= OUTPUT_WRITE_INTERVAL_MS:
                last_output_write_ms = now_ms
                try:
                    out_path = os.path.abspath(os.path.expanduser(output_file))
                    out_dir = os.path.dirname(out_path)
                    if out_dir:
                        os.makedirs(out_dir, exist_ok=True)
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "smile_count": smile_count,
                            "heart_detected": heart_detected_once,
                            "gesture": gesture,
                            "smile": round(smoothed.smile, 4),
                            "lookAway": round(smoothed.look_away_score, 4),
                            "sadness": round(smoothed.sadness, 4),
                        }, f, ensure_ascii=False)
                except Exception:  # noqa: BLE001
                    pass

            # Optional JSON Lines (for Ren'Py later)
            if json_enabled and (now_ms - last_json_ms) >= json_interval_ms:
                last_json_ms = now_ms
                payload = {
                    "ts": round(now_ms / 1000.0, 6),
                    "smile": round(smoothed.smile, 4),
                    "sadness": round(smoothed.sadness, 4),
                    "lookAway": round(smoothed.look_away_score, 4),
                    "lookingAway": bool(smoothed.looking_away),
                    "handPresent": bool(smoothed.hand_present),
                    "gesture": gesture,
                    "heartScore": round(smoothed.heart_score, 4),
                    "heart": bool(smoothed.heart),
                    "dialog": dialog_line,
                }
                sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
                sys.stdout.flush()

            # Display at 25% size (both apology "Talk to her" and grab_one_last_chance use this)
            display_frame = cv2.resize(frame_bgr, None, fx=0.4, fy=0.4, interpolation=cv2.INTER_LINEAR)
            cv2.imshow(window_name, display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            if key == ord("d"):
                debug = not debug
            if key == ord("j"):
                json_enabled = not json_enabled
            if key == ord("c"):
                calib.reset(now_ms)
            if key == ord("s") and screenshot_dir and capture_frame is not None:
                try:
                    out_dir = os.path.abspath(os.path.expanduser(screenshot_dir))
                    os.makedirs(out_dir, exist_ok=True)
                    screenshot_count += 1
                    path = os.path.join(out_dir, f"pose_{screenshot_count:03d}.png")
                    if cv2.imwrite(path, capture_frame):
                        last_screenshot_ms = now_ms
                        print(f"[tracker] Screenshot (s): {path}", file=sys.stderr)
                except Exception as e:  # noqa: BLE001
                    print(f"[tracker] Screenshot failed: {e}", file=sys.stderr)

    finally:
        if output_file:
            try:
                out_path = os.path.abspath(os.path.expanduser(output_file))
                out_dir = os.path.dirname(out_path)
                if out_dir:
                    os.makedirs(out_dir, exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "smile_count": smile_count,
                        "heart_detected": heart_detected_once,
                        "gesture": gesture,
                        "smile": round(smoothed.smile, 4),
                        "lookAway": round(smoothed.look_away_score, 4),
                        "sadness": round(smoothed.sadness, 4),
                    }, f, ensure_ascii=False)
            except Exception as e:  # noqa: BLE001
                print(f"[tracker] Failed to write output file: {e}", file=sys.stderr)
        cap.release()
        cv2.destroyAllWindows()
        try:
            face_landmarker.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            if hand_landmarker is not None:
                hand_landmarker.close()
        except Exception:  # noqa: BLE001
            pass

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Camera tracker (MediaPipe) with HUD + optional JSON output.")
    p.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    p.add_argument("--width", type=int, default=0, help="Requested capture width (optional)")
    p.add_argument("--height", type=int, default=0, help="Requested capture height (optional)")
    p.add_argument("--mirror", action="store_true", default=True, help="Mirror preview (default: on)")
    p.add_argument("--no-mirror", dest="mirror", action="store_false", help="Disable mirror preview")

    p.add_argument("--no-hand", action="store_true", help="Disable hand tracking entirely")
    p.add_argument("--hand-interval-ms", type=float, default=80.0, help="Hand inference interval (default: 80ms)")
    p.add_argument(
        "--heart-sensitivity",
        type=float,
        default=1.25,
        help="Two-hand heart sensitivity (default: 1.25; higher = easier, lower = stricter)",
    )
    p.add_argument(
        "--heart-touch-either",
        action="store_true",
        default=False,
        help="Less strict: accept heart if fingertip clusters OR any cross-fingertips touch (default: require BOTH)",
    )

    p.add_argument("--draw-face", action="store_true", default=True, help="Draw face mesh (default: on)")
    p.add_argument("--no-draw-face", dest="draw_face", action="store_false", help="Disable face drawing")
    p.add_argument("--draw-hand", action="store_true", default=True, help="Draw hand connections (default: on)")
    p.add_argument("--no-draw-hand", dest="draw_hand", action="store_false", help="Disable hand drawing")

    p.add_argument("--json", action="store_true", help="Print JSON Lines to stdout (Ren'Py sidecar integration)")
    p.add_argument("--json-rate-hz", type=float, default=12.5, help="JSON output rate (default: 12.5Hz)")
    p.add_argument(
        "--output-file",
        type=str,
        default=None,
        metavar="PATH",
        help="Write smile_count JSON to file on exit (for Ren'Py)",
    )
    p.add_argument(
        "--screenshot-dir",
        type=str,
        default=None,
        metavar="PATH",
        help="Directory to save pose screenshots (no HUD); auto + manual (s key)",
    )

    p.add_argument("--debug", action="store_true", default=False, help="Show extra HUD/debug help")
    p.add_argument("--window-title", type=str, default="FaceMotion Tracker", help="OpenCV window title")
    return p


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()


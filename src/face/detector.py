"""face.detector — Detection + embedding via InsightFace (primary) with OpenCV Haar fallback."""

from __future__ import annotations

import contextlib
import io
import logging
import os
import warnings
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Data structures ──────────────────────────────────────────


@dataclass
class FaceBox:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float


@dataclass
class DetectedFace:
    bbox: FaceBox
    embedding: np.ndarray  # L2-normalised, 512-D for ArcFace / fallback 128-D
    det_score: float


# ── InsightFace backend ─────────────────────────────────────

_INSIGHT_APP = None  # lazy singleton
_INSIGHT_READY = False
_INSIGHT_ERROR: str | None = None


def _get_insight_model(det_size: int = 640, model_pack: str = "buffalo_l"):
    """Lazy-load InsightFace FaceAnalysis. Returns None if unavailable."""
    global _INSIGHT_APP, _INSIGHT_READY, _INSIGHT_ERROR
    if _INSIGHT_READY:
        return _INSIGHT_APP
    if _INSIGHT_ERROR is not None:
        return None
    try:
        warnings.filterwarnings("ignore", category=FutureWarning)  # insightface's skimage 'estimate' notice
        with contextlib.redirect_stdout(io.StringIO()):  # silence insightface's model-loading prints
            from insightface.app import FaceAnalysis

            app = FaceAnalysis(name=model_pack, providers=["CPUExecutionProvider"])  # CPU only
            app.prepare(ctx_id=0, det_size=(det_size, det_size))
        _INSIGHT_APP = app
        _INSIGHT_READY = True
        logger.info("InsightFace '%s' loaded (det_size=%d)", model_pack, det_size)
        return app
    except Exception as exc:  # noqa: BLE001
        _INSIGHT_ERROR = str(exc)
        logger.warning("InsightFace unavailable: %s — falling back to OpenCV", exc)
        return None


def _insight_detect(image_bgr: np.ndarray, det_size: int = 640, model_pack: str = "buffalo_l") -> list[DetectedFace] | None:
    app = _get_insight_model(det_size=det_size, model_pack=model_pack)
    if app is None:
        return None
    try:
        faces = app.get(image_bgr)
    except Exception as exc:  # noqa: BLE001
        logger.warning("InsightFace.get() failed: %s", exc)
        return None
    out: list[DetectedFace] = []
    for f in faces:
        # InsightFace bbox is [x1, y1, x2, y2]
        x1, y1, x2, y2 = [int(v) for v in f.bbox]
        # normed embedding already L2-normalised by insightface
        emb = np.array(f.normed_embedding, dtype=np.float32)
        # alternative: f.embedding (unnormalised) — we use normed
        out.append(
            DetectedFace(
                bbox=FaceBox(x1=x1, y1=y1, x2=x2, y2=y2, confidence=float(f.det_score)),
                embedding=emb,
                det_score=float(f.det_score),
            )
        )
    return out


# ── OpenCV Haar fallback ────────────────────────────────────

_HAAR = None


def _get_haar():
    global _HAAR
    if _HAAR is not None:
        return _HAAR
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if not os.path.exists(cascade_path):
        return None
    _HAAR = cv2.CascadeClassifier(cascade_path)
    return _HAAR


def _opencv_detect(image_bgr: np.ndarray) -> list[DetectedFace]:
    """Fallback: Haar detection + simple embedding (grayscale histogram + resize).
    Produces a 128-D pseudo-embedding that still supports cosine similarity
    for structural comparisons in tests. For real matching InsightFace is required.
    """
    haar = _get_haar()
    if haar is None:
        return []
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.equalizeHist(gray)
    rects = haar.detectMultiScale(gray_eq, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    faces: list[DetectedFace] = []
    for x, y, w, h in rects:
        # pseudo-embedding: resize face crop to 32x32, flatten, L2-norm → 1024-D then PCA-ish down to 128 by averaging
        crop = gray[y : y + h, x : x + w]
        if crop.size == 0:
            continue
        resized = cv2.resize(crop, (32, 32), interpolation=cv2.INTER_AREA)
        # normalise 0-1, flatten, L2
        vec = resized.astype(np.float32).flatten() / 255.0
        # reduce to 128-D by block averaging (1024 -> 128, block 8)
        vec128 = vec.reshape(128, 8).mean(axis=1)
        # L2 normalise
        n = np.linalg.norm(vec128)
        if n > 1e-9:
            vec128 = vec128 / n
        # expand to 512-D for cosine compat by tiling? keep 128 but matcher handles mixed dims
        # For consistency pad to 512 with zeros
        emb512 = np.zeros(512, dtype=np.float32)
        emb512[:128] = vec128
        # re-normalise
        n2 = np.linalg.norm(emb512)
        if n2 > 1e-9:
            emb512 = emb512 / n2
        faces.append(
            DetectedFace(
                bbox=FaceBox(x1=int(x), y1=int(y), x2=int(x + w), y2=int(y + h), confidence=0.99),
                embedding=emb512,
                det_score=0.99,
            )
        )
    return faces


# ── Public API ──────────────────────────────────────────────


def detect_faces(
    image_path: str | os.PathLike,
    det_size: int = 640,
    model_pack: str = "buffalo_l",
) -> list[DetectedFace]:
    """Detect faces in image_path. Tries InsightFace first, falls back to OpenCV Haar.

    Raises:
        FileNotFoundError: if image_path missing
        ValueError: if image unreadable / no face found (caller may handle) — we return [] instead.
    """
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {p}")
    if p.stat().st_size == 0:
        raise ValueError(f"Image file is empty: {p}")
    # validate extension
    if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        # still attempt to read; warn
        logger.warning("Uncommon image extension: %s", p.suffix)

    image_bgr = cv2.imread(str(p))
    if image_bgr is None:
        raise ValueError(f"Unable to read image (unsupported or corrupt): {p}")

    # Try InsightFace
    faces = _insight_detect(image_bgr, det_size=det_size, model_pack=model_pack)
    if faces is not None:
        # InsightFace returns [] when no face — that's a valid result
        backend = "insightface"
    else:
        faces = _opencv_detect(image_bgr)
        backend = "opencv-haar (fallback)"

    logger.debug("detect_faces backend=%s faces=%d path=%s", backend, len(faces), p)
    return faces


def largest_face(faces: list[DetectedFace]) -> DetectedFace | None:
    if not faces:
        return None

    def area(f: DetectedFace) -> int:
        b = f.bbox
        return (b.x2 - b.x1) * (b.y2 - b.y1)

    return max(faces, key=area)


def is_insightface_available() -> bool:
    return _get_insight_model() is not None

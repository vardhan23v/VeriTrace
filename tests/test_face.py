"""tests/test_face.py — face module tests (no real InsightFace model needed)."""

import tempfile

import cv2
import numpy as np
import pytest


def _make_blank_image(path: str, w=320, h=320, color=(128, 128, 128)):
    img = np.full((h, w, 3), color, dtype=np.uint8)
    cv2.imwrite(path, img)
    return path


def _make_face_like_image(path: str):
    """Create a cartoon face that Haar may or may not detect — for valid-input test.
    We draw a circle face + eyes + mouth. Haar often detects this.
    """
    img = np.full((400, 400, 3), 255, dtype=np.uint8)
    # face oval
    cv2.ellipse(img, (200, 200), (120, 140), 0, 0, 360, (220, 180, 160), -1)
    # eyes
    cv2.circle(img, (160, 170), 18, (40, 40, 40), -1)
    cv2.circle(img, (240, 170), 18, (40, 40, 40), -1)
    cv2.circle(img, (160, 170), 6, (255, 255, 255), -1)
    cv2.circle(img, (240, 170), 6, (255, 255, 255), -1)
    # mouth
    cv2.ellipse(img, (200, 240), (40, 20), 0, 0, 180, (80, 20, 20), 6)
    # nose
    cv2.line(img, (200, 190), (190, 220), (180, 120, 100), 3)
    cv2.line(img, (190, 220), (210, 220), (180, 120, 100), 3)
    cv2.imwrite(path, img)
    return path


def test_invalid_image_raises():
    from src.face.detector import detect_faces

    with pytest.raises(FileNotFoundError):
        detect_faces("/nonexistent/path.jpg")

    # empty file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        tf.write(b"")
        tf.flush()
        with pytest.raises((ValueError, FileNotFoundError)):
            detect_faces(tf.name)


def test_no_face_blank_image_returns_empty():
    from src.face.detector import detect_faces

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        _make_blank_image(tf.name)
        faces = detect_faces(tf.name)
        # Blank image should have 0 faces
        assert faces == []


def test_valid_image_returns_list():
    from src.face.detector import detect_faces

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        _make_face_like_image(tf.name)
        faces = detect_faces(tf.name)
        # Cartoon face may be 0 or 1 depending on Haar threshold — but should not crash
        assert isinstance(faces, list)


def test_matcher_cosine():
    from src.face.matcher import cosine_similarity

    a = np.array([1, 0, 0], dtype=np.float32)
    b = np.array([1, 0, 0], dtype=np.float32)
    c = np.array([0, 1, 0], dtype=np.float32)
    # normalise
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    c = c / np.linalg.norm(c)

    assert cosine_similarity(a, b) == pytest.approx(1.0)
    assert cosine_similarity(a, c) == pytest.approx(0.0)
    assert cosine_similarity(a, -a) == pytest.approx(-1.0)


def test_largest_face():
    import numpy as np

    from src.face.detector import DetectedFace, FaceBox, largest_face

    def mk(x1, y1, x2, y2):
        return DetectedFace(bbox=FaceBox(x1, y1, x2, y2, 0.9), embedding=np.zeros(512, dtype=np.float32), det_score=0.9)

    f1 = mk(0, 0, 100, 100)  # area 10k
    f2 = mk(0, 0, 200, 200)  # area 40k
    assert largest_face([f1, f2]) is f2
    assert largest_face([]) is None


def test_is_match_threshold():
    from src.face.matcher import is_match

    assert is_match(0.9, threshold=0.6) is True
    assert is_match(0.5, threshold=0.6) is False
    assert is_match(0.6, threshold=0.6) is True

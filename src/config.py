"""src.config — central configuration from environment."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root if present
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env.local", override=False)


class Config:
    # Search
    SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "auto")
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    BING_API_KEY: str = os.getenv("BING_API_KEY", "")
    SEARCH_MAX_RESULTS: int = int(os.getenv("SEARCH_MAX_RESULTS", "10"))
    INPUT_IMAGE_URL: str = os.getenv("INPUT_IMAGE_URL", "")
    # Comma-separated substrings; any result whose domain contains one is dropped before evaluation.
    SEARCH_DOMAIN_BLOCKLIST: list[str] = [
        s.strip().lower()
        for s in os.getenv("SEARCH_DOMAIN_BLOCKLIST", "porn,xxx,sex,nude,naked,adult,escort").split(",")
        if s.strip()
    ]
    PREFER_SOCIAL: bool = os.getenv("PREFER_SOCIAL", "true").lower() in ("1", "true", "yes")
    # Ranking bonus added to the similarity of social-media candidates that already pass the
    # threshold, so a confident Instagram/Pinterest match beats a marginally higher blog match.
    SOCIAL_BONUS: float = float(os.getenv("SOCIAL_BONUS", "0.05"))

    # Face
    FACE_SIMILARITY_THRESHOLD: float = float(os.getenv("FACE_SIMILARITY_THRESHOLD", "0.60"))
    FACE_DETECTION_SIZE: int = int(os.getenv("FACE_DETECTION_SIZE", "640"))
    FACE_MODEL: str = os.getenv("FACE_MODEL", "buffalo_l")

    # Blockchain
    RPC_URL: str = os.getenv("RPC_URL", "")
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")
    CHAIN_ID: int = int(os.getenv("CHAIN_ID", "31337"))

    # Pipeline
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def data_dir(cls) -> Path:
        p = Path(cls.DATA_DIR)
        if not p.is_absolute():
            # resolve relative to project root (one level above src)
            p = (Path(__file__).resolve().parents[1] / p).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def records_dir(cls) -> Path:
        d = cls.data_dir() / "records"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @classmethod
    def candidates_dir(cls) -> Path:
        d = cls.data_dir() / "candidates"
        d.mkdir(parents=True, exist_ok=True)
        return d

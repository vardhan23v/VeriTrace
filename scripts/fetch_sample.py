#!/usr/bin/env python3
"""scripts/fetch_sample.py — download a public-domain portrait to use as a demo input.

The bundled samples/input.jpg (OpenCV "Lena") works, but it is a 1972 magazine crop that
reverse-image search associates with adult sites. For a cleaner recording use a public-domain
portrait of a public figure hosted on Wikimedia Commons — reverse search then lands on
Wikipedia / museum / news pages.

Usage:
    python scripts/fetch_sample.py                 # downloads samples/lincoln.jpg
    python scripts/fetch_sample.py --name curie    # samples/curie.jpg
Then:
    python main.py demo --image samples/lincoln.jpg --image-url <printed URL>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"

# Public-domain works (photographers died >100 years ago / US government works).
PORTRAITS = {
    "lincoln": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Abraham_Lincoln_O-77_matte_collodion_print.jpg/800px-Abraham_Lincoln_O-77_matte_collodion_print.jpg",
    "curie": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Marie_Curie_c._1920s.jpg/800px-Marie_Curie_c._1920s.jpg",
    "einstein": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Albert_Einstein_Head.jpg/800px-Albert_Einstein_Head.jpg",
    "tesla": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/Tesla_circa_1890.jpeg/800px-Tesla_circa_1890.jpeg",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", choices=sorted(PORTRAITS), default="lincoln")
    ap.add_argument("--url", default=None, help="Any direct image URL (overrides --name)")
    ap.add_argument("--out", default=None, help="Output path (default samples/<name>.jpg)")
    args = ap.parse_args()

    url = args.url or PORTRAITS[args.name]
    out = Path(args.out) if args.out else SAMPLES / f"{args.name}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)

    # Wikimedia only serves a fixed set of thumbnail widths; try a few, then the original file.
    attempts = [url]
    if "/thumb/" in url:
        base = url.rsplit("/", 1)[0]
        name = url.rsplit("/", 1)[1].split("px-", 1)[-1]
        attempts = [f"{base}/{w}px-{name}" for w in (960, 500, 1280)] + [base.replace("/thumb/", "/")]

    r = None
    for candidate in attempts:
        print(f"Downloading {candidate}")
        r = requests.get(candidate, headers={"User-Agent": "VeriTrace/1.0 (demo sample fetch)"}, timeout=60)
        if r.ok and r.headers.get("Content-Type", "").startswith("image/"):
            url = candidate
            break
        print(f"  … HTTP {r.status_code}, trying next size")
    if r is None or not r.ok:
        print("✗ Could not download the sample image", file=sys.stderr)
        return 1
    out.write_bytes(r.content)
    print(f"✓ Saved {out} ({len(r.content) / 1024:.0f} KB)")
    print("\nRun the demo with the public URL so the search can skip the upload step:")
    print(f"  python main.py demo --image {out.relative_to(ROOT)} --image-url {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

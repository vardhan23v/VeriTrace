#!/usr/bin/env python3
"""VeriTrace CLI — face → reverse-image web search → face match → SHA-256 → blockchain → verify.

python main.py identify --image samples/input.jpg [--image-url URL] [--provider yandex] [--threshold 0.45]
python main.py verify   --record latest [--refetch] [--json]
python main.py tamper   --record latest [--field caption --value "edited"]
python main.py demo     --image samples/input.jpg        # identify → verify → tamper → verify
python main.py list
python main.py deploy   [--rpc http://127.0.0.1:8545]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import Config  # noqa: E402

try:
    from rich.console import Console
    from rich.logging import RichHandler

    _console = Console(stderr=True)
    _RICH = True
except ImportError:  # pragma: no cover
    _RICH = False


def setup_logging(level: str = "INFO") -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    if _RICH:
        logging.basicConfig(
            level=lvl, handlers=[RichHandler(console=_console, show_time=False, show_path=False)], format="%(message)s"
        )
    else:
        logging.basicConfig(level=lvl, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("urllib3", "web3", "insightface", "onnxruntime"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _fail(msg: str, code: int) -> int:
    print(f"\n✗ {msg}", file=sys.stderr)
    return code


# ── commands ─────────────────────────────────────────────────────────


def cmd_identify(args) -> int:
    from src.pipeline import identify_pipeline

    try:
        record = identify_pipeline(
            image_path=args.image,
            threshold=args.threshold,
            max_results=args.max_results,
            search_provider=args.provider,
            image_url=args.image_url,
            verbose=not args.json,
        )
        if args.json:
            print(json.dumps(record, indent=2))
        return 0
    except FileNotFoundError as e:
        return _fail(f"Error: {e}", 2)
    except ValueError as e:
        return _fail(f"Input error: {e}", 2)
    except RuntimeError as e:
        if args.debug:
            traceback.print_exc()
        return _fail(f"Pipeline error: {e}", 3)


def cmd_verify(args) -> int:
    from src.pipeline import verify_pipeline

    try:
        result = verify_pipeline(record_id=args.record, refetch=args.refetch, verbose=not args.json)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        return 0 if result["verified"] else 4
    except FileNotFoundError as e:
        return _fail(f"Error: {e}", 2)
    except Exception as e:  # noqa: BLE001
        if args.debug:
            traceback.print_exc()
        return _fail(f"Verification error: {e}", 1)


def cmd_tamper(args) -> int:
    from src.pipeline import tamper_record

    try:
        dst = tamper_record(args.record, field=args.field, value=args.value, out_id=args.out)
    except (FileNotFoundError, ValueError) as e:
        return _fail(str(e), 2)
    rec = json.loads(dst.read_text())
    tn = rec["tamper_note"]
    print(f"✎ Wrote tampered copy: {dst}")
    print(f"  field '{tn['field']}': {tn['original']!r} → {tn['modified']!r}")
    print(f"  Verify it with: python main.py verify --record {rec['record_id']}   (expect ✗ TAMPERED)")
    return 0


def cmd_list(args) -> int:
    from src.pipeline import list_records

    recs = list_records()
    if not recs:
        print("No records yet. Run: python main.py identify --image samples/input.jpg")
        return 0
    print(f"{'RECORD':<20} {'SIMILARITY':>10}  {'PLATFORM':<18} {'TX':<14} URL")
    for r in recs:
        sim = f"{r['similarity'] * 100:.1f}%" if isinstance(r.get("similarity"), (int, float)) else "-"
        tx = (r.get("tx_hash") or "")[:12]
        print(f"{r['record_id']:<20} {sim:>10}  {r['platform'][:18]:<18} {tx:<14} {r['post_url'][:60]}")
    return 0


def cmd_deploy(args) -> int:
    from src.blockchain.client import VerificationRegistryClient, get_web3

    w3 = get_web3(rpc_url=args.rpc or None)
    client = VerificationRegistryClient(w3)
    addr = client.deploy(private_key=args.private_key or Config.PRIVATE_KEY or None)
    info = client.chain_info()
    print(f"\n✓ VerificationRegistry deployed at: {addr}")
    print(f"  Chain ID  : {info['chain_id']}   provider: {info['provider']}")
    print(f"  Cached in : data/blockchain.json  (or set CONTRACT_ADDRESS={addr} in .env)")
    if info["ephemeral"]:
        print("  ! In-memory chain: this deployment disappears when the process exits.")
    return 0


def cmd_demo(args) -> int:
    """identify → verify (VERIFIED) → tamper → verify (TAMPERED), sharing one chain connection."""
    from src.blockchain.client import get_web3
    from src.pipeline import identify_pipeline, tamper_record, verify_pipeline

    w3 = get_web3()
    try:
        record = identify_pipeline(
            image_path=args.image,
            threshold=args.threshold,
            max_results=args.max_results,
            search_provider=args.provider,
            image_url=args.image_url,
            w3=w3,
            verbose=True,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        if args.debug:
            traceback.print_exc()
        return _fail(f"identify failed: {e}", 3)
    rid = record["record_id"]

    print("\n\n>>> STEP A — verify the untouched record (expect VERIFIED)\n")
    ok = verify_pipeline(rid, refetch=args.refetch, w3=w3, verbose=True)

    print("\n\n>>> STEP B — tamper with one field of the record\n")
    dst = tamper_record(rid, field=args.field, value=args.value)
    tn = json.loads(dst.read_text())["tamper_note"]
    print(f"✎ {dst.name}: '{tn['field']}' {tn['original']!r} → {tn['modified']!r}")

    print("\n\n>>> STEP C — verify the tampered record (expect TAMPERED)\n")
    bad = verify_pipeline(dst.stem, w3=w3, verbose=True)

    print("\n\nSUMMARY")
    print(f"  original : {ok['status']}   {ok['current_hash']}")
    print(f"  tampered : {bad['status']}   {bad['current_hash']}")
    return 0 if (ok["verified"] and not bad["verified"]) else 5


# ── parser ───────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="veritrace",
        description="VeriTrace — Face Identification → Web Discovery → Blockchain Verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n", 2)[2],
    )
    p.add_argument("--debug", action="store_true", help="print full tracebacks on error")
    sub = p.add_subparsers(dest="command", required=True)

    def add_identify_args(sp):
        sp.add_argument("--image", required=True, help="Path to the input face image (jpg/png/webp)")
        sp.add_argument(
            "--image-url",
            dest="image_url",
            default=None,
            help="Public URL of the same image (skips upload; e.g. a Wikimedia/GitHub raw link)",
        )
        sp.add_argument("--provider", default=None, help="auto | yandex | serpapi | bing | bing_scrape")
        sp.add_argument(
            "--threshold", type=float, default=None, help="Face similarity threshold (default $FACE_SIMILARITY_THRESHOLD)"
        )
        sp.add_argument("--max-results", type=int, dest="max_results", default=None, help="Max search results to evaluate")

    pi = sub.add_parser("identify", help="Run the full pipeline on a face image")
    add_identify_args(pi)
    pi.add_argument("--json", action="store_true", help="Print the record as JSON instead of the console trace")
    pi.set_defaults(func=cmd_identify)

    pv = sub.add_parser("verify", help="Re-hash a record and check it against the blockchain")
    pv.add_argument("--record", required=True, help="Record ID, 'latest', or path to a record JSON")
    pv.add_argument("--refetch", action="store_true", help="Re-download the matched image from the web and hash live bytes")
    pv.add_argument("--json", action="store_true", help="Machine-readable output")
    pv.set_defaults(func=cmd_verify)

    pt = sub.add_parser("tamper", help="Write a modified copy of a record to demonstrate tamper detection")
    pt.add_argument("--record", required=True, help="Record ID or 'latest'")
    pt.add_argument("--field", default="caption", help="Canonical field to modify (default: caption)")
    pt.add_argument("--value", default=None, help="New value (default: append ' [edited]')")
    pt.add_argument("--out", default=None, help="ID for the tampered record (default: <id>-tampered)")
    pt.set_defaults(func=cmd_tamper)

    pl = sub.add_parser("list", help="List stored records")
    pl.set_defaults(func=cmd_list)

    pd = sub.add_parser("deploy", help="Deploy the VerificationRegistry contract")
    pd.add_argument("--rpc", default=None, help="RPC URL (default: $RPC_URL or eth-tester)")
    pd.add_argument("--private-key", default=None, help="Deployer private key (external chains)")
    pd.set_defaults(func=cmd_deploy)

    pm = sub.add_parser("demo", help="identify → verify → tamper → verify, end to end (for the screen recording)")
    add_identify_args(pm)
    pm.add_argument("--refetch", action="store_true", help="Also re-download the matched image during verification")
    pm.add_argument("--field", default="caption", help="Field to tamper (default: caption)")
    pm.add_argument("--value", default=None, help="Tampered value")
    pm.set_defaults(func=cmd_demo)
    return p


def main() -> None:
    args = build_parser().parse_args()
    setup_logging("DEBUG" if args.debug else Config.LOG_LEVEL)
    try:
        sys.exit(args.func(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()

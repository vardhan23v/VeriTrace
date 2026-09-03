#!/usr/bin/env python3
"""main.py — VeriTrace CLI

Commands:
  python main.py identify --image <path> [--threshold 0.6] [--provider bing_scrape]
  python main.py verify   --record <record_id | latest | path.json>
  python main.py deploy
  python main.py --help
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path

# Ensure src on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import Config

try:
    from rich.console import Console
    from rich.logging import RichHandler
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None


def setup_logging(level: str = "INFO"):
    lvl = getattr(logging, level.upper(), logging.INFO)
    if RICH:
        logging.basicConfig(level=lvl, handlers=[RichHandler(console=console, show_time=False)], format="%(message)s")
    else:
        logging.basicConfig(level=lvl, format="%(levelname)s %(name)s: %(message)s")


def cmd_identify(args):
    from src.pipeline import identify_pipeline

    try:
        record = identify_pipeline(
            image_path=args.image,
            threshold=args.threshold,
            max_results=args.max_results,
            search_provider=args.provider,
            verbose=True,
        )
        return 0
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"\n✗ Input error: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"\n✗ Pipeline error: {e}", file=sys.stderr)
        # Uncomment for debugging:
        # traceback.print_exc()
        return 3
    except Exception as e:  # noqa: BLE001
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


def cmd_verify(args):
    from src.pipeline import verify_pipeline

    try:
        result = verify_pipeline(record_id=args.record, verbose=True)
        return 0 if result["verified"] else 4
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"\n✗ Verification error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


def cmd_deploy(args):
    from src.blockchain.client import get_web3, VerificationRegistryClient

    w3 = get_web3(rpc_url=args.rpc or None)
    client = VerificationRegistryClient(w3)
    addr = client.ensure_deployed(private_key=args.private_key or Config.PRIVATE_KEY or None)
    print(f"\n✓ Contract deployed at: {addr}")
    print(f"  Chain ID: {w3.eth.chain_id}")
    print(f"  Set in .env: CONTRACT_ADDRESS={addr}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="veritrace",
        description="VeriTrace — Face Identification → Web Discovery → Blockchain Verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python main.py identify --image ./samples/input.jpg
  python main.py identify --image ./samples/input.jpg --threshold 0.65 --provider serpapi
  python main.py verify --record abc12345
  python main.py verify --record latest
  python main.py verify --record ./data/records/abc12345.json
  python main.py deploy --rpc http://127.0.0.1:8545
        """,
    )
    sub = p.add_subparsers(dest="command", required=True)

    # identify
    pi = sub.add_parser("identify", help="Run full pipeline from face image")
    pi.add_argument("--image", required=True, help="Path to input face image (jpg/png/webp)")
    pi.add_argument("--threshold", type=float, default=None, help="Face similarity threshold (default: $FACE_SIMILARITY_THRESHOLD or 0.60)")
    pi.add_argument("--max-results", type=int, default=None, dest="max_results", help="Max candidate results (default: 10)")
    pi.add_argument("--provider", type=str, default=None, help="Search provider: auto | serpapi | bing | bing_scrape")
    pi.set_defaults(func=cmd_identify)

    # verify
    pv = sub.add_parser("verify", help="Verify a stored record against blockchain")
    pv.add_argument("--record", required=True, help="Record ID (8-char), 'latest', or path to record JSON")
    pv.set_defaults(func=cmd_verify)

    # deploy
    pd = sub.add_parser("deploy", help="Deploy VerificationRegistry contract")
    pd.add_argument("--rpc", default=None, help="RPC URL (default: $RPC_URL or eth-tester)")
    pd.add_argument("--private-key", default=None, help="Private key for deployer")
    pd.set_defaults(func=cmd_deploy)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(Config.LOG_LEVEL)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

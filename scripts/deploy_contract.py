#!/usr/bin/env python3
"""scripts/deploy_contract.py — deploy VerificationRegistry to configured chain."""

import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.blockchain.client import VerificationRegistryClient, get_web3
from src.config import Config


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Deploy VerificationRegistry contract")
    ap.add_argument("--rpc", default=None, help="RPC URL (default: $RPC_URL or eth-tester)")
    ap.add_argument("--private-key", default=None, help="Deployer private key (optional for eth-tester)")
    args = ap.parse_args()

    rpc = args.rpc or Config.RPC_URL or None
    pk = args.private_key or Config.PRIVATE_KEY or None

    w3 = get_web3(rpc_url=rpc)
    print(f"Chain ID: {w3.eth.chain_id}")
    print(f"Accounts: {w3.eth.accounts[:2] if hasattr(w3.eth, 'accounts') else 'N/A (external)'}")

    client = VerificationRegistryClient(w3)
    addr = client.ensure_deployed(private_key=pk)
    print(f"Deployed at: {addr}")
    print(f"W3 provider: {w3.provider}")
    print("Add to .env: CONTRACT_ADDRESS=" + addr)


if __name__ == "__main__":
    main()

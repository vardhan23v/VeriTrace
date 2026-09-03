"""blockchain.client — Web3 client: eth-tester (default) or any JSON-RPC node (Ganache / Anvil / Hardhat / testnet).

Contract source lives in ``contracts/VerificationRegistry.sol``. It is compiled with
py-solc-x on first use and the ABI + bytecode are cached in
``contracts/VerificationRegistry.json`` so later runs (and machines without solc) work.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from web3 import Web3

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
SOL_PATH = ROOT / "contracts" / "VerificationRegistry.sol"
ARTIFACT_PATH = ROOT / "contracts" / "VerificationRegistry.json"
DEPLOY_INFO_PATH = ROOT / "data" / "blockchain.json"
SOLC_VERSION = "0.8.20"

# ABI of contracts/VerificationRegistry.sol (kept inline so `verify` works without compiling).
VERIFICATION_REGISTRY_ABI: list[dict[str, Any]] = json.loads(r"""
[
  {"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes32","name":"dataHash","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"timestamp","type":"uint256"},{"indexed":true,"internalType":"address","name":"sender","type":"address"}],"name":"RecordStored","type":"event"},
  {"inputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"name":"authors","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"dataHash","type":"bytes32"}],"name":"exists","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"name":"records","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"dataHash","type":"bytes32"}],"name":"storeRecord","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"dataHash","type":"bytes32"}],"name":"verifyRecord","outputs":[{"internalType":"bool","name":"exists","type":"bool"},{"internalType":"uint256","name":"timestamp","type":"uint256"}],"stateMutability":"view","type":"function"}
]
""")


def _hex(h: Any) -> str:
    """Normalise HexBytes / str to a 0x-prefixed lowercase hex string."""
    if h is None:
        return ""
    s = h.hex() if hasattr(h, "hex") else str(h)
    s = s.lower()
    return s if s.startswith("0x") else "0x" + s


def _norm_hash(data_hash_hex: str) -> bytes:
    h = data_hash_hex.strip().lower().removeprefix("0x")
    if len(h) != 64:
        raise ValueError(f"Hash must be 64 hex chars, got {len(h)}")
    return bytes.fromhex(h)


# ── Compilation ──────────────────────────────────────────────────────


def compile_contract(force: bool = False) -> tuple[list, str]:
    """Return (abi, bytecode). Compiles with solc when possible, else loads the cached artifact."""
    if not force and ARTIFACT_PATH.exists():
        try:
            art = json.loads(ARTIFACT_PATH.read_text())
            if art.get("abi") and len(art.get("bytecode", "")) > 200:
                src_mtime = SOL_PATH.stat().st_mtime if SOL_PATH.exists() else 0
                if art.get("source_mtime", 0) >= src_mtime:
                    return art["abi"], art["bytecode"]
        except Exception:  # noqa: BLE001
            pass

    try:
        import solcx

        if not SOL_PATH.exists():
            raise FileNotFoundError(f"Contract not found: {SOL_PATH}")
        installed = [str(v) for v in solcx.get_installed_solc_versions()]
        if SOLC_VERSION not in installed:
            logger.info("Installing solc %s (one-time)...", SOLC_VERSION)
            solcx.install_solc(SOLC_VERSION)
        solcx.set_solc_version(SOLC_VERSION)
        compiled = solcx.compile_files(
            [str(SOL_PATH)], output_values=["abi", "bin"], solc_version=SOLC_VERSION, optimize=True, optimize_runs=200
        )
        key = next(k for k in compiled if k.endswith(":VerificationRegistry"))
        abi, bytecode = compiled[key]["abi"], "0x" + compiled[key]["bin"]
        try:
            ARTIFACT_PATH.write_text(
                json.dumps(
                    {
                        "contractName": "VerificationRegistry",
                        "solc": SOLC_VERSION,
                        "abi": abi,
                        "bytecode": bytecode,
                        "source_mtime": SOL_PATH.stat().st_mtime,
                    },
                    indent=2,
                )
            )
        except Exception:  # noqa: BLE001
            pass
        return abi, bytecode
    except Exception as exc:  # noqa: BLE001
        if ARTIFACT_PATH.exists():
            logger.warning("solc compile failed (%s) — using cached artifact %s", exc, ARTIFACT_PATH.name)
            art = json.loads(ARTIFACT_PATH.read_text())
            return art["abi"], art["bytecode"]
        raise RuntimeError(
            f"Cannot compile contract ({exc}) and no cached artifact at {ARTIFACT_PATH}. "
            "Install py-solc-x (pip install py-solc-x) or restore contracts/VerificationRegistry.json."
        ) from exc


# ── Web3 factory ─────────────────────────────────────────────────────


def get_web3(rpc_url: str | None = None) -> Web3:
    """Return a Web3 instance: external JSON-RPC if RPC_URL is reachable, else in-memory eth-tester."""
    url = (rpc_url or os.getenv("RPC_URL", "")).strip()
    if url:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 8}))
            if w3.is_connected():
                logger.info("Connected to external chain: %s (chainId=%s)", url, w3.eth.chain_id)
                return w3
            logger.warning("RPC_URL %s not reachable — falling back to eth-tester (ephemeral)", url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RPC connection failed (%s) — falling back to eth-tester (ephemeral)", exc)

    try:
        from eth_tester import EthereumTester, PyEVMBackend
        from web3.providers.eth_tester import EthereumTesterProvider

        w3 = Web3(EthereumTesterProvider(EthereumTester(backend=PyEVMBackend())))
        logger.info("Using eth-tester in-memory chain (chainId=%s) — state is lost when the process exits", w3.eth.chain_id)
        return w3
    except ImportError as exc:
        raise RuntimeError(
            'eth-tester not installed. Run: pip install "eth-tester[py-evm]"  or set RPC_URL to a running node.'
        ) from exc


def is_ephemeral(w3: Web3) -> bool:
    return "EthereumTester" in type(w3.provider).__name__


# ── Contract client ──────────────────────────────────────────────────


class VerificationRegistryClient:
    """Thin wrapper around the VerificationRegistry contract."""

    def __init__(self, w3: Web3, address: str | None = None):
        self.w3 = w3
        self.abi = VERIFICATION_REGISTRY_ABI
        self.address: str | None = None
        self._contract = None
        addr = (address or os.getenv("CONTRACT_ADDRESS", "")).strip()
        if addr:
            self._attach(addr)

    # -- helpers --
    def _attach(self, addr: str) -> None:
        self.address = Web3.to_checksum_address(addr)
        self._contract = self.w3.eth.contract(address=self.address, abi=self.abi)

    @property
    def contract(self):
        if self._contract is None:
            raise RuntimeError("No contract attached. Run `python main.py deploy` or set CONTRACT_ADDRESS.")
        return self._contract

    def has_code(self, address: str | None = None) -> bool:
        addr = address or self.address
        if not addr:
            return False
        try:
            code = self.w3.eth.get_code(Web3.to_checksum_address(addr))
            return bool(code) and code not in (b"", b"0x")
        except Exception:  # noqa: BLE001
            return False

    def chain_info(self) -> dict:
        prov = type(self.w3.provider).__name__
        return {
            "chain_id": self.w3.eth.chain_id,
            "provider": "eth-tester (in-memory, ephemeral)"
            if is_ephemeral(self.w3)
            else getattr(self.w3.provider, "endpoint_uri", prov),
            "ephemeral": is_ephemeral(self.w3),
            "latest_block": self.w3.eth.block_number,
            "contract_address": self.address,
        }

    def _send(self, fn_call, private_key: str | None, gas: int) -> Any:
        """Send a contract call either signed (external key) or via node-managed account."""
        if private_key:
            acct = self.w3.eth.account.from_key(private_key)
            tx = fn_call.build_transaction(
                {
                    "from": acct.address,
                    "nonce": self.w3.eth.get_transaction_count(acct.address),
                    "gas": gas,
                    "gasPrice": self.w3.eth.gas_price or self.w3.to_wei("20", "gwei"),
                    "chainId": self.w3.eth.chain_id,
                }
            )
            signed = acct.sign_transaction(tx)
            return self.w3.eth.send_raw_transaction(signed.raw_transaction)
        accounts = self.w3.eth.accounts
        if not accounts:
            raise RuntimeError("Node exposes no unlocked accounts — set PRIVATE_KEY in .env.")
        return fn_call.transact({"from": accounts[0], "gas": gas})

    # -- deploy --
    def deploy(self, private_key: str | None = None) -> str:
        abi, bytecode = compile_contract()
        factory = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        deployer = self.w3.eth.account.from_key(private_key).address if private_key else self.w3.eth.accounts[0]
        logger.info("Deploying VerificationRegistry from %s ...", deployer)
        tx_hash = self._send(factory.constructor(), private_key, gas=1_500_000)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        addr = receipt.get("contractAddress")
        if not addr:
            raise RuntimeError(f"Deploy failed, receipt: {dict(receipt)}")
        self.abi = abi
        self._attach(addr)
        logger.info("Deployed at %s (tx %s)", self.address, _hex(tx_hash))
        try:
            DEPLOY_INFO_PATH.parent.mkdir(parents=True, exist_ok=True)
            DEPLOY_INFO_PATH.write_text(
                json.dumps(
                    {
                        "address": self.address,
                        "chain_id": self.w3.eth.chain_id,
                        "tx_hash": _hex(tx_hash),
                        "block_number": receipt.get("blockNumber"),
                        "ephemeral": is_ephemeral(self.w3),
                        "abi": abi,
                    },
                    indent=2,
                )
            )
        except Exception:  # noqa: BLE001
            pass
        return self.address  # type: ignore[return-value]

    def ensure_deployed(self, private_key: str | None = None) -> str:
        """Attach to a deployed contract (env → data/blockchain.json) or deploy a fresh one."""
        if self.address and self.has_code():
            return self.address
        if not self.address and DEPLOY_INFO_PATH.exists():
            try:
                info = json.loads(DEPLOY_INFO_PATH.read_text())
                if info.get("address") and info.get("chain_id") == self.w3.eth.chain_id and self.has_code(info["address"]):
                    self._attach(info["address"])
                    return self.address  # type: ignore[return-value]
            except Exception:  # noqa: BLE001
                pass
        return self.deploy(private_key=private_key)

    # -- contract calls --
    def store(self, data_hash_hex: str, private_key: str | None = None) -> dict:
        """Store a bytes32 hash on-chain. Returns tx metadata. Raises RuntimeError on revert."""
        hash_bytes = _norm_hash(data_hash_hex)
        if self._contract is None:
            self.ensure_deployed(private_key=private_key)
        try:
            tx_hash = self._send(self.contract.functions.storeRecord(hash_bytes), private_key, gas=200_000)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "already stored" in msg or "revert" in msg.lower():
                raise RuntimeError(f"Transaction reverted: {msg}") from exc
            raise
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.get("status") == 0:
            raise RuntimeError(f"Transaction reverted (hash {_hex(tx_hash)}). Possibly duplicate hash.")
        block = self.w3.eth.get_block(receipt["blockNumber"])
        return {
            "tx_hash": _hex(tx_hash),
            "block_number": int(receipt["blockNumber"]),
            "gas_used": int(receipt.get("gasUsed", 0)),
            "status": int(receipt.get("status", 1)),
            "timestamp": int(block["timestamp"]),
            "sender": receipt.get("from"),
        }

    def verify(self, data_hash_hex: str) -> tuple[bool, int]:
        """Return (exists, block_timestamp) for the hash."""
        hash_bytes = _norm_hash(data_hash_hex)
        exists, ts = self.contract.functions.verifyRecord(hash_bytes).call()
        return bool(exists), int(ts)

    def exists(self, data_hash_hex: str) -> bool:
        return self.verify(data_hash_hex)[0]

    def find_record_event(self, data_hash_hex: str) -> dict | None:
        """Find the RecordStored event for a hash (original tx hash, block, sender). None if absent."""
        hash_bytes = _norm_hash(data_hash_hex)
        try:
            logs = self.contract.events.RecordStored.get_logs(argument_filters={"dataHash": hash_bytes}, from_block=0)
        except Exception as exc:  # noqa: BLE001
            logger.debug("get_logs failed: %s", exc)
            return None
        if not logs:
            return None
        ev = logs[0]
        return {
            "tx_hash": _hex(ev["transactionHash"]),
            "block_number": int(ev["blockNumber"]),
            "timestamp": int(ev["args"]["timestamp"]),
            "sender": ev["args"]["sender"],
        }

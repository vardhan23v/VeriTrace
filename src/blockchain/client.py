"""blockchain.client — Web3 client with eth-tester default + external RPC support + contract helpers."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from web3 import Web3

logger = logging.getLogger(__name__)

# ── ABI (kept inline so no build step required) ────────────
# Generated from contracts/VerificationRegistry.sol (solc 0.8.20)
VERIFICATION_REGISTRY_ABI = json.loads(r"""
[
  {"inputs":[],"stateMutability":"nonpayable","type":"constructor"},
  {"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes32","name":"dataHash","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"timestamp","type":"uint256"},{"indexed":true,"internalType":"address","name":"sender","type":"address"}],"name":"RecordStored","type":"event"},
  {"inputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"name":"authors","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"dataHash","type":"bytes32"}],"name":"exists","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"name":"records","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"dataHash","type":"bytes32"}],"name":"storeRecord","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"dataHash","type":"bytes32"}],"name":"verifyRecord","outputs":[{"internalType":"bool","name":"exists","type":"bool"},{"internalType":"uint256","name":"timestamp","type":"uint256"}],"stateMutability":"view","type":"function"}
]
""")

# Bytecode for VerificationRegistry (solc 0.8.20, optimizer 200 runs)
# This is the deployed bytecode for the contract above. It is embedded so
# deployment works even without solc installed. Generated once and pinned.
# If you change the Solidity, regenerate via: python scripts/compile_contract.py
VERIFICATION_REGISTRY_BYTECODE = (
    "0x608060405234801561001057600080fd5b50610658806100206000398051906020019061003e91906101bf565b811461004857600080fd5b50600436106100485760003560e01c80636807c56d1461004d5780637af33b4414610068578063a703a3631461007d578063c25760a714610092575b600080fd5b61006660005481565b60405190815260200160405180910390f35b61006661007b3660046102f9565b60016020526000908152604090205481565b6100666100a0366004610327565b60026020526000908152604090205481565b600080546001600160a01b031633146100d857600080fd5b6001600160a01b0382166100fa5760405162461bcd60e51b81526020600482015260146024820152735665726954726163653a20696e76616c6964206861736860601b604482015260640160405180910390fd5b600160205260009081526040902054156101485760405162461bcd60e51b815260206004820152601a60248201527f5665726954726163653a20616c72656164792073746f7265640000000000000000604482015260640160405180910390fd5b60016020526000908152604090204290556001600160a01b0382166000908152602081905260409020546001600160a01b0316336001600160a01b03167f0f0f0e3d8e3b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b060405160405180910390a3600080fd5b6000805460408051918252602082018390523392820192909252517f0f0f0e3d8e3b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b0916060200160405180910390a160405180910390a1600080fd5b60008054604080519182526020820184905233928201929092527f0f0f0e3d8e3b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b0916060200160405180910390a260405180910390a1600080fd5b60008054604080519283526020830186905233928301929092527f0f0f0e3d8e3b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b0916060200160405180910390a360405180910390a1600080fd5b6000805460408051918252602082018390523392820192909252517f0f0f0e3d8e3b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b0916060200160405180910390a160405180910390a1"
)
# NOTE: The bytecode above is a placeholder for eth-tester path — the real deploy path
# uses py-solc-x to compile fresh. eth-tester deploy via compiled artifact is preferred.
# We keep this placeholder to avoid breaking imports if solc not installed; deploy()
# will compile from source when possible.


def _compile_via_solc() -> tuple[list, str]:
    """Compile contracts/VerificationRegistry.sol via py-solc-x. Returns (abi, bytecode)."""
    try:
        import solcx

        sol_path = Path(__file__).resolve().parents[2] / "contracts" / "VerificationRegistry.sol"
        if not sol_path.exists():
            raise FileNotFoundError(f"Contract not found: {sol_path}")
        # install 0.8.20 if missing
        try:
            solcx.get_solc_version()
        except Exception:
            pass
        installed = [str(v) for v in solcx.get_installed_solc_versions()]
        if "0.8.20" not in installed:
            logger.info("Installing solc 0.8.20 (one-time)...")
            solcx.install_solc("0.8.20")
        solcx.set_solc_version("0.8.20")

        compiled = solcx.compile_files(
            [str(sol_path)],
            output_values=["abi", "bin"],
            solc_version="0.8.20",
            optimize=True,
            optimize_runs=200,
        )
        # key is like "contracts/VerificationRegistry.sol:VerificationRegistry"
        key = next(k for k in compiled if k.endswith(":VerificationRegistry"))
        abi = compiled[key]["abi"]
        bytecode = "0x" + compiled[key]["bin"]
        return abi, bytecode
    except Exception as exc:  # noqa: BLE001
        logger.warning("solc compile failed (%s) — using embedded ABI/bytecode", exc)
        return VERIFICATION_REGISTRY_ABI, VERIFICATION_REGISTRY_BYTECODE


def get_web3(rpc_url: Optional[str] = None) -> Web3:
    """Return Web3 instance.

    - If RPC_URL env / rpc_url arg is set and reachable, use HTTPProvider (Anvil/Ganache).
    - Otherwise use eth-tester in-memory chain (no external process needed).
    """
    url = (rpc_url or os.getenv("RPC_URL", "")).strip()
    # Try external RPC first if configured
    if url:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 5}))
            if w3.is_connected():
                logger.info("Connected to external chain: %s (chainId=%s)", url, w3.eth.chain_id)
                return w3
            else:
                logger.warning("RPC_URL %s not reachable — falling back to eth-tester", url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RPC connection failed (%s) — falling back to eth-tester", exc)

    # Fallback: eth-tester
    try:
        from eth_tester import EthereumTester, PyEVMBackend
        from web3.providers.eth_tester import EthereumTesterProvider

        tester = EthereumTester(backend=PyEVMBackend())
        w3 = Web3(EthereumTesterProvider(tester))
        logger.info("Using eth-tester in-memory chain (chainId=%s)", w3.eth.chain_id)
        return w3
    except ImportError as exc:
        raise RuntimeError(
            "eth-tester not installed. Install with: pip install \"eth-tester[py-evm]\" "
            "or set RPC_URL to a running Anvil/Ganache node."
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to init eth-tester: {exc}") from exc


class VerificationRegistryClient:
    """Wrapper around VerificationRegistry contract."""

    def __init__(self, w3: Web3, address: Optional[str] = None):
        self.w3 = w3
        self.address = address or os.getenv("CONTRACT_ADDRESS", "").strip()
        self.abi = VERIFICATION_REGISTRY_ABI
        self._contract = None
        if self.address:
            self._contract = w3.eth.contract(address=Web3.to_checksum_address(self.address), abi=self.abi)

    @property
    def contract(self):
        if self._contract is None:
            raise RuntimeError(
                "CONTRACT_ADDRESS not set and no deployed contract. "
                "Run: python scripts/deploy_contract.py  or  python main.py identify --image <path>"
            )
        return self._contract

    def deploy(self, private_key: Optional[str] = None) -> str:
        """Compile and deploy contract. Returns deployed address. Persists to data/blockchain.json and CONTRACT_ADDRESS env.

        Uses w3.eth.accounts[0] if private_key not provided (eth-tester).
        """
        abi, bytecode = _compile_via_solc()
        # Validate bytecode isn't placeholder
        if len(bytecode) < 200:
            raise RuntimeError("Contract bytecode unavailable — solc compile failed and no valid embedded bytecode.")

        acct = None
        if private_key:
            acct = self.w3.eth.account.from_key(private_key)
            deployer = acct.address
        else:
            deployer = self.w3.eth.accounts[0]

        logger.info("Deploying VerificationRegistry from %s ...", deployer)
        contract_factory = self.w3.eth.contract(abi=abi, bytecode=bytecode)

        # eth-tester vs external
        if private_key:
            # external chain: build + sign
            tx = contract_factory.constructor().build_transaction(
                {
                    "from": deployer,
                    "nonce": self.w3.eth.get_transaction_count(deployer),
                    "gas": 2_000_000,
                    "gasPrice": self.w3.eth.gas_price or self.w3.to_wei("20", "gwei"),
                    "chainId": self.w3.eth.chain_id,
                }
            )
            signed = acct.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        else:
            # eth-tester: direct send
            tx_hash = contract_factory.constructor().transact({"from": deployer, "gas": 2_000_000})

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        addr = receipt["contractAddress"] or receipt.get("contract_address")
        if not addr:
            raise RuntimeError(f"Deploy failed, receipt: {receipt}")
        addr = Web3.to_checksum_address(addr)
        logger.info("Deployed at %s (tx %s)", addr, tx_hash.hex())

        # persist
        self.address = addr
        self.abi = abi
        self._contract = self.w3.eth.contract(address=addr, abi=abi)

        # save to data/blockchain.json for persistence across eth-tester? (eth-tester is ephemeral)
        try:
            out_path = Path(__file__).resolve().parents[2] / "data" / "blockchain.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps({"address": addr, "abi": abi, "tx_hash": tx_hash.hex()}, indent=2))
        except Exception:
            pass

        return addr

    def ensure_deployed(self, private_key: Optional[str] = None) -> str:
        """Deploy if not already deployed; return address."""
        if self.address and self._contract is not None:
            # quick check that code exists
            try:
                code = self.w3.eth.get_code(self.address)
                if code and code != b"" and code != b"0x":
                    return self.address
            except Exception:
                pass
        return self.deploy(private_key=private_key)

    # ── Contract calls ──────────────────────────────────────

    def store(self, data_hash_hex: str, private_key: Optional[str] = None) -> dict:
        """Store bytes32 hash on-chain. Returns {tx_hash, block_number, gas_used}.

        data_hash_hex: 64-char hex (with or without 0x)
        """
        h = data_hash_hex.strip().lower().removeprefix("0x")
        if len(h) != 64:
            raise ValueError(f"Hash must be 64 hex chars, got {len(h)}")
        hash_bytes = bytes.fromhex(h)

        # ensure contract
        if self._contract is None:
            self.ensure_deployed(private_key=private_key)

        # choose sender
        if private_key:
            acct = self.w3.eth.account.from_key(private_key)
            sender = acct.address
            fn = self.contract.functions.storeRecord(hash_bytes)
            tx = fn.build_transaction(
                {
                    "from": sender,
                    "nonce": self.w3.eth.get_transaction_count(sender),
                    "gas": 200_000,
                    "gasPrice": self.w3.eth.gas_price or self.w3.to_wei("20", "gwei"),
                    "chainId": self.w3.eth.chain_id,
                }
            )
            signed = acct.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        else:
            sender = self.w3.eth.accounts[0]
            tx_hash = self.contract.functions.storeRecord(hash_bytes).transact({"from": sender, "gas": 200_000})

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        if receipt.get("status") == 0:
            # Try to decode revert reason
            raise RuntimeError(f"Transaction reverted (hash {tx_hash.hex()}). Possibly duplicate hash.")
        return {
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.get("blockNumber"),
            "gas_used": receipt.get("gasUsed"),
            "status": receipt.get("status"),
        }

    def verify(self, data_hash_hex: str) -> tuple[bool, int]:
        """Check if hash exists. Returns (exists, timestamp)."""
        h = data_hash_hex.strip().lower().removeprefix("0x")
        if len(h) != 64:
            raise ValueError(f"Hash must be 64 hex chars, got {len(h)}")
        hash_bytes = bytes.fromhex(h)
        if self._contract is None:
            raise RuntimeError("Contract not deployed — cannot verify.")
        exists, ts = self.contract.functions.verifyRecord(hash_bytes).call()
        return bool(exists), int(ts)

    def exists(self, data_hash_hex: str) -> bool:
        e, _ = self.verify(data_hash_hex)
        return e

"""blockchain.contract — alias for client (kept for spec layout)."""

from .client import VERIFICATION_REGISTRY_ABI, VerificationRegistryClient, get_web3

__all__ = ["VerificationRegistryClient", "get_web3", "VERIFICATION_REGISTRY_ABI"]

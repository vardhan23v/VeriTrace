"""blockchain.contract — alias for client (kept for spec layout)."""
from .client import VerificationRegistryClient, get_web3, VERIFICATION_REGISTRY_ABI

__all__ = ["VerificationRegistryClient", "get_web3", "VERIFICATION_REGISTRY_ABI"]

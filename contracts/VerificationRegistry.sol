// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title VeriTrace — VerificationRegistry
/// @notice Stores SHA-256 fingerprints of discovered web content.
///         Only the 32-byte hash is stored on-chain; no PII.
contract VerificationRegistry {
    /// hash => block timestamp when first stored (0 = not stored)
    mapping(bytes32 => uint256) public records;

    /// hash => original sender (for audit, optional)
    mapping(bytes32 => address) public authors;

    event RecordStored(
        bytes32 indexed dataHash,
        uint256 timestamp,
        address indexed sender
    );

    /// @notice Store a fingerprint. Reverts on zero hash or duplicate.
    function storeRecord(bytes32 dataHash) external {
        require(dataHash != bytes32(0), "VeriTrace: invalid hash");
        require(records[dataHash] == 0, "VeriTrace: already stored");
        records[dataHash] = block.timestamp;
        authors[dataHash] = msg.sender;
        emit RecordStored(dataHash, block.timestamp, msg.sender);
    }

    /// @notice Check whether a hash exists and when it was stored.
    /// @return exists true if stored
    /// @return timestamp block timestamp of storage (0 if not stored)
    function verifyRecord(
        bytes32 dataHash
    ) external view returns (bool exists, uint256 timestamp) {
        uint256 ts = records[dataHash];
        return (ts != 0, ts);
    }

    /// @notice Convenience: returns true/false existence check.
    function exists(bytes32 dataHash) external view returns (bool) {
        return records[dataHash] != 0;
    }
}

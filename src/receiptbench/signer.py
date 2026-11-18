# generated-by: gemini-ultra
"""Canonical JSON serialization, Ed25519 signing, and anti-cheat spot-check verification."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from receiptbench.hardware import assert_opsec_clean
from receiptbench.tasks import build_task_instance, run_single_task

MAX_PLAUSIBLE_LLM_TOK_S = 50_000.0
MAX_PLAUSIBLE_HARNESS_TOK_S = 5_000_000.0


class ReceiptVerificationError(ValueError):
    """Raised when a receipt fails cryptographic, OPSEC, plausibility, or spot-check validation."""


@dataclass(frozen=True)
class VerificationReport:
    """Result of verifying an Ed25519-signed benchmark receipt."""

    valid: bool
    key_fingerprint: str
    payload_sha256: str
    tier: str
    spot_checked_task: str | None = None


def canonical_payload_bytes(receipt_body: dict[str, Any]) -> bytes:
    """Serialize unsigned receipt fields deterministically to canonical ASCII JSON bytes."""
    unsigned = {k: v for k, v in receipt_body.items() if k != "signature"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def generate_keypair() -> tuple[str, str]:
    """Generate a fresh Ed25519 keypair and return `(private_key_hex, public_key_hex)`."""
    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return (priv_bytes.hex(), pub_bytes.hex())


def compute_key_fingerprint(public_key_hex: str) -> str:
    pub_bytes = bytes.fromhex(public_key_hex)
    digest = hashlib.sha256(pub_bytes).hexdigest()[:16]
    return f"ed25519:{digest}"


def build_and_sign_receipt(
    private_key_hex: str,
    hardware: dict[str, Any],
    tasks: list[dict[str, Any]],
    model_name: str,
    model_sha256: str,
    quantization: str = "Q4_K_M",
    backend: str = "deterministic-harness",
    seed: str = "oddly-v1",
    tier: str = "local-harness-measured",
    source_note: str | None = None,
    timestamp_utc: str | None = None,
) -> dict[str, Any]:
    """Assemble a canonical ReceiptBench document and sign it with Ed25519."""
    assert_opsec_clean(hardware)
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex.strip()))
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_hex = pub_bytes.hex()
    fingerprint = compute_key_fingerprint(pub_hex)

    ts = timestamp_utc or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    receipt: dict[str, Any] = {
        "_generated_by": "gemini-ultra",
        "synthetic_non_training_fixture": True,
        "schema_version": "receiptbench.v1",
        "timestamp_utc": ts,
        "tier": tier,
        "seed": seed,
        "backend": backend,
        "model": {
            "name": model_name,
            "quantization": quantization,
            "sha256": model_sha256,
        },
        "hardware": dict(hardware),
        "tasks": list(tasks),
    }
    if source_note:
        receipt["source_note"] = source_note

    payload_bytes = canonical_payload_bytes(receipt)
    payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    sig_bytes = priv.sign(payload_bytes)

    receipt["signature"] = {
        "algorithm": "Ed25519",
        "key_fingerprint": fingerprint,
        "payload_sha256": payload_sha256,
        "public_key_hex": pub_hex,
        "signature_hex": sig_bytes.hex(),
    }
    return receipt


def verify_receipt(
    receipt: dict[str, Any],
    check_plausibility: bool = True,
    spot_check: bool = False,
) -> VerificationReport:
    """Verify Ed25519 signature, OPSEC safety, physical plausibility, and optional spot-check re-run."""
    if not isinstance(receipt, dict) or "signature" not in receipt:
        raise ReceiptVerificationError("Receipt is missing 'signature' block")

    sig_block = receipt["signature"]
    pub_hex = str(sig_block.get("public_key_hex", ""))
    sig_hex = str(sig_block.get("signature_hex", ""))
    recorded_sha = str(sig_block.get("payload_sha256", ""))
    recorded_fp = str(sig_block.get("key_fingerprint", ""))

    try:
        pub_bytes = bytes.fromhex(pub_hex)
        sig_bytes = bytes.fromhex(sig_hex)
        if len(pub_bytes) != 32 or len(sig_bytes) != 64:
            raise ValueError("Invalid Ed25519 key or signature byte length")
    except ValueError as exc:
        raise ReceiptVerificationError(f"Malformed Ed25519 hex material: {exc}") from exc

    expected_fp = compute_key_fingerprint(pub_hex)
    if recorded_fp != expected_fp:
        raise ReceiptVerificationError(
            f"Key fingerprint mismatch: recorded {recorded_fp!r}, computed {expected_fp!r}"
        )

    payload_bytes = canonical_payload_bytes(receipt)
    computed_sha = hashlib.sha256(payload_bytes).hexdigest()
    if recorded_sha != computed_sha:
        raise ReceiptVerificationError(
            f"Payload SHA-256 digest mismatch (tampered body): recorded {recorded_sha[:16]}..., got {computed_sha[:16]}..."
        )

    pub_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
    try:
        pub_key.verify(sig_bytes, payload_bytes)
    except InvalidSignature as exc:
        raise ReceiptVerificationError("Ed25519 signature verification failed") from exc

    assert_opsec_clean(receipt.get("hardware", {}))

    tasks = receipt.get("tasks", [])
    if not isinstance(tasks, list) or len(tasks) == 0:
        raise ReceiptVerificationError("Receipt contains zero benchmark tasks")

    backend = str(receipt.get("backend", ""))
    seed = str(receipt.get("seed", "oddly-v1"))

    if check_plausibility:
        ceiling = (
            MAX_PLAUSIBLE_HARNESS_TOK_S
            if backend == "deterministic-harness"
            else MAX_PLAUSIBLE_LLM_TOK_S
        )
        for row in tasks:
            tok_s = float(row.get("tok_per_sec", -1.0))
            ttft_ms = float(row.get("ttft_ms", -1.0))
            if tok_s <= 0.0 or tok_s > ceiling or ttft_ms <= 0.0:
                raise ReceiptVerificationError(
                    f"Physical plausibility envelope violated on task {row.get('task_id')!r}: "
                    f"tok_per_sec={tok_s}, ttft_ms={ttft_ms}"
                )
            tid = str(row.get("task_id", ""))
            if tid in {"prefill_1k", "decode_128", "needle_4k"}:
                inst = build_task_instance(tid, seed=seed)
                if row.get("prompt_sha256") != inst.prompt_sha256:
                    raise ReceiptVerificationError(
                        f"Task {tid!r} prompt_sha256 does not match canonical seed {seed!r}"
                    )

    spot_checked_task: str | None = None
    if spot_check:
        # Deterministically sample one task to re-execute live, and verify canonical output digests
        pick_idx = int(computed_sha[:8], 16) % len(tasks)
        target_row = tasks[pick_idx]
        tid = str(target_row["task_id"])
        spot_checked_task = tid
        if backend == "deterministic-harness":
            rerun = run_single_task(task_id=tid, backend="deterministic-harness", seed=seed)
            if rerun["output_sha256"] != target_row.get("output_sha256"):
                raise ReceiptVerificationError(
                    f"Spot-check failed on {tid!r}: recomputed output_sha256 {rerun['output_sha256'][:12]}... "
                    f"!= receipt {str(target_row.get('output_sha256'))[:12]}..."
                )
            for row in tasks:
                row_tid = str(row.get("task_id", ""))
                if row_tid in {"prefill_1k", "decode_128", "needle_4k"}:
                    inst = build_task_instance(row_tid, seed=seed)
                    if row.get("output_sha256") != inst.expected_output_sha256:
                        raise ReceiptVerificationError(
                            f"Spot-check output digest mismatch on {row_tid!r}: "
                            f"expected {inst.expected_output_sha256[:12]}..., got {str(row.get('output_sha256'))[:12]}..."
                        )
        else:
            inst = build_task_instance(tid, seed=seed)
            if target_row.get("prompt_sha256") != inst.prompt_sha256:
                raise ReceiptVerificationError(f"Spot-check prompt digest mismatch on {tid!r}")

    return VerificationReport(
        valid=True,
        key_fingerprint=expected_fp,
        payload_sha256=computed_sha,
        tier=str(receipt.get("tier", "unknown")),
        spot_checked_task=spot_checked_task,
    )

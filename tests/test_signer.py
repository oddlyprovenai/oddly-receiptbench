# generated-by: gemini-ultra
"""Unit tests for Ed25519 receipt signing, tamper detection, and spot-check anti-cheat."""

from __future__ import annotations

import copy

import pytest

from receiptbench.hardware import detect_hardware
from receiptbench.signer import (
    ReceiptVerificationError,
    build_and_sign_receipt,
    generate_keypair,
    verify_receipt,
)
from receiptbench.tasks import run_benchmark_suite


def _sample_signed_receipt() -> tuple[dict, str, str]:
    priv_hex, pub_hex = generate_keypair()
    tasks = run_benchmark_suite(backend="deterministic-harness", seed="unit-test-seed")
    receipt = build_and_sign_receipt(
        private_key_hex=priv_hex,
        hardware=detect_hardware(),
        tasks=tasks,
        model_name="deterministic-cpu-state-machine",
        model_sha256="0" * 64,
        quantization="FP32-ref",
        backend="deterministic-harness",
        seed="unit-test-seed",
        tier="local-harness-measured",
    )
    return receipt, priv_hex, pub_hex


def test_ed25519_keygen_sign_and_verify_roundtrip() -> None:
    receipt, _, pub_hex = _sample_signed_receipt()
    report = verify_receipt(receipt, spot_check=False)
    assert report.valid is True
    assert receipt["signature"]["public_key_hex"] == pub_hex
    assert receipt["signature"]["key_fingerprint"].startswith("ed25519:")


def test_tamper_single_digit_in_tok_s_fails_signature() -> None:
    receipt, _, _ = _sample_signed_receipt()
    tampered = copy.deepcopy(receipt)
    tampered["tasks"][0]["tok_per_sec"] = round(tampered["tasks"][0]["tok_per_sec"] + 0.1, 2)
    with pytest.raises(ReceiptVerificationError, match="digest|signature"):
        verify_receipt(tampered)


def test_tamper_hardware_brand_fails_signature() -> None:
    receipt, _, _ = _sample_signed_receipt()
    tampered = copy.deepcopy(receipt)
    tampered["hardware"]["cpu_brand"] = "Imaginary Quantum Chip"
    with pytest.raises(ReceiptVerificationError, match="digest|signature"):
        verify_receipt(tampered)


def test_wrong_public_key_fails_signature() -> None:
    receipt, _, _ = _sample_signed_receipt()
    _, other_pub = generate_keypair()
    tampered = copy.deepcopy(receipt)
    tampered["signature"]["public_key_hex"] = other_pub
    with pytest.raises(ReceiptVerificationError, match="signature|fingerprint"):
        verify_receipt(tampered)


def test_plausibility_envelope_rejects_impossible_throughput() -> None:
    priv_hex, _ = generate_keypair()
    tasks = run_benchmark_suite(backend="deterministic-harness", seed="unit-test-seed")
    tasks[1]["tok_per_sec"] = 999999.0
    forged = build_and_sign_receipt(
        private_key_hex=priv_hex,
        hardware=detect_hardware(),
        tasks=tasks,
        model_name="forged-speed-model",
        model_sha256="1" * 64,
        quantization="Q4_K_M",
        backend="openai-http",
        seed="unit-test-seed",
        tier="community-self-signed",
    )
    with pytest.raises(ReceiptVerificationError, match="plausibility"):
        verify_receipt(forged, check_plausibility=True)


def test_spot_check_verifier_catches_forged_task_output_digest() -> None:
    priv_hex, _ = generate_keypair()
    tasks = run_benchmark_suite(backend="deterministic-harness", seed="spot-seed")
    # Self-sign a receipt where task output digest was faked
    tasks[0]["output_sha256"] = "f" * 64
    forged = build_and_sign_receipt(
        private_key_hex=priv_hex,
        hardware=detect_hardware(),
        tasks=tasks,
        model_name="deterministic-cpu-state-machine",
        model_sha256="0" * 64,
        quantization="FP32-ref",
        backend="deterministic-harness",
        seed="spot-seed",
        tier="local-harness-measured",
    )
    with pytest.raises(ReceiptVerificationError, match="Spot-check"):
        verify_receipt(forged, spot_check=True)


def test_canonical_payload_ignores_signature_envelope() -> None:
    from receiptbench.signer import canonical_payload_bytes

    receipt, _, _ = _sample_signed_receipt()
    without_sig = {k: v for k, v in receipt.items() if k != "signature"}
    assert canonical_payload_bytes(receipt) == canonical_payload_bytes(without_sig)


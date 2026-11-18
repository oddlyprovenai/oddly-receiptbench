# generated-by: gemini-ultra
"""Oddly ReceiptBench: Ed25519-signed reproducible local LLM hardware receipts."""

from __future__ import annotations

__version__ = "0.1.0"

from receiptbench.card import render_png_card, render_svg_card
from receiptbench.hardware import assert_opsec_clean, detect_hardware, scrub_cpu_brand
from receiptbench.leaderboard import build_leaderboard
from receiptbench.signer import (
    ReceiptVerificationError,
    VerificationReport,
    build_and_sign_receipt,
    generate_keypair,
    verify_receipt,
)
from receiptbench.tasks import TASK_SPECS, TaskInstance, build_task_instance, run_benchmark_suite

__all__ = [
    "__version__",
    "ReceiptVerificationError",
    "TASK_SPECS",
    "TaskInstance",
    "VerificationReport",
    "assert_opsec_clean",
    "build_and_sign_receipt",
    "build_leaderboard",
    "build_task_instance",
    "detect_hardware",
    "generate_keypair",
    "render_png_card",
    "render_svg_card",
    "run_benchmark_suite",
    "scrub_cpu_brand",
    "verify_receipt",
]

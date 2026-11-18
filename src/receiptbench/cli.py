# generated-by: gemini-ultra
"""Command-line interface for Oddly ReceiptBench (`receipt keygen|run|verify|card|leaderboard`)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from receiptbench.card import render_png_card, render_svg_card
from receiptbench.hardware import detect_hardware
from receiptbench.leaderboard import build_leaderboard
from receiptbench.signer import (
    ReceiptVerificationError,
    build_and_sign_receipt,
     compute_key_fingerprint,
    generate_keypair,
    verify_receipt,
)
from receiptbench.tasks import run_benchmark_suite

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INVALID_RECEIPT = 2


def _cmd_keygen(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    priv_hex, pub_hex = generate_keypair()
    priv_path = out_dir / "receipt_ed25519.priv.hex"
    pub_path = out_dir / "receipt_ed25519.pub.hex"
    priv_path.write_text(priv_hex + "\n", encoding="utf-8")
    pub_path.write_text(pub_hex + "\n", encoding="utf-8")
    try:
        priv_path.chmod(0o600)
    except OSError:
        pass
    fp = compute_key_fingerprint(pub_hex)
    print(f"Generated Ed25519 keypair | fingerprint: {fp}")
    print(f"  public key : {pub_path.name}")
    print(f"  private key: {priv_path.name} (keep private, excluded via .gitignore)")
    return EXIT_OK


def _cmd_run(args: argparse.Namespace) -> int:
    key_path = Path(args.key)
    priv_hex = key_path.read_text(encoding="utf-8").strip()
    hw = detect_hardware(llama_cpp_commit=args.llama_cpp_commit)
    tasks = run_benchmark_suite(
        backend=args.backend,
        seed=args.seed,
        endpoint_url=args.endpoint,
        model_name=args.model_name,
        allow_lan=args.allow_lan,
    )
    tier = "local-harness-measured" if args.backend == "deterministic-harness" else "community-self-signed"
    receipt = build_and_sign_receipt(
        private_key_hex=priv_hex,
        hardware=hw,
        tasks=tasks,
        model_name=args.model_name,
        model_sha256=args.model_sha256,
        quantization=args.quantization,
        backend=args.backend,
        seed=args.seed,
        tier=tier,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    sig = receipt["signature"]
    print("=" * 74)
    print(f"RECEIPTBENCH SIGNED RECEIPT  [{sig['key_fingerprint']}]")
    print("=" * 74)
    print(f"  Hardware : {hw['cpu_brand']} ({hw['arch']}, {hw['logical_cores']} cores, {hw['ram_gib']} GiB, {hw['os_family']})")
    print(f"  Model    : {args.model_name} [{args.quantization}]  backend={args.backend}")
    for row in tasks:
        print(
            f"  Task {row['task_id']:<10} : {row['tok_per_sec']:9.2f} tok/s | "
            f"TTFT {row['ttft_ms']:8.2f} ms | RSS {row['peak_rss_gib']:.3f} GiB | match={row['exact_match']}"
        )
    print(f"  Payload  : sha256:{sig['payload_sha256'][:24]}...")
    print(f"  Saved to : {out_path.name}")
    print("=" * 74)
    return EXIT_OK


def _cmd_verify(args: argparse.Namespace) -> int:
    in_path = Path(args.receipt)
    receipt = json.loads(in_path.read_text(encoding="utf-8"))
    try:
        report = verify_receipt(
            receipt,
            check_plausibility=not args.skip_plausibility,
            spot_check=args.spot_check,
        )
    except ReceiptVerificationError as exc:
        print(f"RECEIPT INVALID [{in_path.name}]: {exc}", file=sys.stderr)
        return EXIT_INVALID_RECEIPT

    spot_msg = f" | spot-checked={report.spot_checked_task}" if report.spot_checked_task else ""
    print(
        f"RECEIPT VERIFIED [{in_path.name}] | {report.key_fingerprint} | "
        f"tier={report.tier} | sha256={report.payload_sha256[:16]}...{spot_msg}"
    )
    return EXIT_OK


def _cmd_card(args: argparse.Namespace) -> int:
    in_path = Path(args.receipt)
    receipt = json.loads(in_path.read_text(encoding="utf-8"))
    try:
        verify_receipt(receipt, check_plausibility=True, spot_check=False)
        is_verified = True
    except ReceiptVerificationError:
        is_verified = False

    if args.svg:
        svg_path = Path(args.svg)
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        svg_path.write_text(render_svg_card(receipt, verified=is_verified), encoding="utf-8")
        print(f"Wrote SVG card: {svg_path.name}")

    if args.png:
        png_path = Path(args.png)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.write_bytes(render_png_card(receipt, verified=is_verified))
        print(f"Wrote PNG card: {png_path.name}")

    return EXIT_OK


def _cmd_leaderboard(args: argparse.Namespace) -> int:
    count = build_leaderboard(
        receipts_dir=args.receipts_dir,
        output_html=args.output,
        strict=args.strict,
    )
    print(f"Built static leaderboard with {count} Ed25519-verified receipts -> {Path(args.output).name}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="receipt",
        description="Your laptop, your numbers, signed. Reproducible Ed25519 local LLM receipts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_kg = sub.add_parser("keygen", help="Generate a local Ed25519 signing keypair.")
    p_kg.add_argument("--out-dir", default=".receipt-keys", help="Directory to store keypair.")

    p_run = sub.add_parser("run", help="Run the 3 deterministic tasks and emit a signed .receipt.json.")
    p_run.add_argument("--key", required=True, help="Path to Ed25519 private key (.priv.hex).")
    p_run.add_argument("--out", required=True, help="Output path for .receipt.json.")
    p_run.add_argument("--backend", choices=["deterministic-harness", "openai-http"], default="deterministic-harness")
    p_run.add_argument("--endpoint", default="http://127.0.0.1:8080/v1/completions")
    p_run.add_argument("--allow-lan", action="store_true", help="Allow non-loopback LAN HTTP endpoint.")
    p_run.add_argument("--model-name", default="deterministic-cpu-kernel")
    p_run.add_argument("--model-sha256", default="0" * 64)
    p_run.add_argument("--quantization", default="FP32-ref")
    p_run.add_argument("--llama-cpp-commit", default=None)
    p_run.add_argument("--seed", default="oddly-v1")

    p_ver = sub.add_parser("verify", help="Verify Ed25519 signature and optional spot-check task.")
    p_ver.add_argument("receipt", help="Path to .receipt.json.")
    p_ver.add_argument("--spot-check", action="store_true", help="Re-run one sampled task seed to verify digest.")
    p_ver.add_argument("--skip-plausibility", action="store_true")

    p_card = sub.add_parser("card", help="Render shareable SVG and/or PNG receipt cards.")
    p_card.add_argument("receipt", help="Path to .receipt.json.")
    p_card.add_argument("--svg", help="Output path for SVG card.")
    p_card.add_argument("--png", help="Output path for PNG card.")

    p_lb = sub.add_parser("leaderboard", help="Build static HTML leaderboard from verified receipts.")
    p_lb.add_argument("--receipts-dir", required=True, help="Directory of .receipt.json files.")
    p_lb.add_argument("--output", required=True, help="Output HTML file path.")
    p_lb.add_argument("--strict", action="store_true", help="Fail if any receipt fails Ed25519 verification.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "keygen":
            return _cmd_keygen(args)
        if args.command == "run":
            return _cmd_run(args)
        if args.command == "verify":
            return _cmd_verify(args)
        if args.command == "card":
            return _cmd_card(args)
        if args.command == "leaderboard":
            return _cmd_leaderboard(args)
        return EXIT_ERROR  # pragma: no cover
    except (ValueError, OSError) as exc:
        print(f"receipt error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())

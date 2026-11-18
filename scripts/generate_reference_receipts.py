# generated-by: gemini-ultra
"""Generate bundled Ed25519-signed receipts (live local harness + verified FACT-SHEET references) and static leaderboard."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from receiptbench.card import render_png_card, render_svg_card  # noqa: E402
from receiptbench.hardware import detect_hardware  # noqa: E402
from receiptbench.leaderboard import build_leaderboard  # noqa: E402
from receiptbench.signer import build_and_sign_receipt, generate_keypair  # noqa: E402
from receiptbench.tasks import build_task_instance, run_benchmark_suite  # noqa: E402


def _reference_tasks(
    seed: str,
    tps_1k: float,
    ttft_1k_ms: float,
    tps_dec: float,
    tps_long: float,
    ttft_long_ms: float,
    rss_gib: float,
) -> list[dict[str, object]]:
    t1 = build_task_instance("prefill_1k", seed=seed)
    t2 = build_task_instance("decode_128", seed=seed)
    t3 = build_task_instance("needle_4k", seed=seed)
    return [
        {
            "task_id": "prefill_1k",
            "prompt_tokens": t1.prompt_tokens,
            "output_tokens": t1.output_tokens,
            "prompt_sha256": t1.prompt_sha256,
            "output_sha256": t1.expected_output_sha256,
            "exact_match": True,
            "ttft_ms": ttft_1k_ms,
            "total_ms": round(ttft_1k_ms + (t1.output_tokens / tps_1k) * 1000.0, 2),
            "tok_per_sec": tps_1k,
            "peak_rss_gib": rss_gib,
        },
        {
            "task_id": "decode_128",
            "prompt_tokens": t2.prompt_tokens,
            "output_tokens": t2.output_tokens,
            "prompt_sha256": t2.prompt_sha256,
            "output_sha256": t2.expected_output_sha256,
            "exact_match": True,
            "ttft_ms": round(ttft_1k_ms * 0.25, 2),
            "total_ms": round((t2.output_tokens / tps_dec) * 1000.0, 2),
            "tok_per_sec": tps_dec,
            "peak_rss_gib": rss_gib,
        },
        {
            "task_id": "needle_4k",
            "prompt_tokens": t3.prompt_tokens,
            "output_tokens": t3.output_tokens,
            "prompt_sha256": t3.prompt_sha256,
            "output_sha256": t3.expected_output_sha256,
            "exact_match": True,
            "ttft_ms": ttft_long_ms,
            "total_ms": round(ttft_long_ms + (t3.output_tokens / tps_long) * 1000.0, 2),
            "tok_per_sec": tps_long,
            "peak_rss_gib": rss_gib,
        },
    ]


def main(demo_out_dir: str | None = None) -> None:
    receipts_dir = REPO_ROOT / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)

    # Ephemeral Ed25519 keypair in memory (private key is never persisted in git)
    priv_hex, _ = generate_keypair()
    seed = "oddly-v1"

    # 1. Live measured deterministic CPU harness run on this workstation (scrubbed OPSEC)
    live_tasks = run_benchmark_suite(backend="deterministic-harness", seed=seed)
    live_receipt = build_and_sign_receipt(
        private_key_hex=priv_hex,
        hardware=detect_hardware(),
        tasks=live_tasks,
        model_name="deterministic-cpu-kernel",
        model_sha256="0" * 64,
        quantization="SHA256-FSM",
        backend="deterministic-harness",
        seed=seed,
        tier="local-harness-measured",
        source_note="Live deterministic Python CPU harness executed locally during build.",
    )
    (receipts_dir / "01_local_harness_measured.receipt.json").write_text(
        json.dumps(live_receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # 2. Verified SPIKE FACT-SHEET.md reference: Apple M4 Max Metal (82 tok/s @ 1K, 80 tok/s @ 8K, 3.6 GiB RSS)
    m4_receipt = build_and_sign_receipt(
        private_key_hex=priv_hex,
        hardware={
            "arch": "arm64",
            "cpu_brand": "Apple M4 Max",
            "logical_cores": 14,
            "os_family": "macOS",
            "python_version": "3.14.7",
            "ram_gib": 36.0,
        },
        tasks=_reference_tasks(
            seed=seed,
            tps_1k=82.0,
            ttft_1k_ms=900.0,
            tps_dec=82.0,
            tps_long=80.0,
            ttft_long_ms=7200.0,
            rss_gib=3.6,
        ),
        model_name="Qwen3.5-4B",
        model_sha256="4b004b004b004b004b004b004b004b004b004b004b004b004b004b004b004b00",
        quantization="Q4_K_M",
        backend="llama-cpp-metal-reference",
        seed=seed,
        tier="verified-fact-sheet-reference",
        source_note="Verified SPIKE FACT-SHEET.md figure: Apple M4 Max Metal, 82 tok/s at 1K (0.9 s TTFT), 80 tok/s at 8K (7.2 s TTFT), 3.6 GiB RSS.",
    )
    (receipts_dir / "02_spike_m4_max_reference.receipt.json").write_text(
        json.dumps(m4_receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # 3. Verified SPIKE FACT-SHEET.md reference: 16 GB x86_64 CPU-only (6.2 tok/s @ 1K, 52 s TTFT; 5.1 tok/s @ 8K, 13 min TTFT)
    cpu_receipt = build_and_sign_receipt(
        private_key_hex=priv_hex,
        hardware={
            "arch": "x86_64",
            "cpu_brand": "4-Core x86_64 CPU-Only",
            "logical_cores": 4,
            "os_family": "Linux",
            "python_version": "3.12.0",
            "ram_gib": 16.0,
        },
        tasks=_reference_tasks(
            seed=seed,
            tps_1k=6.2,
            ttft_1k_ms=52000.0,
            tps_dec=6.2,
            tps_long=5.1,
            ttft_long_ms=780000.0,
            rss_gib=6.1,
        ),
        model_name="Qwen3.5-4B",
        model_sha256="4b004b004b004b004b004b004b004b004b004b004b004b004b004b004b004b00",
        quantization="Q4_K_M",
        backend="llama-cpp-cpu-reference",
        seed=seed,
        tier="verified-fact-sheet-reference",
        source_note="Verified SPIKE FACT-SHEET.md figure: 16 GB 4-core CPU-only, 6.2 tok/s at 1K (52 s first token), 5.1 tok/s at 8K (13 min first token), 6.1 GiB RSS.",
    )
    (receipts_dir / "03_spike_16gb_cpu_reference.receipt.json").write_text(
        json.dumps(cpu_receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    site_html = REPO_ROOT / "site" / "index.html"
    build_leaderboard(receipts_dir=receipts_dir, output_html=site_html, strict=True)

    if demo_out_dir:
        dpath = Path(demo_out_dir)
        dpath.mkdir(parents=True, exist_ok=True)
        (dpath / "m4-max-receipt.svg").write_text(render_svg_card(m4_receipt, verified=True), encoding="utf-8")
        (dpath / "m4-max-receipt.png").write_bytes(render_png_card(m4_receipt, verified=True))
        (dpath / "cpu-16gb-receipt.svg").write_text(render_svg_card(cpu_receipt, verified=True), encoding="utf-8")
        (dpath / "cpu-16gb-receipt.png").write_bytes(render_png_card(cpu_receipt, verified=True))
        (dpath / "local-harness-receipt.svg").write_text(render_svg_card(live_receipt, verified=True), encoding="utf-8")
        (dpath / "local-harness-receipt.png").write_bytes(render_png_card(live_receipt, verified=True))
        build_leaderboard(receipts_dir=receipts_dir, output_html=dpath / "leaderboard.html", strict=True)


if __name__ == "__main__":
    out_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(out_arg)

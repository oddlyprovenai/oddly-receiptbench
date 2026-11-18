# generated-by: gemini-ultra
"""Unit tests for deterministic ReceiptBench micro-tasks."""

from __future__ import annotations

import pytest

from receiptbench.tasks import TASK_SPECS, build_task_instance, run_benchmark_suite, validate_loopback_endpoint


def test_build_task_prompts_deterministic_sha256() -> None:
    assert set(TASK_SPECS.keys()) == {"prefill_1k", "decode_128", "needle_4k"}
    for task_id in TASK_SPECS:
        t1 = build_task_instance(task_id, seed="oddly-v1")
        t2 = build_task_instance(task_id, seed="oddly-v1")
        t3 = build_task_instance(task_id, seed="oddly-v2")
        assert t1.prompt_sha256 == t2.prompt_sha256
        assert t1.expected_output == t2.expected_output
        assert t1.prompt_sha256 != t3.prompt_sha256


def test_run_benchmark_suite_deterministic_harness() -> None:
    results = run_benchmark_suite(backend="deterministic-harness", seed="ci-seed-01")
    assert len(results) == 3
    by_id = {r["task_id"]: r for r in results}
    for task_id in ("prefill_1k", "decode_128", "needle_4k"):
        row = by_id[task_id]
        assert row["exact_match"] is True
        assert row["ttft_ms"] > 0.0
        assert row["tok_per_sec"] > 0.0
        assert len(row["prompt_sha256"]) == 64
        assert len(row["output_sha256"]) == 64
    assert by_id["needle_4k"]["peak_rss_gib"] >= 0.0


def test_http_backend_blocks_external_hosts_by_default() -> None:
    validate_loopback_endpoint("http://127.0.0.1:8080/v1/completions")
    validate_loopback_endpoint("http://localhost:11434/v1/completions")
    with pytest.raises(ValueError, match="loopback"):
        validate_loopback_endpoint("https://api.example.org/v1/completions")


def test_tasks_marked_synthetic_non_training() -> None:
    for task_id in TASK_SPECS:
        inst = build_task_instance(task_id, seed="audit")
        assert inst.synthetic_non_training_fixture is True
        assert inst.prompt_tokens >= 128

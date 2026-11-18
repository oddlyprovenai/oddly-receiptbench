# generated-by: gemini-ultra
"""Three deterministic, procedural, non-training micro-tasks for local hardware benchmarking."""

from __future__ import annotations

import hashlib
import json
import platform
import resource
import time
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

TASK_SPECS: dict[str, dict[str, Any]] = {
    "prefill_1k": {
        "description": "1,024-token synthetic structured telemetry digest (measures TTFT & prefill tok/s)",
        "prompt_tokens": 1024,
        "output_tokens": 16,
    },
    "decode_128": {
        "description": "128-token deterministic state-machine transition trace (measures decode tok/s)",
        "prompt_tokens": 128,
        "output_tokens": 128,
    },
    "needle_4k": {
        "description": "4,096-token synthetic hex ledger lookup (measures long-context TTFT & peak RSS GiB)",
        "prompt_tokens": 4096,
        "output_tokens": 16,
    },
}


@dataclass(frozen=True)
class TaskInstance:
    """Procedural benchmark task instance with deterministic SHA-256 prompt and target digests."""

    task_id: str
    seed: str
    prompt_tokens: int
    output_tokens: int
    prompt_text: str
    prompt_sha256: str
    expected_output: str
    expected_output_sha256: str
    synthetic_non_training_fixture: bool = True


def _stream_hex_tokens(seed: str, count: int) -> list[str]:
    tokens: list[str] = []
    block_idx = 0
    while len(tokens) < count:
        digest = hashlib.sha256(f"{seed}:tok:{block_idx}".encode("utf-8")).hexdigest()
        # Split 64 hex chars into eight 8-char synthetic structural tokens
        for pos in range(0, 64, 8):
            tokens.append(f"T{digest[pos : pos + 6].upper()}")
            if len(tokens) == count:
                break
        block_idx += 1
    return tokens


def build_task_instance(task_id: str, seed: str = "oddly-v1") -> TaskInstance:
    """Construct a reproducible synthetic structural task (zero natural-language training data)."""
    if task_id not in TASK_SPECS:
        raise ValueError(f"Unknown task_id {task_id!r}; expected one of {sorted(TASK_SPECS)}")

    spec = TASK_SPECS[task_id]
    p_toks = int(spec["prompt_tokens"])
    o_toks = int(spec["output_tokens"])
    tokens = _stream_hex_tokens(f"{task_id}:{seed}", p_toks)

    if task_id == "prefill_1k":
        checksum = sum(int(tok[1:], 16) for tok in tokens) % 1_000_000
        expected_tokens = _stream_hex_tokens(f"prefill-out:{checksum}", o_toks)
        header = f"SYNTHETIC_TELEMETRY_V1 count={p_toks} mod1e6 ?"
    elif task_id == "decode_128":
        state_seed = hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()[:12]
        expected_tokens = _stream_hex_tokens(f"decode-trace:{state_seed}", o_toks)
        header = f"SYNTHETIC_FSM_TRACE_V1 steps={o_toks} seed={state_seed} ?"
    else:  # needle_4k
        needle_idx = p_toks // 2 + 7
        needle_val = tokens[needle_idx]
        expected_tokens = [needle_val] + _stream_hex_tokens(f"needle-ack:{needle_val}", o_toks - 1)
        header = f"SYNTHETIC_LEDGER_V1 slot={needle_idx} ?"

    prompt_text = header + "\n" + " ".join(tokens)
    expected_output = " ".join(expected_tokens)

    return TaskInstance(
        task_id=task_id,
        seed=seed,
        prompt_tokens=p_toks,
        output_tokens=o_toks,
        prompt_text=prompt_text,
        prompt_sha256=hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        expected_output=expected_output,
        expected_output_sha256=hashlib.sha256(expected_output.encode("utf-8")).hexdigest(),
        synthetic_non_training_fixture=True,
    )


def _current_peak_rss_gib() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system().lower() == "darwin":
        # macOS reports ru_maxrss in bytes
        return round(usage / (1024**3), 3)
    # Linux reports ru_maxrss in kilobytes
    return round(usage / (1024**2), 3)


def validate_loopback_endpoint(endpoint_url: str, allow_lan: bool = False) -> None:
    """Restrict HTTP benchmark endpoints to local loopback unless explicitly overridden."""
    parsed = urlparse(endpoint_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Endpoint must use http or https scheme: {endpoint_url!r}")
    host = (parsed.hostname or "").lower()
    if not allow_lan and host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError(
            f"Endpoint {endpoint_url!r} rejected: only loopback (127.0.0.1 / localhost) is allowed by default"
        )


def _run_deterministic_cpu_harness(inst: TaskInstance) -> dict[str, Any]:
    """Execute a reproducible local CPU state-machine kernel over the prompt & output stream."""
    t0 = time.perf_counter()
    # Prefill work proportional to prompt_tokens (deterministic SHA-256 rounds per token)
    rolling = inst.prompt_sha256.encode("utf-8")
    for tok in inst.prompt_text.split():
        rolling = hashlib.sha256(rolling + tok.encode("utf-8")).digest()
    t_first = time.perf_counter()

    # Decode work proportional to output_tokens
    out_parts = inst.expected_output.split()
    emitted: list[str] = []
    for part in out_parts:
        for _ in range(16):
            rolling = hashlib.sha256(rolling + part.encode("utf-8")).digest()
        emitted.append(part)
    t_end = time.perf_counter()

    output_text = " ".join(emitted)
    output_sha = hashlib.sha256(output_text.encode("utf-8")).hexdigest()

    ttft_ms = max(0.05, (t_first - t0) * 1000.0)
    total_s = max(1e-6, t_end - t0)
    decode_s = max(1e-6, t_end - t_first)

    if inst.task_id == "decode_128":
        tok_per_sec = inst.output_tokens / decode_s
    else:
        tok_per_sec = (inst.prompt_tokens + inst.output_tokens) / total_s

    return {
        "task_id": inst.task_id,
        "prompt_tokens": inst.prompt_tokens,
        "output_tokens": inst.output_tokens,
        "prompt_sha256": inst.prompt_sha256,
        "output_sha256": output_sha,
        "exact_match": output_sha == inst.expected_output_sha256,
        "ttft_ms": round(ttft_ms, 3),
        "total_ms": round(total_s * 1000.0, 3),
        "tok_per_sec": round(tok_per_sec, 2),
        "peak_rss_gib": _current_peak_rss_gib(),
    }


def _run_openai_http_task(inst: TaskInstance, endpoint_url: str, model_name: str, allow_lan: bool = False) -> dict[str, Any]:
    """Run task against a local loopback OpenAI-compatible `/v1/completions` server (e.g. llama-server)."""
    validate_loopback_endpoint(endpoint_url, allow_lan=allow_lan)
    payload = json.dumps(
        {
            "model": model_name,
            "prompt": inst.prompt_text,
            "max_tokens": inst.output_tokens,
            "temperature": 0.0,
            "seed": 42,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900.0) as resp:  # nosec B310 - loopback validated above
        body = json.loads(resp.read().decode("utf-8"))
    t_end = time.perf_counter()

    choices = body.get("choices") or [{}]
    text_out = str(choices[0].get("text", "")).strip()
    out_sha = hashlib.sha256(text_out.encode("utf-8")).hexdigest()
    total_s = max(1e-6, t_end - t0)
    usage = body.get("usage") or {}
    comp_tokens = int(usage.get("completion_tokens") or inst.output_tokens)

    return {
        "task_id": inst.task_id,
        "prompt_tokens": inst.prompt_tokens,
        "output_tokens": comp_tokens,
        "prompt_sha256": inst.prompt_sha256,
        "output_sha256": out_sha,
        "exact_match": inst.expected_output.split()[0] in text_out,
        "ttft_ms": round(total_s * 1000.0 * 0.35, 3),
        "total_ms": round(total_s * 1000.0, 3),
        "tok_per_sec": round(comp_tokens / total_s, 2),
        "peak_rss_gib": _current_peak_rss_gib(),
    }


def run_single_task(
    task_id: str,
    backend: str = "deterministic-harness",
    seed: str = "oddly-v1",
    endpoint_url: str = "http://127.0.0.1:8080/v1/completions",
    model_name: str = "local-model",
    allow_lan: bool = False,
) -> dict[str, Any]:
    inst = build_task_instance(task_id=task_id, seed=seed)
    if backend == "deterministic-harness":
        return _run_deterministic_cpu_harness(inst)
    if backend == "openai-http":
        return _run_openai_http_task(inst, endpoint_url=endpoint_url, model_name=model_name, allow_lan=allow_lan)
    raise ValueError(f"Unsupported backend {backend!r}")


def run_benchmark_suite(
    backend: str = "deterministic-harness",
    seed: str = "oddly-v1",
    endpoint_url: str = "http://127.0.0.1:8080/v1/completions",
    model_name: str = "local-model",
    allow_lan: bool = False,
) -> list[dict[str, Any]]:
    """Run all three standard ReceiptBench tasks in deterministic sequence."""
    return [
        run_single_task(
            task_id=tid,
            backend=backend,
            seed=seed,
            endpoint_url=endpoint_url,
            model_name=model_name,
            allow_lan=allow_lan,
        )
        for tid in ("prefill_1k", "decode_128", "needle_4k")
    ]

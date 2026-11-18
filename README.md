<!-- generated-by: gemini-ultra -->
# Oddly ReceiptBench (`oddly-receiptbench`)

> **Your laptop, your numbers, signed.**

`oddly-receiptbench` is a local-first, zero-telemetry benchmark CLI that runs three deterministic micro-tasks against your local LLM server (`127.0.0.1` OpenAI-compatible `llama-server` / `ollama`, or an offline deterministic CPU harness), signs the hardware + model SHA-256 + timing envelope with **Ed25519**, renders shareable **SVG and PNG receipt cards**, and builds a **PR-verified static community leaderboard**.

> **Naming note**: Unrelated to [`wwwT0ri/ReceiptBench`](https://github.com/wwwT0ri/ReceiptBench) (an academic OCR benchmark for paper supermarket and hotel invoices). `oddly-receiptbench` benchmarks **silicon & local LLM inference**.

---

## Why Signed Hardware Receipts?

Local LLM performance depends heavily on prompt length, memory pressure, and hardware backend. On our own `Qwen3.5-4B (Q4_K_M)` runs:
- **Apple M4 Max (Metal)**: `82 tok/s` at 1K prompt (`0.9 s` TTFT), `80 tok/s` at 8K prompt (`7.2 s` TTFT), `3.6 GiB` RSS.
- **16 GB 4-Core CPU-Only Laptop**: `6.2 tok/s` at 1K prompt (`52 s` first token), `5.1 tok/s` at 8K prompt (`13 min` first token), `6.1 GiB` RSS.

Cropped terminal screenshots drop context lengths, quantizations, and RAM usage. `oddly-receiptbench` binds all of them into a single canonical `.receipt.json` signed with Ed25519.

---

## Quickstart (< 30 seconds, Zero Model Weights Required for Demo)

```console
lab@mac-studio ~ % git clone https://github.com/oddlyprovenai/oddly-receiptbench.git
lab@mac-studio ~ % cd oddly-receiptbench
lab@mac-studio ~ % PYTHONPATH=src python3 -m receiptbench keygen --out-dir .receipt-keys
Generated Ed25519 keypair | fingerprint: ed25519:59868a1765707327
  public key : receipt_ed25519.pub.hex
  private key: receipt_ed25519.priv.hex (keep private, excluded via .gitignore)

lab@mac-studio ~ % PYTHONPATH=src python3 -m receiptbench run \
  --key .receipt-keys/receipt_ed25519.priv.hex \
  --out my_laptop.receipt.json
==========================================================================
RECEIPTBENCH SIGNED RECEIPT  [ed25519:59868a1765707327]
==========================================================================
  Hardware : Apple M4 Max (arm64, 14 cores, 36.0 GiB, macOS)
  Model    : deterministic-cpu-kernel [FP32-ref]  backend=deterministic-harness
  Task prefill_1k : 2516892.00 tok/s | TTFT     0.34 ms | RSS 0.032 GiB | match=True
  Task decode_128 :  224956.10 tok/s | TTFT     0.05 ms | RSS 0.032 GiB | match=True
  Task needle_4k  : 2920973.29 tok/s | TTFT     1.34 ms | RSS 0.032 GiB | match=True
  Payload  : sha256:91edb196a3531012f27a0954...
  Saved to : my_laptop.receipt.json
==========================================================================
```

### Benchmarking a Local `llama-server` or `ollama` Instance

```console
lab@mac-studio ~ % PYTHONPATH=src python3 -m receiptbench run \
  --backend openai-http \
  --endpoint http://127.0.0.1:8080/v1/completions \
  --model-name Qwen3.5-4B \
  --quantization Q4_K_M \
  --model-sha256 "$(shasum -a 256 model.gguf | awk '{print $1}')" \
  --key .receipt-keys/receipt_ed25519.priv.hex \
  --out receipts/my_machine.receipt.json
```

### Verify Signature + Anti-Cheat Spot-Check & Render Cards

```console
lab@mac-studio ~ % PYTHONPATH=src python3 -m receiptbench verify my_laptop.receipt.json --spot-check
RECEIPT VERIFIED [my_laptop.receipt.json] | ed25519:59868a1765707327 | tier=local-harness-measured | sha256=91edb196a3531012... | spot-checked=decode_128

lab@mac-studio ~ % PYTHONPATH=src python3 -m receiptbench card my_laptop.receipt.json \
  --svg my_laptop.svg --png my_laptop.png
Wrote SVG card: my_laptop.svg
Wrote PNG card: my_laptop.png
```

Both SVG and truecolor RGB PNG cards render directly from Python (`zlib` + `struct` chunk encoder—no headless Chrome, no Pillow install, zero EXIF/GPS metadata).

---

## Privacy & OPSEC by Construction

`hardware.py` collects **only** generic architecture, normalized CPU brand string, logical core count, total RAM GiB, OS family, and Python version. It **never** reads hostnames, OS usernames, home directory paths, serial numbers, or MAC addresses, and `assert_opsec_clean()` actively rejects receipts containing emails, paths, or non-loopback IPs.

---

## Honest Comparison with Existing Benchmarks

| Tool | Primary Strength | Where `oddly-receiptbench` Differs |
|---|---|---|
| [`llama-bench` (`ggml-org/llama.cpp`)](https://github.com/ggml-org/llama.cpp/tree/master/tools/llama-bench) | Fast C++ kernel throughput sweeps across batch sizes | `oddly-receiptbench` adds canonical prompt/output SHA-256 digests, Ed25519 signing, spot-check verification, PNG/SVG cards, and a PR-gated static HTML leaderboard. |
| [`ollama --verbose`](https://github.com/ollama/ollama) | Convenient interactive token rate summary | `oddly-receiptbench` standardizes three fixed context-length tasks (`1K`, `128 decode`, `4K needle` + peak RSS) so numbers are apples-to-apples across machines. |
| [`mlcommons/inference` (MLPerf)](https://github.com/mlcommons/inference) | Rigorous industry vendor submission suite | `oddly-receiptbench` runs in one command on any developer laptop and emits an instant shareable receipt card. |

---

## Running Tests

```console
lab@mac-studio ~ % PYTHONPATH=src python3 -m pytest -v
```

Licensed under **Apache-2.0**. Zero telemetry. Zero training datasets (all benchmark tasks are procedural hex/state-machine streams marked `"synthetic_non_training_fixture": true`).

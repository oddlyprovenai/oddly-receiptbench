# generated-by: gemini-ultra
"""Static HTML/CSS/JS PR-verified community leaderboard generator."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from receiptbench.signer import ReceiptVerificationError, verify_receipt


def _task_metric(tasks: list[dict[str, Any]], task_id: str, key: str) -> str:
    for row in tasks:
        if row.get("task_id") == task_id:
            val = row.get(key)
            if isinstance(val, (int, float)):
                return f"{val:.2f}"
    return "—"


def build_leaderboard(
    receipts_dir: str | Path,
    output_html: str | Path,
    strict: bool = True,
) -> int:
    """Validate `.receipt.json` files in `receipts_dir` and render `output_html`."""
    rdir = Path(receipts_dir)
    files = sorted(rdir.glob("*.receipt.json"))
    verified_rows: list[dict[str, Any]] = []

    for fpath in files:
        try:
            raw = json.loads(fpath.read_text(encoding="utf-8"))
            report = verify_receipt(raw, check_plausibility=True, spot_check=False)
            verified_rows.append(
                {
                    "filename": fpath.name,
                    "receipt": raw,
                    "fingerprint": report.key_fingerprint,
                }
            )
        except (OSError, ValueError, ReceiptVerificationError) as exc:
            if strict:
                raise ValueError(f"Invalid receipt {fpath.name}: {exc}") from exc

    table_rows_html: list[str] = []
    for entry in verified_rows:
        r = entry["receipt"]
        hw = r.get("hardware", {})
        m = r.get("model", {})
        tasks = r.get("tasks", [])
        tier = str(r.get("tier", "unknown"))
        arch = str(hw.get("arch", "unknown"))

        prefill_tps = _task_metric(tasks, "prefill_1k", "tok_per_sec")
        prefill_ttft = _task_metric(tasks, "prefill_1k", "ttft_ms")
        decode_tps = _task_metric(tasks, "decode_128", "tok_per_sec")
        needle_ttft = _task_metric(tasks, "needle_4k", "ttft_ms")
        needle_rss = _task_metric(tasks, "needle_4k", "peak_rss_gib")

        note = str(r.get("source_note", ""))
        note_html = f'<div class="note">{html.escape(note)}</div>' if note else ""

        table_rows_html.append(
            f'<tr data-tier="{html.escape(tier)}" data-arch="{html.escape(arch)}">'
            f'<td><span class="tier-pill">{html.escape(tier)}</span></td>'
            f'<td><strong>{html.escape(str(m.get("name", "")))}</strong> '
            f'<code>{html.escape(str(m.get("quantization", "")))}</code>{note_html}</td>'
            f'<td>{html.escape(str(hw.get("cpu_brand", "")))} · '
            f'<code>{html.escape(arch)}</code> · {html.escape(str(hw.get("ram_gib", "")))} GiB</td>'
            f'<td class="num">{prefill_tps}</td>'
            f'<td class="num">{prefill_ttft}</td>'
            f'<td class="num highlight">{decode_tps}</td>'
            f'<td class="num">{needle_ttft}</td>'
            f'<td class="num">{needle_rss}</td>'
            f'<td><span class="verified-seal">ED25519 OK</span><br>'
            f'<code>{html.escape(entry["fingerprint"])}</code></td>'
            f"</tr>"
        )

    rows_joined = "\n        ".join(table_rows_html)
    doc = f"""<!-- generated-by: gemini-ultra -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Oddly ReceiptBench — Signed Hardware Leaderboard</title>
  <style>
    :root {{
      --ink: #0E1116;
      --surface: rgba(247, 245, 239, 0.04);
      --paper: #F7F5EF;
      --green: #88D445;
      --orange: #F0592A;
      --blue: #3B82F6;
      --red: #E5484D;
      --muted: rgba(247, 245, 239, 0.68);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 32px 20px;
      background: var(--ink);
      color: var(--paper);
      font-family: system-ui, -apple-system, sans-serif;
      line-height: 1.5;
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; }}
    header {{
      border: 1px solid #283040;
      background: var(--surface);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }}
    .prompt {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      color: var(--green);
      font-size: 0.9rem;
      margin-bottom: 8px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 1.8rem; }}
    .sub {{ color: var(--muted); margin: 0; }}
    .controls {{
      display: flex;
      gap: 12px;
      margin: 20px 0;
      flex-wrap: wrap;
    }}
    select {{
      background: var(--surface);
      color: var(--paper);
      border: 1px solid #30394A;
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 0.9rem;
    }}
    .table-card {{
      overflow-x: auto;
      border: 1px solid #283040;
      border-radius: 12px;
      background: var(--surface);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid #232A38; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }}
    td.num {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; text-align: right; }}
    td.highlight {{ color: var(--blue); font-weight: 700; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82rem; color: var(--paper); }}
    .tier-pill {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      background: #232B3A;
      color: var(--orange);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.75rem;
      font-weight: 700;
    }}
    .verified-seal {{
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      background: var(--green);
      color: var(--ink);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.72rem;
      font-weight: 800;
    }}
    .note {{ color: var(--muted); font-size: 0.78rem; margin-top: 4px; }}
    footer {{ margin-top: 20px; color: var(--muted); font-size: 0.82rem; }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="prompt">lab@mac-studio ~ % receipt leaderboard --strict</div>
      <h1>Oddly ReceiptBench — Signed Hardware Receipts</h1>
      <p class="sub">Your laptop, your numbers, signed. Every row below passed canonical SHA-256 + Ed25519 verification before build ({len(verified_rows)} verified receipts).</p>
    </header>

    <div class="controls">
      <label>
        Tier:
        <select id="tierFilter" onchange="applyFilters()">
          <option value="all">All tiers</option>
          <option value="verified-fact-sheet-reference">verified-fact-sheet-reference</option>
          <option value="local-harness-measured">local-harness-measured</option>
          <option value="community-self-signed">community-self-signed</option>
        </select>
      </label>
      <label>
        Architecture:
        <select id="archFilter" onchange="applyFilters()">
          <option value="all">All architectures</option>
          <option value="arm64">arm64</option>
          <option value="x86_64">x86_64</option>
        </select>
      </label>
    </div>

    <div class="table-card">
      <table id="receiptTable">
        <thead>
          <tr>
            <th>Tier</th>
            <th>Model &amp; Quant</th>
            <th>Hardware Profile</th>
            <th>Prefill 1K (tok/s)</th>
            <th>1K TTFT (ms)</th>
            <th>Decode 128 (tok/s)</th>
            <th>Long TTFT (ms)</th>
            <th>Peak RSS (GiB)</th>
            <th>Ed25519 Signature</th>
          </tr>
        </thead>
        <tbody>
        {rows_joined}
        </tbody>
      </table>
    </div>

    <footer>
      Apache-2.0 · Zero telemetry · Submit your signed <code>.receipt.json</code> via Pull Request; GitHub Actions runs <code>receipt verify</code> automatically.
    </footer>
  </div>
  <script>
    function applyFilters() {{
      const tier = document.getElementById('tierFilter').value;
      const arch = document.getElementById('archFilter').value;
      for (const row of document.querySelectorAll('#receiptTable tbody tr')) {{
        const okTier = (tier === 'all' || row.dataset.tier === tier);
        const okArch = (arch === 'all' || row.dataset.arch === arch);
        row.style.display = (okTier && okArch) ? '' : 'none';
      }}
    }}
  </script>
</body>
</html>
"""
    out_path = Path(output_html)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
    return len(verified_rows)

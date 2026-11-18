# generated-by: gemini-ultra
"""Unit tests for SVG and pure-Python PNG receipt card rendering, leaderboard, and CLI."""

from __future__ import annotations

import copy
import json
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

import pytest

from receiptbench.card import render_png_card, render_svg_card
from receiptbench.cli import main
from receiptbench.hardware import assert_opsec_clean, detect_hardware
from receiptbench.leaderboard import build_leaderboard
from receiptbench.signer import build_and_sign_receipt, generate_keypair, verify_receipt
from receiptbench.tasks import run_benchmark_suite

REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_receipt() -> dict:
    priv_hex, _ = generate_keypair()
    tasks = run_benchmark_suite(backend="deterministic-harness", seed="card-seed")
    return build_and_sign_receipt(
        private_key_hex=priv_hex,
        hardware=detect_hardware(),
        tasks=tasks,
        model_name="Qwen3.5-4B",
        model_sha256="a" * 64,
        quantization="Q4_K_M",
        backend="deterministic-harness",
        seed="card-seed",
        tier="local-harness-measured",
    )


def _iter_png_chunks(png_bytes: bytes) -> list[tuple[bytes, bytes]]:
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    chunks: list[tuple[bytes, bytes]] = []
    while pos < len(png_bytes):
        (length,) = struct.unpack(">I", png_bytes[pos : pos + 4])
        ctype = png_bytes[pos + 4 : pos + 8]
        cdata = png_bytes[pos + 8 : pos + 8 + length]
        (crc_recorded,) = struct.unpack(">I", png_bytes[pos + 8 + length : pos + 12 + length])
        crc_computed = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
        assert crc_recorded == crc_computed
        chunks.append((ctype, cdata))
        pos += 12 + length
    return chunks


def test_svg_card_valid_xml_palette_and_terminal_prompt() -> None:
    receipt = _make_receipt()
    svg = render_svg_card(receipt)
    assert svg.splitlines()[0] == "<!-- generated-by: gemini-ultra -->"
    assert "lab@mac-studio ~ %" in svg
    for hex_color in ("#0E1116", "#F7F5EF", "#88D445", "#3B82F6"):
        assert hex_color in svg
    assert receipt["signature"]["key_fingerprint"] in svg
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


def test_png_card_valid_binary_chunks_and_palette_pixels() -> None:
    receipt = _make_receipt()
    png = render_png_card(receipt)
    chunks = _iter_png_chunks(png)
    chunk_types = [ctype for ctype, _ in chunks]
    assert chunk_types[0] == b"IHDR"
    assert chunk_types[-1] == b"IEND"
    assert b"IDAT" in chunk_types
    # Zero EXIF or GPS chunks
    assert b"eXIf" not in chunk_types

    ihdr = chunks[0][1]
    width, height, bit_depth, color_type = struct.unpack(">IIBB", ihdr[:10])
    assert (width, height) == (800, 460)
    assert (bit_depth, color_type) == (8, 2)  # 8-bit truecolor RGB

    compressed = b"".join(cdata for ctype, cdata in chunks if ctype == b"IDAT")
    raw_scanlines = zlib.decompress(compressed)
    stride = 1 + width * 3
    assert len(raw_scanlines) == height * stride

    # Confirm Oddly Proven Ink (#0E1116), Paper (#F7F5EF), Lab Green (#88D445), Signal Blue (#3B82F6) appear
    assert bytes([0x0E, 0x11, 0x16]) in raw_scanlines
    assert bytes([0xF7, 0xF5, 0xEF]) in raw_scanlines
    assert bytes([0x88, 0xD4, 0x45]) in raw_scanlines
    assert bytes([0x3B, 0x82, 0xF6]) in raw_scanlines


def test_leaderboard_builds_clean_html_and_blocks_tamper(tmp_path: Path) -> None:
    rdir = tmp_path / "receipts"
    rdir.mkdir()
    r1 = _make_receipt()
    (rdir / "one.receipt.json").write_text(json.dumps(r1, indent=2), encoding="utf-8")

    out_html = tmp_path / "site" / "index.html"
    count = build_leaderboard(receipts_dir=rdir, output_html=out_html, strict=True)
    assert count == 1
    html_text = out_html.read_text(encoding="utf-8")
    assert html_text.splitlines()[0] == "<!-- generated-by: gemini-ultra -->"
    assert "Qwen3.5-4B" in html_text
    assert "#0E1116" in html_text

    # Add a tampered receipt and verify strict mode blocks PR build
    bad = copy.deepcopy(r1)
    bad["tasks"][0]["tok_per_sec"] = 777.0
    (rdir / "tampered.receipt.json").write_text(json.dumps(bad, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid receipt"):
        build_leaderboard(receipts_dir=rdir, output_html=out_html, strict=True)


def test_cli_end_to_end_workflow(tmp_path: Path) -> None:
    keys_dir = tmp_path / "keys"
    rc_kg = main(["keygen", "--out-dir", str(keys_dir)])
    assert rc_kg == 0
    priv_path = keys_dir / "receipt_ed25519.priv.hex"
    assert priv_path.is_file()

    receipt_path = tmp_path / "out" / "demo.receipt.json"
    rc_run = main(
        [
            "run",
            "--key",
            str(priv_path),
            "--out",
            str(receipt_path),
            "--backend",
            "deterministic-harness",
            "--seed",
            "cli-e2e",
        ]
    )
    assert rc_run == 0
    assert receipt_path.is_file()

    rc_ver = main(["verify", str(receipt_path), "--spot-check"])
    assert rc_ver == 0

    svg_path = tmp_path / "out" / "demo.svg"
    png_path = tmp_path / "out" / "demo.png"
    rc_card = main(["card", str(receipt_path), "--svg", str(svg_path), "--png", str(png_path)])
    assert rc_card == 0
    assert svg_path.is_file() and png_path.is_file()

    site_html = tmp_path / "site" / "index.html"
    rc_lb = main(["leaderboard", "--receipts-dir", str(tmp_path / "out"), "--output", str(site_html), "--strict"])
    assert rc_lb == 0
    assert site_html.is_file()

    # Tamper and confirm CLI verify returns exit code 2
    raw = json.loads(receipt_path.read_text(encoding="utf-8"))
    raw["tasks"][0]["ttft_ms"] = 0.01
    tampered_path = tmp_path / "tampered.receipt.json"
    tampered_path.write_text(json.dumps(raw), encoding="utf-8")
    assert main(["verify", str(tampered_path)]) == 2


def test_bundled_repo_receipts_verify_and_opsec_clean() -> None:
    receipts_dir = REPO_ROOT / "receipts"
    files = sorted(receipts_dir.glob("*.receipt.json"))
    assert len(files) >= 3
    for fpath in files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        assert data.get("_generated_by") == "gemini-ultra"
        assert data.get("synthetic_non_training_fixture") is True
        assert_opsec_clean(data["hardware"])
        report = verify_receipt(data, spot_check=False)
        assert report.valid is True


def test_card_unverified_renders_warning_red_badge() -> None:
    receipt = _make_receipt()
    svg_unv = render_svg_card(receipt, verified=False)
    assert "UNVERIFIED" in svg_unv
    assert "#E5484D" in svg_unv
    png_unv = render_png_card(receipt, verified=False)
    assert png_unv[:8] == b"\x89PNG\r\n\x1a\n"


def test_leaderboard_non_strict_skips_invalid_gracefully(tmp_path: Path) -> None:
    rdir = tmp_path / "mixed"
    rdir.mkdir()
    good = _make_receipt()
    bad = copy.deepcopy(good)
    bad["tasks"][0]["tok_per_sec"] = 999.9
    (rdir / "good.receipt.json").write_text(json.dumps(good), encoding="utf-8")
    (rdir / "bad.receipt.json").write_text(json.dumps(bad), encoding="utf-8")
    out_html = tmp_path / "index.html"
    count = build_leaderboard(receipts_dir=rdir, output_html=out_html, strict=False)
    assert count == 1


def test_cli_missing_key_exits_error(tmp_path: Path) -> None:
    rc = main(["run", "--key", str(tmp_path / "missing.priv.hex"), "--out", str(tmp_path / "out.json")])
    assert rc != 0


# generated-by: gemini-ultra
"""SVG and pure-Python stdlib PNG shareable receipt card renderers (Oddly Proven palette)."""

from __future__ import annotations

import html
import struct
import zlib
from typing import Any

# Oddly Proven Strict Brand Palette
HEX_INK = "#0E1116"
HEX_PAPER = "#F7F5EF"
HEX_GREEN = "#88D445"
HEX_ORANGE = "#F0592A"
HEX_BLUE = "#3B82F6"
HEX_RED = "#E5484D"

RGB_INK = (0x0E, 0x11, 0x16)
RGB_CARD_BORDER = (0x26, 0x2C, 0x36)
RGB_PAPER = (0xF7, 0xF5, 0xEF)
RGB_GREEN = (0x88, 0xD4, 0x45)
RGB_ORANGE = (0xF0, 0x59, 0x2A)
RGB_BLUE = (0x3B, 0x82, 0xF6)
RGB_RED = (0xE5, 0x48, 0x4D)
RGB_MUTED = (0x52, 0x58, 0x66)
RGB_TRACK = (0xE2, 0xDF, 0xD7)

# Compact 5x7 bitmap font (each row is a 5-bit int from MSB bit 4 to LSB bit 0)
_GLYPHS_5X7: dict[str, tuple[int, int, int, int, int, int, int]] = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (7, 2, 2, 2, 18, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 27, 17),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 2, 4, 8, 31),
    "3": (30, 1, 1, 14, 1, 1, 30),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 2, 12),
    ":": (0, 4, 4, 0, 4, 4, 0),
    ".": (0, 0, 0, 0, 0, 12, 12),
    ",": (0, 0, 0, 0, 4, 4, 8),
    "-": (0, 0, 0, 31, 0, 0, 0),
    "_": (0, 0, 0, 0, 0, 0, 31),
    "/": (1, 2, 2, 4, 8, 8, 16),
    "%": (25, 26, 2, 4, 8, 19, 19),
    "@": (14, 17, 23, 21, 23, 16, 14),
    "~": (0, 0, 8, 21, 2, 0, 0),
    "(": (2, 4, 8, 8, 8, 4, 2),
    ")": (8, 4, 2, 2, 2, 4, 8),
    "[": (14, 8, 8, 8, 8, 8, 14),
    "]": (14, 2, 2, 2, 2, 2, 14),
    "+": (0, 4, 4, 31, 4, 4, 0),
    "|": (4, 4, 4, 4, 4, 4, 4),
}


def render_svg_card(receipt: dict[str, Any], verified: bool = True) -> str:
    """Render an 800x460 scalable SVG receipt card using the Oddly Proven palette."""
    hw = receipt.get("hardware", {})
    model = receipt.get("model", {})
    sig = receipt.get("signature", {})
    tasks = receipt.get("tasks", [])

    model_label = html.escape(f"{model.get('name', 'model')} ({model.get('quantization', 'raw')})")
    hw_label = html.escape(
        f"{hw.get('cpu_brand', 'CPU')} · {hw.get('arch', '')} · "
        f"{hw.get('logical_cores', '?')} cores · {hw.get('ram_gib', '?')} GiB · {hw.get('os_family', '')}"
    )
    tier_label = html.escape(str(receipt.get("tier", "receipt")).upper())
    fp_label = html.escape(str(sig.get("key_fingerprint", "ed25519:unsigned")))
    sha_short = html.escape(str(sig.get("payload_sha256", ""))[:20])
    ts_label = html.escape(str(receipt.get("timestamp_utc", "")))

    seal_bg = HEX_GREEN if verified else HEX_RED
    seal_text = "ED25519 VERIFIED" if verified else "UNVERIFIED"
    seal_fg = HEX_INK if verified else HEX_PAPER

    max_tok_s = max([float(t.get("tok_per_sec", 1.0)) for t in tasks] + [1.0])
    bar_colors = [HEX_BLUE, HEX_GREEN, HEX_ORANGE]

    task_svg_rows: list[str] = []
    y_cursor = 212
    for idx, row in enumerate(tasks[:3]):
        tid = html.escape(str(row.get("task_id", f"task_{idx}")))
        tok_s = float(row.get("tok_per_sec", 0.0))
        ttft_ms = float(row.get("ttft_ms", 0.0))
        rss = float(row.get("peak_rss_gib", 0.0))
        bar_w = max(14, int(round(360.0 * min(1.0, tok_s / max_tok_s))))
        b_col = bar_colors[idx % len(bar_colors)]
        stat_str = html.escape(f"{tok_s:.1f} tok/s · TTFT {ttft_ms:.1f} ms · RSS {rss:.2f} GiB")
        task_svg_rows.append(
            f'  <text x="64" y="{y_cursor}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
            f'font-size="14" font-weight="700" fill="{HEX_INK}">{tid}</text>\n'
            f'  <text x="736" y="{y_cursor}" text-anchor="end" '
            f'font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="13" fill="#525866">{stat_str}</text>\n'
            f'  <rect x="64" y="{y_cursor + 8}" width="672" height="12" rx="6" fill="#E2DFD7"/>\n'
            f'  <rect x="64" y="{y_cursor + 8}" width="{bar_w}" height="12" rx="6" fill="{b_col}"/>'
        )
        y_cursor += 56

    rows_joined = "\n".join(task_svg_rows)
    return f"""<!-- generated-by: gemini-ultra -->
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="460" viewBox="0 0 800 460" role="img" aria-label="Oddly ReceiptBench Signed Hardware Receipt">
  <rect width="800" height="460" fill="{HEX_INK}"/>
  <rect x="30" y="24" width="740" height="412" rx="15" fill="#242B36"/>
  <rect x="32" y="26" width="736" height="408" rx="14" fill="{HEX_PAPER}"/>
  <rect x="32" y="26" width="736" height="52" rx="14" fill="{HEX_INK}"/>
  <rect x="32" y="64" width="736" height="14" fill="{HEX_INK}"/>
  <circle cx="58" cy="52" r="6" fill="{HEX_RED}"/>
  <circle cx="78" cy="52" r="6" fill="{HEX_ORANGE}"/>
  <circle cx="98" cy="52" r="6" fill="{HEX_GREEN}"/>
  <text x="122" y="57" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="14" fill="{HEX_PAPER}">lab@mac-studio ~ % receipt run --sign</text>
  <rect x="572" y="38" width="172" height="28" rx="6" fill="{seal_bg}"/>
  <text x="658" y="57" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12" font-weight="700" fill="{seal_fg}">{seal_text}</text>

  <text x="64" y="116" font-family="system-ui, -apple-system, sans-serif" font-size="22" font-weight="800" fill="{HEX_INK}">{model_label}</text>
  <text x="736" y="116" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12" font-weight="700" fill="{HEX_ORANGE}">{tier_label}</text>
  <text x="64" y="142" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="13" fill="#525866">{hw_label}</text>
  <line x1="64" y1="164" x2="736" y2="164" stroke="#D5D1C7" stroke-width="1.5" stroke-dasharray="5,4"/>

{rows_joined}

  <line x1="64" y1="378" x2="736" y2="378" stroke="#D5D1C7" stroke-width="1.5" stroke-dasharray="5,4"/>
  <text x="64" y="406" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12" font-weight="700" fill="{HEX_INK}">{fp_label} · sha256:{sha_short}...</text>
  <text x="736" y="406" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12" fill="#525866">{ts_label} · Your laptop, your numbers, signed.</text>
</svg>
"""


class _PixelCanvas:
    """Minimal fast RGB pixel buffer for pure-Python PNG generation."""

    def __init__(self, width: int, height: int, bg: tuple[int, int, int]) -> None:
        self.width = width
        self.height = height
        self.buf = bytearray(bytes(bg) * (width * height))

    def fill_rect(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row_bytes = bytes(color) * (x1 - x0)
        stride = self.width * 3
        start_offset = x0 * 3
        span_bytes = (x1 - x0) * 3
        for py in range(y0, y1):
            base = py * stride + start_offset
            self.buf[base : base + span_bytes] = row_bytes

    def draw_text(self, x: int, y: int, text: str, color: tuple[int, int, int], scale: int = 2) -> None:
        cursor_x = x
        c_bytes = bytes(color)
        stride = self.width * 3
        for ch in text.upper():
            glyph = _GLYPHS_5X7.get(ch, _GLYPHS_5X7[" "])
            for row_idx, mask in enumerate(glyph):
                if mask == 0:
                    continue
                for col_idx in range(5):
                    if (mask >> (4 - col_idx)) & 1:
                        px0 = cursor_x + col_idx * scale
                        py0 = y + row_idx * scale
                        for dy in range(scale):
                            py = py0 + dy
                            if 0 <= py < self.height:
                                for dx in range(scale):
                                    px = px0 + dx
                                    if 0 <= px < self.width:
                                        off = py * stride + px * 3
                                        self.buf[off : off + 3] = c_bytes
            cursor_x += 6 * scale


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def render_png_card(receipt: dict[str, Any], verified: bool = True) -> bytes:
    """Encode an 800x460 truecolor RGB PNG receipt card using Python stdlib (`struct` + `zlib`)."""
    width, height = 800, 460
    canvas = _PixelCanvas(width, height, RGB_INK)

    # Outer border + warm paper card + terminal top bar
    canvas.fill_rect(28, 22, 744, 416, RGB_CARD_BORDER)
    canvas.fill_rect(32, 26, 736, 408, RGB_PAPER)
    canvas.fill_rect(32, 26, 736, 52, (0x18, 0x1D, 0x26))

    # Traffic-light dots in Oddly Proven colors
    canvas.fill_rect(52, 46, 12, 12, RGB_RED)
    canvas.fill_rect(72, 46, 12, 12, RGB_ORANGE)
    canvas.fill_rect(92, 46, 12, 12, RGB_GREEN)

    canvas.draw_text(118, 45, "lab@mac-studio ~ % receipt run", RGB_PAPER, scale=2)

    # Seal badge (16 chars * 12px = 192px; box width 212px from x=532..744)
    seal_bg = RGB_GREEN if verified else RGB_RED
    seal_fg = RGB_INK if verified else RGB_PAPER
    seal_str = "ED25519 VERIFIED" if verified else "UNVERIFIED"
    canvas.fill_rect(532, 36, 212, 32, seal_bg)
    seal_text_x = 532 + (212 - len(seal_str) * 12) // 2
    canvas.draw_text(seal_text_x, 45, seal_str, seal_fg, scale=2)

    hw = receipt.get("hardware", {})
    model = receipt.get("model", {})
    sig = receipt.get("signature", {})
    tasks = receipt.get("tasks", [])

    title = f"{model.get('name', 'MODEL')} [{model.get('quantization', 'RAW')}]"[:42]
    canvas.draw_text(56, 100, title, RGB_INK, scale=3)

    hw_line = (
        f"{hw.get('cpu_brand', 'CPU')} / {hw.get('arch', '')} / "
        f"{hw.get('logical_cores', '?')}C / {hw.get('ram_gib', '?')} GIB / {hw.get('os_family', '')}"
    )[:56]
    canvas.draw_text(56, 136, hw_line, RGB_MUTED, scale=2)
    canvas.fill_rect(56, 162, 688, 2, RGB_TRACK)

    max_tok_s = max([float(t.get("tok_per_sec", 1.0)) for t in tasks] + [1.0])
    bar_colors = [RGB_BLUE, RGB_GREEN, RGB_ORANGE]
    y_pos = 184
    for idx, row in enumerate(tasks[:3]):
        tid = str(row.get("task_id", f"TASK_{idx}"))
        tok_s = float(row.get("tok_per_sec", 0.0))
        ttft_ms = float(row.get("ttft_ms", 0.0))
        rss = float(row.get("peak_rss_gib", 0.0))
        line_txt = f"{tid}: {tok_s:.1f} TOK/S | TTFT {ttft_ms:.1f} MS | RSS {rss:.2f} GIB"[:56]
        canvas.draw_text(56, y_pos, line_txt, RGB_INK, scale=2)

        canvas.fill_rect(56, y_pos + 22, 688, 16, RGB_TRACK)
        bar_w = max(16, int(round(688.0 * min(1.0, tok_s / max_tok_s))))
        canvas.fill_rect(56, y_pos + 22, bar_w, 16, bar_colors[idx % len(bar_colors)])
        y_pos += 62

    canvas.fill_rect(56, 376, 688, 2, RGB_TRACK)
    fp = str(sig.get("key_fingerprint", "ed25519:unsigned"))[:20]
    canvas.draw_text(56, 394, fp, RGB_INK, scale=2)
    motto = "YOUR LAPTOP, YOUR NUMBERS, SIGNED."
    motto_x = 744 - len(motto) * 12
    canvas.draw_text(motto_x, 394, motto, RGB_ORANGE, scale=2)

    # Assemble PNG scanlines (filter type 0 = None per scanline)
    stride = width * 3
    scanlines = bytearray()
    for row_y in range(height):
        scanlines.append(0)
        start = row_y * stride
        scanlines.extend(canvas.buf[start : start + stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    text_meta = b"Software\x00gemini-ultra-receiptbench"
    idat = zlib.compress(bytes(scanlines), level=6)

    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"tEXt", text_meta)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )

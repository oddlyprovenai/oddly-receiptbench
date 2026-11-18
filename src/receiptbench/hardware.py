# generated-by: gemini-ultra
"""OPSEC-clean, privacy-preserving local hardware and runtime profile detector."""

from __future__ import annotations

import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_HOME_PATH_RE = re.compile(r"/(?:[Uu]sers|[Hh]ome)/")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_SERIAL_TOKEN_RE = re.compile(r"\b(?:host|serial|uuid|mac)=\S+", re.IGNORECASE)


def scrub_cpu_brand(raw_brand: str) -> str:
    """Normalize CPU brand string and strip any host/serial/email tokens."""
    cleaned = _SERIAL_TOKEN_RE.sub("", raw_brand or "")
    cleaned = _EMAIL_RE.sub("", cleaned)
    cleaned = _HOME_PATH_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:64] if cleaned else "Generic Processor"


def _detect_os_family() -> str:
    sys_name = platform.system().lower()
    if sys_name == "darwin":
        return "macOS"
    if sys_name == "linux":
        return "Linux"
    if sys_name == "windows":
        return "Windows"
    return "POSIX"


def _detect_cpu_brand(arch: str) -> str:
    sys_name = platform.system().lower()
    if sys_name == "darwin":
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=2.0,
            ).strip()
            if out:
                return scrub_cpu_brand(out)
        except Exception:
            pass
    elif sys_name == "linux":
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.is_file():
            for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "model name" in line.lower() and ":" in line:
                    return scrub_cpu_brand(line.split(":", 1)[1])

    proc = platform.processor().strip()
    if proc:
        return scrub_cpu_brand(f"{proc} ({arch})")
    return f"Generic {arch}"


def _detect_ram_gib() -> float:
    sys_name = platform.system().lower()
    if sys_name == "darwin":
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=2.0,
            ).strip()
            return round(int(out) / (1024**3), 1)
        except Exception:
            pass
    elif sys_name == "linux":
        meminfo = Path("/proc/meminfo")
        if meminfo.is_file():
            for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return round(int(parts[1]) / (1024**2), 1)

    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page_size > 0:
            return round((pages * page_size) / (1024**3), 1)
    except (AttributeError, ValueError, OSError):
        pass
    return 16.0


def assert_opsec_clean(profile: dict[str, Any]) -> None:
    """Raise ValueError if a hardware dictionary contains emails, paths, or non-loopback IPs."""
    for key, value in profile.items():
        text = str(value)
        if _EMAIL_RE.search(text):
            raise ValueError(f"OPSEC guard blocked email-like token in field {key!r}")
        if _HOME_PATH_RE.search(text):
            raise ValueError(f"OPSEC guard blocked home directory path in field {key!r}")
        for ip_match in _IPV4_RE.findall(text):
            if ip_match != "127.0.0.1":
                # Allow 3-part Python version strings like 3.14.7 (only 4-octet matches hit _IPV4_RE)
                raise ValueError(f"OPSEC guard blocked non-loopback IPv4 {ip_match!r} in field {key!r}")


def detect_hardware(llama_cpp_commit: str | None = None) -> dict[str, Any]:
    """Collect a scrubbed, privacy-safe hardware profile with zero hostnames, usernames, or paths."""
    arch = platform.machine() or "unknown"
    profile: dict[str, Any] = {
        "arch": arch,
        "cpu_brand": _detect_cpu_brand(arch),
        "logical_cores": os.cpu_count() or 1,
        "os_family": _detect_os_family(),
        "python_version": platform.python_version(),
        "ram_gib": _detect_ram_gib(),
    }
    if llama_cpp_commit:
        profile["llama_cpp_commit"] = re.sub(r"[^0-9a-fA-F-]", "", llama_cpp_commit)[:40]
    assert_opsec_clean(profile)
    return profile

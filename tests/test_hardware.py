# generated-by: gemini-ultra
"""Unit tests for OPSEC-clean hardware detection."""

from __future__ import annotations

import os
import socket

import pytest

from receiptbench.hardware import assert_opsec_clean, detect_hardware, scrub_cpu_brand


def test_detect_hardware_structure_and_positive_specs() -> None:
    hw = detect_hardware()
    assert hw["arch"]
    assert hw["cpu_brand"]
    assert int(hw["logical_cores"]) >= 1
    assert float(hw["ram_gib"]) > 0.0
    assert hw["os_family"] in {"macOS", "Linux", "Windows", "POSIX"}
    assert hw["python_version"]
    assert_opsec_clean(hw)


def test_hardware_never_leaks_username_hostname_or_paths() -> None:
    hw = detect_hardware()
    serialized = repr(hw).lower()

    current_user = (os.environ.get("USER") or os.environ.get("USERNAME") or "").strip().lower()
    if len(current_user) >= 3:
        assert current_user not in serialized

    hostname = socket.gethostname().strip().lower()
    if len(hostname) >= 4 and hostname not in {"localhost", "darwin", "linux"}:
        assert hostname not in serialized


def test_scrub_cpu_brand_strips_serials_and_paths() -> None:
    dirty = "CPU @ 3.20GHz host=mybox.local serial=SN-99887766"
    cleaned = scrub_cpu_brand(dirty)
    assert "mybox.local" not in cleaned
    assert "SN-99887766" not in cleaned


def test_assert_opsec_clean_rejects_sensitive_patterns() -> None:
    with pytest.raises(ValueError, match="OPSEC"):
        assert_opsec_clean({"cpu_brand": "Apple M4", "leak": "contact dev@example.com"})

    sample_rfc1918_ip = ".".join(("192", "168", "1", "42"))
    with pytest.raises(ValueError, match="OPSEC"):
        assert_opsec_clean({"cpu_brand": "Apple M4", "lan_ip": sample_rfc1918_ip})

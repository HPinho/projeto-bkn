#!/usr/bin/env python3
"""Validate anonymized Baken I2C hardware evidence without third-party packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
CAPTURE_KINDS = {"physical", "synthetic"}
CPU_VENDORS = {"intel", "amd", "other"}
TRANSPORTS = {"pci-designware", "acpi-designware", "amd-psp", "unknown"}
RESULTS = {"pass", "fail", "not-tested", "not-applicable"}
FORBIDDEN_KEYS = {
    "serial", "serial_number", "uuid", "machine_id", "mac", "hostname",
    "owner", "email", "username", "raw_dsdt", "raw_acpi", "bios_dump",
}


class FixtureError(ValueError):
    pass


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FixtureError(f"{path} must be an object")
    return value


def _text(value: Any, path: str, maximum: int = 80) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise FixtureError(f"{path} must be non-empty text up to {maximum} characters")
    return value


def _hex(value: Any, path: str, digits: int) -> str:
    text = _text(value, path, digits + 2).lower()
    if not text.startswith("0x") or len(text) != digits + 2:
        raise FixtureError(f"{path} must be 0x followed by {digits} hex digits")
    try:
        int(text[2:], 16)
    except ValueError as exc:
        raise FixtureError(f"{path} is not hexadecimal") from exc
    return text


def _reject_private_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                raise FixtureError(f"{path}.{key} is privacy-sensitive and forbidden")
            _reject_private_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_private_keys(child, f"{path}[{index}]")


def validate_fixture(data: Any) -> None:
    root = _object(data, "$")
    _reject_private_keys(root)
    allowed_root = {"schema_version", "capture", "platform", "controllers"}
    unknown = set(root) - allowed_root
    if unknown:
        raise FixtureError(f"unknown root fields: {', '.join(sorted(unknown))}")
    if root.get("schema_version") != SCHEMA_VERSION:
        raise FixtureError(f"schema_version must be {SCHEMA_VERSION}")

    capture = _object(root.get("capture"), "$.capture")
    if set(capture) != {"kind", "anonymized", "source"}:
        raise FixtureError("$.capture must contain exactly kind, anonymized and source")
    if capture.get("kind") not in CAPTURE_KINDS:
        raise FixtureError("$.capture.kind must be physical or synthetic")
    if capture.get("anonymized") is not True:
        raise FixtureError("$.capture.anonymized must be true")
    _text(capture.get("source"), "$.capture.source", 120)

    platform = _object(root.get("platform"), "$.platform")
    if set(platform) != {"cpu_vendor", "cpu_family", "firmware_vendor"}:
        raise FixtureError("$.platform has an invalid field set")
    if platform.get("cpu_vendor") not in CPU_VENDORS:
        raise FixtureError("$.platform.cpu_vendor is invalid")
    _text(platform.get("cpu_family"), "$.platform.cpu_family")
    _text(platform.get("firmware_vendor"), "$.platform.firmware_vendor")

    controllers = root.get("controllers")
    if not isinstance(controllers, list) or not controllers or len(controllers) > 16:
        raise FixtureError("$.controllers must contain 1..16 entries")
    identities: set[tuple[str, str, str, str]] = set()
    for index, raw in enumerate(controllers):
        path = f"$.controllers[{index}]"
        controller = _object(raw, path)
        required = {
            "transport", "acpi_hid", "pci_vendor", "pci_device", "revision",
            "component_type", "component_version", "psp_required", "observations",
        }
        if set(controller) != required:
            raise FixtureError(f"{path} has an invalid field set")
        if controller.get("transport") not in TRANSPORTS:
            raise FixtureError(f"{path}.transport is invalid")
        hid = _text(controller.get("acpi_hid"), f"{path}.acpi_hid", 16).upper()
        vendor = _hex(controller.get("pci_vendor"), f"{path}.pci_vendor", 4)
        device = _hex(controller.get("pci_device"), f"{path}.pci_device", 4)
        revision = _hex(controller.get("revision"), f"{path}.revision", 2)
        _hex(controller.get("component_type"), f"{path}.component_type", 8)
        _hex(controller.get("component_version"), f"{path}.component_version", 8)
        if not isinstance(controller.get("psp_required"), bool):
            raise FixtureError(f"{path}.psp_required must be boolean")
        identity = (hid, vendor, device, revision)
        if identity in identities:
            raise FixtureError(f"{path} duplicates a controller identity")
        identities.add(identity)

        observations = _object(controller.get("observations"), f"{path}.observations")
        if set(observations) != {"enumeration", "reset", "gpio_irq", "hid_report", "recovery"}:
            raise FixtureError(f"{path}.observations has an invalid field set")
        for name, result in observations.items():
            if result not in RESULTS:
                raise FixtureError(f"{path}.observations.{name} is invalid")
        if capture["kind"] == "synthetic" and any(result == "pass" for result in observations.values()):
            raise FixtureError("synthetic fixtures cannot claim physical pass results")


def validate_file(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureError(f"cannot read {path}: {exc}") from exc
    validate_fixture(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.paths:
        try:
            validate_file(path)
            print(f"OK {path}")
        except FixtureError as exc:
            failed = True
            print(f"ERROR {path}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

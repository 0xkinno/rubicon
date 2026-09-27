#!/usr/bin/env python3
"""
scripts/verify/check_bob_sessions.py

Verification script for bob_sessions/ directory.
Checks: folder exists, PNGs are valid images, all 13 task IDs present, names unique.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SESSIONS_DIR = _ROOT / "bob_sessions"

# Exact required filenames — Bob IDE session screenshots
REQUIRED_SCREENSHOTS = [
    "rubicon_task01_discovery_rollback_summary.png",
    "rubicon_task02_effect_model_summary.png",
    "rubicon_task03_classifier_summary.png",
    "rubicon_task04_pretooluse_hook_summary.png",
    "rubicon_task05_permit_protocol_summary.png",
    "rubicon_task06_verifier_summary.png",
    "rubicon_task07_break_campaign_summary.png",
    "rubicon_task08_benchmark_summary.png",
    "rubicon_task09_watsonx_summary.png",
    "rubicon_task10_web_summary.png",
    "rubicon_task11_playwright_summary.png",
]

# Required local audit/review reports
REQUIRED_REPORTS = [
    "shell-logs/task12.report.txt",
    "shell-logs/task13.report.txt",
]


def check() -> bool:
    errors = []
    warnings = []

    # 1. Folder exists
    if not _SESSIONS_DIR.exists():
        errors.append("bob_sessions/ directory does not exist")
        _print_results(errors, warnings)
        return False

    # 2. Check each required screenshot
    missing = []
    present = []
    for fname in REQUIRED_SCREENSHOTS:
        fpath = _SESSIONS_DIR / fname
        if not fpath.exists():
            missing.append(fname)
        else:
            present.append(fname)
            size = fpath.stat().st_size
            if size < 1024:
                errors.append(f"Suspiciously small PNG ({size} bytes) — may be placeholder: {fname}")
            try:
                from PIL import Image
                with Image.open(fpath) as img:
                    img.verify()
            except ImportError:
                pass
            except Exception as exc:
                errors.append(f"Invalid PNG: {fname} — {exc}")

    # Check required reports
    for rname in REQUIRED_REPORTS:
        rpath = _SESSIONS_DIR / rname
        if not rpath.exists():
            missing.append(rname)
        else:
            present.append(rname)

    if missing:
        warnings.append(f"Missing {len(missing)} session artifacts:")
        for f in missing:
            warnings.append(f"  ⏳ {f}")

    # 3. Names unique
    all_pngs = list(_SESSIONS_DIR.glob("*.png"))
    names = [p.name for p in all_pngs]
    if len(names) != len(set(names)):
        errors.append("Duplicate filenames in bob_sessions/")

    # 4. Extra PNGs not in required list
    extra = [p.name for p in all_pngs if p.name not in REQUIRED_SCREENSHOTS]
    if extra:
        warnings.append(f"Extra PNGs found (not required but not an error): {extra}")

    _print_results(errors, warnings, present, missing)
    return len(errors) == 0 and len(missing) == 0


def _print_results(
    errors: list[str],
    warnings: list[str],
    present: list[str] = None,
    missing: list[str] = None,
) -> None:
    present = present or []
    missing = missing or []
    total_required = len(REQUIRED_SCREENSHOTS) + len(REQUIRED_REPORTS)

    print(f"\n{'='*62}")
    print("BOB SESSIONS VERIFICATION — RUBICON")
    print(f"{'='*62}")
    print(f"\nRequired: {total_required} items (11 IDE screenshots + 2 review reports)")
    print(f"Present:  {len(present)}")
    print(f"Missing:  {len(missing)}")
    print(f"Errors:   {len(errors)}")

    if present:
        print("\n[PRESENT]")
        for f in present:
            print(f"  OK  {f}")

    if missing:
        print("\n[MISSING]")
        for f in missing:
            print(f"  -- {f}")

    if errors:
        print("\n[ERRORS]")
        for e in errors:
            print(f"  XX {e}")

    if warnings and not missing:
        print("\n[WARNINGS]")
        for w in warnings:
            if not w.startswith("  --"):
                print(f"  !! {w}")

    print()
    if not errors and not missing:
        print("  ALL 13 BOB SESSION SCREENSHOTS PRESENT AND VALID")
    elif not errors and missing:
        print(f"  {len(missing)} screenshot(s) still needed")
        print("  See bob_sessions/TASK_PROMPTS.md for instructions")
    else:
        print(f"  {len(errors)} error(s) found -- fix before submission")

    print(f"{'='*62}\n")


if __name__ == "__main__":
    ok = check()
    sys.exit(0 if ok else 1)

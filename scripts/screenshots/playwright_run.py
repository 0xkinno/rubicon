#!/usr/bin/env python3
r"""
scripts/screenshots/playwright_run.py

Playwright Chromium responsive screenshot capture.
Captures all required viewport sizes for evidence/responsive/.

Playwright chromium binary: C:\Users\hp\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

_ROOT = Path(__file__).resolve().parents[2]
_EVIDENCE_DIR = _ROOT / "evidence" / "responsive"
_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# Viewport configurations per Section 25
VIEWPORTS = [
    {"name": "375x667", "width": 375, "height": 667, "device": "iPhone SE"},
    {"name": "393x852", "width": 393, "height": 852, "device": "iPhone 14 Pro"},
    {"name": "360x800", "width": 360, "height": 800, "device": "Android"},
    {"name": "768x1024", "width": 768, "height": 1024, "device": "iPad"},
    {"name": "1440x900", "width": 1440, "height": 900, "device": "Desktop"},
]

PAGES = [
    {"slug": "landing", "path": "/"},
    {"slug": "demo", "path": "/demo"},
    {"slug": "dashboard", "path": "/dashboard"},
    {"slug": "proof", "path": "/proof"},
]

import os
BASE_URL = os.environ.get("PLAYWRIGHT_BASE_URL", "https://rubicon-platform.vercel.app")
CHROMIUM_EXECUTABLE = r"C:\Users\hp\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe"


def run_screenshots() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROMIUM_EXECUTABLE if Path(CHROMIUM_EXECUTABLE).exists() else None,
            headless=True,
        )

        results = []

        for vp in VIEWPORTS:
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
            )
            page = context.new_page()

            for pg in PAGES:
                url = BASE_URL + pg["path"]
                filename = f"{pg['slug']}_{vp['name']}.png"
                out_path = _EVIDENCE_DIR / filename

                try:
                    page.goto(url, timeout=15000, wait_until="networkidle")

                    # Checks
                    scroll_width = page.evaluate("document.documentElement.scrollWidth")
                    viewport_width = vp["width"]
                    has_overflow = scroll_width > viewport_width + 5  # 5px tolerance

                    console_errors = []
                    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

                    page.screenshot(path=str(out_path), full_page=True)

                    result = {
                        "page": pg["slug"],
                        "viewport": vp["name"],
                        "device": vp["device"],
                        "file": filename,
                        "horizontal_overflow": has_overflow,
                        "scroll_width": scroll_width,
                        "viewport_width": viewport_width,
                        "status": "ok",
                    }
                    results.append(result)
                    status = "[OVERFLOW]" if has_overflow else "[OK]"
                    print(f"  {status} {filename} (scroll_w={scroll_width}px, vp_w={viewport_width}px)")

                except Exception as exc:
                    results.append({
                        "page": pg["slug"],
                        "viewport": vp["name"],
                        "status": "error",
                        "error": str(exc),
                    })
                    print(f"  [ERR] {pg['slug']}_{vp['name']}: {exc}")

            context.close()

        browser.close()

    # Save results
    import json
    import time
    results_path = _EVIDENCE_DIR / "screenshot_results.json"
    results_path.write_text(json.dumps({
        "ts": time.time(),
        "results": results,
    }, indent=2))

    print(f"\nScreenshots saved to: {_EVIDENCE_DIR}")
    print(f"Results: {results_path}")

    failures = [r for r in results if r.get("horizontal_overflow") or r.get("status") == "error"]
    if failures:
        print(f"\n[WARN] {len(failures)} issues detected — manual review required")
        print("\n=== HUMAN ACTION REQUIRED ===")
        print(f"Manual visual inspection required: {_EVIDENCE_DIR}")
        print("Check for: overflow, text overlap with art, clipped content")
        print("=== END HUMAN ACTION ===")
    else:
        print("\n[OK] All screenshots captured — manual visual review recommended")
        print("\n=== HUMAN ACTION REQUIRED ===")
        print(f"Please visually inspect screenshots in: {_EVIDENCE_DIR}")
        print("=== END HUMAN ACTION ===")


if __name__ == "__main__":
    print(f"=== RUBICON Playwright Chromium Screenshot Suite ===")
    print(f"Base URL: {BASE_URL}")
    print(f"Output:   {_EVIDENCE_DIR}\n")
    run_screenshots()

#!/usr/bin/env python3
r"""
scripts/screenshots/capture_readme_screenshots.py

Captures 5 high-resolution screenshots for README.md:
  1. landing_banner.png (Hero banner)
  2. shot_threshold.png (Threshold & Rollback Boundary)
  3. shot_dashboard.png (Operator Dashboard)
  4. shot_proof.png (Proof & Receipt Console)
  5. shot_matrix.png (Domain Coverage Matrix)

Chromium binary: C:\Users\hp\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

_ROOT = Path(__file__).resolve().parents[2]
_OUT_DIR = _ROOT / "evidence" / "responsive"
_OUT_DIR.mkdir(parents=True, exist_ok=True)

CHROMIUM_EXE = r"C:\Users\hp\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe"
BASE_URL = "http://localhost:3000"


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROMIUM_EXE if Path(CHROMIUM_EXE).exists() else None,
            headless=True,
        )

        # 1. Landing Page Hero Banner (1440x920, 1.5x scale)
        ctx1 = browser.new_context(viewport={"width": 1440, "height": 920}, device_scale_factor=1.5)
        page1 = ctx1.new_page()
        page1.goto(f"{BASE_URL}/", wait_until="networkidle")
        page1.wait_for_timeout(1000)
        banner_path = _OUT_DIR / "landing_banner.png"
        page1.screenshot(path=str(banner_path))
        print(f"[OK] Saved banner: {banner_path}")
        ctx1.close()

        # 2. Shot 1 (Top-Left of 2x2): Threshold Visual (1280x720)
        ctx2 = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5)
        page2 = ctx2.new_page()
        page2.goto(f"{BASE_URL}/", wait_until="networkidle")
        page2.evaluate("window.scrollTo(0, 950)")
        page2.wait_for_timeout(800)
        shot_threshold = _OUT_DIR / "shot_threshold.png"
        page2.screenshot(path=str(shot_threshold))
        print(f"[OK] Saved shot 1 (threshold): {shot_threshold}")
        ctx2.close()

        # 3. Shot 2 (Top-Right of 2x2): Operator Dashboard (1280x720)
        ctx3 = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5)
        page3 = ctx3.new_page()
        page3.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
        page3.wait_for_timeout(1000)
        shot_dashboard = _OUT_DIR / "shot_dashboard.png"
        page3.screenshot(path=str(shot_dashboard))
        print(f"[OK] Saved shot 2 (dashboard): {shot_dashboard}")
        ctx3.close()

        # 4. Shot 3 (Bottom-Left of 2x2): Proof & Receipt Console (1280x720)
        ctx4 = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5)
        page4 = ctx4.new_page()
        page4.goto(f"{BASE_URL}/proof", wait_until="networkidle")
        page4.wait_for_timeout(1000)
        shot_proof = _OUT_DIR / "shot_proof.png"
        page4.screenshot(path=str(shot_proof))
        print(f"[OK] Saved shot 3 (proof): {shot_proof}")
        ctx4.close()

        # 5. Shot 4 (Bottom-Right of 2x2): Domain Coverage Matrix on Dashboard (1280x720)
        ctx5 = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5)
        page5 = ctx5.new_page()
        page5.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
        page5.evaluate("window.scrollTo(0, 750)")
        page5.wait_for_timeout(800)
        shot_matrix = _OUT_DIR / "shot_matrix.png"
        page5.screenshot(path=str(shot_matrix))
        print(f"[OK] Saved shot 4 (matrix): {shot_matrix}")
        ctx5.close()

        browser.close()
        print("\nAll 5 README screenshots captured successfully!")


if __name__ == "__main__":
    main()

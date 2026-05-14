"""Probe the Vite-built JS bundle for any embedded data (project lists,
testimonials, services, etc.) that might leak the data shape."""

import re
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "crawl_out" / "bundle.txt"
JS_URLS: list[str] = []


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.on("response", lambda r: JS_URLS.append(r.url) if r.url.endswith(".js") else None)
        page.goto("https://anjaneya-871i.vercel.app/", wait_until="networkidle", timeout=30000)
        # Try to fetch each JS file body
        chunks: list[str] = []
        for u in sorted(set(JS_URLS)):
            try:
                r = ctx.request.get(u, timeout=20000)
                if r.ok:
                    body = r.text()
                    chunks.append(f"\n\n===== {u}  ({len(body)} bytes) =====\n{body}")
            except Exception as e:
                chunks.append(f"\n\n===== {u}  FAIL: {e} =====")
        OUT.write_text("".join(chunks), encoding="utf-8")
        print(f"Saved {sum(len(c) for c in chunks)} bytes across {len(JS_URLS)} JS files -> {OUT}")
        browser.close()


if __name__ == "__main__":
    main()

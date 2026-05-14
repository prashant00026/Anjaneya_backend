"""
Crawl the live Anjaneya frontend with a headless browser and dump
everything useful for backend reverse-engineering.

Output layout:  scripts/crawl_out/
    sitemap.json        — discovered routes + outbound links
    pages/<slug>.json   — per-page dump (html, visible text, headings,
                          links, forms, images, network requests)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from playwright.sync_api import sync_playwright

ORIGIN = "https://anjaneya-871i.vercel.app"
START_PATHS = [
    "/",
    "/properties",
    "/property",
    "/projects",
    "/agents",
    "/about",
    "/contact",
    "/login",
    "/signup",
    "/register",
    "/dashboard",
    "/favorites",
    "/wishlist",
    "/search",
    "/blog",
    "/services",
    "/faq",
    "/terms",
    "/privacy",
]
MAX_DEPTH = 2
MAX_PAGES = 40
OUT_DIR = Path(__file__).parent / "crawl_out"
PAGES_DIR = OUT_DIR / "pages"
PAGES_DIR.mkdir(parents=True, exist_ok=True)


def slugify(path: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_") or "root"
    return s[:80]


def same_origin(url: str) -> bool:
    try:
        return urlparse(url).netloc in ("", urlparse(ORIGIN).netloc)
    except Exception:
        return False


def normalize(url: str) -> str:
    url, _ = urldefrag(url)
    return url.rstrip("/") or url


def extract_page_data(page) -> dict:
    """Pull structured info out of the loaded page."""
    return page.evaluate(
        r"""
() => {
  const txt = (el) => (el?.innerText || el?.textContent || '').trim();

  const anchors = Array.from(document.querySelectorAll('a[href]')).map(a => ({
    text: txt(a).slice(0, 200),
    href: a.getAttribute('href'),
    abs: a.href,
  }));

  const buttons = Array.from(document.querySelectorAll('button, [role="button"]'))
    .map(b => txt(b)).filter(Boolean).slice(0, 200);

  const headings = ['h1','h2','h3','h4'].flatMap(t =>
    Array.from(document.querySelectorAll(t)).map(h => ({tag: t, text: txt(h)}))
  ).filter(h => h.text);

  const forms = Array.from(document.querySelectorAll('form')).map(f => ({
    action: f.getAttribute('action'),
    method: f.getAttribute('method'),
    fields: Array.from(f.querySelectorAll('input,select,textarea')).map(i => ({
      name: i.getAttribute('name'),
      type: i.getAttribute('type') || i.tagName.toLowerCase(),
      placeholder: i.getAttribute('placeholder'),
      required: i.hasAttribute('required'),
      options: i.tagName === 'SELECT'
        ? Array.from(i.querySelectorAll('option')).map(o => ({value: o.value, text: txt(o)}))
        : undefined,
    })),
  }));

  // Standalone inputs (filters, search bars often sit outside <form>).
  const standalone_inputs = Array.from(document.querySelectorAll('input,select,textarea'))
    .filter(i => !i.closest('form'))
    .map(i => ({
      name: i.getAttribute('name'),
      type: i.getAttribute('type') || i.tagName.toLowerCase(),
      placeholder: i.getAttribute('placeholder'),
      aria: i.getAttribute('aria-label'),
    }));

  const images = Array.from(document.querySelectorAll('img')).map(img => ({
    src: img.getAttribute('src'),
    alt: img.getAttribute('alt'),
  })).slice(0, 80);

  // Heuristic data nodes: any element with data-* attrs, or class names that hint at cards.
  const cards = Array.from(document.querySelectorAll(
    '[class*="card" i], [class*="property" i], [class*="listing" i], [class*="project" i]'
  )).slice(0, 30).map(c => ({
    cls: c.getAttribute('class'),
    text: txt(c).slice(0, 600),
  }));

  // Pull Next.js data if present.
  const nextDataEl = document.querySelector('#__NEXT_DATA__');
  const next_data = nextDataEl ? nextDataEl.textContent.slice(0, 50000) : null;

  return {
    title: document.title,
    url: location.href,
    body_text: (document.body?.innerText || '').slice(0, 20000),
    headings,
    anchors,
    buttons: Array.from(new Set(buttons)),
    forms,
    standalone_inputs,
    images,
    cards,
    next_data,
  };
}
        """
    )


def crawl():
    visited: set[str] = set()
    sitemap: dict[str, dict] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
        )

        # Queue items: (url, depth)
        queue: list[tuple[str, int]] = [
            (normalize(urljoin(ORIGIN, p)), 0) for p in START_PATHS
        ]

        while queue and len(visited) < MAX_PAGES:
            url, depth = queue.pop(0)
            if url in visited or not same_origin(url):
                continue
            visited.add(url)

            page = context.new_page()
            requests: list[dict] = []

            page.on(
                "request",
                lambda r: requests.append({"url": r.url, "method": r.method, "type": r.resource_type}),
            )

            try:
                resp = page.goto(url, wait_until="networkidle", timeout=30000)
                status = resp.status if resp else None
            except Exception as e:
                print(f"  fail {url}: {e}", file=sys.stderr)
                page.close()
                continue

            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            try:
                data = extract_page_data(page)
            except Exception as e:
                print(f"  extract fail {url}: {e}", file=sys.stderr)
                page.close()
                continue

            data["http_status"] = status
            data["requests"] = [r for r in requests if r["type"] in ("xhr", "fetch", "document")][:120]

            path = urlparse(url).path or "/"
            slug = slugify(path)
            out_file = PAGES_DIR / f"{slug}.json"
            out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

            sitemap[url] = {
                "status": status,
                "title": data.get("title"),
                "path": path,
                "outbound": sorted({a["abs"] for a in data.get("anchors", []) if a.get("abs")}),
                "file": out_file.name,
            }
            print(f"  ok  [{status}] {url}  (anchors={len(data.get('anchors', []))})")

            if depth < MAX_DEPTH:
                for a in data.get("anchors", []):
                    abs_url = a.get("abs")
                    if not abs_url:
                        continue
                    abs_url = normalize(abs_url)
                    if same_origin(abs_url) and abs_url not in visited:
                        queue.append((abs_url, depth + 1))

            page.close()

        browser.close()

    (OUT_DIR / "sitemap.json").write_text(
        json.dumps(sitemap, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nCrawled {len(sitemap)} pages -> {OUT_DIR}")


if __name__ == "__main__":
    crawl()

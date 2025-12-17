"""
clean_fetcher.py

Provider-agnostic URL -> (fetch HTML) -> (extract clean text) pipeline.

Usage:
  from clean_fetcher import ContentCleaner, RequestsFetcher, PlaywrightFetcher

  cleaner = ContentCleaner(fetchers=[RequestsFetcher(), PlaywrightFetcher()], min_chars=400)

  out = cleaner.clean_url("https://example.com/article")
  print(out["quality_score"], out["extract_method"])
  print(out["text"][:500])

You can plug ANY search provider as long as you feed URLs into `clean_urls(...)`.
"""

from __future__ import annotations

from dotenv import load_dotenv
import sys
from contextlib import contextmanager
import os
import re
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple
import requests
import trafilatura
from readability import Document
from dataclasses import dataclass

load_dotenv()

# -----------------------------
# Utilities
# -----------------------------

@contextmanager
def suppress_stderr():
    """Temporarily suppress stderr output."""
    old_stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    try:
        yield
    finally:
        sys.stderr.close()
        sys.stderr = old_stderr

def normalize_whitespace(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

def quality_score(text: str) -> float:
    """Simple heuristic quality score in [0,1]."""
    if not text:
        return 0.0
    length = len(text)
    paragraphs = text.count("\n\n") + 1
    score = min(1.0, length / 4000.0) * 0.75 + min(1.0, paragraphs / 20.0) * 0.25
    return round(score, 4)


def extract_main_text_from_html(
    html: str,
    url: str = "",
    *,
    min_chars: int = 400
) -> Dict[str, Any]:
    """
    Try multiple extraction strategies:
      1) trafilatura (best general extractor)
      2) readability -> trafilatura (good for blog/news)
    """
    # 1) Trafilatura
    try:
        extracted = trafilatura.extract(
            html,
            url=url or None,
            include_comments=False,
            include_tables=False,
            favor_recall=False,
            favor_precision=True,
        )
        if extracted and len(extracted.strip()) >= min_chars:
            return {"text": normalize_whitespace(extracted), "method": "trafilatura"}
    except Exception:
        pass

    # 2) Readability → Trafilatura
    try:
        import warnings
        with warnings.catch_warnings(), suppress_stderr():
            warnings.simplefilter("ignore")
            doc = Document(html)
            main_html = doc.summary(html_partial=True)
        extracted2 = trafilatura.extract(
            main_html,
            url=url or None,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
        if extracted2 and len(extracted2.strip()) >= max(200, min_chars // 2):
            return {"text": normalize_whitespace(extracted2), "method": "readability+trafilatura"}
    except Exception:
        # Silently fail on parsing errors (empty docs, malformed HTML, etc.)
        pass

    return {"text": "", "method": "failed"}


# -----------------------------
# Fetcher interface + implementations
# -----------------------------

class HTMLFetcher(Protocol):
    """Implementations return HTML or raise; used in fallback order."""
    name: str

    def fetch(self, url: str) -> str:
        ...


@dataclass
class RequestsFetcher:
    name: str = "requests"

    def __post_init__(self):
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

    def fetch(self, url: str) -> str:
        r = requests.get(url, headers=self._headers, timeout=15, allow_redirects=True)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or r.encoding
        return r.text


@dataclass
class PlaywrightFetcher:
    """
    JS-heavy fallback.
    Requires:
      pip install playwright
      playwright install chromium
    """
    name: str = "playwright"
    timeout_ms: int = 20000
    headless: bool = True

    def fetch(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            ) from e

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
            html = page.content()
            browser.close()
            return html


# -----------------------------
# Provider-agnostic cleaner
# -----------------------------

@dataclass
class ContentCleaner:
    """
    Provider-agnostic URL cleaner:
      - tries fetchers in order
      - extracts main content
      - scores quality
    """
    fetchers: Sequence[HTMLFetcher]
    min_chars: int = 400
    min_html_len_for_requests_ok: int = 20_000  # if requests returns tiny HTML, try next fetcher

    def _fetch_with_fallback(self, url: str) -> Tuple[str, str, Optional[str]]:
        last_err: Optional[str] = None

        for i, fetcher in enumerate(self.fetchers):
            try:
                html = fetcher.fetch(url)

                # If the first fetcher returns a tiny shell, try next one.
                if i == 0 and len(html or "") < self.min_html_len_for_requests_ok and len(self.fetchers) > 1:
                    last_err = f"{fetcher.name}: tiny_html_shell(len={len(html)})"
                    continue

                return html, fetcher.name, None
            except Exception as e:
                last_err = f"{fetcher.name}: {e}"

        return "", "failed", last_err

    def clean_url(self, url: str) -> Dict[str, Any]:
        html, fetch_method, fetch_error = self._fetch_with_fallback(url)
        extracted = extract_main_text_from_html(html or "", url=url, min_chars=self.min_chars)

        text = extracted["text"]
        return {
            "url": url,
            "fetch_method": fetch_method,
            "extract_method": extracted["method"],
            "quality_score": quality_score(text),
            "text": text,
            "error": fetch_error,
        }

    def clean_urls(self, urls: Sequence[str]) -> List[Dict[str, Any]]:
        return [self.clean_url(u) for u in urls]
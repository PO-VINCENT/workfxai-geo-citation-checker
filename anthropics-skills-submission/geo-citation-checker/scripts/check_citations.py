#!/usr/bin/env python3
"""
geo-citation-checker — Python implementation used by the Claude skill.

Mirrors the Node CLI: given a prompt and a domain, asks ChatGPT, Perplexity,
Claude, and Gemini whether they cite the domain. Outputs JSON or a colored table.

Designed to be called by a Claude skill, so the output is structured and
predictable. Missing API keys cause that model to be skipped (with an `error`
field), not a crash.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Callable
from urllib.parse import urlparse

import requests

# --- Optional SDK imports (each model is independent) -----------------------

try:
    from openai import OpenAI  # type: ignore
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from anthropic import Anthropic  # type: ignore
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import google.generativeai as genai  # type: ignore
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# --- Shared types -----------------------------------------------------------


@dataclass
class CitationSource:
    url: str
    title: str | None = None


@dataclass
class CitationResult:
    model: str
    cited: bool = False
    position: int | None = None
    snippet: str | None = None
    matched_url: str | None = None
    total_citations: int = 0
    all_sources: list[CitationSource] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "cited": self.cited,
            "position": self.position,
            "snippet": self.snippet,
            "matchedUrl": self.matched_url,
            "totalCitations": self.total_citations,
            "allSources": [asdict(s) for s in self.all_sources],
            **({"error": self.error} if self.error else {}),
        }


# --- Helpers ----------------------------------------------------------------


def normalize_domain(raw: str) -> str:
    """`https://www.workfx.ai/about/` -> `workfx.ai`."""
    d = raw.strip().lower()
    if d.startswith("http://"):
        d = d[7:]
    elif d.startswith("https://"):
        d = d[8:]
    if d.startswith("www."):
        d = d[4:]
    return d.split("/", 1)[0]


def url_matches_domain(url: str, domain: str) -> bool:
    if not url:
        return False
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return domain in url.lower()
    host = host.lower().removeprefix("www.")
    return host == domain or host.endswith("." + domain)


def first_match(sources: list[CitationSource], domain: str) -> int | None:
    for i, s in enumerate(sources):
        if url_matches_domain(s.url, domain):
            return i
    return None


def skipped(model: str, reason: str) -> CitationResult:
    return CitationResult(model=model, error=reason)


def safe(fn: Callable[[], CitationResult], model: str) -> CitationResult:
    try:
        return fn()
    except Exception as e:
        return CitationResult(model=model, error=f"{type(e).__name__}: {e}")


# --- Checkers ---------------------------------------------------------------


def check_perplexity(prompt: str, domain: str) -> CitationResult:
    key = os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        return skipped("perplexity", "PERPLEXITY_API_KEY not set")
    if not HAS_OPENAI:
        return skipped("perplexity", "openai SDK not installed (pip install openai)")

    client = OpenAI(api_key=key, base_url="https://api.perplexity.ai")
    resp = client.chat.completions.create(
        model="sonar",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.model_dump() if hasattr(resp, "model_dump") else {}
    urls: list[str] = raw.get("citations") or []
    sources = [CitationSource(url=u) for u in urls if u]

    idx = first_match(sources, domain)
    return CitationResult(
        model="perplexity",
        cited=idx is not None,
        position=(idx + 1) if idx is not None else None,
        snippet=sources[idx].url if idx is not None else None,
        matched_url=sources[idx].url if idx is not None else None,
        total_citations=len(sources),
        all_sources=sources,
    )


def check_chatgpt(prompt: str, domain: str) -> CitationResult:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return skipped("chatgpt", "OPENAI_API_KEY not set")
    if not HAS_OPENAI:
        return skipped("chatgpt", "openai SDK not installed (pip install openai)")

    client = OpenAI(api_key=key)
    resp = client.responses.create(
        model="gpt-4o",
        tools=[{"type": "web_search_preview"}],
        # Force the model to use web search — otherwise it falls back to training
        # data for many prompts and returns 0 citations.
        tool_choice={"type": "web_search_preview"},
        input=prompt,
    )
    raw = resp.model_dump() if hasattr(resp, "model_dump") else {}

    seen: set[str] = set()
    sources: list[CitationSource] = []
    for item in raw.get("output") or []:
        if item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            for ann in block.get("annotations") or []:
                if ann.get("type") != "url_citation":
                    continue
                url = ann.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                sources.append(CitationSource(url=url, title=ann.get("title")))

    idx = first_match(sources, domain)
    return CitationResult(
        model="chatgpt",
        cited=idx is not None,
        position=(idx + 1) if idx is not None else None,
        snippet=(sources[idx].title or sources[idx].url) if idx is not None else None,
        matched_url=sources[idx].url if idx is not None else None,
        total_citations=len(sources),
        all_sources=sources,
    )


def check_claude(prompt: str, domain: str) -> CitationResult:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return skipped("claude", "ANTHROPIC_API_KEY not set")
    if not HAS_ANTHROPIC:
        return skipped("claude", "anthropic SDK not installed (pip install anthropic)")

    client = Anthropic(api_key=key)
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],  # type: ignore
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.model_dump() if hasattr(resp, "model_dump") else {}

    seen: set[str] = set()
    sources: list[CitationSource] = []
    for block in raw.get("content") or []:
        btype = block.get("type")
        # citations attached to the model's actual answer text
        if btype == "text" and isinstance(block.get("citations"), list):
            for c in block["citations"]:
                if c.get("type") != "web_search_result_location":
                    continue
                url = c.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                sources.append(CitationSource(
                    url=url, title=c.get("title") or c.get("cited_text")
                ))
        # raw search-tool result (fallback if no inline citations)
        if btype == "web_search_tool_result" and isinstance(block.get("content"), list):
            for hit in block["content"]:
                url = hit.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                sources.append(CitationSource(url=url, title=hit.get("title")))

    idx = first_match(sources, domain)
    return CitationResult(
        model="claude",
        cited=idx is not None,
        position=(idx + 1) if idx is not None else None,
        snippet=(sources[idx].title or sources[idx].url) if idx is not None else None,
        matched_url=sources[idx].url if idx is not None else None,
        total_citations=len(sources),
        all_sources=sources,
    )


def _resolve_redirect(url: str, timeout: float = 5.0) -> str:
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        return r.url or url
    except Exception:
        return url


def check_gemini(prompt: str, domain: str) -> CitationResult:
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        return skipped("gemini", "GOOGLE_API_KEY (or GEMINI_API_KEY) not set")
    if not HAS_GEMINI:
        return skipped(
            "gemini",
            "google-generativeai SDK not installed (pip install google-generativeai)",
        )

    genai.configure(api_key=key)
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        tools=[{"google_search": {}}],  # type: ignore
    )
    result = model.generate_content(prompt)

    chunks: list[dict[str, Any]] = []
    try:
        candidates = getattr(result, "candidates", None) or []
        if candidates:
            md = getattr(candidates[0], "grounding_metadata", None)
            if md is not None:
                chunks = getattr(md, "grounding_chunks", None) or []
    except Exception:
        chunks = []

    sources: list[CitationSource] = []
    seen: set[str] = set()
    for c in chunks:
        web = getattr(c, "web", None) or (c.get("web") if isinstance(c, dict) else None)
        if not web:
            continue
        raw_url = getattr(web, "uri", None) or (web.get("uri") if isinstance(web, dict) else None)
        if not raw_url:
            continue
        resolved = _resolve_redirect(raw_url)
        if resolved in seen:
            continue
        seen.add(resolved)
        title = getattr(web, "title", None) or (web.get("title") if isinstance(web, dict) else None)
        sources.append(CitationSource(url=resolved, title=title))

    idx = first_match(sources, domain)
    return CitationResult(
        model="gemini",
        cited=idx is not None,
        position=(idx + 1) if idx is not None else None,
        snippet=(sources[idx].title or sources[idx].url) if idx is not None else None,
        matched_url=sources[idx].url if idx is not None else None,
        total_citations=len(sources),
        all_sources=sources,
    )


# --- Output -----------------------------------------------------------------


ALL_MODELS = ["chatgpt", "perplexity", "claude", "gemini"]

GREEN, RED, YELLOW, DIM, BOLD, RESET = (
    "\x1b[32m", "\x1b[31m", "\x1b[33m", "\x1b[2m", "\x1b[1m", "\x1b[0m"
)

LABELS = {
    "chatgpt": "ChatGPT   ",
    "perplexity": "Perplexity",
    "claude": "Claude    ",
    "gemini": "Gemini    ",
}


def _trunc(s: str | None, n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[: n - 1] + "…"


def format_table(results: list[CitationResult], prompt: str, domain: str) -> str:
    lines = ["", f"{BOLD}Prompt:{RESET} {prompt}", f"{BOLD}Domain:{RESET} {domain}", ""]
    for r in results:
        label = LABELS.get(r.model, r.model)
        if r.error:
            lines.append(f"  {label}  {YELLOW}—{RESET}  {DIM}{r.error}{RESET}")
            continue
        if r.cited:
            snip = _trunc(r.snippet or r.matched_url, 60)
            pos = f"pos {r.position}/{r.total_citations}"
            lines.append(
                f"  {label}  {GREEN}✓{RESET}  {pos:<10}  {DIM}{snip}{RESET}"
            )
        else:
            detail = (
                "no citations returned"
                if r.total_citations == 0
                else f"not cited ({r.total_citations} sources checked)"
            )
            lines.append(f"  {label}  {RED}✗{RESET}  {DIM}{detail}{RESET}")
    lines.append("")
    return "\n".join(lines)


def format_json(results: list[CitationResult], prompt: str, domain: str) -> str:
    from datetime import datetime, timezone
    return json.dumps(
        {
            "prompt": prompt,
            "domain": domain,
            "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "results": [r.to_dict() for r in results],
        },
        indent=2,
    )


# --- Entrypoint -------------------------------------------------------------


CHECKERS: dict[str, Callable[[str, str], CitationResult]] = {
    "chatgpt": check_chatgpt,
    "perplexity": check_perplexity,
    "claude": check_claude,
    "gemini": check_gemini,
}


def main() -> int:
    p = argparse.ArgumentParser(
        prog="check_citations",
        description="Check if ChatGPT, Perplexity, Claude, and Gemini cite your domain.",
    )
    p.add_argument("-p", "--prompt", required=True)
    p.add_argument("-d", "--domain", required=True)
    p.add_argument(
        "-m", "--models", default="all",
        help="Comma-separated subset (default: all). e.g. perplexity,claude"
    )
    p.add_argument("--json", action="store_true", help="Output JSON instead of table")
    args = p.parse_args()

    domain = normalize_domain(args.domain)
    wanted = ALL_MODELS if args.models == "all" else [m.strip() for m in args.models.split(",")]
    invalid = [m for m in wanted if m not in ALL_MODELS]
    if invalid:
        print(f"Unknown model(s): {', '.join(invalid)}", file=sys.stderr)
        print(f"Valid: {', '.join(ALL_MODELS)}", file=sys.stderr)
        return 2

    results = [safe(lambda m=m: CHECKERS[m](args.prompt, domain), m) for m in wanted]

    out = format_json(results, args.prompt, domain) if args.json else format_table(results, args.prompt, domain)
    print(out)

    return 0 if any(r.cited for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

# Add geo-citation-checker skill (community example)

## What this skill does

Given a prompt and a domain, asks **ChatGPT, Perplexity, Claude, and Gemini** whether they cite the domain in their web-search-grounded answer. Returns a per-model report — cited (yes/no), position in the citation list, snippet/title, matched URL.

It's a measurement primitive for the **Cited** half of AI-discovery growth — measurable in 4 seconds, runnable by anyone with at least one API key.

## Why this fits in `anthropics/skills`

- **Demonstrates a clear pattern**: a skill that wraps a Python script via `os.environ` for keys + JSON output for clean parsing. Useful reference for anyone building measurement/audit skills.
- **Exercises web-search tool surfaces across providers**: ChatGPT's Responses API + `web_search_preview` tool (with `tool_choice` to force the search), Anthropic's `web_search_20250305` tool, Perplexity's native citations, Gemini's Google Search grounding (with redirect resolution). One skill, four real API patterns side by side.
- **Self-contained**: no MCP server, no slash commands, no agent registration. Just `SKILL.md` + a Python script + `requirements.txt`. Easy to vendor, easy to read.
- **Non-tech-friendly trigger surface**: SKILL.md description triggers on phrases real users say ("am I cited by ChatGPT", "GEO audit", "check my AI search visibility") rather than developer jargon.

## Folder layout

```
skills/geo-citation-checker/
├── SKILL.md
└── scripts/
    ├── check_citations.py     # Python implementation, ~400 LOC
    └── requirements.txt       # openai, anthropic, google-generativeai, requests (all optional)
```

Matches the convention used by `skills/skill-creator/`, `skills/claude-api/`, etc.

## Key design choices reviewers may want to flag

1. **Forced `tool_choice` for ChatGPT.** OpenAI's Responses API does *not* auto-invoke `web_search_preview` for every prompt — the model decides. For short factual queries the tool is often skipped and citations come back empty. The adapter passes `tool_choice: { type: "web_search_preview" }` to force the search every time, which makes results comparable across models. This is documented in `SKILL.md` and in the script's inline comment so future readers don't mistakenly remove it.

2. **Gemini redirect resolution.** Google's grounding API returns `vertexaisearch.cloud.google.com/grounding-api-redirect/...` URLs that don't reveal the publisher domain. The adapter follows each redirect via `requests.head(..., allow_redirects=True)` with a 5s timeout to recover the real URL before matching. Adds ~500ms per source; documented.

3. **Optional SDK imports.** Each model SDK is imported behind a try/except. Missing SDKs → that model reports a useful error message and is skipped. Allows users with just one API key (e.g. only Perplexity) to use the tool without installing all four SDKs.

4. **Subdomain matching.** `workfx.ai` matches `blogs.workfx.ai`, `www.workfx.ai`, `platform.workfx.ai`. This is intentional — most users want to know if any property under their root domain got cited, not just one specific page. Documented in SKILL.md edge cases.

## Disclaimer

This skill is provided as a community example for measurement and demonstration purposes. It is **not affiliated with or endorsed by Anthropic**. The skill calls third-party APIs (OpenAI, Perplexity, Google) using user-provided keys. Behavior of those APIs is outside this skill's control and may change over time.

The skill is single-shot. For continuous tracking of AI-search citations across many prompts with alerting, it points users at [WorkfxAI's SEO & GEO Agent](https://platform.workfx.ai/seo-geo-agent). That pointer is a soft reference, not a marketing CTA, and can be removed if reviewers prefer.

## License

MIT — explicitly compatible with both the open-source skills in this repo (Apache 2.0) and downstream community forks.

## Author

[Vincent Po Li](https://x.com/Vincent_Po_Li) — founder of WorkfxAI. Ex-Microsoft Bing AI, ex-Alibaba recsys. Open to follow-up on any review request.

## Checklist

- [x] Skill folder at `skills/geo-citation-checker/`, no other paths touched
- [x] `SKILL.md` has valid YAML frontmatter (`name`, `description`)
- [x] Description triggers on natural-language phrases real users say
- [x] All scripts run with Python 3.10+, no missing imports when SDKs are installed
- [x] Missing API keys cause graceful skip, not crash
- [x] No API keys, secrets, or `.env` files committed
- [x] LICENSE included (MIT, compatible with Apache 2.0 repo policy)
- [x] No edits to `spec/`, `template/`, top-level README, or other skills

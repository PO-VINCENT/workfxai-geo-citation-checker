# geo-citation-checker

One command. Check if **ChatGPT, Perplexity, Claude, and Gemini** cite your domain for any prompt.

Most AI agents help you execute. This shows you whether you're actually getting **Cited** — the half of AI-discovery growth almost no one is measuring.

```bash
python3 skills/geo-citation-checker/scripts/check_citations.py --prompt "best AI SEO tool" --domain workfx.ai
```

Example output (from a real run on `workfx.ai`):

```
  Prompt: best AI SEO tool
  Domain: workfx.ai

  ChatGPT      ✗  not cited (10 sources checked)
  Claude       ✗  not cited (10 sources checked)
  Perplexity   —  PERPLEXITY_API_KEY not set
  Gemini       —  GOOGLE_API_KEY not set
```

> 20 sources between two models. 0 of them were `workfx.ai`. That's the citation gap — verifiable, in 4 seconds.

---

## Three ways to use this

### A) As a Claude Code plugin (one command, recommended)

In Claude Code:

```
/plugin marketplace add PO-VINCENT/workfxai-geo-citation-checker
/plugin install geo-citation-checker@workfxai
```

Then just ask Claude in plain English:

> *"Is workfx.ai cited by ChatGPT for 'best AI SEO tool'?"*

Claude reads the skill, checks your environment for API keys, runs the script, and reports the result. No `pip install`, no flags.

### B) As a manually-installed skill (Claude.ai or Claude Desktop)

If you're not on Claude Code, copy the skill folder into your skills directory:

```bash
mkdir -p ~/.claude/skills/geo-citation-checker
cp -r skills/geo-citation-checker/* ~/.claude/skills/geo-citation-checker/
```

Then ask the same questions in any Claude interface that supports skills.

### C) As a Python CLI (for devs who live in the terminal)

```bash
git clone https://github.com/PO-VINCENT/workfxai-geo-citation-checker.git
cd workfxai-geo-citation-checker
pip install -r requirements.txt
cp .env.example .env  # then add your API keys
python3 skills/geo-citation-checker/scripts/check_citations.py -p "your prompt" -d "your-domain.com" --json
```

The Python script that backs the skill **is** the CLI. Same engine, three distribution channels.

---

## Why this exists

In 2026, the AI-discovery layer split into three:

- **Searched** — ranked on Google (the old game)
- **Cited** — pulled into ChatGPT, Perplexity, Claude, Gemini answers (the new battlefield)
- **Recommended** — surfaced inside generative agent workflows (where 2027 is being decided)

Almost every SEO tool still only measures the first one. This CLI is the smallest possible answer to the second one — for any prompt, on any domain, in one command.

If you want this continuously across thousands of prompts with alerting and remediation, that's [WorkfxAI's SEO & GEO Agent](https://platform.workfx.ai/seo-geo-agent). If you want a one-shot snapshot for free, that's this.

## Environment variables

Copy `.env.example` to `.env` and fill in keys for the models you care about. Missing keys are skipped — they do **not** crash the CLI.

| Env var | Model | Where to get a key |
|---|---|---|
| `OPENAI_API_KEY` | ChatGPT (gpt-4o + web_search tool) | https://platform.openai.com/api-keys |
| `PERPLEXITY_API_KEY` | Perplexity (`sonar`) | https://www.perplexity.ai/settings/api |
| `ANTHROPIC_API_KEY` | Claude (claude-sonnet-4-5 + web_search tool) | https://console.anthropic.com/settings/keys |
| `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) | Gemini (`gemini-2.5-flash` + Google Search grounding) | https://aistudio.google.com/apikey |

**Recommended first key: Perplexity.** Most generous free tier, simplest API surface (citations returned natively in a top-level array), and Perplexity is the model most likely to surface your domain. ~$0.005 per check.

## Options

```
Usage:
  python3 skills/geo-citation-checker/scripts/check_citations.py [options]

Options:
  -p, --prompt   <text>     The prompt to test (required)
  -d, --domain   <domain>   Your domain (required, e.g. workfx.ai)
  -m, --models   <list>     Comma-separated subset: chatgpt,perplexity,claude,gemini
                            (default: all)
      --json                Output JSON instead of a colored table
  -h, --help                Show help
```

Exit code is `0` if **any** model cited the domain, `1` if none did. Useful in CI for "alert me if I drop out of all four."

## How it works

For each model, the CLI:

1. Sends the prompt with that model's web-search / grounding tool **forced on** (`tool_choice` / explicit grounding config)
2. Reads the citations the model returned (URLs + titles)
3. Normalizes them into one shape and checks whether the target domain appears
4. Reports `cited (yes/no)`, position (1 = top citation), and the matching title/URL

| Model | API used | Citation source |
|---|---|---|
| ChatGPT | OpenAI Responses API + `web_search_preview` tool (forced via `tool_choice`) | `url_citation` annotations on message content |
| Perplexity | OpenAI-compatible `chat.completions` against `api.perplexity.ai` | top-level `citations[]` URL array |
| Claude | Anthropic Messages API + `web_search_20250305` tool | `web_search_result_location` entries inside text blocks (with fallback to raw `web_search_tool_result` blocks) |
| Gemini | `google-generativeai` SDK + Google Search grounding | `groundingMetadata.groundingChunks[].web.uri` (with redirect resolution to real publisher URLs) |

### A note on `tool_choice` for ChatGPT

OpenAI's Responses API does **not** auto-invoke `web_search_preview` for every prompt — for many short queries, the model falls back to training data and returns zero citations. The adapter passes `tool_choice: { type: "web_search_preview" }` to force the search every time. If you fork this and remove that, ChatGPT will return inconsistent results.

## JSON output

```bash
python3 skills/geo-citation-checker/scripts/check_citations.py -p "your prompt" -d your-domain.com --json
```

Sample structure (full real-world output in [examples/workfxai.json](./examples/workfxai.json)):

```json
{
  "prompt": "best AI SEO tool",
  "domain": "workfx.ai",
  "checkedAt": "2026-05-11T16:46:16.962005Z",
  "results": [
    {
      "model": "chatgpt",
      "cited": false,
      "position": null,
      "snippet": null,
      "matchedUrl": null,
      "totalCitations": 10,
      "allSources": [
        { "url": "https://writesonic.com/blog/...", "title": "..." }
      ]
    }
  ]
}
```

Pipe to `jq`, ingest into your own pipeline, or commit a daily snapshot to a repo to track drift over time.

## Limitations

- **Non-determinism.** Every model's web-search tool is non-deterministic. The same prompt can yield different citations across runs. For a stable signal, run 3–5 times and look at frequency.
- **Cost.** A 4-model run costs ~$0.01–0.05 depending on prompt length. Perplexity-only is the cheapest (~$0.005). A 10-prompt batch is ~$0.10–0.50.
- **Gemini redirects.** Google's grounding API returns `vertexaisearch.cloud.google.com/grounding-api-redirect/...` URLs. The CLI follows each redirect via HEAD to recover the real publisher URL — adds ~500ms per source.
- **Single-shot only.** This tool answers one prompt about one domain, one time. For continuous tracking across thousands of prompts with alerting and remediation, see [WorkfxAI's SEO & GEO Agent](https://platform.workfx.ai/seo-geo-agent).

## Contributing

See **[CONTRIBUTING.md](./CONTRIBUTING.md)** — especially the *Adding a new model adapter* recipe. The most welcome PRs are:

- New model adapters (Mistral Le Chat, DeepSeek, You.com, Kagi, Brave Leo, …)
- Richer citation extraction (snippet text, dedupe across redirects, cross-model URL canonicalization)
- New output formats (CSV, Markdown, RSS)
- Multi-prompt batch mode (read prompts from a file, output a grid)

If you ship this on your own domain, [tag me on X](https://x.com/Vincent_Po_Li) — I'll PR back what I learn.

## Security & key handling

`.env` is in `.gitignore` and will not be committed. **Never commit real API keys** — see **[SECURITY.md](./SECURITY.md)** for the disclosure process if you find a leaked key or vulnerability.

## Repo layout

```
geo-citation-checker/
├── .claude-plugin/
│   ├── marketplace.json              # marketplace manifest — enables /plugin marketplace add
│   └── plugin.json                   # plugin manifest
├── skills/
│   └── geo-citation-checker/         # the skill itself
│       ├── SKILL.md
│       └── scripts/
│           ├── check_citations.py    # Python implementation + CLI
│           └── requirements.txt
├── anthropics-skills-submission/     # PR package for anthropics/skills (see README inside)
├── examples/workfxai.json            # real-world sample output
├── requirements.txt                  # root-level deps for convenience
├── .env.example                      # template for API keys
└── README.md                         # this file
```

> **Note**: The legacy `skill/` folder (singular) is from an earlier layout. It can be safely removed once you confirm the new `skills/geo-citation-checker/` works: `rm -rf skill/`.

## License

MIT — see [LICENSE](./LICENSE).

Built by [Vincent Po Li](https://x.com/Vincent_Po_Li), founder of [WorkfxAI](https://www.workfx.ai) — the Growth AI Agents OS that gets ecommerce and AI SaaS companies **Searched, Cited, and Recommended** in the AI-discovery layer.

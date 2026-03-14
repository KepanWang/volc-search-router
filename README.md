# volc-search-router

An open-source OpenClaw skill that routes Volcengine search requests between:

- `web` (raw search)
- `web_summary` (search + generated summary)
- `auto` (intent-based selection with user override)

It is designed for production use with **no hardcoded secrets**.

---

## Features

- Intent-aware routing (`auto`) between `web` and `web_summary`
- Explicit user override (`--mode web` / `--mode web_summary`)
- Side-by-side comparison mode (`--compare`)
- SSE parsing support for `web_summary`
- Normalized JSON output (results, summary, usage, latency)
- Token visibility when available (`PromptTokens`, `CompletionTokens`, `TotalTokens`)

---

## Directory Structure

```text
volc-search-router/
├── SKILL.md
├── README.md
├── .env.example
└── scripts/
    └── volc_search.py
```

---

## Security

- Do **not** commit API keys.
- This project reads key from env var only:

```bash
VOLC_SEARCH_API_KEY
```

Copy `.env.example` and set your local secret safely.

---

## Installation

### Option A: Command-line local install (manual)

Copy this skill folder into your OpenClaw skills directory:

```bash
cp -r volc-search-router /root/clawd/skills/
```

Or in a generic setup:

```bash
cp -r volc-search-router <your-openclaw-workspace>/skills/
```

### Option B: Agent-driven install (after you publish)

Once published to ClawHub, ask your agent to run:

```bash
clawhub install volc-search-router
```

You can also pin a version:

```bash
clawhub install volc-search-router --version <version>
```

---

## Quick Start

Set API key:

```bash
export VOLC_SEARCH_API_KEY="<your_key_here>"
```

Run in auto mode:

```bash
python3 scripts/volc_search.py --query "AI SKILL聚合平台有哪些" --mode auto --pretty
```

Force raw web mode:

```bash
python3 scripts/volc_search.py --query "AI SKILL聚合平台有哪些" --mode web --pretty
```

Force summary mode:

```bash
python3 scripts/volc_search.py --query "AI SKILL聚合平台有哪些" --mode web_summary --pretty
```

Compare both:

```bash
python3 scripts/volc_search.py --query "AI SKILL聚合平台有哪些" --compare --pretty
```

---

## Mode Selection Logic (`auto`)

`auto` chooses `web_summary` for synthesis-style intent (e.g. “有哪些/区别/优缺点/总结/趋势/推荐”) and chooses `web` for source-discovery intent (e.g. “官网/链接/地址/文档”).

If user explicitly specifies mode, user choice wins.

---

## Output Schema (simplified)

```json
{
  "query": "...",
  "selected_mode": "web_summary",
  "selection_reason": "intent-synthesis",
  "compare": false,
  "result": {
    "http_status": 200,
    "content_type": "text/event-stream",
    "mode": "web_summary",
    "result_count": 8,
    "time_cost": 142,
    "log_id": "...",
    "results": [
      {"title": "...", "site": "...", "url": "..."}
    ],
    "summary": "...",
    "usage": {
      "PromptTokens": 3049,
      "CompletionTokens": 171,
      "TotalTokens": 3220,
      "SearchTimeCost": 142,
      "FirstTokenTimeCost": 674,
      "TotalTimeCost": 4171
    }
  }
}
```

---

## Notes

- The API usually returns cost-related **token** and **time** metrics in `web_summary`.
- Monetary amount is not returned directly; compute cost using your billing unit price.

---

## License

MIT (recommended). Add your `LICENSE` file before publishing.

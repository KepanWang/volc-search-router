---
name: volc-search-router
description: Route Volcengine Web Search requests between web and web_summary with automatic mode selection and explicit user override. Use when user asks to search via Volcengine, wants direct summarized answers, wants lower-cost raw search results, or wants side-by-side comparison between normal search and summary mode.
---

# Volc Search Router

Use this skill to call Volcengine Web Search in three modes:
- `web`: raw search results (faster, cheaper)
- `web_summary`: search + LLM summary (more direct answer, slower, higher token cost)
- `auto`: decide mode from query intent, but allow explicit override

## Inputs

- `query` (required): user search query
- `mode` (optional): `auto` | `web` | `web_summary`
- `count` (optional): 1-50, default `8`
- `compare` (optional): when true, run both `web` and `web_summary` and compare

## Decision Policy (auto mode)

Choose `web_summary` when query asks for:
- explanation / summary / recommendation / comparison / trends
- “有哪些”“怎么选”“区别”“优缺点”“总结”“盘点”“趋势”“是什么”

Choose `web` when query asks for:
- source discovery, URL collection, monitoring, or low-cost batch lookup
- short navigational lookup with minimal synthesis

If user explicitly specifies mode, always honor user preference.

## Execution

1. Require `VOLC_SEARCH_API_KEY` from environment.
2. Call API endpoint:
   - `POST https://open.feedcoopapi.com/search_api/web_search`
   - Header: `Authorization: Bearer $VOLC_SEARCH_API_KEY`
   - Header: `Content-Type: application/json`
3. For `web`:
   - send `SearchType=web`, `NeedSummary=false`
4. For `web_summary`:
   - send `SearchType=web_summary`, `NeedSummary=true`
   - parse SSE frames and merge final summary text from `Choices[].Delta.Content` / `Choices[].Message.Content`
5. Return normalized output:
   - selected mode
   - top results list
   - summary text (if any)
   - usage (`PromptTokens`, `CompletionTokens`, `TotalTokens`) when available
   - timing (`SearchTimeCost`, `TotalTimeCost`, `TimeCost`) when available

## Script

Run the bundled script:

```bash
python3 scripts/volc_search.py --query "AI SKILL聚合平台有哪些" --mode auto
```

Compare both modes:

```bash
python3 scripts/volc_search.py --query "AI SKILL聚合平台有哪些" --compare
```

Force summary mode:

```bash
python3 scripts/volc_search.py --query "AI SKILL聚合平台有哪些" --mode web_summary
```

## Output Guidance

When reporting to user:
1. State selected mode and why (for auto).
2. Show top sources briefly.
3. If `web_summary`, surface token usage and latency.
4. If `compare`, provide:
   - quality difference
   - speed difference
   - token/cost implication

## Security

- Never hardcode or commit API keys.
- Read key only from env var: `VOLC_SEARCH_API_KEY`.
- Redact secrets in logs and examples.

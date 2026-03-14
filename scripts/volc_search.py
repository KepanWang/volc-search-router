#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from typing import Dict, List, Any, Tuple

import requests

API_URL = "https://open.feedcoopapi.com/search_api/web_search"


SUMMARY_HINTS = [
    "有哪些", "怎么选", "区别", "优缺点", "总结", "盘点", "趋势", "是什么", "推荐", "对比", "分析"
]

WEB_HINTS = [
    "官网", "链接", "地址", "url", "文档", "原文", "来源", "站点", "清单"
]


def choose_mode(query: str, user_mode: str) -> Tuple[str, str]:
    if user_mode in {"web", "web_summary"}:
        return user_mode, "user-specified"

    q = query.strip().lower()

    if any(k in q for k in SUMMARY_HINTS):
        return "web_summary", "intent-synthesis"

    if any(k in q for k in WEB_HINTS) and len(q) <= 40:
        return "web", "intent-source-discovery"

    if len(q) <= 12:
        return "web", "short-query-default"

    return "web_summary", "default-synthesis"


def post_volc(api_key: str, query: str, search_type: str, count: int, query_rewrite: bool = False) -> requests.Response:
    payload = {
        "Query": query,
        "SearchType": search_type,
        "Count": count,
        "Filter": {
            "NeedUrl": True,
            "NeedContent": False,
        },
        "NeedSummary": search_type == "web_summary",
        "QueryControl": {
            "QueryRewrite": query_rewrite,
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(API_URL, headers=headers, json=payload, timeout=120)


def parse_sse_text(text: str) -> List[Dict[str, Any]]:
    events = []
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        raw = line[len("data:"):].strip()
        if not raw or raw == "[DONE]":
            continue
        try:
            events.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return events


def extract_summary_and_usage(events: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    parts: List[str] = []
    usage: Dict[str, Any] = {}

    for ev in events:
        result = ev.get("Result") or {}

        if result.get("Usage"):
            usage = result["Usage"]

        for ch in result.get("Choices") or []:
            delta = ch.get("Delta") or {}
            d_content = delta.get("Content")
            if d_content:
                parts.append(d_content)

            msg = ch.get("Message") or {}
            m_content = msg.get("Content")
            if m_content:
                parts.append(m_content)

    summary = "".join(parts).strip()
    # Remove accidental repeated whitespaces
    summary = re.sub(r"\n{3,}", "\n\n", summary)
    return summary, usage


def normalize_results(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for it in result.get("WebResults") or []:
        out.append({
            "title": it.get("Title"),
            "site": it.get("SiteName"),
            "url": it.get("Url"),
            "snippet": it.get("Snippet"),
            "summary": it.get("Summary"),
            "rank_score": it.get("RankScore"),
            "auth_level": it.get("AuthInfoLevel"),
            "auth_desc": it.get("AuthInfoDes"),
        })
    return out


def run_single(api_key: str, query: str, mode: str, count: int, query_rewrite: bool = False) -> Dict[str, Any]:
    response = post_volc(api_key, query, mode, count, query_rewrite)
    output: Dict[str, Any] = {
        "http_status": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "mode": mode,
    }

    # web_summary usually returns text/event-stream
    if "text/event-stream" in output["content_type"]:
        response.encoding = "utf-8"
        events = parse_sse_text(response.text)
        if not events:
            output["error"] = "empty_sse_events"
            return output

        first = events[0]
        meta = first.get("ResponseMetadata") or {}
        result = first.get("Result") or {}
        if meta.get("Error"):
            output["error"] = meta["Error"]
            return output

        summary, usage = extract_summary_and_usage(events)
        output.update({
            "result_count": result.get("ResultCount"),
            "time_cost": result.get("TimeCost"),
            "log_id": result.get("LogId"),
            "results": normalize_results(result),
            "summary": summary,
            "usage": usage,
            "event_count": len(events),
        })
        return output

    # regular json response
    try:
        data = response.json()
    except json.JSONDecodeError:
        output["error"] = "invalid_json_response"
        output["raw_head"] = response.text[:500]
        return output

    meta = data.get("ResponseMetadata") or {}
    if meta.get("Error"):
        output["error"] = meta["Error"]
        return output

    result = data.get("Result") or {}
    output.update({
        "result_count": result.get("ResultCount"),
        "time_cost": result.get("TimeCost"),
        "log_id": result.get("LogId"),
        "results": normalize_results(result),
        "summary": "",
        "usage": result.get("Usage") or {},
    })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Volc Search Router: auto-select web vs web_summary")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--mode", default="auto", choices=["auto", "web", "web_summary"], help="Search mode")
    parser.add_argument("--count", default=8, type=int, help="Result count (1-50)")
    parser.add_argument("--compare", action="store_true", help="Run both web and web_summary for comparison")
    parser.add_argument("--query-rewrite", action="store_true", help="Enable QueryRewrite")
    parser.add_argument("--pretty", action="store_true", help="Pretty JSON output")

    args = parser.parse_args()

    api_key = os.getenv("VOLC_SEARCH_API_KEY", "").strip()
    if not api_key:
        print("ERROR: VOLC_SEARCH_API_KEY is not set", file=sys.stderr)
        return 2

    count = max(1, min(args.count, 50))

    if args.compare:
        chosen_mode, reason = choose_mode(args.query, args.mode)
        web_res = run_single(api_key, args.query, "web", count, args.query_rewrite)
        summary_res = run_single(api_key, args.query, "web_summary", count, args.query_rewrite)
        output = {
            "query": args.query,
            "selected_mode": chosen_mode,
            "selection_reason": reason,
            "compare": True,
            "web": web_res,
            "web_summary": summary_res,
        }
    else:
        chosen_mode, reason = choose_mode(args.query, args.mode)
        result = run_single(api_key, args.query, chosen_mode, count, args.query_rewrite)
        output = {
            "query": args.query,
            "selected_mode": chosen_mode,
            "selection_reason": reason,
            "compare": False,
            "result": result,
        }

    if args.pretty:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

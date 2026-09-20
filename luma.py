#!/usr/bin/env python3
"""Export public (or cookie-authenticated) Luma event data to event.json."""
import argparse, datetime as dt, html, json, re, sys
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from urllib.request import HTTPCookieProcessor, Request, build_opener
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
MYT = ZoneInfo("Asia/Kuala_Lumpur")

def fetch(url, cookies=None):
    opener = build_opener()
    if cookies:
        jar = MozillaCookieJar(cookies)
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except Exception as exc:
            raise SystemExit(f"Could not read Netscape cookies file {cookies}: {exc}")
        opener = build_opener(HTTPCookieProcessor(jar))
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 Vigil/1.0"})
    return opener.open(request, timeout=30).read().decode("utf-8")

def next_data(page):
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page, re.S)
    if not match:
        raise ValueError("Luma __NEXT_DATA__ was not found; the public page format may have changed.")
    return json.loads(html.unescape(match.group(1)))

def plain_description(data):
    initial = data["props"]["pageProps"]["initialData"]["data"]
    doc = initial.get("description_mirror", {})
    pieces = []
    def walk(value):
        if isinstance(value, dict):
            block = value.get("type") in {"paragraph", "list_item", "bullet_list", "heading"}
            if block and pieces and pieces[-1] != "\n": pieces.append("\n")
            if isinstance(value.get("text"), str): pieces.append(value["text"])
            for child in value.get("content", []): walk(child)
            if block: pieces.append("\n")
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(doc)
    return "".join(pieces).strip()

def parse_clock(text, date, tz):
    text = text.strip().upper().replace(".", "")
    for fmt in ("%I:%M %p", "%I %p"):
        try: return dt.datetime.strptime(text, fmt).replace(year=date.year, month=date.month, day=date.day, tzinfo=tz)
        except ValueError: pass
    raise ValueError(f"Unrecognised clock: {text}")

def parse_sessions(description, start, tz):
    sessions, current_date = [], start.date()
    for line in description.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        date_match = re.search(r"Day\s+(\d+)\s*:\s*([A-Za-z]+)\s+(\d{1,2})", line, re.I)
        if date_match:
            current_date = dt.datetime.strptime(f"{date_match.group(2)} {date_match.group(3)} {start.year}", "%B %d %Y").date()
            continue
        match = re.match(r"(\d{1,2}(?::\d{2})?\s*(?:AM|PM)?)\s*-\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM))\s*:\s*(.+)", line, re.I)
        if match:
            end_text = match.group(2)
            begin_text = match.group(1)
            if not re.search(r"(?:AM|PM)", begin_text, re.I): begin_text += " " + re.search(r"(AM|PM)", end_text, re.I).group(1)
            begins, ends = parse_clock(begin_text, current_date, tz), parse_clock(end_text, current_date, tz)
            sessions.append({"title": match.group(3), "start_utc": begins.astimezone(UTC).isoformat(), "end_utc": ends.astimezone(UTC).isoformat(), "start_malaysia": begins.astimezone(MYT).isoformat(), "end_malaysia": ends.astimezone(MYT).isoformat()})
    return sessions

def exposed_stream(value):
    if not isinstance(value, dict): return None
    for key in ("virtual_url", "join_url", "stream_url", "url"):
        url = value.get(key)
        if isinstance(url, str) and url.startswith("http"): return url
    return None

def build(url, cookies=None):
    data = next_data(fetch(url, cookies))
    initial = data["props"]["pageProps"]["initialData"]["data"]
    event = initial["event"]
    tz = ZoneInfo(event.get("timezone") or "America/Los_Angeles")
    start, end = dt.datetime.fromisoformat(event["start_at"].replace("Z", "+00:00")), dt.datetime.fromisoformat(event["end_at"].replace("Z", "+00:00"))
    description = plain_description(data)
    virtual = event.get("virtual_info") or {}
    return {
        "source_url": url, "name": event["name"], "timezone": str(tz),
        "start_utc": start.astimezone(UTC).isoformat(), "end_utc": end.astimezone(UTC).isoformat(),
        "start_malaysia": start.astimezone(MYT).isoformat(), "end_malaysia": end.astimezone(MYT).isoformat(),
        "description": description, "sessions": parse_sessions(description, start.astimezone(tz), tz),
        "speakers": [{"name": "Matt Palmer", "x": "https://x.com/mattyp"}, {"name": "Lauren Tan", "x": "https://x.com/poteto"}, {"name": "Roshan Sadanani", "x": "https://x.com/roshan_s"}],
        "platform_hints": ["Luma virtual event", "Luma hides the join link until the attendee has access", "Search YouTube and host X profiles for live/replay"],
        "virtual_info": {"has_access": bool(virtual.get("has_access")), "stream_url": exposed_stream(virtual)},
    }

def main():
    p = argparse.ArgumentParser(); p.add_argument("url"); p.add_argument("--cookies"); p.add_argument("--output", default="event.json")
    a = p.parse_args()
    event = build(a.url, a.cookies)
    Path(a.output).write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {a.output}: {event['name']}")
    print("Stream link: " + (event["virtual_info"]["stream_url"] or "not exposed (register and optionally export Netscape-format Luma cookies)"))

if __name__ == "__main__": main()

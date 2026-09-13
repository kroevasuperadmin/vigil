#!/usr/bin/env python3
"""Find plausible Luma, YouTube, and X live/replay links; never registers or posts."""
import argparse, datetime as dt, json, subprocess
from pathlib import Path
from luma import build

def youtube(query):
    command = ["yt-dlp", "--flat-playlist", "--print", "%(webpage_url)s\t%(title)s\t%(live_status)s", f"ytsearch10:{query}"]
    run = subprocess.run(command, text=True, capture_output=True, timeout=90)
    results = []
    for line in run.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) >= 2:
            results.append({"url": fields[0], "title": fields[1], "status": fields[2] if len(fields)>2 else "unknown", "confidence": "medium - YouTube search result; verify title/channel before capture"})
    return results

def main():
    p = argparse.ArgumentParser(); p.add_argument("event_json"); p.add_argument("--cookies"); p.add_argument("--output", default="stream_candidates.json")
    a = p.parse_args(); event = json.loads(Path(a.event_json).read_text(encoding="utf-8"))
    candidates = []
    try:
        fresh = build(event["source_url"], a.cookies)
        stream = fresh["virtual_info"]["stream_url"]
        if stream: candidates.append({"url": stream, "title": "Luma virtual room", "confidence": "high - exposed by Luma to this attendee"})
        else: candidates.append({"url": event["source_url"], "title": "Luma event page", "confidence": "low - stream is still access-gated"})
    except Exception as exc: candidates.append({"url": event["source_url"], "title": "Luma event page", "confidence": f"unknown - refresh failed: {exc}"})
    candidates.extend(youtube(event["name"]))
    for speaker in event.get("speakers", []): candidates.append({"url": speaker["x"], "title": speaker["name"] + " on X", "confidence": "low - inspect for an X broadcast or replay"})
    payload = {"checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "candidates": candidates}
    Path(a.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for candidate in candidates: print(f"{candidate['confidence']}\n  {candidate['title']}: {candidate['url']}")

if __name__ == "__main__": main()

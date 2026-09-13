#!/usr/bin/env python3
"""Prepare an event and print the Malaysia-time schedule plus exact Actions triggers."""
import argparse, json, subprocess, sys
from pathlib import Path

def main():
    p = argparse.ArgumentParser(); p.add_argument("luma_url"); p.add_argument("--cookies"); a = p.parse_args()
    cmd = [sys.executable, str(Path(__file__).with_name("luma.py")), a.luma_url]
    if a.cookies: cmd += ["--cookies", a.cookies]
    subprocess.run(cmd, check=True)
    event = json.loads(Path("event.json").read_text(encoding="utf-8"))
    print("\nMalaysia schedule (UTC+8):")
    for item in event["sessions"]:
        print(f"- {item['start_malaysia'][0:16].replace('T', ' ')} to {item['end_malaysia'][11:16]}  {item['title']}")
    print("\nWhat runs when:")
    print("1. Register yourself on Luma. After approval, export a Netscape-format cookie file only if luma.py still says no stream link.")
    print("2. At event start or after it ends: python find_stream.py event.json --cookies cookies.txt")
    print("3. Trigger Actions once per <=5h45 capture chunk. For a replay, use segment offsets; for live, run a bounded session capture.")
    print("\nCommands (replace STREAM_URL only after you have access):")
    base = "gh workflow run capture.yml --repo kroevasuperadmin/attend --ref main"
    print(base + " --field url=STREAM_URL --field label=day1-part1 --field event='Grok Bot Galaxy' --field capture_minutes=345")
    print(base + " --field url=STREAM_URL --field label=day1-part2 --field event='Grok Bot Galaxy' --field segment_start=05:45:00 --field segment_end=09:30:00 --field capture_minutes=240")
    print("4. When the transcript is committed, run: python learn.py transcripts/grok-bot-galaxy/day1-part1.txt")

if __name__ == "__main__": main()

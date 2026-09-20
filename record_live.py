#!/usr/bin/env python3
"""Record a live stream's audio on this laptop in 30-minute files until a stop time (Malaysia time).

Usage: python record_live.py --url STREAM_URL --stop 2026-09-16T09:15 --out recordings/day1
Files are named by their start time (MYT), e.g. 0916-003000.m4a, so sessions can be cut out later.
If the stream drops or has not started, it re-resolves the URL every minute until the stop time.
"""
import argparse, datetime as dt, subprocess, time
from pathlib import Path

MYT = dt.timezone(dt.timedelta(hours=8))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True); p.add_argument("--stop", required=True); p.add_argument("--out", required=True)
    a = p.parse_args()
    stop = dt.datetime.fromisoformat(a.stop).replace(tzinfo=MYT)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    def say(s):
        with open(out / "record.log", "a", encoding="utf-8") as f:
            f.write(dt.datetime.now(MYT).strftime("%m-%d %H:%M:%S ") + s + "\n")
    say(f"start, stop at {a.stop} MYT, url {a.url}")
    while dt.datetime.now(MYT) < stop:
        r = subprocess.run(["yt-dlp", "-g", "-f", "bestaudio/best", a.url], capture_output=True, text=True)
        media = r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else ""
        if not media:
            say("stream not available: " + ((r.stderr.strip().splitlines() or ["no output"])[-1])[:200]); time.sleep(60); continue
        left = int((stop - dt.datetime.now(MYT)).total_seconds())
        say(f"recording ({left}s left)")
        # ponytail: audio-only mono 48 kbps (~21 MB/hour); a drop simply starts new files on the next loop.
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", media, "-t", str(left), "-vn", "-ac", "1",
                        "-c:a", "aac", "-b:a", "48k", "-f", "segment", "-segment_time", "1800", "-reset_timestamps", "1",
                        "-strftime", "1", str(out / "%m%d-%H%M%S.m4a")])
        say("ffmpeg stopped"); time.sleep(10)
    say("DONE")

if __name__ == "__main__":
    main()

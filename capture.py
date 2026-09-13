#!/usr/bin/env python3
"""Download one bounded audio segment then transcribe it. Intended for GitHub Actions."""
import argparse, os, re, subprocess
from pathlib import Path
from transcribe import transcribe

def slug(value): return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

def main():
    p = argparse.ArgumentParser(); p.add_argument("--url", required=True); p.add_argument("--event", required=True); p.add_argument("--label", required=True); p.add_argument("--segment-start", default=""); p.add_argument("--segment-end", default=""); p.add_argument("--capture-minutes", type=int, default=345)
    a = p.parse_args(); work = Path("work"); work.mkdir(exist_ok=True)
    template = str(work / "audio.%(ext)s")
    command = ["yt-dlp", "--no-playlist", "--js-runtimes", "node", "--extractor-args", "youtube:player_client=android", "--live-from-start", "-x", "--audio-format", "mp3", "--continue", "-o", template]
    if a.segment_start or a.segment_end:
        command += ["--download-sections", f"*{a.segment_start or '00:00:00'}-{a.segment_end or '99:00:00'}"]
    command.append(a.url)
    # A run must finish under GitHub-hosted runner's six-hour limit. For a true live stream this stops at the cap.
    subprocess.run(["timeout", str(a.capture_minutes * 60)] + command, check=False)
    media = next(iter(work.glob("audio.*")), None)
    if not media: raise SystemExit("yt-dlp did not save audio. Check the candidate URL and access.")
    base = Path("transcripts") / slug(a.event) / slug(a.label)
    raw, text = transcribe(str(media), str(base), os.environ["ASSEMBLYAI_API_KEY"])
    print(f"Transcript ready: {raw} {text}")

if __name__ == "__main__": main()

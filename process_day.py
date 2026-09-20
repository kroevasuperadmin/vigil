#!/usr/bin/env python3
"""After a Grok Bot Galaxy night: cut each session out of the 30-minute recordings, transcribe it, write learnings.

Usage: python process_day.py --day 1   (reads recordings/day1, writes output/grok-galaxy/day1/<session>/)
Sessions are the official x.ai times converted to Malaysia time (PT + 15 h). One failed session never stops the rest.
"""
import argparse, datetime as dt, re, subprocess, sys
from pathlib import Path
from transcribe import transcribe

HERE = Path(__file__).resolve().parent
PY = sys.executable
SESSIONS = {  # Malaysia time, from https://x.ai/galaxy (15 Sep 2026)
    1: [("grok-bot-101", "09-16 00:00", "09-16 01:00"), ("engineering", "09-16 03:30", "09-16 05:00"),
        ("product-managers", "09-16 05:30", "09-16 07:00"), ("founders", "09-16 07:30", "09-16 08:30")],
    2: [("sales-engineering", "09-17 00:00", "09-17 01:30"), ("sales", "09-17 03:30", "09-17 05:00"),
        ("sdrs", "09-17 05:30", "09-17 06:30"), ("customer-support", "09-17 07:00", "09-17 08:00")],
    3: [("marketing-ops", "09-18 00:00", "09-18 01:30"), ("post-sales", "09-18 03:30", "09-18 04:30"),
        ("marketing", "09-18 05:30", "09-18 07:00"), ("wrap-and-showcase", "09-18 07:30", "09-18 08:30")],
}

def t(s): return dt.datetime.strptime("2026-" + s, "%Y-%m-%d %H:%M")

def assemblyai_key():
    # Key lives in Claude's memory note; read at runtime, never printed or written anywhere.
    note = Path.home() / ".claude/projects/C--WINDOWS-system32/memory/reference_assemblyai.md"
    m = re.search(r"\b[0-9a-f]{32}\b", note.read_text(encoding="utf-8"))
    if not m: raise SystemExit("No AssemblyAI key found in reference_assemblyai.md")
    return m.group(0)

def main():
    p = argparse.ArgumentParser(); p.add_argument("--day", type=int, required=True, choices=[1, 2, 3])
    p.add_argument("--only", default="", help="comma list of session slugs to process"); a = p.parse_args()
    rec = HERE / "recordings" / f"day{a.day}"; out = HERE / "output" / "grok-galaxy" / f"day{a.day}"; out.mkdir(parents=True, exist_ok=True)
    log = out / "process.log"
    def say(s):
        with open(log, "a", encoding="utf-8") as f: f.write(dt.datetime.now().strftime("%H:%M:%S ") + s + "\n")
    # Chunk start times come from file names like 0916-003000.m4a; each chunk is <= 30 min.
    chunks = sorted((dt.datetime.strptime("2026" + f.stem, "%Y%m%d-%H%M%S"), f) for f in rec.glob("*.m4a"))
    say(f"day {a.day}: {len(chunks)} recording files")
    key = assemblyai_key()
    only = {s for s in a.only.split(",") if s}
    for slug, start, end in SESSIONS[a.day]:
        if only and slug not in only: continue
        s, e = t(start), t(end)
        parts = [f for c, f in chunks if c < e and c + dt.timedelta(minutes=30) > s]
        if not parts: say(f"{slug}: NO AUDIO for {start}-{end}"); continue
        d = out / slug; d.mkdir(exist_ok=True)
        listing = d / "parts.txt"; listing.write_text("".join(f"file '{f.as_posix()}'\n" for f in parts), encoding="utf-8")
        first = min(c for c, f in chunks if f in parts)
        offset = max(0, int((s - first).total_seconds())); length = int((e - s).total_seconds())
        audio = d / f"{slug}.m4a"
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                            "-ss", str(offset), "-t", str(length), "-c", "copy", str(audio)])
        if r.returncode != 0 or not audio.exists(): say(f"{slug}: FAILED to cut audio"); continue
        try:
            raw, text = transcribe(str(audio), str(d / slug), key)
            say(f"{slug}: transcript {text}")
        except Exception as ex:
            say(f"{slug}: FAILED transcription: {type(ex).__name__}: {str(ex)[:200]}"); continue
        r = subprocess.run([PY, str(HERE / "learn.py"), str(text), "--output-dir", str(d)])
        say(f"{slug}: learnings {'written' if r.returncode == 0 else 'FAILED'}")
    say("DONE")

if __name__ == "__main__":
    main()

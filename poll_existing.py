#!/usr/bin/env python3
"""Poll an existing AssemblyAI transcript_id to completion and write it out, without re-uploading."""
import argparse, json, os, sys, time
from pathlib import Path
import requests

API = "https://api.assemblyai.com/v2"

def stamp(ms):
    seconds = ms // 1000
    return f"{seconds//3600:02}:{(seconds%3600)//60:02}:{seconds%60:02}"

def readable(result):
    utterances = result.get("utterances") or []
    if utterances:
        return "\n".join(f"[{stamp(x.get('start', 0))}] Speaker {x.get('speaker', '?')}: {x.get('text', '')}" for x in utterances) + "\n"
    return f"[00:00:00] Speaker ?: {result.get('text', '')}\n"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("transcript_id")
    p.add_argument("--output", required=True)
    p.add_argument("--poll-seconds", type=int, default=5)
    a = p.parse_args()
    key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not key:
        raise SystemExit("ASSEMBLYAI_API_KEY required")
    headers = {"authorization": key}
    for attempt in range(1, 200):
        try:
            r = requests.get(f"{API}/transcript/{a.transcript_id}", headers=headers, timeout=60)
            r.raise_for_status()
            result = r.json()
        except requests.exceptions.RequestException as e:
            print(f"poll attempt {attempt} network error: {e}, retrying in {a.poll_seconds}s", file=sys.stderr)
            time.sleep(a.poll_seconds)
            continue
        status = result.get("status")
        if status == "completed":
            out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
            out.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            out.with_suffix(".txt").write_text(readable(result), encoding="utf-8")
            print(f"Wrote {out.with_suffix('.json')} and {out.with_suffix('.txt')}")
            return
        if status == "error":
            raise RuntimeError(result.get("error", "AssemblyAI transcription failed"))
        time.sleep(a.poll_seconds)
    raise SystemExit("gave up after 200 polls")

if __name__ == "__main__":
    main()

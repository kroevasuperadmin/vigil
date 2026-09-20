#!/usr/bin/env python3
"""AssemblyAI transcription using raw HTTP. Input may be a local file or a public video/audio URL."""
import argparse, json, os, shutil, subprocess, sys, tempfile, time
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

def download_url(url, directory):
    template = str(Path(directory) / "source.%(ext)s")
    cmd = ["yt-dlp", "--no-playlist", "--js-runtimes", "node", "--extractor-args", "youtube:player_client=android", "-x", "--audio-format", "mp3", "-o", template, url]
    subprocess.run(cmd, check=True)
    files = list(Path(directory).glob("source.*"))
    if not files: raise RuntimeError("yt-dlp produced no audio file")
    return files[0]

def upload(path, headers):
    with open(path, "rb") as stream:
        response = requests.post(API + "/upload", headers=headers, data=stream, timeout=900)
    response.raise_for_status()
    return response.json()["upload_url"]

def transcribe(source, output_base, key, poll_seconds=3):
    headers = {"authorization": key}
    temporary = None
    source_path = Path(source)
    if source.startswith(("http://", "https://")):
        temporary = tempfile.TemporaryDirectory(prefix="vigil-")
        source_path = download_url(source, temporary.name)
    if not source_path.is_file(): raise FileNotFoundError(source_path)
    audio_url = upload(source_path, headers)
    # auto_chapters is retained for this requested workflow. AssemblyAI may migrate it to LLM Gateway.
    payload = {"audio_url": audio_url, "speaker_labels": True, "auto_chapters": True, "language_detection": True, "speech_models": ["universal-3-pro", "universal-2"]}
    response = requests.post(API + "/transcript", headers={**headers, "content-type": "application/json"}, json=payload, timeout=60)
    response.raise_for_status(); transcript_id = response.json()["id"]
    while True:
        result = requests.get(f"{API}/transcript/{transcript_id}", headers=headers, timeout=60).json()
        if result.get("status") == "completed": break
        if result.get("status") == "error": raise RuntimeError(result.get("error", "AssemblyAI transcription failed"))
        time.sleep(poll_seconds)
    out = Path(output_base); out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    out.with_suffix(".txt").write_text(readable(result), encoding="utf-8")
    if temporary: temporary.cleanup()
    return out.with_suffix(".json"), out.with_suffix(".txt")

def main():
    p = argparse.ArgumentParser(); p.add_argument("source", help="local audio/video file or a public media/page URL"); p.add_argument("--output", default="output/transcript", help="path without extension"); p.add_argument("--poll-seconds", type=int, default=3)
    a = p.parse_args(); key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not key: raise SystemExit("ASSEMBLYAI_API_KEY is required (it is never read from or printed by this script).")
    raw, text = transcribe(a.source, a.output, key, a.poll_seconds)
    print(f"Wrote {raw} and {text}")

if __name__ == "__main__": main()

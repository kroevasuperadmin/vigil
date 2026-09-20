import os, re, subprocess, sys, datetime, pathlib
os.chdir(pathlib.Path(__file__).resolve().parent)
key = re.search(r"`([0-9a-f]{32})`", open(r"C:\Users\diony\.claude\projects\C--WINDOWS-system32\memory\reference_assemblyai.md", encoding="utf-8").read()).group(1)
env = dict(os.environ, ASSEMBLYAI_API_KEY=key)
out = pathlib.Path("output/grok-galaxy/day1"); out.mkdir(parents=True, exist_ok=True)
log = open(out / "transcribe_full.log", "a", encoding="utf-8")
def say(s): log.write(f"{datetime.datetime.now():%m-%d %H:%M:%S} {s}\n"); log.flush()
# 1) the 7 s our copy lost at the tail: pull the official replay's last 3 minutes as a separate clip
tail = out / "day1_tail.m4a"
if not tail.exists():
    r = subprocess.run(["yt-dlp","--no-warnings","--download-sections","*31300-","-x","--audio-format","m4a","-o",str(tail),
                        "https://x.com/i/broadcasts/1AxRnZbVpjaxl"], capture_output=True, text=True)
    say(f"tail pull rc={r.returncode} {r.stderr[-200:]}")
# 2) whole Day 1 file (8.75 h) -> full.json/full.txt, then the tail -> tail.json/tail.txt
for src, base in [("recordings/day1_replay/0915-233000.m4a", out / "full"), (str(tail), out / "tail")]:
    if (base.with_suffix(".txt")).exists() or not os.path.exists(src): say(f"skip {src}"); continue
    say(f"start {src}")
    r = subprocess.run([sys.executable, "transcribe.py", src, "--output", str(base), "--poll-seconds", "30"], env=env, capture_output=True, text=True)
    say(f"done rc={r.returncode} {r.stdout[-200:]} {r.stderr[-300:]}")
say("all done")

# Vigil

Vigil prepares virtual events, captures a public or attendee-authorized replay in GitHub Actions, sends audio to AssemblyAI, and produces evidence-first startup learnings.

## Fast path

```powershell
python vigil.py https://luma.com/3ifrgttw
# After Faris registers and can access the stream:
python find_stream.py event.json --cookies cookies.txt
gh workflow run capture.yml --repo kroevasuperadmin/vigil --ref main --field url=STREAM_URL --field label=day1-part1 --field event="Grok Bot Galaxy" --field capture_minutes=345
python learn.py transcripts/grok-bot-galaxy/day1-part1.txt
```

`cookies.txt` must be a Netscape-format export from Faris's browser. It is ignored by git. Vigil does not register, complete forms, post, or send messages.

## Limits and cost

GitHub-hosted runners time out at six hours, so use one capture per 5h45 chunk. For replays, use `segment_start` and `segment_end`; for live sources, trigger bounded captures near the sessions you want. The workflow has an optional daily schedule but does nothing until `VIGIL_SCHEDULE_URL` (and related `VIGIL_SCHEDULE_*` variables) are set in the private repository. Legacy `ATTEND_SCHEDULE_*` names still work until you rename them.

AssemblyAI billing is duration-based; check the current plan before a long event. The short test is deliberately under 10 minutes. The workflow uploads audio only to AssemblyAI and commits the resulting JSON and readable text to the private repository.

## Local transcription

`transcribe.py` reads `ASSEMBLYAI_API_KEY` only from the environment. It downloads a URL as audio with yt-dlp, uploads raw bytes to AssemblyAI, then writes `output/transcript.json` and `.txt`. Use Actions for long sources.

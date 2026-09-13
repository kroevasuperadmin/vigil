#!/usr/bin/env python3
"""Ask Codex for evidence-first startup learnings, then turn the result into a one-page PDF."""
import argparse, subprocess, tempfile
from pathlib import Path

def make_pdf(markdown, output):
    from fpdf import FPDF
    pdf = FPDF(format="A4"); pdf.set_auto_page_break(False); pdf.add_page(); pdf.set_margins(14, 12, 14)
    pdf.set_font("Helvetica", "B", 15); pdf.cell(0, 8, "Attend - verified learnings", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=8.5)
    # Keep the single-page handoff readable. The full, sourced analysis remains in learnings.md.
    compact = markdown.replace("**", "").replace("`", "")[:6200]
    for line in compact.splitlines():
        line = line.encode("latin-1", "replace").decode("latin-1")
        if not line.strip(): pdf.ln(1.2); continue
        if line.startswith("#"):
            pdf.set_font("Helvetica", "B", 10); pdf.multi_cell(0, 4.2, line.lstrip("# ")); pdf.set_font("Helvetica", size=8.5)
        else: pdf.multi_cell(0, 3.45, line)
        if pdf.get_y() > 280: break
    Path(output).parent.mkdir(parents=True, exist_ok=True); pdf.output(output)

def main():
    p = argparse.ArgumentParser(); p.add_argument("transcript"); p.add_argument("--output-dir", default="output"); a = p.parse_args()
    transcript = Path(a.transcript).read_text(encoding="utf-8")
    prompt = f'''You are a skeptical research analyst. Analyze this transcript for a generic startup. Never state a speaker claim as fact without verification. Use web search for every material claim and unfamiliar term that your recommendation relies on. Produce concise Markdown with these exact sections: Key ideas; Tools and tactics; Claims and unfamiliar terms to verify (include every material claim/term, quote or precise paraphrase, and why it matters); Fact-check (one row per claim with verdict, current primary source URL, and a one-sentence evidence note); What should change (ranked, separately tagged Example Company / Example Product / Example Console, with effort and confidence). Prefer primary sources. Say insufficient evidence where appropriate.\n\nTRANSCRIPT:\n{transcript}'''
    out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True); md = out / "learnings.md"
    subprocess.run(["codex", "exec", "--search", "--output-last-message", str(md), prompt], check=True)
    make_pdf(md.read_text(encoding="utf-8"), str(out / "learnings.pdf"))
    print(f"Wrote {md} and {out / 'learnings.pdf'}")

if __name__ == "__main__": main()

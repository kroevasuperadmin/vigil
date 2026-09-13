#!/usr/bin/env python3
"""Ask Codex for evidence-first startup learnings, then turn the result into a one-page PDF."""
import argparse, os, re, subprocess, unicodedata
from pathlib import Path

def one_page_digest(markdown):
    sections = {}
    for part in re.split(r"^##\s+", markdown, flags=re.M)[1:]:
        title, _, body = part.partition("\n")
        sections[title.strip().lower()] = body.strip()
    def bullets(name, limit):
        return [line for line in sections.get(name, "").splitlines() if line.lstrip().startswith(("- ", "1.", "2.", "3.", "4.", "5.", "6."))][:limit]
    fact_rows = [line for line in sections.get("fact-check", "").splitlines() if line.startswith("|") and not re.match(r"^\|[- ]+\|", line) and "Claim | Verdict" not in line][:5]
    lines = ["# Attend - verified learning brief", "## Key ideas", *bullets("key ideas", 4), "## Tools and tactics", *bullets("tools and tactics", 4), "## Fact-check highlights"]
    for row in fact_rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) >= 2: lines.append(f"- {cells[0]}: {cells[1]}.")
    lines += ["## What should change", *bullets("what should change", 6), "Full claim ledger and source links: learnings.md"]
    return "\n".join(lines)

def make_pdf(markdown, output):
    from fpdf import FPDF
    pdf = FPDF(format="A4"); pdf.set_auto_page_break(False); pdf.add_page(); pdf.set_margins(14, 12, 14)
    pdf.set_font("Helvetica", "B", 15); pdf.cell(0, 8, "Attend - verified learnings", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10.5)
    # The PDF is a readable one-page decision brief; the complete claim ledger remains in Markdown.
    compact = one_page_digest(markdown).replace("**", "").replace("`", "")
    for line in compact.splitlines():
        try:
            if "â" in line: line = line.encode("latin-1").decode("utf-8")
        except UnicodeError: pass
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", line)
        line = (line.replace("→", "->").replace("–", "-").replace("—", "-").replace("’", "'").replace("“", '"').replace("”", '"'))
        line = unicodedata.normalize("NFKD", line).encode("ascii", "ignore").decode("ascii")
        if not line.strip(): pdf.ln(1.2); continue
        if line.startswith("#"):
            pdf.set_font("Helvetica", "B", 12); pdf.multi_cell(0, 6.0, line.lstrip("# "), new_x="LMARGIN", new_y="NEXT", align="L"); pdf.set_font("Helvetica", size=10.5)
        else: pdf.multi_cell(0, 5.2, line, new_x="LMARGIN", new_y="NEXT", align="L")
        if pdf.get_y() > 280: break
    Path(output).parent.mkdir(parents=True, exist_ok=True); pdf.output(output)

def main():
    p = argparse.ArgumentParser(); p.add_argument("transcript"); p.add_argument("--output-dir", default="output"); a = p.parse_args()
    transcript = Path(a.transcript).read_text(encoding="utf-8")
    prompt = f'''You are a skeptical research analyst. Analyze this transcript for a generic startup. Never state a speaker claim as fact without verification. Use web search for every material claim and unfamiliar term that your recommendation relies on. Produce concise Markdown with these exact sections: Key ideas; Tools and tactics; Claims and unfamiliar terms to verify (include every material claim/term, quote or precise paraphrase, and why it matters); Fact-check (one row per claim with verdict, current primary source URL, and a one-sentence evidence note); What should change (ranked, separately tagged Example Company / Example Product / Example Console, with effort and confidence). Prefer primary sources. Say insufficient evidence where appropriate.\n\nTRANSCRIPT:\n{transcript}'''
    out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True); md = out / "learnings.md"
    codex = os.environ.get("ATTEND_CODEX_BIN", "codex.cmd" if os.name == "nt" else "codex")
    # Newer Codex CLIs expose --search on exec; older installed CLIs do not. Preserve the
    # requested search mode where available, otherwise the prompt still requires web research.
    help_text = subprocess.run([codex, "exec", "--help"], text=True, capture_output=True, check=True).stdout
    command = [codex, "exec"] + (["--search"] if "--search" in help_text else []) + ["--output-last-message", str(md), prompt]
    subprocess.run(command, check=True)
    make_pdf(md.read_text(encoding="utf-8"), str(out / "learnings.pdf"))
    print(f"Wrote {md} and {out / 'learnings.pdf'}")

if __name__ == "__main__": main()

#!/usr/bin/env python3
"""Ask a free model (dev/model-cli/bulk.py) for evidence-first startup learnings, then turn the result into a one-page PDF."""
import argparse, os, re, subprocess, sys, unicodedata
from pathlib import Path

def one_page_digest(markdown):
    # Free models sometimes write "**Key ideas**" instead of "## Key ideas"; treat both as headings.
    markdown = re.sub(r"^\s*\*\*([^*\n]+?)\*\*:?\s*$", r"## \1", markdown, flags=re.M)
    sections = {}
    for part in re.split(r"^##\s+", markdown, flags=re.M)[1:]:
        title, _, body = part.partition("\n")
        # Models also write "Fact‑check" with a non-breaking hyphen; normalise dashes so lookups match.
        key = re.sub(r"[‐‑‒–—]", "-", title.strip().lower())
        sections[key] = body.strip()
    def bullets(name, limit):
        out = []
        for line in sections.get(name, "").splitlines():
            s = line.strip()
            if s.startswith(("- ", "* ", "• ", "1.", "2.", "3.", "4.", "5.", "6.")):
                out.append("- " + s.lstrip("-*• ").strip())
            elif s.startswith("|") and not re.match(r"^\|[\s:|-]+\|?$", s):
                cells = [c.strip() for c in s.strip("|").split("|")]
                # Skip the header row (its first cell is a column name like "Tool / Tactic" or "Area").
                if len(cells) >= 2 and not out and cells[0].lower().strip("* ") in ("tool / tactic", "area", "#", "tool", "change", "claim"):
                    continue
                if len(cells) >= 2: out.append(f"- {cells[0]}: {cells[1]}")
        return out[:limit]
    fact_rows = [line for line in sections.get("fact-check", "").splitlines() if line.startswith("|") and not re.match(r"^\|[- ]+\|", line) and "Claim | Verdict" not in line][:5]
    lines = ["# Vigil - verified learning brief", "## Key ideas", *bullets("key ideas", 4), "## Tools and tactics", *bullets("tools and tactics", 4), "## Fact-check highlights"]
    for row in fact_rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) >= 2: lines.append(f"- {cells[0]}: {cells[1]}.")
    lines += ["## What should change", *bullets("what should change", 6), "Full claim ledger and source links: learnings.md"]
    return "\n".join(lines)

def make_pdf(markdown, output):
    from fpdf import FPDF
    pdf = FPDF(format="A4"); pdf.set_auto_page_break(False); pdf.add_page(); pdf.set_margins(14, 12, 14)
    pdf.set_font("Helvetica", "B", 15); pdf.cell(0, 8, "Vigil - verified learnings", new_x="LMARGIN", new_y="NEXT")
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
    prompt = f'''You are a skeptical research analyst. Analyze this transcript for a generic startup. You cannot browse the web, so never state a speaker claim as fact: label every material claim SPEAKER CLAIM (unverified) unless it is common knowledge. Produce concise Markdown with these exact sections: Key ideas; Tools and tactics; Claims and unfamiliar terms to verify (include every material claim/term, quote or precise paraphrase, and why it matters); Fact-check (a table: Claim | Verdict | Source to check | Note, where Verdict is UNVERIFIED unless common knowledge, and Source to check names the primary source that would settle it); What should change (ranked, tagged by relevant product, with effort and confidence). Say insufficient evidence where appropriate. Formatting: start every section with a "## " heading using exactly those names; write Key ideas, Tools and tactics and What should change as "- " bullet lists (no tables); use a table only for Fact-check.\n\nTRANSCRIPT:\n{transcript}'''
    out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True); md = out / "learnings.md"
    # ponytail: free-model text only (Codex hit its usage limit until 10 Oct 2026); no web fact-check.
    # Upgrade path: verify the Fact-check rows with dev/model-cli/exa.py once a transcript is worth it.
    prompt_file = out / "learn_prompt.txt"; prompt_file.write_text(prompt, encoding="utf-8")
    bulk = os.environ.get("VIGIL_BULK") or os.environ.get("ATTEND_BULK") or r"C:\Users\diony\dev\model-cli\bulk.py"
    subprocess.run([sys.executable, bulk, "-i", str(prompt_file), "-o", str(md), "--max-tokens", "8192", "--must", "What should change"], check=True)
    make_pdf(md.read_text(encoding="utf-8"), str(out / "learnings.pdf"))
    print(f"Wrote {md} and {out / 'learnings.pdf'}")

if __name__ == "__main__": main()

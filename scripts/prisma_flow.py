#!/usr/bin/env python3
"""
prisma_flow.py — Generate a PRISMA-2020 flow diagram as SVG and PDF.

Reads a flow definition JSON:
{
  "identification": {
    "from_databases": [{"name": "arXiv", "n": 320}, ...],
    "from_other": [{"name": "Snowballing", "n": 14}, ...]
  },
  "after_dedup": 412,
  "screening": {
    "screened": 412,
    "excluded_title_abstract": 312,
    "exclusion_reasons": [
      {"reason": "Off-topic", "n": 220},
      {"reason": "Not peer-reviewed", "n": 60},
      {"reason": "Other language", "n": 32}
    ]
  },
  "retrieval": {
    "sought": 100,
    "not_retrieved": 5
  },
  "eligibility": {
    "assessed": 95,
    "excluded_full_text": 38,
    "exclusion_reasons": [
      {"reason": "Insufficient methodology", "n": 12},
      {"reason": "Below QA threshold", "n": 10},
      {"reason": "Not addressing RQ", "n": 16}
    ]
  },
  "included": {"studies": 57, "reports": 57}
}

Usage:
    python prisma_flow.py --flow flow.json --out prisma_flow.svg
    python prisma_flow.py --flow flow.json --out prisma_flow.pdf

PDF requires cairosvg (pip install cairosvg --break-system-packages).
"""
import argparse
import json
import sys
from xml.sax.saxutils import escape


# Layout: two-column stacked boxes with arrows. Height grows with content.
# Left column = main flow (identification → screening → eligibility → included).
# Right column = exclusions / "other sources" annotations.
PAD = 12
BOX_W = 360
BOX_H_BASE = 42
LINE_H = 16
GAP = 22
LEFT_X = 60                       # left edge of main column
RIGHT_X = LEFT_X + BOX_W + 40     # left edge of right column = 460
W = RIGHT_X + BOX_W + 40          # total width with right margin = 860


def wrap(text, max_chars=58):
    """Naive word-wrap into lines of <= max_chars chars."""
    words = text.split()
    out, cur = [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if len(cand) > max_chars and cur:
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out


def box(x, y, lines, fill="#f5f5f5", stroke="#222"):
    h = max(BOX_H_BASE, PAD * 2 + LINE_H * len(lines))
    rect = (f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.2" rx="4" ry="4"/>')
    text_lines = []
    ty = y + PAD + 12
    for ln in lines:
        text_lines.append(
            f'<text x="{x + BOX_W/2}" y="{ty}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="12" text-anchor="middle" fill="#111">{escape(ln)}</text>'
        )
        ty += LINE_H
    return rect + "\n" + "\n".join(text_lines), h


def arrow(x1, y1, x2, y2):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="#222" stroke-width="1.2" marker-end="url(#arrow)"/>')


def section_title(x, y, txt):
    return (f'<text x="{x}" y="{y}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="13" font-weight="bold" fill="#333">{escape(txt)}</text>')


def render_svg(flow):
    parts = []
    # Defs for arrowhead
    parts.append('''<defs>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3"
                orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#222"/>
        </marker>
    </defs>''')

    y = 30

    # Section: Identification
    parts.append(section_title(20, y, "Identification"))
    y += 14

    # Identification — from databases
    db_total = sum(d["n"] for d in flow["identification"].get("from_databases", []))
    other_total = sum(d["n"] for d in flow["identification"].get("from_other", []))

    db_lines = ["Records identified from databases", f"Total: n = {db_total}"]
    db_lines += [f'{d["name"]}: n = {d["n"]}'
                 for d in flow["identification"].get("from_databases", [])]
    svg, h1 = box(LEFT_X, y, db_lines)
    parts.append(svg)
    bottom_db = y + h1

    # Other sources box (right of databases)
    if other_total > 0:
        other_lines = ["Records identified from other sources", f"Total: n = {other_total}"]
        other_lines += [f'{d["name"]}: n = {d["n"]}'
                        for d in flow["identification"].get("from_other", [])]
        svg2, h2 = box(RIGHT_X, y, other_lines, fill="#fafaf0")
        parts.append(svg2)

    y = bottom_db + GAP

    # Dedup
    dedup_lines = [f'Records after deduplication', f'n = {flow["after_dedup"]}']
    svg, h = box(LEFT_X, y, dedup_lines, fill="#eef2f7")
    parts.append(svg)
    parts.append(arrow(LEFT_X + BOX_W / 2, bottom_db, LEFT_X + BOX_W / 2, y))
    y += h + GAP

    # Section: Screening
    parts.append(section_title(20, y - 6, "Screening"))

    scr = flow["screening"]
    screened_lines = ["Records screened (title/abstract)", f'n = {scr["screened"]}']
    svg, h_scr = box(LEFT_X, y, screened_lines)
    parts.append(svg)
    parts.append(arrow(LEFT_X + BOX_W / 2, y - GAP, LEFT_X + BOX_W / 2, y))

    # Exclusions box (right)
    excl_lines = [f'Excluded after T/A: n = {scr["excluded_title_abstract"]}']
    for r in scr.get("exclusion_reasons", []):
        excl_lines.append(f'  {r["reason"]}: n = {r["n"]}')
    svg_excl, h_excl = box(RIGHT_X, y, excl_lines, fill="#fff0f0")
    parts.append(svg_excl)
    # Arrow from screened to exclusions
    parts.append(arrow(LEFT_X + BOX_W, y + h_scr / 2, RIGHT_X, y + h_excl / 2))

    y_after_screen = y + max(h_scr, h_excl) + GAP

    # Retrieval
    ret = flow["retrieval"]
    sought_lines = ["Reports sought for retrieval", f'n = {ret["sought"]}']
    svg, h_sg = box(LEFT_X, y_after_screen, sought_lines)
    parts.append(svg)
    parts.append(arrow(LEFT_X + BOX_W / 2, y_after_screen - GAP,
                       LEFT_X + BOX_W / 2, y_after_screen))

    # Not retrieved (right)
    nr_lines = [f'Reports not retrieved: n = {ret["not_retrieved"]}']
    svg_nr, h_nr = box(RIGHT_X, y_after_screen, nr_lines, fill="#fff0f0")
    parts.append(svg_nr)
    parts.append(arrow(LEFT_X + BOX_W, y_after_screen + h_sg / 2,
                       RIGHT_X, y_after_screen + h_nr / 2))

    y_after_ret = y_after_screen + max(h_sg, h_nr) + GAP

    # Eligibility
    elig = flow["eligibility"]
    elig_lines = ["Reports assessed for eligibility (full-text)",
                  f'n = {elig["assessed"]}']
    svg, h_el = box(LEFT_X, y_after_ret, elig_lines)
    parts.append(svg)
    parts.append(arrow(LEFT_X + BOX_W / 2, y_after_ret - GAP,
                       LEFT_X + BOX_W / 2, y_after_ret))

    excl_ft_lines = [f'Excluded after full-text: n = {elig["excluded_full_text"]}']
    for r in elig.get("exclusion_reasons", []):
        excl_ft_lines.append(f'  {r["reason"]}: n = {r["n"]}')
    svg_ef, h_ef = box(RIGHT_X, y_after_ret, excl_ft_lines, fill="#fff0f0")
    parts.append(svg_ef)
    parts.append(arrow(LEFT_X + BOX_W, y_after_ret + h_el / 2,
                       RIGHT_X, y_after_ret + h_ef / 2))

    y_after_elig = y_after_ret + max(h_el, h_ef) + GAP

    # Included
    parts.append(section_title(20, y_after_elig - 6, "Included"))
    inc = flow["included"]
    inc_lines = ["Studies included in review", f'n = {inc["studies"]}',
                 f'Reports of included studies: n = {inc.get("reports", inc["studies"])}']
    svg, h_inc = box(LEFT_X, y_after_elig, inc_lines, fill="#e6f5e6")
    parts.append(svg)
    parts.append(arrow(LEFT_X + BOX_W / 2, y_after_elig - GAP,
                       LEFT_X + BOX_W / 2, y_after_elig))

    total_h = y_after_elig + h_inc + 30
    svg_open = (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{W}" height="{total_h}" viewBox="0 0 {W} {total_h}">')
    return svg_open + "\n" + "\n".join(parts) + "\n</svg>"


def to_pdf(svg_text, out_path):
    try:
        import cairosvg
    except ImportError:
        print("cairosvg not available. Install with:")
        print("  pip install cairosvg --break-system-packages")
        sys.exit(1)
    cairosvg.svg2pdf(bytestring=svg_text.encode("utf-8"), write_to=out_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--flow", required=True, help="Flow definition JSON")
    p.add_argument("--out", required=True, help="Output .svg or .pdf")
    args = p.parse_args()

    with open(args.flow, "r", encoding="utf-8") as f:
        flow = json.load(f)

    svg = render_svg(flow)
    if args.out.lower().endswith(".pdf"):
        to_pdf(svg, args.out)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(svg)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

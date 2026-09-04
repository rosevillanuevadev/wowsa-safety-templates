#!/usr/bin/env python3
"""
Shared machinery for the WOWSA Learn guide builders.

The cover, the stylesheet, the height measurement and the sheet packing are
identical for every guide family. Only the section body rendering differs, so
that is all a family specific builder has to supply.

Sheets are fixed rather than flowing. Chrome does not paint a page background
into the @page margins, so a flowing layout can have the cream bleed to the
edge or per page margins, but not both. Fixed sheets of 8.5 by 11 inches with
their own padding give both, at the cost of having to paginate deliberately,
which is what measure() and pack() do.
"""

import base64, html, json, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

SHELL = """<!doctype html>
<html><head><meta charset="utf-8">
<link rel="stylesheet" href="fonts.css">
<link rel="stylesheet" href="rr.css">
</head><body>{body}</body></html>"""

# usable height inside a sheet, in CSS pixels: 11in less 0.62in top and bottom
PAGE_PX = (11 - 0.62 * 2) * 96

# Blocks are measured inside a flow-root wrapper and placed inside an
# identical one, so inner margins are contained in both passes and the height
# measured here is the height the block actually occupies on a sheet.
MEASURE_JS = """
<script>
addEventListener('load', function () {
  document.querySelectorAll('.mb').forEach(function (el) {
    el.setAttribute('data-h', Math.ceil(el.getBoundingClientRect().height));
  });
});
</script>"""


def e(s):
    return html.escape(s, quote=False)


def ul(items):
    return "<ul>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>"


def seal():
    with open(os.path.join(HERE, "assets", "wowsa-seal.png"), "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def cover_html(g):
    cline = (f'<div class="compline">{e(g["components_line"])}</div>'
             if g.get("components_line") else "")
    return f"""
<div class="cover">
  <img class="seal" src="{seal()}">
  <div class="eyebrow">{e(g['eyebrow'])}</div>
  <div class="acronym">{e(g['acronym'])}</div>
  <div class="tagline">{e(g['tagline'])}</div>
  <div class="rule"></div>
  <h1>{e(g['title'])}</h1>
  <div class="deck">{e(g['deck'])}</div>
  {cline}
  <div class="spacer"></div>
  <div class="whobox">
    <div class="lbl">Who this is for</div>
    <p>{e(g['who'])}</p>
  </div>
  <div class="online">
    <div class="lbl">Read this guide online</div>
    <a href="{g['canonical']}">{e(g['canonical'])}</a>
  </div>
  <div class="colophon">{e(g['colophon'])}</div>
</div>"""


def measure(blocks):
    """Render the blocks once and read back each one's real height."""
    marked = "".join('<div class="mb" data-i="%d">%s</div>' % (i, b)
                     for i, b in enumerate(blocks))
    doc = SHELL.format(body='<div class="measure">%s</div>%s' % (marked, MEASURE_JS))
    path = os.path.join(HERE, "_measure.html")
    with open(path, "w") as fh:
        fh.write(doc)
    out = subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--virtual-time-budget=8000",
         "--dump-dom", path],
        check=True, capture_output=True, text=True).stdout

    hs = {}
    for m in re.finditer(r'<div class="mb"([^>]*)>', out):
        i = re.search(r'data-i="(\d+)"', m.group(1))
        h = re.search(r'data-h="(\d+)"', m.group(1))
        if i and h:
            hs[int(i.group(1))] = int(h.group(1))
    missing = [i for i in range(len(blocks)) if i not in hs]
    if missing:
        raise SystemExit("measurement failed for blocks %s" % missing)
    return [hs[i] for i in range(len(blocks))]


def pack(blocks, heights):
    """Greedily fill sheets, never splitting a block across two sheets."""
    sheets, used, cur, h = [], [], [], 0
    for b, bh in zip(blocks, heights):
        if cur and h + bh > PAGE_PX:
            sheets.append(cur)
            used.append(h)
            cur, h = [], 0
        cur.append(b)
        h += bh
    if cur:
        sheets.append(cur)
        used.append(h)
    return sheets, used


def render(g, built, outdir):
    """Measure, paginate and print one guide to PDF."""
    cover, blocks = built
    heights = measure(blocks)

    over = [i for i, h in enumerate(heights) if h > PAGE_PX]
    if over:
        raise SystemExit("block(s) taller than one sheet: %s" % over)

    sheets, used = pack(blocks, heights)
    body = '<div class="sheet">%s</div>' % cover
    body += "".join(
        '<div class="sheet">%s</div>'
        % "".join('<div class="blk">%s</div>' % b for b in s)
        for s in sheets)

    html_path = os.path.join(HERE, "_build.html")
    with open(html_path, "w") as fh:
        fh.write(SHELL.format(body=body))

    outdir = os.path.join(HERE, outdir)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, g["filename"])
    subprocess.run([
        CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        "--virtual-time-budget=12000", "--print-to-pdf=%s" % out, html_path,
    ], check=True, capture_output=True)

    print("wrote %-34s sheets=%d  fullest=%d/%d px"
          % (os.path.basename(out), 1 + len(sheets), max(used), PAGE_PX))
    return out

#!/usr/bin/env python3
"""
Build a Compound Risk guide PDF on the approved WOWSA design.

    python3 build_cr.py content/cr/compound-risk-for-swimmers.json

Shares the stylesheet, the cover and the sheet packing with the lettered
framework guides. Only the section body rendering differs, because Compound
Risk is built from groups and numbered steps rather than lettered components.
"""

import json, os, sys

from guide_common import cover_html, e, render, ul


def block(b):
    k = b["kind"]
    if k == "bullets":
        close = f'<p class="tail">{e(b["close"])}</p>' if b.get("close") else ""
        return ul(b["items"]) + close
    if k == "group":
        return f'<div class="grp">{e(b["title"])}</div>'
    if k == "step":
        body = "".join(f"<p>{e(p)}</p>" for p in b["body"])
        q = f'<div class="q">{e(b["question"])}</div>' if b["question"] else ""
        return (f'<div class="step"><div class="n">{e(b["number"])}</div>'
                f'<div><h4>{e(b["title"])}</h4>{q}{body}</div></div>')
    if k == "ask":
        return ('<div class="ask"><div class="lbl">Ask</div>'
                f'<div class="q2">{e(b["text"])}</div></div>')
    if k == "note":
        return ('<div class="notebox"><div class="lbl">Note</div>'
                f'<p>{e(b["text"])}</p></div>')
    if k == "text":
        return "".join(f"<p>{e(p)}</p>" for p in b["body"])
    raise ValueError("unknown block: " + k)


def build(g):
    def head(kicker, title):
        return (f'<div class="kicker">{e(kicker)}</div>'
                f'<h2 class="big">{e(title)}</h2><div class="headrule"></div>')

    blocks = [head("Introduction", g["intro_title"])
              + "".join(f"<p>{e(p)}</p>" for p in g["intro"])]

    for s in g["sections"]:
        # some sections open with a short title and some with a full sentence;
        # a sentence set in the display face would run over a sheet and read
        # badly, so it becomes the opening paragraph instead
        if len(s["lede"]) <= 58:
            opened = head(s["key"].title(), s["lede"])
            lead = []
        else:
            opened = head(s["key"].title(), s["key"].title())
            lead = [s["lede"]]
        opened += "".join(f"<p>{e(p)}</p>" for p in lead + s["body"])
        blocks.append(opened)
        for b in s["blocks"]:
            blocks.append(block(b))

    d = g["decision"]
    blocks.append(head("Putting it together", d["title"])
                  + "".join(f"<p>{e(x)}</p>" for x in d["lede"]))
    for o in d["options"]:
        blocks.append(
            f'<div class="opts"><div class="opt"><div class="k">{e(o["label"])} '
            f'<span class="dash">/</span> <span class="lede">{e(o["lede"])}</span></div>'
            + "".join(f"<p>{e(x)}</p>" for x in o["body"]) + "</div></div>")
    if d["override"] or d["quick_check"]:
        blocks.append(
            '<div class="pairs">'
            + (f'<div class="pair"><div class="lbl">Override</div>'
               f'<p>{e(d["override"])}</p></div>' if d["override"] else "")
            + (f'<div class="pair"><div class="lbl">Quick check</div>'
               f'<p>{e(d["quick_check"])}</p></div>' if d["quick_check"] else "")
            + "</div>")

    blocks.append(head("Where this leads next", "Keep going"))
    blocks += [f'<div class="nxt"><div class="kind">{e(n["kind"])}</div>'
               f'<div class="lab">{e(n["label"])}</div><p>{e(n["desc"])}</p>'
               f'<div class="u"><a href="{n["url"]}">{e(n["url"])}</a></div></div>'
               for n in g["next"]]

    src = "".join(
        f'<div class="src"><div class="t">{e(s["label"])}</div>'
        f'<div class="u"><a href="{s["url"]}">{e(s["url"])}</a></div></div>'
        for s in g["sources"])
    blocks.append(head("Sources and further reading", "References") + src)
    blocks.append(f'<div class="endnote">Canonical guide: '
                  f'<a href="{g["canonical"]}">{e(g["canonical"])}</a><br>'
                  f'World Open Water Swimming Association, WOWSA Learn.</div>')

    return cover_html(g), blocks


if __name__ == "__main__":
    with open(sys.argv[1]) as fh:
        g = json.load(fh)
    render(g, build(g), os.path.join("output", "cr"))

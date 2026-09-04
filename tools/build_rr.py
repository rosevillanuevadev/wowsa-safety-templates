#!/usr/bin/env python3
"""
Build a Reading Risk guide PDF on the approved WOWSA design.

    python3 build_rr.py content/rr/check-framework-for-swimmers.json

Renders through headless Chrome. One template, one content file per guide.
"""

import json, os, sys

from guide_common import cover_html, e, render, seal, ul

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def component(c):
    tail = f'<p class="tail">{e(c["note"])}</p>' if c["note"] else ""
    body = "".join(f"<p>{e(p)}</p>" for p in c["body"])
    return f"""
<div class="comp">
  <div class="comp-head">
    <div class="badge">{e(c['letter'])}</div>
    <div>
      <h3>{e(c['name'])}</h3>
      <div class="q">{e(c['tagline'])}</div>
    </div>
  </div>
  <div class="comp-rule"></div>
  {body}
  <div class="ask">
    <div class="lbl">Ask</div>
    <div class="q2">{e(c['ask'])}</div>
  </div>
  <div class="cols">
    <div class="col"><div class="lbl">What to look for</div>{ul(c['look_for'])}</div>
    <div class="col"><div class="lbl">If something changes</div>{ul(c['if_changes'])}</div>
  </div>
  {tail}
</div>"""


def build(g):
    d = g["decision"]
    opts = "".join(
        f'<div class="opt"><div class="k">{e(o["label"])} '
        f'<span class="dash">/</span> <span class="lede">{e(o["lede"])}</span></div>'
        + "".join(f"<p>{e(b)}</p>" for b in o["body"]) + "</div>"
        for o in d["options"]
    )

    pairs = ""
    if d["override"] or d["quick_check"]:
        pairs = ('<div class="pairs">'
                 + (f'<div class="pair"><div class="lbl">Override</div>'
                    f'<p>{e(d["override"])}</p></div>' if d["override"] else "")
                 + (f'<div class="pair"><div class="lbl">Quick check</div>'
                    f'<p>{e(d["quick_check"])}</p></div>' if d["quick_check"] else "")
                 + "</div>")

    extra = ""
    if g["extra"]:
        x = g["extra"]
        extra = (f'<div class="kicker">Also</div><h2 class="big">{e(x["title"])}</h2>'
                 f'<div class="headrule"></div>'
                 + "".join(f"<p>{e(p)}</p>" for p in x["lede"])
                 + ul(x["items"]))

    cp = g["compound"]
    close = f'<p class="tail">{e(cp["close"])}</p>' if cp["close"] else ""

    nxt = "".join(
        f'<div class="nxt"><div class="kind">{e(n["kind"])}</div>'
        f'<div class="lab">{e(n["label"])}</div>'
        f'<p>{e(n["desc"])}</p>'
        f'<div class="u"><a href="{n["url"]}">{e(n["url"])}</a></div></div>'
        for n in g["next"]
    )

    src = "".join(
        f'<div class="src"><div class="t">{e(s["label"])}</div>'
        f'<div class="u"><a href="{s["url"]}">{e(s["url"])}</a></div></div>'
        for s in g["sources"]
    )

    intro = "".join(f"<p>{e(p)}</p>" for p in g["intro"])
    cline = (f'<div class="compline">{e(g["components_line"])}</div>'
             if g["components_line"] else "")

    def head(kicker, title):
        return (f'<div class="kicker">{e(kicker)}</div>'
                f'<h2 class="big">{e(title)}</h2><div class="headrule"></div>')

    blocks = [head("Introduction", g["intro_title"]) + intro,
              head("The components", g["components_line"] or g["components_sub"])]
    blocks += [component(c) for c in g["components"]]
    blocks.append(head("Putting it together", d["title"])
                  + "".join(f"<p>{e(x)}</p>" for x in d["lede"]))
    blocks += [f'<div class="opts">{o}</div>' for o in [
        f'<div class="opt"><div class="k">{e(o["label"])} '
        f'<span class="dash">/</span> <span class="lede">{e(o["lede"])}</span></div>'
        + "".join(f"<p>{e(x)}</p>" for x in o["body"]) + "</div>"
        for o in d["options"]]]
    if pairs:
        blocks.append(pairs)
    if extra:
        blocks.append(extra)
    blocks.append(head("Compound risk", "The inputs interact")
                  + "".join(f"<p>{e(x)}</p>" for x in cp["lede"])
                  + ul(cp["items"]) + close)
    blocks.append(head("Where this leads next", "Keep going"))
    blocks += [f'<div class="nxt"><div class="kind">{e(n["kind"])}</div>'
               f'<div class="lab">{e(n["label"])}</div><p>{e(n["desc"])}</p>'
               f'<div class="u"><a href="{n["url"]}">{e(n["url"])}</a></div></div>'
               for n in g["next"]]
    blocks.append(head("Sources and further reading", "References") + src)
    blocks.append(f'<div class="endnote">Canonical guide: '
                  f'<a href="{g["canonical"]}">{e(g["canonical"])}</a><br>'
                  f'World Open Water Swimming Association, WOWSA Learn.</div>')

    cover = f"""
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
    return cover, blocks


if __name__ == "__main__":
    with open(sys.argv[1]) as fh:
        g = json.load(fh)
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join("output", "rr")
    render(g, build(g), outdir)


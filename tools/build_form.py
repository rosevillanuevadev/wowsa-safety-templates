#!/usr/bin/env python3
"""
Build a fillable WOWSA form PDF in the approved design.

    python3 build_form.py content/forms/safe-coach-risk-assessment.json

Two stages. Chrome renders the design and emits a link annotation with an exact
rectangle everywhere a field belongs. PyMuPDF then replaces each of those links
with a real AcroForm widget, so the file keeps the approved look and stays
fillable and saveable.
"""

import base64
import json
import os
import subprocess
import sys

import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MARK = "https://f.local/"


def seal_uri():
    with open(os.path.join(HERE, "assets", "wowsa-seal.png"), "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


# ---------- html components ----------

def txt(name, cls="box"):
    return f'<a class="{cls}" href="{MARK}text/{name}"></a>'


def dot(group, value):
    return f'<a class="dot" href="{MARK}radio/{group}/{value}"></a>'


def chk(name):
    return f'<a class="chk" href="{MARK}check/{name}"></a>'


def field(label, name, cls="box"):
    return f'<div class="f"><label>{label}</label>{txt(name, cls)}</div>'


def block(b):
    t = b["type"]

    if t == "section":
        return (f'<div class="sec-head"><div class="sec-bar"></div>'
                f'<h2>{b["label"]}</h2></div><div class="sec-rule"></div>')

    if t == "hint":
        return f'<p class="hint">{b["text"]}</p>'

    if t == "row":
        return ('<div class="row">' + "".join(
            field(f["label"], f["name"], f.get("cls", "box")) for f in b["fields"]
        ) + "</div>")

    if t == "legend":
        return ('<div class="legend">' + "".join(
            f'<div class="{i["cls"]}"><b>{i["k"]}</b> <span>{i["v"]}</span></div>'
            for i in b["items"]
        ) + "</div>")

    if t == "table":
        head = "".join(
            f'<th style="width:{c["w"]}">{c["label"]}</th>' for c in b["cols"]
        )
        rows = ""
        for r in range(b["rows"]):
            cells = ""
            for c in b["cols"]:
                if c.get("radio"):
                    opts = "".join(
                        f'<div class="opt {o["cls"]}">{dot(c["name"] + f"_r{r}", o["v"])}'
                        f'<em>{o["v"]}</em></div>'
                        for o in c["radio"]
                    )
                    cells += f'<td><div class="radios stack">{opts}</div></td>'
                else:
                    cells += f'<td>{txt(c["name"] + f"_r{r}")}</td>'
            rows += f"<tr>{cells}</tr>"
        return (f'<table><thead><tr>{head}</tr></thead>'
                f"<tbody>{rows}</tbody></table>")

    if t == "decision":
        return ('<div class="decision">' + "".join(
            f'<div class="pill-opt">{dot(b["name"], o)}<em>{o}</em></div>'
            for o in b["options"]
        ) + "</div>")

    if t == "radiorow":
        opts = "".join(
            f'<div class="opt">{dot(b["name"], o)}<em>{o}</em></div>'
            for o in b["options"]
        )
        return (f'<div class="f"><label>{b["label"]}</label>'
                f'<div class="radios" style="height:22px">{opts}</div></div>')

    if t == "inline":
        parts = ""
        for f in b["fields"]:
            if f["type"] == "text":
                parts += field(f["label"], f["name"], f.get("cls", "box"))
            else:
                opts = "".join(
                    f'<div class="opt">{dot(f["name"], o)}<em>{o}</em></div>'
                    for o in f["options"]
                )
                parts += (f'<div class="f"><label>{f["label"]}</label>'
                          f'<div class="radios" style="height:22px">{opts}</div></div>')
        return f'<div class="row">{parts}</div>'

    if t == "callout":
        return (f'<div class="callout"><h3>{b["title"]}</h3>'
                f'<p>{b["text"]}</p>{txt(b["name"], "box xtall")}</div>')

    if t == "checklist":
        cols = b.get("cols", 3)
        cells = "".join(
            f'<div class="ck" style="width:{100/cols:.4f}%">{chk(i["name"])}'
            f'<span>{i["label"]}</span></div>'
            for i in b["items"]
        )
        head = f'<label class="stand">{b["label"]}</label>' if b.get("label") else ""
        other = ""
        if b.get("other"):
            other = ('<div class="row" style="margin-top:6px">'
                     + field(b["other"]["label"], b["other"]["name"]) + "</div>")
        return f'{head}<div class="checks">{cells}</div>{other}'

    if t == "scenario":
        return (f'<div class="scn"><div class="scn-t">{b["title"]}</div>'
                f'<div class="row">'
                f'<div class="f"><label>{b.get("a_label", "How it is activated")}</label>'
                f'{txt(b["a_name"], "box tall")}</div>'
                f'<div class="f"><label>{b.get("r_label", "How the team responds")}</label>'
                f'{txt(b["r_name"], "box tall")}</div>'
                f"</div></div>")

    if t == "grid":
        head = "".join(f'<th style="width:{c["w"]}">{c["label"]}</th>'
                       for c in b["cols"])
        rows = ""
        for r in b["rows"]:
            cells = f'<td class="lead">{r["label"]}</td>'
            cells += "".join(f"<td>{txt(n)}</td>" for n in r["fields"])
            rows += f"<tr>{cells}</tr>"
        return (f'<table class="grid"><thead><tr>{head}</tr></thead>'
                f"<tbody>{rows}</tbody></table>")

    if t == "spacer":
        return f'<div style="height:{b["h"]}px"></div>'

    raise ValueError("unknown block: " + t)


def build_html(c):
    seal = seal_uri()
    pages = ""
    total = len(c["pages"])
    for i, pg in enumerate(c["pages"], start=1):
        body = "".join(block(b) for b in pg["blocks"])
        pages += f"""
<div class="page">
  <div class="head">
    <img class="seal" src="{seal}">
    <div>
      <h1>{pg['title']}</h1>
      <div class="deck">{pg['deck']}</div>
    </div>
  </div>
  <div class="head-rule"></div>
  {body}
  <div class="foot">
    <span>{c['footer_left']}</span>
    <span>{c['footer_right']} - {i} / {total}</span>
  </div>
</div>"""

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<link rel="stylesheet" href="fonts.css">
<link rel="stylesheet" href="form.css">
</head><body>{pages}</body></html>"""


# ---------- stage 2: links become real form fields ----------

def add_widgets(pdf_path):
    doc = fitz.open(pdf_path)
    made = {"text": 0, "radio": 0, "check": 0}

    for page in doc:
        links = [l for l in page.get_links()
                 if l.get("uri", "").startswith(MARK)]

        # drop the marker links first so they cannot survive as clickable areas
        for l in reversed(links):
            page.delete_link(l)

        for l in links:
            spec = l["uri"][len(MARK):].split("/")
            rect = fitz.Rect(l["from"])

            if spec[0] == "text":
                w = fitz.Widget()
                w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
                w.field_name = spec[1]
                w.rect = rect
                w.text_fontsize = 9
                w.text_font = "Helv"
                w.text_color = (0.07, 0.15, 0.23)
                w.fill_color = None
                w.border_color = None
                if rect.height > 30:
                    w.field_flags = fitz.PDF_TX_FIELD_IS_MULTILINE
                page.add_widget(w)
                made["text"] += 1

            elif spec[0] == "check":
                w = fitz.Widget()
                w.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
                w.field_name = spec[1]
                w.rect = rect
                w.fill_color = None
                w.border_color = None
                w.field_value = False
                page.add_widget(w)
                made["check"] = made.get("check", 0) + 1

            elif spec[0] == "radio":
                group, value = spec[1], spec[2]
                w = fitz.Widget()
                w.field_type = fitz.PDF_WIDGET_TYPE_RADIOBUTTON
                w.field_name = group
                w.button_caption = ""
                w.rect = rect
                w.fill_color = None
                w.border_color = None
                w.field_value = False
                w.field_label = value
                page.add_widget(w)
                made["radio"] += 1

    doc.saveIncr()
    doc.close()
    return made


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "content", "forms", "safe-coach-risk-assessment.json")
    with open(src) as fh:
        c = json.load(fh)

    html_path = os.path.join(HERE, "_form.html")
    with open(html_path, "w") as fh:
        fh.write(build_html(c))

    out = os.path.join(HERE, "output", c["filename"])
    subprocess.run([
        CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        "--virtual-time-budget=10000", f"--print-to-pdf={out}", html_path,
    ], check=True, capture_output=True)

    made = add_widgets(out)
    print(f"wrote {out}")
    print(f"  text: {made['text']}  radio: {made['radio']}  checkbox: {made['check']}")


if __name__ == "__main__":
    main()

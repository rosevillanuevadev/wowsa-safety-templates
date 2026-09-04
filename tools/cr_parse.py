#!/usr/bin/env python3
"""
Parse an extracted Compound Risk guide into structured JSON.

    python3 cr_parse.py <name>.txt content/cr/<name>.json

Compound Risk is a different shape from the lettered frameworks. There are no
components. Each section is a lede followed by some mix of prose, named groups
with bullets, numbered steps, and labeled Ask and Note blocks, so the parser
reads that general shape rather than a fixed list of headings.
"""

import json, os, re, sys

from rr_parse import HEAD, OPT, bullets, clean, is_head, joiner, split_at

STEP = re.compile(r"^(\d+)\.\s+(.+)$")
LABELS = ("Ask", "Note")

# sections that carry the decision options rather than ordinary prose
DECISION_KEY = "PUTTING IT TOGETHER"


def walk(lines):
    """Read a section as a sequence of paragraphs and bullets.

    Lines are wrapped at the layout width, so a line shorter than that width
    closes whatever it is part of. Applying that rule during the walk, rather
    than after grouping, is what keeps a group title such as "Exposure" from
    being absorbed into the bullet above it.
    """
    width = max((len(l) for l in lines), default=0)
    cut = width * 0.90
    out, i = [], 0

    def is_group_title(k):
        """A short, unpunctuated line sitting directly on top of a bullet."""
        return (k + 1 < len(lines)
                and lines[k] not in LABELS and lines[k] != "-"
                and len(lines[k]) < 70
                and lines[k][-1] not in ".?!,:;"
                and lines[k + 1] == "-")

    def take(start):
        """Consume one wrapped block beginning at start."""
        buf, k = [], start
        while k < len(lines):
            l = lines[k]
            if l == "-" or l in LABELS:
                break
            buf.append(l)
            k += 1
            # a bullet that happens to fill the full line width would
            # otherwise swallow the group title that follows it
            if is_group_title(k):
                break
            # A numbered step title is complete on its own line.
            if STEP.match(l):
                break
            # Wrapped lines vary in length by more than a tenth, so a short
            # line is not on its own proof that a block ended. A block ends
            # only where a sentence also ends, which is why a line that
            # breaks mid sentence always continues.
            if len(l) < cut and l[-1] in ".?!\u201d)":
                break
        return " ".join(buf), k

    while i < len(lines):
        l = lines[i]
        if l == "-":
            text, i = take(i + 1)
            out.append(("bullet", text))
        elif l in LABELS:
            text, i = take(i + 1)
            out.append((l.lower(), text))
        else:
            text, i = take(i)
            out.append(("para", text))
    return out


def parse_section(key, body):
    """One section: a lede, then any number of typed blocks."""
    sec = {"key": key, "lede": "", "body": [], "blocks": []}
    seq = walk(body)
    first = True
    pending = None  # bullets accumulate until something closes them

    def flush():
        nonlocal pending
        if pending:
            sec["blocks"].append(pending)
            pending = None

    for n, (kind, text) in enumerate(seq):
        if kind == "bullet":
            if not pending:
                pending = {"kind": "bullets", "items": [], "close": ""}
            pending["items"].append(text)
            continue

        if kind in ("ask", "note"):
            flush()
            sec["blocks"].append({"kind": kind, "text": text})
            continue

        # a paragraph
        if first:
            sec["lede"] = text
            first = False
            continue

        nxt = seq[n + 1][0] if n + 1 < len(seq) else None
        m = STEP.match(text)

        if m:
            flush()
            sec["blocks"].append({
                "kind": "step", "number": m.group(1), "title": m.group(2),
                "question": "", "body": [],
            })
        elif nxt == "bullet" and len(text) < 70:
            flush()
            sec["blocks"].append({"kind": "group", "title": text})
        elif pending:
            # prose directly after bullets closes them
            pending["close"] = text
            flush()
        elif sec["blocks"] and sec["blocks"][-1]["kind"] == "step":
            step = sec["blocks"][-1]
            if not step["question"]:
                step["question"] = text
            else:
                step["body"].append(text)
        elif sec["blocks"]:
            sec["blocks"].append({"kind": "text", "body": [text]})
        else:
            sec["body"].append(text)

    flush()
    return sec


def parse(raw):
    all_lines = clean(raw)
    cut = next((i for i, l in enumerate(all_lines) if l == "WHO THIS IS FOR"),
               len(all_lines))
    cover, lines = all_lines[:cut], all_lines[cut:]

    marks = [(i, l) for i, l in enumerate(lines) if is_head(l)]
    g = {}

    # ---- cover ----
    g["eyebrow"] = cover[0] if cover else ""
    g["acronym"] = cover[1] if len(cover) > 1 else ""
    g["tagline"] = cover[2] if len(cover) > 2 else ""
    g["title"] = cover[3] if len(cover) > 3 else ""
    g["deck"] = " ".join(joiner(cover[4:])) if len(cover) > 4 else ""
    g["components_line"] = ""

    blocks = {}
    for n, (i, name) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else len(lines)
        blocks.setdefault(name, []).extend(lines[i + 1 : end])

    g["who"] = " ".join(joiner(blocks.pop("WHO THIS IS FOR", [])))
    online = blocks.pop("READ THIS GUIDE ONLINE", [])
    g["canonical"] = next((l for l in online if l.startswith("http")), "")
    g["colophon"] = " ".join(joiner([l for l in online if not l.startswith("http")]))

    intro = blocks.pop("INTRODUCTION", [])
    g["intro_title"] = intro[0] if intro else ""
    g["intro"] = joiner(intro[1:], prose=True)

    # ---- decision ----
    pit = blocks.pop(DECISION_KEY, [])
    pre, parts = split_at(pit, ("Override", "Quick check"))
    opts, head = [], []
    for l in joiner(pre):
        m = OPT.match(l)
        if m:
            opts.append({"label": m.group(1).strip(), "lede": m.group(2).strip(), "body": []})
        elif opts:
            opts[-1]["body"].append(l)
        else:
            head.append(l)
    g["decision"] = {
        "title": head[0] if head else "",
        "lede": head[1:],
        "options": opts,
        "override": " ".join(joiner(parts.get("Override", []))),
        "quick_check": " ".join(joiner(parts.get("Quick check", []))),
    }

    # ---- next and sources ----
    nxt, cur = [], None
    for l in joiner(blocks.pop("WHERE THIS LEADS NEXT", [])):
        if l.startswith("http"):
            if cur:
                cur["url"] = l
        elif ":" in l and l.split(":")[0] in ("Primary", "Related", "Explore", "Revisit"):
            if cur:
                nxt.append(cur)
            kind, rest = l.split(":", 1)
            cur = {"kind": kind.strip(), "label": rest.strip(), "desc": "", "url": ""}
        elif cur:
            cur["desc"] = (cur["desc"] + " " + l).strip()
    if cur:
        nxt.append(cur)
    g["next"] = nxt

    src, cur = [], None
    for l in joiner(blocks.pop("SOURCES AND FURTHER READING", [])):
        if l.startswith("http"):
            if cur:
                src.append({"label": cur, "url": l})
                cur = None
        elif l.startswith("Canonical guide") or l.startswith("World Open Water"):
            continue
        else:
            cur = l
    g["sources"] = src

    # ---- everything else, in document order ----
    seen, order = set(), []
    for _, name in marks:
        if name in blocks and name not in seen:
            seen.add(name)
            order.append(name)
    g["sections"] = [parse_section(k, blocks[k]) for k in order
                     if k not in (g["eyebrow"], g["acronym"])]
    return g


if __name__ == "__main__":
    raw = open(sys.argv[1]).read()
    g = parse(raw)
    slug = os.path.basename(sys.argv[1]).replace(".txt", "")
    g["slug"] = slug
    g["filename"] = slug + ".pdf"
    os.makedirs(os.path.dirname(sys.argv[2]), exist_ok=True)
    with open(sys.argv[2], "w") as fh:
        json.dump(g, fh, indent=2, ensure_ascii=False)
    kinds = {}
    for s in g["sections"]:
        for b in s["blocks"]:
            kinds[b["kind"]] = kinds.get(b["kind"], 0) + 1
    print(f"{slug}: {len(g['sections'])} sections, "
          f"{len(g['decision']['options'])} options, blocks={kinds}")

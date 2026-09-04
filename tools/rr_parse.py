#!/usr/bin/env python3
"""
Parse an extracted Reading Risk guide into the structured JSON the builder uses.

    python3 rr_parse.py <name>.txt content/rr/<name>.json

The source PDFs wrap lines at the layout width, so a line noticeably shorter
than the widest line ends its paragraph. Everything else is driven by the
headings the guides share.
"""

import json, os, re, sys

SUBS = ("Ask", "What to look for", "If something changes")
BIG = ("INTRODUCTION", "THE FIVE COMPONENTS", "THE FOUR COMPONENTS",
       "PUTTING IT TOGETHER", "COMPOUND RISK", "WHERE THIS LEADS NEXT",
       "SOURCES AND FURTHER READING", "WHO THIS IS FOR", "READ THIS GUIDE ONLINE",
       "READING RISK | FOR SWIMMERS")
COMP = re.compile(r"^([A-Z]) ([A-Z][A-Z' ]+)$")
# a label may contain a hyphen of its own, as in FULL RE-EVALUATION,
# so the separator is a spaced hyphen rather than any hyphen
OPT = re.compile(r"^([A-Z][A-Z\-' ]{1,28}) - (.+)$")
HEAD = re.compile(r"^[A-Z][A-Z |']{3,44}$")


def is_head(l):
    """A standalone all-caps line starts a new block."""
    return bool(HEAD.match(l)) and not OPT.match(l)


def is_hard(l):
    """Lines that must never be merged into a neighbour."""
    return l.startswith("http") or bool(OPT.match(l)) or is_head(l)


def clean(raw):
    lines = []
    for l in raw.split("\n"):
        s = l.rstrip()
        if not s.strip():
            continue
        if s.strip().startswith("WOWSA Learn  |"):
            continue
        if s.strip().isdigit():
            continue
        lines.append(s.strip())
    return lines


SENTENCE_END = ".?!\u201d)"


def joiner(lines, prose=False):
    """Join wrapped lines. A line shorter than the wrap width ends a block.

    Hard lines (URLs, decision labels, headings) are never merged into a
    neighbour, because a paragraph whose last line happens to run the full
    width would otherwise swallow the line that follows it.

    With prose=True a block may only end where a sentence ends. Wrapped lines
    vary in length by more than a tenth, so width alone will sometimes read a
    full line as the end of a paragraph and split it mid sentence. Headings,
    link labels and source titles legitimately end without punctuation, so
    this rule is opt in rather than applied everywhere.
    """
    width = max((len(l) for l in lines), default=0)
    cut = width * 0.90
    out, buf = [], ""
    for l in lines:
        if is_hard(l):
            if buf:
                out.append(buf)
                buf = ""
            out.append(l)
            continue
        buf = (buf + " " + l).strip() if buf else l
        if len(l) < cut and (not prose or l[-1] in SENTENCE_END):
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out


def bullets(lines):
    """Turn the '-' marker style into a list of joined strings.

    Returns (items, note). Text following the last bullet is a closing note,
    not part of that bullet, so the final group is joined and split.
    """
    groups, cur = [], None
    for l in lines:
        if l == "-":
            if cur is not None:
                groups.append(cur)
            cur = []
        elif cur is not None:
            cur.append(l)
    if cur is not None:
        groups.append(cur)
    if not groups:
        return [], ""
    items = [" ".join(joiner(g)) for g in groups[:-1]]
    last = joiner(groups[-1])
    items.append(last[0] if last else "")
    return items, " ".join(last[1:])


def split_at(lines, markers):
    """Split a run of lines into (before, {marker: lines})."""
    idx = [(i, l) for i, l in enumerate(lines) if l in markers]
    if not idx:
        return lines, {}
    before = lines[: idx[0][0]]
    parts = {}
    for n, (i, name) in enumerate(idx):
        end = idx[n + 1][0] if n + 1 < len(idx) else len(lines)
        parts[name] = lines[i + 1 : end]
    return before, parts


def parse(raw):
    all_lines = clean(raw)

    # the cover runs to the first real heading and is positional, not keyed
    cut = next((i for i, l in enumerate(all_lines) if l == "WHO THIS IS FOR"),
               len(all_lines))
    cover_lines, lines = all_lines[:cut], all_lines[cut:]

    # locate every heading that starts a top level block
    marks = []
    for i, l in enumerate(lines):
        if l in BIG or COMP.match(l) or is_head(l):
            marks.append((i, l))

    blocks = {}
    comps = []
    for n, (i, name) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else len(lines)
        body = lines[i + 1 : end]
        if COMP.match(name):
            comps.append((name, body))
        else:
            blocks.setdefault(name, []).extend(body)

    g = {}

    # ---- cover ----
    c = cover_lines
    g["eyebrow"] = c[0] if c else ""
    g["acronym"] = c[1] if len(c) > 1 else ""
    g["tagline"] = c[2] if len(c) > 2 else ""
    g["title"] = c[3] if len(c) > 3 else ""
    # the components line is the one built from mid dot separators; the deck
    # is whatever precedes it, which can run to the full wrap width
    tail = c[4:] if len(c) > 4 else []
    ci = next((i for i, l in enumerate(tail) if "\u00b7" in l), None)
    if ci is None:
        rest = joiner(tail)
        g["deck"] = rest[0] if rest else ""
        g["components_line"] = ""
    else:
        g["deck"] = " ".join(joiner(tail[:ci]))
        g["components_line"] = tail[ci].strip()
    g["who"] = " ".join(joiner(blocks.get("WHO THIS IS FOR", [])))
    online = blocks.get("READ THIS GUIDE ONLINE", [])
    g["canonical"] = next((l for l in online if l.startswith("http")), "")
    g["colophon"] = " ".join(joiner([l for l in online if not l.startswith("http")]))

    # ---- introduction ----
    intro = blocks.get("INTRODUCTION", [])
    g["intro_title"] = intro[0] if intro else ""
    g["intro"] = joiner(intro[1:], prose=True)

    # ---- components ----
    lead = blocks.get("THE FIVE COMPONENTS", blocks.get("THE FOUR COMPONENTS", []))
    g["components_sub"] = " ".join(joiner(lead)) if lead else ""
    g["components"] = []
    for name, body in comps:
        m = COMP.match(name)
        pre, parts = split_at(body, SUBS)
        pre = joiner(pre, prose=True)
        look, _ = bullets(parts.get("What to look for", []))
        changes, note = bullets(parts.get("If something changes", []))
        g["components"].append({
            "letter": m.group(1),
            "name": m.group(2).title(),
            "tagline": pre[0] if pre else "",
            "body": pre[1:],
            "ask": " ".join(joiner(parts.get("Ask", []))),
            "look_for": look,
            "if_changes": changes,
            "note": note,
        })

    # ---- putting it together ----
    pit = blocks.get("PUTTING IT TOGETHER", [])
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

    # ---- optional extra section (CHANGE SOMETHING, SIGNALS) ----
    known = set(BIG) | {g["acronym"]}
    extra = [k for k in blocks if k not in known and blocks[k]]
    g["extra"] = None
    if extra:
        k = extra[0]
        body = blocks[k]
        cut = next((i for i, l in enumerate(body) if l == "-"), len(body))
        items, _ = bullets(body[cut:])
        g["extra"] = {
            "title": k.title(),
            "lede": joiner(body[:cut]),
            "items": items,
        }

    # ---- compound risk ----
    cr = blocks.get("COMPOUND RISK", [])
    cut = next((i for i, l in enumerate(cr) if l == "-"), len(cr))
    items, close = bullets(cr[cut:])
    g["compound"] = {
        "lede": joiner(cr[:cut]),
        "items": items,
        "close": close,
    }

    # ---- where this leads next ----
    nxt = []
    cur = None
    for l in joiner(blocks.get("WHERE THIS LEADS NEXT", [])):
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

    # ---- sources ----
    src, cur = [], None
    for l in joiner(blocks.get("SOURCES AND FURTHER READING", [])):
        if l.startswith("http"):
            if cur:
                src.append({"label": cur, "url": l})
                cur = None
        elif l.startswith("Canonical guide") or l.startswith("World Open Water"):
            continue
        else:
            cur = l
    g["sources"] = src
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
    print(f"{slug}: {len(g['components'])} components, "
          f"{len(g['decision']['options'])} decision options, "
          f"{'extra' if g['extra'] else 'no extra'}, "
          f"{len(g['next'])} next, {len(g['sources'])} sources")

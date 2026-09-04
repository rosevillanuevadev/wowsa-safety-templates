#!/usr/bin/env python3
"""
Check that parsing lost nothing.

    python3 verify_coverage.py <source>.txt <parsed>.json

Every word in the source PDF text, less the running headers and page numbers,
must appear in the parsed structure the same number of times. This catches a
dropped bullet, a swallowed heading or a truncated paragraph, which a page
count or a visual skim will not.
"""

import json, re, sys
from collections import Counter

from rr_parse import clean, is_head

# Text the template supplies rather than stores: section headings, the fixed
# field labels, and the closing colophon lines. Excluded so that a real loss,
# a dropped bullet or a truncated paragraph, is not hidden among them.
TEMPLATE_LABELS = {
    "Ask", "Note", "What to look for", "If something changes",
    "Override", "Quick check",
}
TEMPLATE_PREFIXES = ("Canonical guide:", "World Open Water Swimming Association, WOWSA Learn.")


def words(s):
    return re.findall(r"[A-Za-z0-9']+", s.lower())


def harvest(node, out):
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, list):
        for v in node:
            harvest(v, out)
    elif isinstance(node, dict):
        for k, v in node.items():
            if k in ("slug", "filename"):
                continue
            harvest(v, out)


def main():
    src = open(sys.argv[1]).read()
    parsed = json.load(open(sys.argv[2]))

    kept = [l for l in clean(src)
            if not is_head(l)
            and l not in TEMPLATE_LABELS
            and not l.startswith(TEMPLATE_PREFIXES)]
    source_words = Counter(words(" ".join(kept)))
    chunks = []
    harvest(parsed, chunks)
    parsed_words = Counter(words(" ".join(chunks)))

    missing = source_words - parsed_words
    # urls appear once in the structure but twice in the source colophon
    missing = Counter({w: c for w, c in missing.items() if not w.startswith("http")})

    name = sys.argv[2].split("/")[-1]
    if not missing:
        print(f"  {name:<38} complete, {sum(source_words.values())} words all present")
        return 0
    total = sum(missing.values())
    print(f"  {name:<38} MISSING {total} words: "
          f"{', '.join(f'{w}x{c}' for w, c in missing.most_common(12))}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

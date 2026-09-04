# Rebuilding a Learn document, from fix to verification

How a downloadable WOWSA Learn document is rebuilt onto the approved design,
published, approved, deployed and verified. Written so the work can be repeated
by someone who was not there the first time.

Everything below has been used in production. The gotchas section is the part
worth reading first, because most of it was learned by getting it wrong.

---

## 1. What the approved design is

The standard is `WOWSA-CHECK-Framework-for-Coaches-Approved-2-Page.pdf`. Every
value below was sampled from it, not invented.

| Token | Value | Used for |
| --- | --- | --- |
| cream | `#F6F2E6` | page background |
| cream-soft | `#FBF8EF` | callouts, table cells |
| navy | `#14263B` | headings, rules |
| body | `#2B3441` | body text |
| orange | `#FF4F00` | accents, badges, kickers |
| muted | `#6E7681` | captions, secondary text |
| rule | `#E0DACA` | hairlines, borders |

Typefaces: Oswald for display, Barlow Semi Condensed for labels and kickers,
Source Sans 3 for body. All three must be embedded in the PDF.

A file is on-brand only if it uses these values and embeds these fonts. Nothing
else counts as evidence, and a file that merely looks similar is not on-brand.

---

## 2. Diagnose before rebuilding

Do not take anyone's word that a file is off-brand, including your own from an
earlier session. Open it and compare.

```
python3 - <<'EOF'
import fitz
d = fitz.open("suspect.pdf")
fonts = sorted({f[3].split('+')[-1] for i in range(len(d))
                for f in d[i].get_fonts(full=True) if f[3]})
cols = set()
for pg in d:
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if s["text"].strip():
                    cols.add("#%06X" % s["color"])
print("fonts :", ", ".join(fonts))
print("colors:", ", ".join(sorted(cols)))
EOF
```

Helvetica and Times with nothing embedded is the signature of a file where no
fonts were specified at all. That plus a white background and a gold accent is
what the pre-rebuild Reading Risk guides looked like.

---

## 3. Extract the existing content

Content is carried over, never rewritten. Pull the text out of the live file:

```
python3 - <<'EOF'
import fitz
d = fitz.open("live.pdf")
open("live.txt", "w").write("\n".join(pg.get_text() for pg in d))
EOF
```

Fetching from the site requires the routing cookie, or you will be served a
different application's assets and may see a 404 that does not exist for real
visitors:

```
curl -b "learn_owner=learn" -L \
  https://www.openwaterswimming.com/learn-assets/<slug>.pdf -o live.pdf
```

---

## 4. Parse into structured content

Two parsers, because there are two document shapes.

`rr_parse.py` handles the lettered frameworks (CHECK, ABLE, FLOW, CARE). Each
has a cover, an introduction, four or five lettered components with an Ask, a
"what to look for" list and an "if something changes" list, a decision section,
a compound risk section, onward links and sources.

`cr_parse.py` handles Compound Risk, which has no lettered components. Its
sections are built from a lede, named groups with bullets, numbered steps, and
labeled Ask and Note blocks.

```
python3 tools/rr_parse.py live.txt tools/content/rr/<slug>.json
python3 tools/cr_parse.py live.txt tools/content/cr/<slug>.json
```

Both write JSON. Read it before rendering. Wrong parsing is far cheaper to spot
in the JSON than in a PDF.

---

## 5. Verify nothing was lost

This is the step that makes carrying content over trustworthy.

```
python3 tools/verify_coverage.py live.txt tools/content/rr/<slug>.json
```

Every word in the source, less the headings and fixed labels the template
supplies, must appear in the parsed structure the same number of times. A
dropped bullet, a swallowed heading or a truncated paragraph fails here. A page
count or a visual skim will not catch any of those.

Expected output:

```
  <slug>.json      complete, 1468 words all present
```

Coverage alone does not catch a paragraph split in the wrong place, because the
words are all still there. Check for that separately: any stored paragraph that
begins with a lowercase letter is a paragraph that was broken mid sentence.

---

## 6. Render

```
python3 tools/build_rr.py tools/content/rr/<slug>.json output/rr
python3 tools/build_cr.py tools/content/cr/<slug>.json
```

Both print the sheet count and how full the fullest sheet is. If a single block
is taller than one sheet the build stops rather than clipping it.

Fillable operational forms use `build_form.py` instead, which renders link
annotations and then converts them into real AcroForm widgets, so the file
keeps the approved look and stays fillable.

---

## 7. Verify the output

```
python3 - <<'EOF'
import fitz, glob
STD = {"#F6F2E6","#FBF8EF","#14263B","#2B3441","#FF4F00","#6E7681","#E0DACA","#FFFFFF"}
for p in sorted(glob.glob("output/**/*.pdf", recursive=True)):
    d = fitz.open(p)
    faces = {(f[3], f[4]) for i in range(len(d)) for f in d[i].get_fonts(full=True)}
    cols, clipped, links = set(), 0, 0
    for pg in d:
        links += len([l for l in pg.get_links() if l.get("uri")])
        for b in pg.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    if s["text"].strip():
                        cols.add("#%06X" % s["color"])
                        if s["bbox"][3] > pg.rect.height - 20:
                            clipped += 1
    print(p, len(d), "pages", len(faces), "faces", links, "links",
          "clipped", clipped, "offpalette", sorted(cols - STD) or "none")
EOF
```

All four must hold before a file goes anywhere:

- every text color is in the approved palette
- all font faces embedded, seven for a guide
- no clipped text on any page
- links preserved

White `#FFFFFF` is expected: it is the badge text sitting on orange.

Then look at the pages. Render each to PNG and actually open them. The checks
above cannot see an ugly page.

---

## 8. Human review

Nothing is published before a person has looked at it. Put the rebuilt files,
the current live versions and page images into one folder so the comparison is
easy, and wait.

This is not a formality. The approval recorded in step 10 names a human as
having certified the design. If nobody looked, that record is false.

---

## 9. Publish to this repository

This repository is the source of truth. A revision is a commit, not a manual
re-upload.

Keep the filename identical to what is already live, so existing URLs keep
working. Record the checksums, they are needed in the next step:

```
shasum -a 256 <slug>.pdf
git add <slug>.pdf && git commit && git push
```

Confirm the raw URL serves the file and the checksum still matches after upload:

```
curl -L https://raw.githubusercontent.com/rose2023va/wowsa-safety-templates/main/<slug>.pdf -o check.pdf
shasum -a 256 check.pdf
```

---

## 10. Approve in Learn

A resource page does not link to a file. It asks a release gate whether the
document may be delivered, and the gate answers from a registry. Publishing a
file is not enough on its own.

The order matters:

1. Fetch each file and verify its checksum. Stop the whole job on any mismatch
   rather than applying half of it.
2. Replace the file in `public/learn-assets/`.
3. Write the file facts, including the new size and checksum.
4. Write the brand check, bound to the new checksum.
5. Write the approval and the release state.
6. Regenerate both committed JSON mirrors from the view.

Rules that are not negotiable:

- The approver is a real account, looked up rather than assumed. Never a name in
  a uuid column, never a substitute account.
- QA evidence records the checks that were actually performed. Not boilerplate.
- Changing a file resets its approval by design. The file must be final first.
- Release state must be `ready_to_publish` or `published`, approval status
  `approved`, lifecycle status `published`, and `brand_certified` true.

Anything intentionally held stays in `src/data/held-documents.ts` with an honest
reason. A resource that fails to resolve and is not named there fails the build.

---

## 11. Deploy

Before deploying, record what already works, so a regression is provable rather
than a matter of opinion:

```
for n in <every currently working slug>; do
  curl -s -b "learn_owner=learn" -o /tmp/b.pdf -L \
    "https://www.openwaterswimming.com/learn-assets/$n.pdf"
  echo "$(shasum -a 256 /tmp/b.pdf | cut -c1-12) $n"
done > baseline.txt
```

Then deploy.

---

## 12. Verify live

Re-run the same command and compare to `baseline.txt`.

- Every new file must serve its expected checksum.
- Every previously working file must be byte for byte unchanged.

Then open the resource page and use the download button. A reachable file and a
working button are two different things, and only the second one matters to a
visitor.

---

## 13. If it goes wrong

The build assertion turns a broken registry into a failed build that names the
offending slugs, so the common failure is a deploy that does not happen rather
than a silent outage.

If a deploy did land and the baseline shows a regression, revert rather than
debug forward. Reverts go through the History interface.

---

## Gotchas

Every one of these cost real time.

**Variable fonts do not embed.** Google Fonts serves variable fonts, and Chrome
does not embed them into PDF output. The text silently renders as unnamed
outlines. Static instances must be generated and embedded as base64. That is
what `fonts.css` is, and it is large for that reason.

**The routing cookie decides which application answers.** Asset paths are routed
by a `learn_owner` cookie, which defaults to another application when absent. A
request without it can return 404 for a file that works perfectly in a browser.
An entire launch blocker was once reported on the strength of that mistake.

**Cream cannot bleed and have per page margins in a flowing layout.** Chrome
does not paint a page background into the `@page` margins, and a fixed backdrop
is clipped to the content box. Fixed sheets of 8.5 by 11 inches with their own
padding give both, at the cost of paginating deliberately.

**Measure blocks inside the same formatting context you place them in.** A
wrapper with no border or padding lets a child's top margin collapse out of the
measured box, so heights come back short and sheets overflow. Both passes use
`display: flow-root`.

**Wrapped line width is not a reliable block boundary on its own.** Wrapped
lines vary in length by more than a tenth, so a full line gets misread as the
end of a paragraph and the paragraph is split mid sentence. A paragraph may only
end where a sentence ends. A group title is instead recognized by being short,
unpunctuated and sitting directly on top of a bullet.

**A label can contain a hyphen.** `FULL RE-EVALUATION` is a decision label. The
separator is a spaced hyphen, not any hyphen.

**A held document and a broken one look identical.** Both render the same polite
unavailable panel, to a visitor and to us. That is why the held list and the
build assertion exist. Never let a document fail quietly.

---

## What is in `tools/`

| File | Purpose |
| --- | --- |
| `rr_parse.py` | parse a lettered framework guide into JSON |
| `cr_parse.py` | parse a Compound Risk guide into JSON |
| `verify_coverage.py` | prove no content was lost in parsing |
| `guide_common.py` | cover, height measurement, sheet packing, printing |
| `build_rr.py` | render a lettered framework guide |
| `build_cr.py` | render a Compound Risk guide |
| `build_form.py` | render a fillable operational form |
| `rr.css`, `form.css` | the approved design |
| `fonts.css` | static font instances, embedded as base64 |
| `assets/wowsa-seal.png` | the seal, with transparency preserved |
| `content/` | the parsed content for each document |

Requires Python with PyMuPDF, and Google Chrome for rendering.

Fonts are Oswald, Barlow Semi Condensed and Source Sans 3, all under the SIL
Open Font License.

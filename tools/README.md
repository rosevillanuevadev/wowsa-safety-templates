# Guide build tools

The toolchain that produces WOWSA Learn documents on the approved design.

Full process, from diagnosing an off-brand file through to verifying the live
download, is in [`../docs/REBUILDING-GUIDES.md`](../docs/REBUILDING-GUIDES.md).
Read the gotchas section before changing anything here.

## Quick reference

```
# 1. extract the text from the current live file
python3 -c "import fitz;d=fitz.open('live.pdf');open('live.txt','w').write('\n'.join(p.get_text() for p in d))"

# 2. parse to structured content
python3 rr_parse.py live.txt content/rr/<slug>.json     # CHECK, ABLE, FLOW, CARE
python3 cr_parse.py live.txt content/cr/<slug>.json     # Compound Risk

# 3. prove nothing was lost
python3 verify_coverage.py live.txt content/rr/<slug>.json

# 4. render
python3 build_rr.py content/rr/<slug>.json output/rr
python3 build_cr.py content/cr/<slug>.json
```

Requires Python with PyMuPDF, and Google Chrome.

## Why content is parsed rather than retyped

Every guide keeps its existing words. Parsing and re-rendering means the rebuild
changes the design and nothing else, and `verify_coverage.py` proves it: every
word of the source must survive into the output, counted.

Retyping cannot make that promise.

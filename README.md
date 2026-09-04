# WOWSA Safety Templates

Canonical production PDFs for the WOWSA operational template set, built on the approved
WOWSA design system. Every form here keeps working AcroForm fields.

These files are the source that the public resource pages and the Customer.io delivery
emails point at. Replace a file in place for a revision rather than publishing a second
copy under a new name.

## Files

| File | Pages | Fields |
|---|---|---|
| wowsa-safe-coach-risk-assessment.pdf | 2 | 114 |
| wowsa-safe-coach-normal-operating-plan.pdf | 3 | 53 |
| wowsa-safe-coach-emergency-action-plan.pdf | 2 | 29 |
| wowsa-safe-coach-incident-near-miss-report.pdf | 2 | 47 |
| wowsa-safe-organizer-risk-assessment.pdf | 2 | 114 |
| wowsa-safe-organizer-normal-operating-plan.pdf | 3 | 53 |
| wowsa-safe-organizer-emergency-action-plan.pdf | 2 | 29 |
| wowsa-safe-organizer-incident-near-miss-report.pdf | 2 | 47 |
| wowsa-check-framework-for-coaches.pdf | 2 | read-only guide |

## Design

Cream `#F6F2E6`, navy `#14263B`, orange `#FF4F00`, body copy `#2B3441`, labels `#6E7681`.
Oswald for headings, Barlow Semi Condensed for labels, Source Sans 3 for body. Fonts are
embedded, so nothing depends on a network fetch at render time.

House style: no em dashes or en dashes anywhere.

## Rebuilding

The generator lives outside this repo. This repository holds the built artifacts only, so
the URLs stay stable.

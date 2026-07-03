# StaySD — Phase 0 scoring engine

The engine behind the ZIP comparison cards. Takes a household profile
(income, filing status, household size, bedrooms, job center) and returns
per-ZIP cost breakdowns, cash leftover, time-adjusted RDI, and a 0–100 score.

## Run it

```bash
python3 engine.py        # three-ZIP demo comparison
python3 taxes.py         # tax calc sanity check
```

## Files

- `engine.py` — Profile in, ranked ZipResults out. `compare()` is the API
  a FastAPI endpoint or React frontend will call.
- `taxes.py` — gross annual -> net monthly (federal + CA + FICA + SDI).
- `zip_data.json` — the hand-curated Phase 0 data layer. **This file is
  the product right now.** Everything marked `_verify` or PLACEHOLDER
  needs a human check before anything goes public.

## Verification checklist (do before posting anywhere)

**9 ZIPs pending verification**: 92057 (Oceanside), 92084 (Vista),
92078 (San Marcos), 92126 (Mira Mesa), 92117 (Clairemont), 92104
(North Park), 92020 (El Cajon), 91913 (Chula Vista/Eastlake), 92024
(Encinitas) — added with placeholder rent/commute/utilities figures
and `_verify: true`. Run the full checklist below for each before
flipping `_verify` to `false`.

1. **Taxes**: run `taxes.py` outputs against SmartAsset or ADP paycheck
   calculator for $95K and $141K single/CA. Target: within ~2%.
2. **Rent**: replace placeholders with Zillow ZORI (free CSV) for each ZIP,
   cross-checked against RentCast free tier. Record source + date in
   `rent_source`.
3. **Commute**: Google Maps, Tuesday 8:00 AM depart, each ZIP centroid ->
   each job center. Record peak minutes and miles.
4. **Childcare**: CDSS Regional Market Rate survey, San Diego County,
   licensed center full-time infant/toddler.
5. **SDG&E**: residential rate calculator for a 2–3BR household; note
   whether the ZIP is in a CCA (Clean Energy Alliance vs SDCP) territory.
6. **Vehicle $/mile**: confirm current IRS standard mileage rate.
7. Flip `_verify` to `false` per ZIP only when all of the above are logged.

## Tuning knobs (in `zip_data.json` -> cost_constants)

- `time_value_factor` (default 0.5): fraction of hourly wage a commute
  hour costs. DOT convention is ~50% for personal travel.
- RDI score ceiling: in `engine.py`, score = 100 when time-adjusted RDI
  hits 60% of net income. Tune once real comparisons exist.

## Next (sprint days 3–5)

- Wrap `compare()` in FastAPI (`/compare?zips=...` returning JSON).
- Point the React mock's sliders at it.
- Share-card image generation (server-side render of the winning card).

# StaySD — SD County affordability comparison tool
- engine.py: RDI scoring. compare() is the public API. Don't change the
  RDI formula or score mapping without asking.
- zip_data.json: hand-curated data layer. Numbers marked _verify=true are
  placeholders — never present them as real. New ZIPs must follow the
  README verification checklist.
- taxes.py: simplified CA+federal calc. Bracket constants update annually.
- app.py: Streamlit UI. Escape $ as \$ in all st.markdown strings
  (LaTeX rendering bug). Test with: python -m pytest or the
  streamlit.testing.v1 AppTest harness.
- Style: keep it Phase 0 — no databases, no accounts, no new dependencies
  without asking.
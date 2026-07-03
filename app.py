"""
StaySD — Phase 0 web app.

Run locally:   streamlit run app.py
Deploy:        push repo to GitHub -> share.streamlit.io -> point at repo.
"""

import json
from pathlib import Path

import streamlit as st

from engine import Profile, compare

st.set_page_config(page_title="StaySD — What's actually left over?",
                   page_icon="🌊", layout="wide")

DATA = json.loads((Path(__file__).parent / "zip_data.json").read_text())
JOB_CENTERS = {k: v["name"] for k, v in DATA["job_centers"].items()}
ZIPS = list(DATA["zips"].keys())
UNVERIFIED_FLAG = "DATA UNVERIFIED — placeholder numbers"

# ---------------- header ----------------
st.title("StaySD")
st.caption("San Diego County, priced honestly — rent, commute, taxes, "
           "childcare, and the value of your time, by ZIP code.")

# ---------------- inputs ----------------
st.subheader("Your household")
c1, c2, c3, c4 = st.columns(4)
with c1:
    if "gross_monthly_input" not in st.session_state:
        st.session_state["gross_monthly_input"] = 11_750
        st.session_state["gross_monthly_slider"] = 11_750

    def _sync_from_slider():
        st.session_state["gross_monthly_input"] = st.session_state["gross_monthly_slider"]

    def _sync_from_input():
        st.session_state["gross_monthly_slider"] = min(30_000, st.session_state["gross_monthly_input"])

    st.caption("Monthly income (gross)")
    slider_col, input_col = st.columns([2, 1])
    with slider_col:
        st.slider("Monthly income (gross)", 1_000, 30_000, step=250,
                 key="gross_monthly_slider", on_change=_sync_from_slider,
                 label_visibility="collapsed")
    with input_col:
        st.number_input("Monthly income (gross)", min_value=1_000, max_value=50_000, step=50,
                        key="gross_monthly_input", on_change=_sync_from_input,
                        label_visibility="collapsed")
    gross_monthly = st.session_state["gross_monthly_input"]

    filing = st.radio("Filing status", ["single", "married"], horizontal=True)
with c2:
    household = st.number_input("Household size", 1, 10, 3)
    max_kids = max(0, household - 1)
    if "kids_u5" not in st.session_state:
        st.session_state["kids_u5"] = min(1, max_kids)
    elif st.session_state["kids_u5"] > max_kids:
        st.session_state["kids_u5"] = max_kids
        st.caption(f"Kids under 5 capped at {max_kids} for a household of {household}.")
    kids_u5 = st.number_input("Kids under 5 (childcare)", min_value=0, max_value=max_kids,
                              key="kids_u5")
with c3:
    bedrooms = st.select_slider("Bedrooms", ["studio", "1br", "2br", "3br", "4br"], value="2br")
    if bedrooms in ("studio", "4br"):
        st.caption("Estimated tier — less verified than 1–3BR.")
    default_wage = round(gross_monthly * 12 / 2080)
    wage = st.number_input("Hourly wage equiv. (values your time)",
                           min_value=10, max_value=300, value=default_wage,
                           help="Defaults to your salary's implied hourly rate. "
                                "Override if your time is worth more to you.")
with c4:
    job_center = st.selectbox("Where do you work?", options=list(JOB_CENTERS),
                              format_func=lambda k: JOB_CENTERS[k])
    commute_days = st.slider("Commute days / month", 0, 23, 21,
                             help="Hybrid? Set your real in-office days.")

profile = Profile(
    gross_annual_income=gross_monthly * 12,
    filing=filing,
    household_size=household,
    kids_under_5=kids_u5,
    bedrooms=bedrooms,
    job_center=job_center,
    hourly_wage_equiv=wage,
    commute_days_per_month=commute_days,
)

results = compare(profile, ZIPS)
net = results[0].net_monthly

st.markdown(f"**Net monthly after CA + federal taxes: \\${net:,}**  \n"
            f"_(from \\${gross_monthly:,}/mo gross, filing {filing})_")

# ---------------- cards ----------------
st.subheader("Comparing ZIP codes")
unverified_count = sum(1 for z in DATA["zips"].values() if z.get("_verify"))
st.info(f"Beta: {unverified_count} of {len(DATA['zips'])} ZIPs still use placeholder data "
        f"pending verification — treat those comparisons as directional.")

CARDS_PER_ROW = 3
for row_start in range(0, len(results), CARDS_PER_ROW):
    row_results = results[row_start:row_start + CARDS_PER_ROW]
    cols = st.columns(len(row_results))
    for col, r in zip(cols, row_results):
        with col:
            # Fixed-height slot so the badge (shown on one card only) doesn't
            # push that card's title/table down relative to its row-mates.
            with st.container(height=55, border=False):
                if r is results[0]:
                    st.success("Best fit — after valuing your time")

            is_unverified = UNVERIFIED_FLAG in r.flags
            marker = " · :gray[unverified]" if is_unverified else ""
            st.markdown(f"### {r.name}\n`{r.zip_code}` · RDI score **{r.rdi_score}/100**{marker}")
            st.markdown(
                f"| | |\n|---|---:|\n"
                f"| Rent ({bedrooms}) | \\${r.rent:,} |\n"
                f"| Commute (vehicle) | \\${r.commute_cash:,} |\n"
                f"| Time in car | {r.commute_hours} hrs/mo |\n"
                f"| Time cost | \\${r.commute_time_cost:,} |\n"
                f"| SDG&E est. | \\${r.utilities:,} |\n"
                f"| Childcare | \\${r.childcare:,} |\n"
                f"| Groceries + baseline | \\${r.groceries_misc:,} |"
            )
            st.metric("Cash left over", f"${r.cash_leftover:,}")
            st.metric("RDI (time-adjusted)", f"${r.rdi:,}")
            for fl in r.flags:
                if fl != UNVERIFIED_FLAG:
                    st.warning(fl, icon="⚠️")

# ---------------- footnotes ----------------
with st.expander("How the math works"):
    st.markdown(
        "- **Net income**: federal + CA brackets, FICA, CA SDI, standard "
        "deduction. Estimate — not tax advice.\n"
        "- **Commute**: round-trip miles × IRS mileage rate × your in-office "
        "days, plus peak drive time valued at 50% of your hourly wage "
        "(standard DOT travel-time convention).\n"
        "- **RDI**: what's left after everything above, minus the monetized "
        "value of your commute time. The score maps RDI as a share of net "
        "income to 0–100.\n"
        "- Data is hand-curated for Phase 0; ZIPs flagged *unverified* use "
        "placeholder figures pending source checks."
    )
st.caption("StaySD Phase 0 · feedback → post in the thread that sent you here")
"""
StaySD scoring engine.

Takes a household profile + target ZIPs, returns per-ZIP cost breakdowns,
Real Disposable Income (RDI), and a 0-100 RDI score — the numbers behind
the comparison cards.

Design notes:
- Two leftover figures per ZIP:
    cash_leftover : net income minus actual cash outflows (what hits the bank)
    rdi           : cash_leftover minus the monetized value of commute time
  Cards display cash_leftover as "Left over" and rank/score on rdi, so the
  time-adjusted view picks the winner while the cash view stays honest.
- RDI score maps rdi as a share of net income onto 0-100
  (0% of net left => 0, 60%+ of net left => 100). Simple, explainable,
  screenshot-friendly. Tune the ceiling later with real user data.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from taxes import net_monthly_income

DATA_PATH = Path(__file__).parent / "zip_data.json"


@dataclass
class Profile:
    gross_annual_income: float
    filing: str = "single"              # "single" | "married"
    household_size: int = 1
    kids_under_5: int = 0
    bedrooms: str = "2br"               # "studio" | "1br" | "2br" | "3br" | "4br"
    job_center: str = "sorrento_valley" # key in zip_data.json job_centers
    hourly_wage_equiv: float | None = None  # default: derived from salary
    commute_days_per_month: int | None = None

    def wage(self) -> float:
        if self.hourly_wage_equiv:
            return self.hourly_wage_equiv
        return self.gross_annual_income / 2080  # standard work-year hours


@dataclass
class ZipResult:
    zip_code: str
    name: str
    rent: float
    commute_cash: float          # vehicle cost, $/mo
    commute_hours: float         # hrs/mo in the car
    commute_time_cost: float     # monetized time, $/mo
    utilities: float
    childcare: float
    groceries_misc: float
    net_monthly: float
    cash_leftover: float
    rdi: float
    rdi_score: int
    flags: list[str] = field(default_factory=list)


def _load_data() -> dict:
    with open(DATA_PATH) as f:
        return json.load(f)


def score_zip(profile: Profile, zip_code: str, data: dict | None = None) -> ZipResult:
    data = data or _load_data()
    z = data["zips"][zip_code]
    c = data["cost_constants"]

    tax = net_monthly_income(profile.gross_annual_income, profile.filing)
    net = tax["net_monthly"]

    rent = z["rent_monthly"][profile.bedrooms]

    workdays = profile.commute_days_per_month or c["workdays_per_month"]
    cm = z["commute"][profile.job_center]
    miles_month = cm["miles_oneway"] * 2 * workdays
    commute_cash = miles_month * c["vehicle_cost_per_mile"]
    commute_hours = cm["minutes_oneway_peak"] * 2 * workdays / 60
    commute_time_cost = commute_hours * profile.wage() * c["time_value_factor"]

    utilities = z["sdge_monthly_est"]
    childcare = profile.kids_under_5 * c["childcare_monthly_per_child_under5"]
    groceries = (c["groceries_base_single"]
                 + c["groceries_per_additional_person"] * (profile.household_size - 1))
    groceries_misc = groceries + c["misc_baseline_monthly"]

    cash_out = rent + commute_cash + utilities + childcare + groceries_misc
    cash_leftover = net - cash_out
    rdi = cash_leftover - commute_time_cost

    # 0-100 score: rdi as share of net, 0% -> 0, 60% -> 100
    score = max(0, min(100, round((rdi / net) / 0.60 * 100))) if net > 0 else 0

    flags = []
    if z.get("mello_roos"):
        flags.append("Mello-Roos district — extra tax if buying")
    if rent / net > 0.40:
        flags.append("Rent exceeds 40% of net income")
    if commute_hours > 40:
        flags.append(f"Commute burden: {commute_hours:.0f} hrs/mo in the car")
    if z.get("_verify"):
        flags.append("DATA UNVERIFIED — placeholder numbers")

    return ZipResult(
        zip_code=zip_code, name=z["name"], rent=rent,
        commute_cash=round(commute_cash), commute_hours=round(commute_hours, 1),
        commute_time_cost=round(commute_time_cost), utilities=utilities,
        childcare=childcare, groceries_misc=groceries_misc,
        net_monthly=round(net), cash_leftover=round(cash_leftover),
        rdi=round(rdi), rdi_score=score, flags=flags,
    )


def compare(profile: Profile, zip_codes: list[str]) -> list[ZipResult]:
    """Score multiple ZIPs, best RDI first."""
    data = _load_data()
    results = [score_zip(profile, zc, data) for zc in zip_codes]
    return sorted(results, key=lambda r: r.rdi, reverse=True)


def print_cards(profile: Profile, results: list[ZipResult]) -> None:
    jc = _load_data()["job_centers"][profile.job_center]["name"]
    print(f"\nHousehold: ${profile.gross_annual_income:,.0f} gross | "
          f"{profile.filing} | size {profile.household_size} "
          f"({profile.kids_under_5} under 5) | {profile.bedrooms} | works in {jc}")
    print(f"Net monthly after taxes: ${results[0].net_monthly:,}\n")
    for i, r in enumerate(results):
        badge = "  << BEST FIT (after valuing your time)" if i == 0 else ""
        print(f"--- {r.name} ({r.zip_code}){badge}")
        print(f"    Rent ({profile.bedrooms}):        ${r.rent:>6,}")
        print(f"    Commute (vehicle):    ${r.commute_cash:>6,}   ({r.commute_hours} hrs/mo)")
        print(f"    Commute (time cost):  ${r.commute_time_cost:>6,}")
        print(f"    SDG&E est.:           ${r.utilities:>6,}")
        print(f"    Childcare:            ${r.childcare:>6,}")
        print(f"    Groceries + baseline: ${r.groceries_misc:>6,}")
        print(f"    Cash left over:       ${r.cash_leftover:>6,}")
        print(f"    RDI (time-adjusted):  ${r.rdi:>6,}   -> score {r.rdi_score}/100")
        for fl in r.flags:
            print(f"    [!] {fl}")
        print()


if __name__ == "__main__":
    profile = Profile(
        gross_annual_income=141_000,   # ~$11,750/mo gross, matching the mock
        filing="single",
        household_size=3,
        kids_under_5=1,
        bedrooms="2br",
        job_center="sorrento_valley",
        hourly_wage_equiv=40,
    )
    print_cards(profile, compare(profile, ["92008", "91910", "92025"]))

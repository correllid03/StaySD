"""
StaySD tax module: gross annual income -> net monthly take-home.

Simplified but structurally correct: federal brackets, CA brackets,
FICA, CA SDI, standard deductions. Single or married-joint filing.

VERIFY BEFORE PUBLIC USE:
- Bracket thresholds and standard deductions are 2025 figures; update annually.
- Cross-check output against SmartAsset/ADP paycheck calculator for
  3-4 sample incomes. Target: within ~2% of their net figure.
"""

FED_BRACKETS = {
    "single": [
        (0, 0.10), (11_925, 0.12), (48_475, 0.22), (103_350, 0.24),
        (197_300, 0.32), (250_525, 0.35), (626_350, 0.37),
    ],
    "married": [
        (0, 0.10), (23_850, 0.12), (96_950, 0.22), (206_700, 0.24),
        (394_600, 0.32), (501_050, 0.35), (751_600, 0.37),
    ],
}
FED_STD_DEDUCTION = {"single": 15_000, "married": 30_000}

CA_BRACKETS = {
    "single": [
        (0, 0.01), (10_756, 0.02), (25_499, 0.04), (40_245, 0.06),
        (55_866, 0.08), (70_606, 0.093), (360_659, 0.103),
        (432_787, 0.113), (721_314, 0.123),
    ],
    "married": [
        (0, 0.01), (21_512, 0.02), (50_998, 0.04), (80_490, 0.06),
        (111_732, 0.08), (141_212, 0.093), (721_318, 0.103),
        (865_574, 0.113), (1_442_628, 0.123),
    ],
}
CA_STD_DEDUCTION = {"single": 5_540, "married": 11_080}

FICA_RATE = 0.0765        # SS 6.2% + Medicare 1.45% (SS wage cap ignored at these incomes)
CA_SDI_RATE = 0.012       # VERIFY current year rate; no wage cap since 2024


def _bracket_tax(taxable: float, brackets: list[tuple[float, float]]) -> float:
    """Progressive tax over (threshold, rate) bracket list."""
    if taxable <= 0:
        return 0.0
    tax = 0.0
    for i, (lower, rate) in enumerate(brackets):
        upper = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        if taxable > lower:
            tax += (min(taxable, upper) - lower) * rate
        else:
            break
    return tax


def net_monthly_income(gross_annual: float, filing: str = "single") -> dict:
    """Return net monthly take-home and the tax breakdown behind it."""
    filing = filing if filing in ("single", "married") else "single"

    fed_taxable = max(0.0, gross_annual - FED_STD_DEDUCTION[filing])
    fed_tax = _bracket_tax(fed_taxable, FED_BRACKETS[filing])

    ca_taxable = max(0.0, gross_annual - CA_STD_DEDUCTION[filing])
    ca_tax = _bracket_tax(ca_taxable, CA_BRACKETS[filing])

    fica = gross_annual * FICA_RATE
    sdi = gross_annual * CA_SDI_RATE

    total_tax = fed_tax + ca_tax + fica + sdi
    net_annual = gross_annual - total_tax

    return {
        "gross_annual": round(gross_annual, 2),
        "federal_tax": round(fed_tax, 2),
        "ca_tax": round(ca_tax, 2),
        "fica": round(fica, 2),
        "ca_sdi": round(sdi, 2),
        "total_tax": round(total_tax, 2),
        "effective_rate": round(total_tax / gross_annual, 4) if gross_annual else 0.0,
        "net_annual": round(net_annual, 2),
        "net_monthly": round(net_annual / 12, 2),
    }


if __name__ == "__main__":
    for gross in (95_000, 141_000):
        r = net_monthly_income(gross, "single")
        print(f"${gross:,} gross -> ${r['net_monthly']:,.0f}/mo net "
              f"(effective rate {r['effective_rate']:.1%})")

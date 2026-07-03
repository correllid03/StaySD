"""
Ground truth for net_monthly_income() sanity checks, manually pulled from
SmartAsset's California paycheck calculator (smartasset.com/taxes/california-paycheck-calculator)
on 2026-07-02, single filer, no extra withholdings:

    $95,000  gross -> $2,886 semi-monthly -> $5,772/mo net
    $141,000 gross -> $4,012 semi-monthly -> $8,024/mo net

taxes.py is a simplified model, not a payroll engine, so we only assert
it lands within 2% of SmartAsset's figure rather than matching exactly.
"""

import pytest

from taxes import net_monthly_income

SMARTASSET_NET_MONTHLY = {
    95_000: 5_772,
    141_000: 8_024,
}


@pytest.mark.parametrize("gross_annual, expected_net_monthly", SMARTASSET_NET_MONTHLY.items())
def test_net_monthly_income_within_2_percent_of_smartasset(gross_annual, expected_net_monthly):
    result = net_monthly_income(gross_annual, "single")
    tolerance = expected_net_monthly * 0.02
    assert result["net_monthly"] == pytest.approx(expected_net_monthly, abs=tolerance)


def test_net_monthly_income_breakdown_sums_to_net_annual():
    result = net_monthly_income(95_000, "single")
    reconstructed = result["gross_annual"] - result["total_tax"]
    assert result["net_annual"] == pytest.approx(reconstructed, abs=0.01)
    assert result["net_monthly"] == pytest.approx(result["net_annual"] / 12, abs=0.01)


def test_net_monthly_income_zero_gross_has_no_tax():
    result = net_monthly_income(0, "single")
    assert result["total_tax"] == 0.0
    assert result["net_monthly"] == 0.0
    assert result["effective_rate"] == 0.0


def test_net_monthly_income_defaults_unknown_filing_status_to_single():
    result = net_monthly_income(95_000, "not_a_real_status")
    expected = net_monthly_income(95_000, "single")
    assert result == expected

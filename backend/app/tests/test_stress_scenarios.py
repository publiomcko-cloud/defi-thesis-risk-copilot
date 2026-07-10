from app.risk.checklist import generate_monitoring_checklist
from app.risk.framework import RiskComponent, RiskScore
from app.risk.scenarios import generate_stress_scenarios


def test_stress_scenarios_are_generated() -> None:
    risk_score = RiskScore(
        score=7,
        rating="Very Risky",
        components=[
            RiskComponent("liquidation_risk", 1, "Borrowing creates liquidation risk.")
        ],
        confidence="low",
        main_risk_drivers=["liquidation_risk", "maturity_risk"],
    )

    scenarios = generate_stress_scenarios(risk_score)

    assert any("Collateral price drops 10%" in scenario for scenario in scenarios)
    assert any("Borrow APY doubles" in scenario for scenario in scenarios)
    assert any("Multiple adverse events" in scenario for scenario in scenarios)


def test_monitoring_checklist_is_generated() -> None:
    risk_score = RiskScore(
        score=5,
        rating="Aggressive",
        components=[],
        confidence="medium",
        main_risk_drivers=["maturity_risk", "incentive_risk"],
    )

    checklist = generate_monitoring_checklist(risk_score)

    assert any("borrow apy" in item.lower() for item in checklist)
    assert any("maturity" in item.lower() for item in checklist)
    assert any("incentive" in item.lower() or "reward" in item.lower() for item in checklist)

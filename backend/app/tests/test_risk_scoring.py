from app.risk.scoring import score_strategy_risk


def test_conservative_strategy_scores_low() -> None:
    score = score_strategy_risk(
        strategy_description="Analyze a single protocol stable lending position.",
        protocols=["aave"],
        manual_inputs={
            "liquidity_usd": 2_000_000,
            "oracle_status": "known",
        },
        missing_data=[],
    )

    assert score.rating == "Conservative"
    assert score.score == 1
    assert score.confidence == "high"


def test_moderate_strategy_scores_mid_range() -> None:
    score = score_strategy_risk(
        strategy_description="Analyze a borrow strategy with known liquidity.",
        protocols=["aave"],
        manual_inputs={
            "borrow_apy": 0.04,
            "liquidity_usd": 1_000_000,
            "ltv": 0.25,
        },
        missing_data=[],
    )

    assert score.rating == "Moderate"
    assert score.score == 3


def test_aggressive_strategy_scores_high_range() -> None:
    score = score_strategy_risk(
        strategy_description="Analyze a Pendle PT strategy using Morpho borrow.",
        protocols=["pendle", "morpho"],
        manual_inputs={
            "borrow_apy": 0.07,
            "liquidity_usd": 250_000,
            "ltv": 0.5,
        },
        missing_data=[],
    )

    assert score.rating == "Aggressive"
    assert score.score == 6
    assert "composability_risk" in score.main_risk_drivers


def test_very_risky_strategy_scores_top_range() -> None:
    score = score_strategy_risk(
        strategy_description=(
            "Analyze a leveraged Pendle PT strategy using Morpho borrow, oracle risk, "
            "secondary market exit, and incentive rewards."
        ),
        protocols=["pendle", "morpho"],
        manual_inputs={
            "borrow_apy": 0.08,
            "liquidity_usd": 100_000,
            "ltv": 0.7,
            "collateral_asset": "wstETH",
        },
        missing_data=[
            "Market data: morpho.oracle_metadata",
            "Market data: pendle.maturity_date",
            "Liquidation buffer calculation",
            "Market data: manual.lltv",
        ],
    )

    assert score.rating == "Very Risky"
    assert score.score >= 7
    assert score.confidence == "low"

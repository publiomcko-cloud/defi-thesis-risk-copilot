from dataclasses import dataclass

from app.schemas.analysis import AnalysisRequest


@dataclass(frozen=True)
class ParsedStrategy:
    description: str
    protocols: list[str]
    market_url: str | None
    manual_inputs: dict
    analysis_depth: str


def parse_strategy(request: AnalysisRequest) -> ParsedStrategy:
    protocols = _normalize_protocols(request)
    return ParsedStrategy(
        description=request.strategy_description,
        protocols=protocols,
        market_url=request.market_url,
        manual_inputs=request.manual_inputs.model_dump(exclude_none=True),
        analysis_depth=request.analysis_depth,
    )


def _normalize_protocols(request: AnalysisRequest) -> list[str]:
    if request.protocols:
        return sorted({protocol.lower() for protocol in request.protocols})

    description = request.strategy_description.lower()
    detected = [
        protocol
        for protocol in ("pendle", "morpho", "aave")
        if protocol in description
    ]
    return detected or ["unknown"]

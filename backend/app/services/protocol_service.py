from app.schemas.protocols import Protocol, ProtocolListResponse


SUPPORTED_PROTOCOLS = [
    Protocol(
        id="pendle",
        name="Pendle",
        category="fixed-yield",
        supported_in_mvp=True,
        description="Fixed-yield and principal token strategies.",
    ),
    Protocol(
        id="morpho",
        name="Morpho",
        category="lending",
        supported_in_mvp=True,
        description="Isolated lending markets and vault-based lending.",
    ),
    Protocol(
        id="aave",
        name="Aave",
        category="lending",
        supported_in_mvp=True,
        description="Collateralized lending, borrowing, and health factor risk.",
    ),
]


def list_protocols() -> ProtocolListResponse:
    return ProtocolListResponse(protocols=SUPPORTED_PROTOCOLS)

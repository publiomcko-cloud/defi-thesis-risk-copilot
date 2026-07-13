import math
import re
from collections import Counter
from dataclasses import dataclass

from app.rag.embeddings import STOPWORDS, TOKEN_PATTERN


SYNONYM_GROUPS = (
    ("lltv", "liquidation", "loan", "value", "threshold"),
    ("health", "factor", "liquidation", "borrow", "collateral"),
    ("oracle", "price", "feed", "manipulation"),
    ("maturity", "expiry", "expiration", "principal", "token", "pt"),
    ("liquidity", "slippage", "exit", "depth"),
    ("volatility", "implied", "realized", "option", "premium"),
)


@dataclass(frozen=True)
class SemanticEmbeddingMetadata:
    provider: str
    dimensions: int


class LocalSemanticEmbeddingProvider:
    """Deterministic semantic-ish provider for offline retrieval experiments."""

    name = "local_semantic"

    def embed(self, text: str) -> dict[str, float]:
        tokens = [
            token
            for token in TOKEN_PATTERN.findall(text.lower())
            if token not in STOPWORDS
        ]
        counts = Counter(tokens)

        for index, group in enumerate(SYNONYM_GROUPS):
            if any(token in counts for token in group):
                counts[f"semantic_group_{index}"] += 1.5

        for phrase in _domain_phrases(text):
            counts[f"phrase:{phrase}"] += 2.0

        norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        return {token: value / norm for token, value in counts.items()}


def get_semantic_embedding_provider(provider_name: str = "local_semantic") -> LocalSemanticEmbeddingProvider:
    if provider_name != "local_semantic":
        raise ValueError(
            f"Unsupported semantic embedding provider '{provider_name}'. "
            "Only local_semantic is available in this offline MVP stage."
        )
    return LocalSemanticEmbeddingProvider()


def semantic_metadata(provider_name: str = "local_semantic") -> SemanticEmbeddingMetadata:
    return SemanticEmbeddingMetadata(provider=provider_name, dimensions=0)


def _domain_phrases(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.lower())
    phrases = []
    for phrase in (
        "health factor",
        "loan to value",
        "principal token",
        "implied volatility",
        "oracle risk",
        "liquidation risk",
        "maturity risk",
    ):
        if phrase in normalized:
            phrases.append(phrase.replace(" ", "_"))
    return phrases

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import re

from app.jobs.cancellation import CancellationContext


LOCAL_EMBEDDING_PROVIDER = "local_deterministic"
LOCAL_EMBEDDING_MODEL = "local-hash-384-v1"
LOCAL_EMBEDDING_DIMENSIONS = 384
EMBEDDING_ALGORITHM_VERSION = "phase18d.local-hash.v1"
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class LocalDeterministicEmbeddingProvider:
    """Dense local hash embeddings; source text never crosses a process boundary."""

    provider = LOCAL_EMBEDDING_PROVIDER
    model = LOCAL_EMBEDDING_MODEL
    dimensions = LOCAL_EMBEDDING_DIMENSIONS

    def embed(self, text: str, cancellation: CancellationContext) -> list[float]:
        values = [0.0] * self.dimensions
        tokens = Counter(_TOKEN_PATTERN.findall(text.lower()))
        for token, count in tokens.items():
            cancellation.raise_if_cancelled()
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            values[index] += sign * count
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return values
        return [round(value / norm, 10) for value in values]


def vector_literal(values: list[float]) -> str:
    """Return a pgvector literal after the provider has enforced dimensions."""

    if len(values) != LOCAL_EMBEDDING_DIMENSIONS:
        raise ValueError("Embedding dimensions are invalid")
    return "[" + ",".join(format(value, ".10g") for value in values) + "]"

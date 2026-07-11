from hashlib import sha256

from app.monitoring.schemas import RawDiscoveredItem


def normalize_discovered_item(raw: RawDiscoveredItem) -> dict:
    protocol = raw.protocol.lower() if raw.protocol else None
    source = raw.source.lower()
    source_type = raw.source_type.lower()
    url = raw.url.strip() if raw.url else None
    market_identifier = raw.market_identifier.strip() if raw.market_identifier else None
    key_material = "|".join(
        [
            source,
            source_type,
            protocol or "",
            market_identifier or "",
            url or raw.title.strip().lower(),
        ]
    )
    discovery_key = sha256(key_material.encode("utf-8")).hexdigest()
    return {
        "discovery_key": discovery_key,
        "source": source,
        "source_type": source_type,
        "title": raw.title.strip(),
        "url": url,
        "protocol": protocol,
        "chain": raw.chain.lower() if raw.chain else None,
        "asset": raw.asset,
        "market_identifier": market_identifier,
        "raw_payload": raw.raw_payload,
    }

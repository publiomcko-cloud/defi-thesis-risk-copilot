from typing import Any


def source_quality_notes(item: dict[str, Any], source: str) -> list[str]:
    notes = [f"Source collected from {source} public data or manual input."]
    if item.get("url") or item.get("slug"):
        notes.append("Candidate includes a source URL or stable source identifier.")
    else:
        notes.append("Candidate lacks a source URL; reviewer should verify source manually.")
    if item.get("tvl") or item.get("tvlUsd"):
        notes.append("TVL-like signal was present in the source payload.")
    if item.get("category"):
        notes.append(f"Source category: {item.get('category')}.")
    notes.append("This candidate is not trusted until human review approves it.")
    return notes

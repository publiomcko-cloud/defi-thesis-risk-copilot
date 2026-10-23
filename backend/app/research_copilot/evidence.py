"""Bounded, extractive question matching over citation-validated retrieval."""

from __future__ import annotations

import re

from app.rag.retriever import RetrievalResult
from app.rag.source_urls import normalize_citation_url
from app.schemas.reports import QuestionAnswer, ResearchAnswerCitation


_WORD = re.compile(r"[a-z0-9][a-z0-9'-]{1,}", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
_STOPWORDS = frozenset(
    "a an and are as at be by can could did do does for from how i in is it of on or that the this to was were what when where which who why will with would".split()
)
_POLARITY_GROUPS = {
    "magnitude": ({"increase", "increases", "increased"}, {"decrease", "decreases", "decreased"}),
    "permission": ({"allow", "allows", "allowed", "enabled"}, {"prohibit", "prohibits", "prohibited", "disabled"}),
    "evidence": ({"support", "supports", "supported"}, {"unsupported"}),
    "requirement": ({"require", "requires", "required"}, {"not", "never", "without"}),
    "safety": ({"safe", "solvent"}, {"unsafe", "insolvent"}),
    "availability": ({"available"}, {"unavailable"}),
}
_POSITIVE = frozenset().union(*(positive for positive, _ in _POLARITY_GROUPS.values()))
_NEGATIVE = frozenset().union(*(negative for _, negative in _POLARITY_GROUPS.values()))
SEMANTIC_SUPPORT_LIMITATION = "semantic entailment is not established by lexical matching"


def build_question_answer(question: str, evidence: list[RetrievalResult]) -> QuestionAnswer:
    """Select short source sentences with lexical overlap; never synthesize new facts."""

    query_terms = _terms(question)
    candidates: list[tuple[int, float, RetrievalResult, str, set[str]]] = []
    for result in evidence[:8]:
        metadata = result.metadata
        if normalize_citation_url(metadata.get("source_url")) is None:
            continue
        sentences = _SENTENCE.split(str(result.text))
        best_for_source: tuple[int, float, RetrievalResult, str, set[str]] | None = None
        for raw in sentences:
            sentence = " ".join(raw.split()).strip(" -*#\t")
            if not sentence or len(sentence) < 24:
                continue
            terms = _terms(sentence)
            overlap = query_terms & terms
            minimum_matches = 1 if len(query_terms) <= 2 else 2
            if len(overlap) < minimum_matches:
                continue
            score = len(overlap) / max(len(query_terms), 1)
            row = (len(overlap), score, result, sentence[:1_000], terms)
            if best_for_source is None or (row[0], row[1]) > (best_for_source[0], best_for_source[1]):
                best_for_source = row
        if best_for_source:
            candidates.append(best_for_source)

    candidates.sort(key=lambda row: (row[0], row[1]), reverse=True)
    selected: list[tuple[int, float, RetrievalResult, str, set[str]]] = []
    seen_sources: set[str] = set()
    for row in candidates:
        if row[2].chunk_id in seen_sources:
            continue
        seen_sources.add(row[2].chunk_id)
        selected.append(row)
        if len(selected) == 4:
            break

    citations = [
        ResearchAnswerCitation(
            source_id=row[2].chunk_id[:128],
            title=(
                f"{row[2].metadata.get('document_title', 'Curated source')} — "
                f"{row[2].metadata.get('section_title', '')}"
            ).strip(" —")[:255],
            excerpt=row[3],
            url=normalize_citation_url(row[2].metadata.get("source_url")),
        )
        for row in selected
    ]
    covered = set().union(*(row[4] for row in selected)) if selected else set()
    missing = sorted(query_terms - covered)[:11]
    # Lexical overlap can find passages, but it cannot establish that a source
    # semantically entails the question (including its polarity). Never mark a
    # matched answer fully supported on that basis alone.
    unsupported_aspects = [*missing, SEMANTIC_SUPPORT_LIMITATION]
    contradictions = _potential_contradictions(selected)

    if not citations:
        return QuestionAnswer(
            status="insufficient",
            answer="Insufficient relevant evidence was found to answer this question. No answer is inferred.",
            citations=[],
            unsupported_aspects=sorted(query_terms)[:12],
            potential_contradictions=[],
            method="Bounded lexical matching over citation-validated retrieved sentences; no generative claim was added.",
        )

    status = "weak"
    evidence_lines = [
        f"{citation.excerpt} [S{index}]"
        for index, citation in enumerate(citations, start=1)
    ]
    answer = "Evidence-matched statements: " + " ".join(evidence_lines)
    answer = "Evidence matched, but semantic support is unverified: " + answer
    if contradictions:
        answer += " Potentially conflicting statements are listed below and require human review."
    return QuestionAnswer(
        status=status,
        answer=answer[:4_000],
        citations=citations,
        unsupported_aspects=unsupported_aspects,
        potential_contradictions=contradictions,
        method=(
            "Bounded extractive matching requires question-term overlap and preserves the source sentence; "
            "it does not establish semantic entailment."
        ),
    )


def question_evidence_needs_followup(answer: QuestionAnswer | None) -> bool:
    """Whether retrieval missed lexical evidence, not whether entailment was proven."""

    if answer is None or answer.status == "insufficient":
        return True
    return any(aspect != SEMANTIC_SUPPORT_LIMITATION for aspect in answer.unsupported_aspects)


def _terms(value: str) -> set[str]:
    return {
        _normalize_term(match.group(0).lower())
        for match in _WORD.finditer(value[:5_000])
        if match.group(0).lower() not in _STOPWORDS
    }


def _normalize_term(term: str) -> str:
    """Normalize a narrow set of common English inflections for lexical matching."""

    explicit = {
        "increases": "increase",
        "increased": "increase",
        "decreases": "decrease",
        "decreased": "decrease",
        "supports": "support",
        "supported": "support",
        "requires": "require",
        "required": "require",
        "allows": "allow",
        "allowed": "allow",
        "prohibits": "prohibit",
        "prohibited": "prohibit",
        "withdrawals": "withdrawal",
        "protocols": "protocol",
    }
    return explicit.get(term, term)


def _potential_contradictions(
    selected: list[tuple[int, float, RetrievalResult, str, set[str]]],
) -> list[str]:
    results: list[str] = []
    for index, first in enumerate(selected):
        for second in selected[index + 1 :]:
            shared = (first[4] & second[4]) - _POSITIVE - _NEGATIVE - _STOPWORDS
            has_opposite_claim = any(
                (bool(first[4] & up) and bool(second[4] & down))
                or (bool(first[4] & down) and bool(second[4] & up))
                for up, down in _POLARITY_GROUPS.values()
            )
            if len(shared) >= 3 and has_opposite_claim:
                results.append(
                    f"Potential conflict between {first[2].chunk_id[:64]} and {second[2].chunk_id[:64]}; "
                    "review the cited source passages."
                )
    return results[:8]

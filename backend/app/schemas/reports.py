from pydantic import BaseModel, Field, field_validator

from app.schemas.analysis import RiskRating
from app.schemas.research import ResearchRunMetadata
from app.rag.source_urls import normalize_citation_url


class CitationLineageReference(BaseModel):
    """Stable durable citation identifiers; never includes an object key or URL."""

    citation_id: str
    source_id: str
    source_title: str
    document_id: str
    document_version_id: str
    document_version_checksum: str
    chunk_id: str
    chunk_checksum: str
    heading_path: list[str]


class SourceReference(BaseModel):
    title: str
    source_type: str
    url: str | None = None
    protocol: str | None = None
    citation_lineage: CitationLineageReference | None = None

    @field_validator("url", mode="before")
    @classmethod
    def safe_url(cls, value):
        return normalize_citation_url(value) if value is not None else None


class ResearchAnswerCitation(BaseModel):
    source_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    excerpt: str = Field(min_length=1, max_length=1_000)
    url: str | None = Field(default=None, max_length=2_048)

    @field_validator("url", mode="before")
    @classmethod
    def safe_url(cls, value):
        return normalize_citation_url(value) if value is not None else None


class QuestionAnswer(BaseModel):
    status: str = Field(pattern=r"^(supported|weak|insufficient)$")
    answer: str = Field(min_length=1, max_length=4_000)
    citations: list[ResearchAnswerCitation] = Field(max_length=8)
    unsupported_aspects: list[str] = Field(max_length=12)
    potential_contradictions: list[str] = Field(max_length=8)
    method: str = Field(max_length=256)


class ReportSection(BaseModel):
    title: str
    content: str


class ReportResponse(BaseModel):
    report_id: str
    status: str = "completed"
    risk_rating: RiskRating
    executive_summary: str
    strategy_description: str
    research_question: str | None = None
    question_answer: QuestionAnswer | None = None
    protocols: list[str]
    assumptions: list[str]
    missing_data: list[str]
    sections: list[ReportSection]
    sources: list[SourceReference]
    research: ResearchRunMetadata | None = None
    disclaimer: str = Field(
        default=(
            "This report is for research and educational purposes only. "
            "It is not financial, investment, legal, or tax advice."
        )
    )


class MarkdownExportResponse(BaseModel):
    report_id: str
    filename: str
    markdown: str

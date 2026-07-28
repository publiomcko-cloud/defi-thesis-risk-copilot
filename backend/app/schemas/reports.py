from pydantic import BaseModel, Field

from app.schemas.analysis import RiskRating


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


class ReportSection(BaseModel):
    title: str
    content: str


class ReportResponse(BaseModel):
    report_id: str
    status: str = "completed"
    risk_rating: RiskRating
    executive_summary: str
    strategy_description: str
    protocols: list[str]
    assumptions: list[str]
    missing_data: list[str]
    sections: list[ReportSection]
    sources: list[SourceReference]
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

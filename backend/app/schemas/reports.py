from pydantic import BaseModel, Field

from app.schemas.analysis import RiskRating


class SourceReference(BaseModel):
    title: str
    source_type: str
    url: str | None = None
    protocol: str | None = None


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

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadedDocument:
    path: Path
    protocol: str
    title: str
    source_url: str
    content: str


def load_markdown_documents(root: Path) -> list[LoadedDocument]:
    documents: list[LoadedDocument] = []
    for path in sorted(root.rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        protocol = path.parent.name
        title = _extract_title(content) or path.stem.replace("_", " ").title()
        documents.append(
            LoadedDocument(
                path=path,
                protocol=protocol,
                title=title,
                source_url=str(path),
                content=content,
            )
        )
    return documents


def _extract_title(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None

"""Small local retrieval layer for approved project documentation."""
from pathlib import Path
from typing import Iterable, List

from src.domain.assistant import EvidenceRecord


class AssistantRagService:
    DEFAULT_DOCUMENTS = (
        "docs/scope.md",
        "docs/common.md",
        "docs/problemStatement.md",
        "docs/data-summary.md",
    )

    def __init__(self, repository_root: Path, document_paths: Iterable[str] = DEFAULT_DOCUMENTS):
        self.repository_root = Path(repository_root)
        self.document_paths = tuple(document_paths)

    def retrieve(self, query: str, limit: int = 3) -> List[EvidenceRecord]:
        terms = {term for term in query.lower().replace("?", " ").split() if len(term) >= 4}
        ranked = []
        for rel_path in self.document_paths:
            path = self.repository_root / rel_path
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
            for index, paragraph in enumerate(paragraphs):
                words = set(paragraph.lower().replace("_", " ").split())
                score = len(terms.intersection(words))
                if score:
                    ranked.append((score, rel_path, index, " ".join(paragraph.split())[:1200]))

        ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [
            EvidenceRecord(
                source_id=f"doc-{rel_path}-{index}",
                source_type="project_document",
                scope="project",
                metric="document_excerpt",
                value=excerpt,
                unit="text",
                source_label=f"{rel_path} (paragraph {index + 1})",
            )
            for _, rel_path, index, excerpt in ranked[:limit]
        ]

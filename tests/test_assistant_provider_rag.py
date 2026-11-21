from pathlib import Path

from src.domain.assistant import EvidenceRecord
from src.domain.overview import MonthlyRevenue, NetworkOverview
from src.services.assistant_evidence_service import AssistantEvidenceService
from src.services.assistant_provider import IAssistantProvider, SarvamAssistantProvider
from src.services.assistant_rag_service import AssistantRagService
from src.services.assistant_service import AssistantService


class FakeProvider(IAssistantProvider):
    def __init__(self, configured=True, text="Verified answer"):
        self.configured = configured
        self.text = text

    def status(self):
        from src.domain.assistant import AssistantProviderStatus
        return AssistantProviderStatus(self.configured, "Test", None)

    def generate(self, system_prompt, user_prompt):
        return self.text


def test_sarvam_provider_requires_key_and_url():
    provider = SarvamAssistantProvider(api_key=None, api_url=None)
    status = provider.status()
    assert status.configured is False
    assert "KEY" in status.message or "key" in status.message


def test_rag_retrieves_checked_project_document():
    rag = AssistantRagService(Path.cwd())
    records = rag.retrieve("stockout velocity cover")
    assert records
    assert all(record.source_type == "project_document" for record in records)
    assert all(record.source_id.startswith("doc-docs/") for record in records)


def test_assistant_falls_back_without_provider_and_uses_citations():
    evidence = AssistantEvidenceService(
        NetworkOverview(100.0, 1, []),
        MonthlyRevenue(["2026-10"], {}),
    )
    service = AssistantService(
        evidence,
        AssistantRagService(Path.cwd()),
        FakeProvider(configured=False),
    )

    answer = service.answer("show the overall network")

    assert answer.fallback is True
    assert answer.provider_status == "not_configured"
    assert answer.citations
    assert "100.0" in answer.text

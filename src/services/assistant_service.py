"""Orchestration between deterministic evidence and provider phrasing."""
from typing import Iterable, List

from src.domain.assistant import AssistantAnswer, EvidenceCitation, EvidenceRecord
from src.services.assistant_evidence_service import AssistantEvidenceService
from src.services.assistant_provider import IAssistantProvider
from src.services.assistant_rag_service import AssistantRagService


class AssistantService:
    def __init__(
        self,
        evidence_service: AssistantEvidenceService,
        rag_service: AssistantRagService,
        provider: IAssistantProvider,
    ):
        self.evidence_service = evidence_service
        self.rag_service = rag_service
        self.provider = provider

    def answer(self, query: str) -> AssistantAnswer:
        evidence = self.evidence_service.retrieve(query)
        evidence += self.rag_service.retrieve(query)
        citations = self._citations(evidence)
        provider_status = self.provider.status()

        if not evidence:
            return AssistantAnswer(
                text="No reliable evidence is available for that scope. It may be missing, untrusted, or outside the current data.",
                citations=[],
                fallback=True,
                provider_status="insufficient_evidence",
            )

        factual_text = self._fallback_text(query, evidence)
        if not provider_status.configured:
            return AssistantAnswer(
                text=factual_text,
                citations=citations,
                fallback=True,
                provider_status="not_configured",
            )

        system_prompt = (
            "You are a Manager Assistant for a retail operations dashboard. "
            "Use only the supplied evidence. Never calculate or invent a number, owner, store, date, or action. "
            "Return a concise plain-text answer. If evidence is insufficient, say so."
        )
        evidence_prompt = "\n".join(
            f"- {record.source_id} | {record.scope} | {record.metric} | "
            f"{record.value} | {record.unit} | {record.source_label}"
            for record in evidence
        )
        try:
            text = self.provider.generate(system_prompt, f"Evidence:\n{evidence_prompt}\n\nQuestion: {query}")
        except Exception:
            return AssistantAnswer(
                text=factual_text,
                citations=citations,
                fallback=True,
                provider_status="provider_error",
            )
        return AssistantAnswer(
            text=text,
            citations=citations,
            fallback=False,
            provider_status="ready",
        )

    def daily_briefing(self) -> AssistantAnswer:
        tasks = self.evidence_service.daily_tasks()
        if not tasks:
            return AssistantAnswer(
                text="No reliable daily task is available from the current trusted evidence.",
                citations=[],
                tasks=[],
                fallback=True,
                provider_status="insufficient_evidence",
            )
        lines = ["Daily tasks:"]
        citations = []
        for task in tasks:
            lines.append(
                f"{task.rank}. {task.owner}: {task.action} "
                f"Reason: {task.reason}. Timing: {task.timing}. "
                f"Impact: {task.impact_value:g} {task.impact_unit}."
            )
            for evidence_id in task.evidence_ids:
                record = next(
                    (item for item in self._all_evidence_records() if item.source_id == evidence_id),
                    None,
                )
                if record:
                    citations.append(self._citation(record))
        return AssistantAnswer(
            text="\n".join(lines),
            citations=citations,
            tasks=tasks,
            fallback=False,
            provider_status="local",
        )

    def _all_evidence_records(self) -> Iterable[EvidenceRecord]:
        for state in self.evidence_service.overview.states:
            for city in state.cities:
                for store in city.stores:
                    yield EvidenceRecord(
                        source_id=f"store-stock-{store.store_id}",
                        source_type="network_overview",
                        scope=f"store:{store.store_id}",
                        metric="stock_and_revenue",
                        value=round(store.revenue, 2),
                        unit="INR",
                        source_label=f"Store overview / {store.store_id}",
                    )
        for notification in self.evidence_service.notifications:
            yield EvidenceRecord(
                source_id=f"notification-{notification.id}",
                source_type="notification",
                scope="network",
                metric="data_issue",
                value=notification.title,
                unit="notification",
                source_label=f"Notification / {notification.title}",
            )

    @staticmethod
    def _citations(records: Iterable[EvidenceRecord]) -> List[EvidenceCitation]:
        return [AssistantService._citation(record) for record in records]

    @staticmethod
    def _citation(record: EvidenceRecord) -> EvidenceCitation:
        return EvidenceCitation(
            source_id=record.source_id,
            source_label=record.source_label,
            metric=record.metric,
            value=record.value,
            unit=record.unit,
            scope=record.scope,
        )

    @staticmethod
    def _fallback_text(query: str, evidence: Iterable[EvidenceRecord]) -> str:
        records = list(evidence)
        facts = [
            f"{record.metric}: {record.value} {record.unit} ({record.scope})"
            for record in records
            if record.source_type != "project_document"
        ]
        if not facts:
            return f"No verified application fact matched: {query}"
        return "Verified evidence:\n" + "\n".join(f"- {fact}" for fact in facts[:10])

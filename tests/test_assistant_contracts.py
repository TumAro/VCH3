from src.domain.assistant import (
    AssistantAnswer,
    DailyTask,
    EvidenceCitation,
    EvidenceRecord,
)


def test_evidence_record_and_citation_are_immutable():
    evidence = EvidenceRecord(
        source_id="network-state-UP",
        source_type="network_overview",
        scope="state:Uttar Pradesh",
        metric="revenue",
        value=125000.0,
        unit="INR",
        source_label="State revenue / Uttar Pradesh",
    )
    citation = EvidenceCitation(
        source_id=evidence.source_id,
        source_label=evidence.source_label,
        metric=evidence.metric,
        value=evidence.value,
        unit=evidence.unit,
        scope=evidence.scope,
    )

    assert citation.value == 125000.0
    assert evidence.metric == "revenue"


def test_daily_task_holds_one_owner_action_reason_timing_and_evidence():
    task = DailyTask(
        rank=1,
        owner="LKO-01",
        action="Review the stockout-risk SKU list at opening.",
        reason="Cover is below the warehouse route lead time.",
        timing="Today",
        impact_value=48000.0,
        impact_unit="INR",
        evidence_ids=["finding-LKO-01-KUR-01-M"],
    )

    answer = AssistantAnswer(
        text="One stock risk needs attention today.",
        citations=[],
        tasks=[task],
    )

    assert answer.tasks[0].evidence_ids == ["finding-LKO-01-KUR-01-M"]

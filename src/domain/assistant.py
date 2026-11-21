from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union


EvidenceValue = Union[int, float, str]


@dataclass(frozen=True)
class EvidenceRecord:
    source_id: str
    source_type: str
    scope: str
    metric: str
    value: EvidenceValue
    unit: str
    source_label: str
    details: Dict[str, EvidenceValue] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceCitation:
    source_id: str
    source_label: str
    metric: str
    value: EvidenceValue
    unit: str
    scope: str


@dataclass(frozen=True)
class DailyTask:
    rank: int
    owner: str
    action: str
    reason: str
    timing: str
    impact_value: float
    impact_unit: str
    evidence_ids: List[str]


@dataclass(frozen=True)
class AssistantAnswer:
    text: str
    citations: List[EvidenceCitation]
    tasks: List[DailyTask] = field(default_factory=list)
    fallback: bool = False
    provider_status: str = "not_configured"


@dataclass(frozen=True)
class AssistantProviderStatus:
    configured: bool
    provider: str
    message: Optional[str] = None

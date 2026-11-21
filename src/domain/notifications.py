"""Notification model shown in the dashboard bell (REQ-15)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Notification:
    id: str  # content fingerprint: same content -> same id across re-runs
    kind: str  # "data_issue" | "sign_off"
    title: str
    detail: str

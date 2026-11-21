"""Fixed Track 2 pipeline assembly."""
from src.velocity_cover.models import VelocityCoverResult
from src.velocity_cover.position_cover_service import PositionCoverService
from src.velocity_cover.problem_detection_service import ProblemDetectionService
from src.velocity_cover.repositories import VelocityCoverRepository
from src.velocity_cover.velocity_service import VelocityService


class VelocityCoverPipeline:
    def __init__(self, repository: VelocityCoverRepository):
        self.velocity = VelocityService(repository)
        self.position_cover = PositionCoverService(repository)
        self.problem_detection = ProblemDetectionService(repository)

    def run(self) -> VelocityCoverResult:
        sku, style, category = self.velocity.compute()
        positions = self.position_cover.compute(sku)
        findings = self.problem_detection.detect(positions, sku)
        return VelocityCoverResult(sku, style, category, positions, findings)

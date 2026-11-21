from src.moves.explain import ExplanationService

svc = ExplanationService()


def test_s2s_exact():
    assert svc.reason(5, "SKU1", "S1", 3.24, 1.25, "S2", 52.06) == (
        "Send 5: SKU1 has 3.2d cover at S1, sells 1.2/d; donor S2 retains 52.1d cover"
    )


def test_w2s_exact():
    assert svc.reason(10, "SKU9", "S3", 0.0, 2.0, "WH-KOL", 12.0) == (
        "Send 10: SKU9 has 0.0d cover at S3, sells 2.0/d; donor WH-KOL retains 12.0d cover"
    )


def test_rounding_matches_format():
    x = 2.675
    assert f"{x:.1f}d" in svc.reason(1, "A", "B", x, x, "C", x)


def test_none_donor_cover():
    r = svc.reason(4, "SKU9", "S3", 1.0, 2.0, "WH-KOL", None)
    assert r.endswith("retains n/a cover")

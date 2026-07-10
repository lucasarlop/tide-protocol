from tide.policy import decide


def test_sensitive_task_requires_review() -> None:
    decision = decide("apply database migration in production", [], [])
    assert "database" in decision.hardgates
    assert "production" in decision.hardgates
    assert decision.review_required
    assert decision.max_writers == 1

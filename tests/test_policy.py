from tide.policy import decide


def test_sensitive_task_requires_review() -> None:
    decision = decide("apply database migration in production", [], [])
    assert "database" in decision.hardgates
    assert "production" in decision.hardgates
    assert decision.review_required
    assert decision.max_writers == 1


def test_portuguese_sensitive_task_is_detected() -> None:
    decision = decide("aplicar migração no banco em produção", [], [])
    assert "database" in decision.hardgates
    assert "production" in decision.hardgates


def test_sensitive_paths_are_detected_without_prompt_keywords() -> None:
    decision = decide("ajustar arquivos", [".github/workflows/ci.yml", "pyproject.toml"], [])
    assert "infrastructure" in decision.hardgates
    assert "dependency" in decision.hardgates


def test_product_word_does_not_trigger_production_hardgate() -> None:
    decision = decide("adjust product service", ["src/product.py"], [])
    assert "production" not in decision.hardgates

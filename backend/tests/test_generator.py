"""Tests for the deterministic synthetic data generator."""

from app.ml.data_generator import FEATURES, generate


def test_generator_is_reproducible_and_matches_schema():
    first = generate(50, seed=7)
    second = generate(50, seed=7)

    assert first.equals(second)
    assert set(FEATURES).issubset(first.columns)
    assert "application_id" in first
    assert "defaulted" in first
    assert set(first["defaulted"].unique()).issubset({0, 1})

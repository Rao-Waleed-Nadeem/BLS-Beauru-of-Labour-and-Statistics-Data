"""
Tests for M20 Feature Engineering.
"""

from typing import Any
import pytest
from pipeline.features.feature_builder import FeatureBuilder
from pipeline.parsers.models import UnifiedObject, APISchema, MetadataSchema


def _mock_unified(value: str, period: str, year: str) -> UnifiedObject:
    """Helper to mock UnifiedObject for testing."""
    return UnifiedObject(
        api=APISchema(
            series_id="TEST01",
            series_title="Test Series",
            frequency="M",
            year=year,
            period=period,
            period_name="Test",
            value=value,
            latest=True,
            footnotes=[]
        ),
        metadata=MetadataSchema(
            uuid="123",
            dataset_id="test",
            program_id="test_program",
            series_id="TEST01",
            source_type="api",
            collection_timestamp="2026-07-23T00:00:00Z",
            normalization_timestamp="2026-07-23T00:00:00Z",
            checksum="abc",
            collector="test",
            collector_version="1.0",
            schema_version="1.0",
            validation_status="valid"
        )
    )


def test_calculate_features_month():
    objects = [
        _mock_unified("100.0", "M01", "2026"),
        _mock_unified("105.0", "M02", "2026"),
    ]
    features = FeatureBuilder._calculate_features(objects)

    assert len(features) == 2
    
    # First row
    assert features[0]["month"] == 1
    assert features[0]["quarter"] is None
    assert features[0]["value"] == 100.0
    assert features[0]["previous_value"] is None
    assert features[0]["value_diff"] is None
    assert features[0]["pct_change"] is None

    # Second row
    assert features[1]["month"] == 2
    assert features[1]["value"] == 105.0
    assert features[1]["previous_value"] == 100.0
    assert features[1]["value_diff"] == 5.0
    assert features[1]["pct_change"] == 5.0


def test_calculate_features_quarter():
    objects = [
        _mock_unified("200.0", "Q01", "2026"),
        _mock_unified("180.0", "Q02", "2026"),
    ]
    features = FeatureBuilder._calculate_features(objects)

    assert len(features) == 2
    
    assert features[0]["quarter"] == 1
    assert features[0]["month"] is None
    
    assert features[1]["quarter"] == 2
    assert features[1]["value"] == 180.0
    assert features[1]["previous_value"] == 200.0
    assert features[1]["value_diff"] == -20.0
    assert features[1]["pct_change"] == -10.0


def test_calculate_features_invalid_value():
    objects = [
        _mock_unified("100.0", "M01", "2026"),
        _mock_unified("BAD", "M02", "2026"),
        _mock_unified("110.0", "M03", "2026"),
    ]
    features = FeatureBuilder._calculate_features(objects)

    assert len(features) == 3
    
    # Second row (invalid)
    assert features[1]["value"] is None
    assert features[1]["previous_value"] == 100.0
    assert features[1]["value_diff"] is None
    assert features[1]["pct_change"] is None
    
    # Third row (valid again, previous should still be 100.0 because BAD didn't update it)
    assert features[2]["value"] == 110.0
    assert features[2]["previous_value"] == 100.0
    assert features[2]["value_diff"] == 10.0
    assert features[2]["pct_change"] == 10.0

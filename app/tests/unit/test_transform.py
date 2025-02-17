import pytest
from datetime import datetime
from app.api.core.transform import (
    TransformationType,
    TransformationConfig,
    TransformationRule,
    TransformationPipeline,
    TimestampEnrichmentRule,
    SchemaValidationRule,
    DataNormalizationRule
)
from app.api.core.metrics import metrics

@pytest.fixture
def transformation_pipeline():
    """Create a test transformation pipeline instance"""
    return TransformationPipeline()

@pytest.fixture
def timestamp_rule():
    """Create a timestamp enrichment rule"""
    config = TransformationConfig(
        name="timestamp_enrichment",
        type=TransformationType.ENRICH,
        order=1,
        config={}
    )
    return TimestampEnrichmentRule(config)

@pytest.fixture
def schema_rule():
    """Create a schema validation rule"""
    config = TransformationConfig(
        name="schema_validation",
        type=TransformationType.VALIDATE,
        order=2,
        config={
            "required_fields": ["event_type", "timestamp", "source"]
        }
    )
    return SchemaValidationRule(config)

@pytest.fixture
def normalization_rule():
    """Create a data normalization rule"""
    config = TransformationConfig(
        name="data_normalization",
        type=TransformationType.NORMALIZE,
        order=3,
        config={
            "normalizations": {
                "event_type": "lowercase",
                "source": "lowercase"
            }
        }
    )
    return DataNormalizationRule(config)

@pytest.mark.asyncio
async def test_timestamp_enrichment_rule(timestamp_rule):
    """Test timestamp enrichment rule"""
    test_data = {"event_type": "test"}
    
    # Apply rule
    result = await timestamp_rule.apply(test_data)
    
    # Verify timestamp was added
    assert "processed_at" in result
    # Verify timestamp format
    datetime.fromisoformat(result["processed_at"])
    # Verify metrics
    assert timestamp_rule.metrics["processed"] == 1
    assert timestamp_rule.metrics["errors"] == 0
    assert timestamp_rule.metrics["processing_time"] > 0

@pytest.mark.asyncio
async def test_schema_validation_rule_valid(schema_rule):
    """Test schema validation rule with valid data"""
    test_data = {
        "event_type": "test",
        "timestamp": "2024-01-01T00:00:00",
        "source": "test_source"
    }
    
    # Apply rule
    result = await schema_rule.apply(test_data)
    
    # Verify data passed validation
    assert result == test_data
    # Verify metrics
    assert schema_rule.metrics["processed"] == 1
    assert schema_rule.metrics["errors"] == 0

@pytest.mark.asyncio
async def test_schema_validation_rule_invalid(schema_rule):
    """Test schema validation rule with invalid data"""
    test_data = {
        "event_type": "test"
        # Missing required fields
    }
    
    # Apply rule
    result = await schema_rule.apply(test_data)
    
    # Verify data was filtered out
    assert result is None
    # Verify metrics
    assert schema_rule.metrics["processed"] == 1
    assert schema_rule.metrics["errors"] == 0

@pytest.mark.asyncio
async def test_data_normalization_rule(normalization_rule):
    """Test data normalization rule"""
    test_data = {
        "event_type": "TEST_EVENT",
        "source": "TEST_SOURCE",
        "other_field": "UNCHANGED"
    }
    
    # Apply rule
    result = await normalization_rule.apply(test_data)
    
    # Verify normalization
    assert result["event_type"] == "test_event"
    assert result["source"] == "test_source"
    assert result["other_field"] == "UNCHANGED"  # Not configured for normalization
    # Verify metrics
    assert normalization_rule.metrics["processed"] == 1
    assert normalization_rule.metrics["errors"] == 0

@pytest.mark.asyncio
async def test_transformation_pipeline_execution(
    transformation_pipeline,
    timestamp_rule,
    schema_rule,
    normalization_rule
):
    """Test complete transformation pipeline execution"""
    # Register rules
    transformation_pipeline.register_rule(timestamp_rule)
    transformation_pipeline.register_rule(schema_rule)
    transformation_pipeline.register_rule(normalization_rule)
    
    test_data = {
        "event_type": "TEST_EVENT",
        "timestamp": "2024-01-01T00:00:00",
        "source": "TEST_SOURCE"
    }
    
    # Apply pipeline
    result = await transformation_pipeline.apply_rules(test_data)
    
    # Verify transformations
    assert "processed_at" in result  # Timestamp enrichment
    assert result["event_type"] == "test_event"  # Normalization
    assert result["source"] == "test_source"  # Normalization
    
    # Verify rule order
    assert len(transformation_pipeline._ordered_rules) == 3
    assert transformation_pipeline._ordered_rules[0] == "timestamp_enrichment"
    assert transformation_pipeline._ordered_rules[1] == "schema_validation"
    assert transformation_pipeline._ordered_rules[2] == "data_normalization"

@pytest.mark.asyncio
async def test_transformation_pipeline_rule_disabled(
    transformation_pipeline,
    timestamp_rule,
    schema_rule
):
    """Test pipeline with disabled rule"""
    # Disable schema validation
    schema_rule.config.enabled = False
    
    # Register rules
    transformation_pipeline.register_rule(timestamp_rule)
    transformation_pipeline.register_rule(schema_rule)
    
    test_data = {
        "event_type": "test"
        # Missing required fields, but validation is disabled
    }
    
    # Apply pipeline
    result = await transformation_pipeline.apply_rules(test_data)
    
    # Verify only timestamp enrichment was applied
    assert "processed_at" in result
    assert timestamp_rule.metrics["processed"] == 1
    assert schema_rule.metrics["processed"] == 0

@pytest.mark.asyncio
async def test_transformation_pipeline_error_handling(transformation_pipeline):
    """Test pipeline error handling"""
    # Create a rule that raises an exception
    class ErrorRule(TransformationRule):
        async def apply(self, data):
            raise ValueError("Test error")
    
    error_config = TransformationConfig(
        name="error_rule",
        type=TransformationType.ENRICH,
        order=1,
        config={}
    )
    error_rule = ErrorRule(error_config)
    
    # Register rule
    transformation_pipeline.register_rule(error_rule)
    
    # Apply pipeline
    with pytest.raises(ValueError, match="Test error"):
        await transformation_pipeline.apply_rules({"test": "data"})
    
    # Verify error metrics
    assert error_rule.metrics["errors"] == 1

@pytest.mark.asyncio
async def test_transformation_metrics_integration(
    transformation_pipeline,
    timestamp_rule,
    schema_rule,
    normalization_rule
):
    """Test metrics integration"""
    # Register rules
    transformation_pipeline.register_rule(timestamp_rule)
    transformation_pipeline.register_rule(schema_rule)
    transformation_pipeline.register_rule(normalization_rule)
    
    test_data = {
        "event_type": "TEST_EVENT",
        "timestamp": "2024-01-01T00:00:00",
        "source": "TEST_SOURCE"
    }
    
    # Apply pipeline multiple times
    for _ in range(3):
        await transformation_pipeline.apply_rules(test_data)
    
    # Verify Prometheus metrics
    for rule in [timestamp_rule, schema_rule, normalization_rule]:
        # Check processed count
        assert metrics.transformation_processed_total.labels(
            rule=rule.config.name,
            type=rule.config.type
        )._value.get() == 3
        
        # Check duration histogram
        assert metrics.transformation_duration_seconds.labels(
            rule=rule.config.name,
            type=rule.config.type
        )._sum.get() > 0
    
    # Check pipeline duration
    assert metrics.pipeline_duration_seconds._sum.get() > 0 
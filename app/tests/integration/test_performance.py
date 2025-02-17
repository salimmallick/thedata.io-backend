import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.api.core.query_optimization import query_optimizer
from app.api.core.resource_tracking import resource_tracker
from app.api.core.metrics import metrics
from app.api.core.transform.pipeline import BatchTransformationPipeline
from app.api.core.transform.cache import transformation_cache
from app.api.core.transform import (
    TransformationType,
    TransformationConfig,
    DataTypeConversionRule,
    FieldMappingRule,
    DataMaskingRule
)

class TestPerformanceMonitoring:
    """Integration tests for performance monitoring"""
    
    @pytest.fixture
    async def setup_monitoring(self):
        """Setup monitoring components"""
        await resource_tracker.start_tracking()
        yield
        await resource_tracker.stop_tracking()
    
    @pytest.mark.asyncio
    async def test_resource_tracking(self, setup_monitoring):
        """Test resource tracking functionality"""
        # Wait for initial metrics collection
        await asyncio.sleep(2)
        
        # Get resource summary
        summary = await resource_tracker.get_resource_summary()
        
        # Verify all required metrics are present
        assert "cpu_percent" in summary
        assert "memory_percent" in summary
        assert "disk_percent" in summary
        assert "network_connections" in summary
        
        # Verify metrics are within reasonable ranges
        assert 0 <= summary["cpu_percent"] <= 100
        assert 0 <= summary["memory_percent"] <= 100
        assert 0 <= summary["disk_percent"] <= 100
        assert summary["network_connections"] >= 0
    
    @pytest.mark.asyncio
    async def test_query_optimization(self):
        """Test query optimization functionality"""
        test_query = "SELECT * FROM users WHERE name LIKE '%test%'"
        
        # Analyze query
        analysis = await query_optimizer.analyze_query(
            query=test_query,
            duration=0.5,
            database="postgres"
        )
        
        # Verify analysis results
        assert "pattern" in analysis
        assert "recommendations" in analysis
        assert len(analysis["recommendations"]) > 0
        
        # Test optimization
        optimization = await query_optimizer.optimize_query(test_query)
        assert "optimized_query" in optimization
        assert optimization["optimized_query"] != test_query
    
    @pytest.mark.asyncio
    async def test_performance_regression(self):
        """Test performance regression detection"""
        # Simulate normal query performance
        base_duration = 0.1
        test_query = "SELECT id, name FROM users WHERE id = 1"
        
        # Record baseline performance
        for _ in range(5):
            await query_optimizer.analyze_query(
                query=test_query,
                duration=base_duration,
                database="postgres"
            )
        
        # Simulate performance degradation
        degraded_duration = base_duration * 3
        await query_optimizer.analyze_query(
            query=test_query,
            duration=degraded_duration,
            database="postgres"
        )
        
        # Get optimization stats
        stats = await query_optimizer.get_optimization_stats()
        
        # Verify degradation detection
        pattern_stats = stats["pattern_stats"]
        assert len(pattern_stats) > 0
        for pattern_data in pattern_stats.values():
            assert pattern_data["max_duration"] >= degraded_duration
    
    @pytest.mark.asyncio
    async def test_resource_alerts(self, setup_monitoring):
        """Test resource monitoring alerts"""
        # Get initial resource usage
        initial_usage = await resource_tracker.get_resource_usage(
            time_range=timedelta(minutes=5)
        )
        
        # Verify all resource types are tracked
        assert "cpu" in initial_usage
        assert "memory" in initial_usage
        assert "disk" in initial_usage
        assert "network" in initial_usage
        
        # Verify historical data format
        for resource_type, history in initial_usage.items():
            assert isinstance(history, list)
            if history:
                entry = history[0]
                assert "timestamp" in entry
                assert "data" in entry
                assert isinstance(entry["timestamp"], datetime)
    
    @pytest.mark.asyncio
    async def test_load_simulation(self):
        """Test system behavior under load"""
        async def generate_load():
            """Generate test load"""
            test_queries = [
                "SELECT * FROM users",
                "SELECT id, name FROM products WHERE price > 100",
                "SELECT COUNT(*) FROM orders GROUP BY status",
                "SELECT * FROM inventory WHERE quantity < 10"
            ]
            
            for query in test_queries:
                await query_optimizer.analyze_query(
                    query=query,
                    duration=0.2,
                    database="postgres"
                )
                await asyncio.sleep(0.1)
        
        # Run load test
        tasks = [generate_load() for _ in range(5)]
        await asyncio.gather(*tasks)
        
        # Get optimization stats after load test
        stats = await query_optimizer.get_optimization_stats()
        
        # Verify load test impact
        assert stats["patterns"] >= len(tasks)
        assert stats["optimization_stats"]["total_optimizations"] > 0
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, setup_monitoring):
        """Test metrics collection under various conditions"""
        # Test CPU metrics
        metrics.record_system_cpu_usage([50.0, 60.0, 70.0, 80.0])
        assert metrics.get_metric("system_cpu_usage").samples[0].value > 0

        # Test memory metrics
        metrics.record_system_memory_usage(75.5)
        assert metrics.get_metric("system_memory_usage").samples[0].value > 0

        # Test request metrics
        metrics.record_http_request("GET", "/api/test", 200)
        assert metrics.get_metric("http_requests_total").samples[0].value > 0

        # Test latency metrics
        metrics.record_request_duration("GET", "/api/test", 0.5)
        assert metrics.get_metric("http_request_duration_seconds").samples[0].value > 0
        
        # Wait for metrics to be processed
        await asyncio.sleep(1)
        
        # Verify resource tracking is active
        summary = await resource_tracker.get_resource_summary()
        assert all(key in summary for key in [
            "cpu_percent",
            "memory_percent",
            "disk_percent",
            "network_connections"
        ])

@pytest.fixture
async def pipeline():
    """Create a test pipeline instance"""
    pipeline = BatchTransformationPipeline(batch_size=100)
    
    # Register test rules
    rules = [
        DataTypeConversionRule(TransformationConfig(
            name="type_conversion",
            type=TransformationType.NORMALIZE,
            order=1,
            config={
                "conversions": {
                    "timestamp": "datetime",
                    "amount": "float"
                }
            }
        )),
        FieldMappingRule(TransformationConfig(
            name="field_mapping",
            type=TransformationType.NORMALIZE,
            order=2,
            config={
                "mappings": {
                    "ts": "timestamp",
                    "amt": "amount"
                }
            }
        )),
        DataMaskingRule(TransformationConfig(
            name="data_masking",
            type=TransformationType.NORMALIZE,
            order=3,
            config={
                "patterns": {
                    "email": "email",
                    "phone": "phone"
                }
            }
        ))
    ]
    
    for rule in rules:
        pipeline.register_rule(rule)
    
    yield pipeline

def generate_test_data(count: int) -> List[Dict[str, Any]]:
    """Generate test data batch"""
    return [
        {
            "ts": datetime.utcnow().isoformat(),
            "amt": str(i * 10.5),
            "email": f"user{i}@example.com",
            "phone": f"555-{i:04d}"
        }
        for i in range(count)
    ]

@pytest.mark.asyncio
async def test_batch_processing(pipeline):
    """Test batch processing functionality"""
    # Generate large test dataset
    data = generate_test_data(250)  # More than 2 batches
    
    # Process data
    start_time = time.time()
    results = await pipeline.process_batches(data)
    duration = time.time() - start_time
    
    # Verify results
    assert len(results) == len(data)
    for result in results:
        assert "timestamp" in result  # Field mapping
        assert isinstance(result["amount"], float)  # Type conversion
        assert "@" not in result["email"]  # Data masking
    
    # Verify batch processing
    assert duration < 5.0  # Should process within reasonable time

@pytest.mark.asyncio
async def test_cache_effectiveness(pipeline):
    """Test cache hit rate and performance"""
    # Generate test data
    data = generate_test_data(100)
    
    # First run - should miss cache
    start_time = time.time()
    results1 = await pipeline.process_batch(data)
    first_duration = time.time() - start_time
    
    # Second run - should hit cache
    start_time = time.time()
    results2 = await pipeline.process_batch(data)
    second_duration = time.time() - start_time
    
    # Verify cache improved performance
    assert second_duration < first_duration
    assert results1 == results2  # Results should be identical

@pytest.mark.asyncio
async def test_parallel_batch_processing(pipeline):
    """Test parallel batch processing performance"""
    # Generate multiple batches
    batches = [generate_test_data(50) for _ in range(5)]
    
    # Process batches in parallel
    start_time = time.time()
    tasks = [pipeline.process_batch(batch) for batch in batches]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start_time
    
    # Verify all batches processed
    assert len(results) == len(batches)
    for batch_result in results:
        assert len(batch_result) == 50
    
    # Verify parallel processing was faster than sequential
    sequential_time = sum(
        len(batch) * 0.01  # Estimated time per item
        for batch in batches
    )
    assert duration < sequential_time

@pytest.mark.asyncio
async def test_error_handling_in_batch(pipeline):
    """Test error handling in batch processing"""
    # Generate test data with some invalid items
    data = generate_test_data(100)
    data[25]["amt"] = "invalid"  # Invalid amount
    data[75]["ts"] = "invalid"   # Invalid timestamp
    
    # Process batch
    results = await pipeline.process_batch(data)
    
    # Verify error handling
    valid_results = [r for r in results if r is not None]
    assert len(valid_results) < len(data)  # Some items should be filtered
    assert all(isinstance(r["amount"], float) for r in valid_results)
    assert all("timestamp" in r for r in valid_results)

@pytest.mark.asyncio
async def test_cache_invalidation(pipeline):
    """Test cache invalidation behavior"""
    # Generate test data
    data = generate_test_data(50)
    
    # First run
    results1 = await pipeline.process_batch(data)
    
    # Invalidate cache for type conversion rule
    await transformation_cache.invalidate("type_conversion")
    
    # Second run - should partially miss cache
    start_time = time.time()
    results2 = await pipeline.process_batch(data)
    partial_cache_duration = time.time() - start_time
    
    # Invalidate all caches
    await transformation_cache.cleanup(max_age=0)
    
    # Third run - should completely miss cache
    start_time = time.time()
    results3 = await pipeline.process_batch(data)
    no_cache_duration = time.time() - start_time
    
    # Verify timing behavior
    assert partial_cache_duration < no_cache_duration
    # Verify results consistency
    assert results1 == results2 == results3

@pytest.mark.asyncio
async def test_large_batch_memory_usage(pipeline):
    """Test memory usage with large batches"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Generate large dataset
    data = generate_test_data(1000)
    
    # Process in batches
    results = await pipeline.process_batches(data)
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Verify memory usage
    assert memory_increase < 100 * 1024 * 1024  # Less than 100MB increase
    assert len(results) == len(data)

@pytest.mark.asyncio
async def test_batch_size_performance(pipeline):
    """Test performance with different batch sizes"""
    data = generate_test_data(500)
    timings = {}
    
    for batch_size in [10, 50, 100, 250]:
        pipeline.batch_size = batch_size
        start_time = time.time()
        results = await pipeline.process_batches(data)
        timings[batch_size] = time.time() - start_time
        
        # Verify all data processed
        assert len(results) == len(data)
    
    # Verify optimal batch size performance
    assert timings[100] <= timings[10]  # Larger batches should be more efficient
    assert timings[100] <= timings[250]  # But not too large 
import pytest
from dagster import execute_job
from app.dagster.jobs.materialized_views import (
    realtime_views,
    view_optimization
)

@pytest.mark.asyncio
async def test_realtime_views_job(dagster_resources, setup_test_tables):
    """Test the realtime views materialization job."""
    # Insert test data
    test_events = [
        {
            "event_id": f"test-event-{i}",
            "timestamp": "2024-02-10T00:00:00",
            "event_type": "user_interaction",
            "event_name": "page_view",
            "properties": '{"page": "home"}',
            "context": '{"user_agent": "test-browser"}'
        }
        for i in range(10)
    ]
    
    await dagster_resources.resources.clickhouse.execute(
        "INSERT INTO test_events FORMAT JSONEachRow",
        test_events
    )
    
    # Run the realtime views job
    result = execute_job(
        realtime_views,
        resources=dagster_resources.resources
    )
    
    # Verify job execution
    assert result.success
    
    # Verify materialized views were created
    views = await dagster_resources.resources.materialize.list_views()
    assert len(views) > 0
    assert any(view["name"] == "realtime_page_views" for view in views)

@pytest.mark.asyncio
async def test_view_optimization_job(dagster_resources, setup_test_tables):
    """Test the view optimization job."""
    # Create a test materialized view
    await dagster_resources.resources.materialize.execute("""
        CREATE MATERIALIZED VIEW test_view AS
        SELECT
            toStartOfHour(timestamp) as hour,
            event_type,
            count(*) as event_count
        FROM test_events
        GROUP BY hour, event_type
    """)
    
    # Insert test data
    test_events = [
        {
            "event_id": f"test-event-{i}",
            "timestamp": "2024-02-10T00:00:00",
            "event_type": "user_interaction",
            "event_name": "button_click",
            "properties": '{"button_id": "submit"}',
            "context": '{"user_agent": "test-browser"}'
        }
        for i in range(20)
    ]
    
    await dagster_resources.resources.clickhouse.execute(
        "INSERT INTO test_events FORMAT JSONEachRow",
        test_events
    )
    
    # Run the optimization job
    result = execute_job(
        view_optimization,
        resources=dagster_resources.resources
    )
    
    # Verify job execution
    assert result.success
    
    # Verify view optimization metrics
    metrics = result.output_for_node("optimize_views")
    assert "optimization_stats" in metrics
    assert metrics["optimization_stats"]["views_optimized"] > 0

@pytest.mark.asyncio
async def test_view_refresh_schedule(dagster_resources, setup_test_tables, test_repository):
    """Test the view refresh schedule."""
    # Get the schedule from repository
    schedule = test_repository.get_schedule_def("realtime_views_schedule")
    
    # Create a schedule context
    context = schedule.execution_context_for_schedule_eval()
    
    # Evaluate schedule
    result = schedule.evaluate_tick(context)
    
    # Verify schedule evaluation
    assert result.should_execute
    assert len(result.run_requests) > 0
    
    # Verify schedule configuration
    run_config = result.run_requests[0].run_config
    assert "resources" in run_config
    assert "ops" in run_config 
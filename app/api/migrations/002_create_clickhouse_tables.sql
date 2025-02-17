-- User Interaction Events
CREATE TABLE IF NOT EXISTS user_interaction_events (
    event_id UUID,
    timestamp DateTime64(9),
    platform LowCardinality(String),
    device_info Nested (
        type String,
        os String,
        version String,
        manufacturer String
    ),
    session_id UUID,
    user_id Nullable(UUID),
    event_type LowCardinality(String),
    event_name String,
    properties JSON,
    context Nested (
        app_version String,
        network_type String,
        carrier String,
        locale String,
        timezone String
    ),
    _partition_key String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, event_type, event_id)
TTL timestamp + INTERVAL 6 MONTH;

-- Performance Events
CREATE TABLE IF NOT EXISTS performance_events (
    event_id UUID,
    timestamp DateTime64(9),
    platform LowCardinality(String),
    category LowCardinality(String),
    measurements Nested (
        name String,
        value Float64,
        unit String
    ),
    context Nested (
        session_id UUID,
        view_name String,
        network_type String,
        network_strength Float32
    ),
    _partition_key String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, category, event_id)
TTL timestamp + INTERVAL 3 MONTH;

-- Video Analytics Events
CREATE TABLE IF NOT EXISTS video_events (
    event_id UUID,
    timestamp DateTime64(9),
    platform LowCardinality(String),
    video_id String,
    player_type LowCardinality(String),
    event_name Enum8(
        'start' = 1,
        'pause' = 2,
        'buffer' = 3,
        'quality_change' = 4,
        'error' = 5
    ),
    measurements Nested (
        startup_time Float32,
        buffer_duration Float32,
        bitrate Int32,
        resolution String,
        fps Float32,
        latency Float32
    ),
    quality_metrics Nested (
        video_quality_score Float32,
        buffering_ratio Float32,
        startup_time_score Float32
    ),
    context Nested (
        cdn_provider String,
        player_version String,
        drm_type String
    ),
    _partition_key String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, video_id, event_id)
TTL timestamp + INTERVAL 6 MONTH;

-- Application Metrics
CREATE TABLE IF NOT EXISTS application_metrics (
    metric_id UUID,
    timestamp DateTime64(9),
    service LowCardinality(String),
    environment LowCardinality(String),
    metric_type Enum8(
        'counter' = 1,
        'gauge' = 2,
        'histogram' = 3
    ),
    name String,
    value Float64,
    labels JSON,
    host_info Nested (
        hostname String,
        ip String,
        region String
    ),
    _partition_key String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, service, metric_id)
TTL timestamp + INTERVAL 3 MONTH;

-- Distributed Traces
CREATE TABLE IF NOT EXISTS distributed_traces (
    trace_id UUID,
    span_id UUID,
    parent_span_id Nullable(UUID),
    service LowCardinality(String),
    operation String,
    start_time DateTime64(9),
    end_time DateTime64(9),
    duration_ms Int32,
    status Enum8('success' = 1, 'error' = 2),
    attributes JSON,
    resource Nested (
        service_name String,
        service_version String,
        host_name String
    ),
    _partition_key String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(start_time)
ORDER BY (start_time, trace_id, span_id)
TTL start_time + INTERVAL 1 MONTH;

-- Log Events
CREATE TABLE IF NOT EXISTS log_events (
    log_id UUID,
    timestamp DateTime64(9),
    service LowCardinality(String),
    level Enum8(
        'debug' = 1,
        'info' = 2,
        'warn' = 3,
        'error' = 4,
        'fatal' = 5
    ),
    message String,
    logger_name String,
    thread_name String,
    stack_trace String,
    context JSON,
    metadata JSON,
    _partition_key String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, level, log_id)
TTL timestamp + INTERVAL 2 MONTH;

-- Infrastructure Metrics
CREATE TABLE IF NOT EXISTS infrastructure_metrics (
    metric_id UUID,
    timestamp DateTime64(9),
    resource_type LowCardinality(String),
    resource_id String,
    provider LowCardinality(String),
    region LowCardinality(String),
    measurements Nested (
        cpu_usage Float32,
        memory_usage Float32,
        disk_io Float32,
        network_io Float32
    ),
    cost_data Nested (
        cost_per_hour Float32,
        currency String
    ),
    _partition_key String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, resource_type, metric_id)
TTL timestamp + INTERVAL 3 MONTH; 
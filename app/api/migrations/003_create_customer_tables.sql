-- Customer Organization Table
CREATE TABLE IF NOT EXISTS organizations (
    org_id UUID PRIMARY KEY,
    name String,
    slug String UNIQUE,
    created_at DateTime64(9),
    updated_at DateTime64(9),
    status Enum8(
        'active' = 1,
        'suspended' = 2,
        'deactivated' = 3
    ),
    subscription_tier Enum8(
        'free' = 1,
        'starter' = 2,
        'professional' = 3,
        'enterprise' = 4
    ),
    settings JSON,
    metadata JSON
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (org_id);

-- Customer API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY,
    org_id UUID,
    name String,
    key_hash String,
    scopes Array(String),
    created_at DateTime64(9),
    expires_at Nullable(DateTime64(9)),
    last_used_at Nullable(DateTime64(9)),
    status Enum8(
        'active' = 1,
        'revoked' = 2,
        'expired' = 3
    )
) ENGINE = ReplacingMergeTree(last_used_at)
ORDER BY (org_id, key_id);

-- Customer Data Retention Policies
CREATE TABLE IF NOT EXISTS retention_policies (
    policy_id UUID PRIMARY KEY,
    org_id UUID,
    data_type LowCardinality(String),
    retention_days UInt32,
    archival_enabled Bool DEFAULT false,
    archival_days Nullable(UInt32),
    created_at DateTime64(9),
    updated_at DateTime64(9)
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (org_id, data_type);

-- Customer Usage Metrics
CREATE TABLE IF NOT EXISTS usage_metrics (
    org_id UUID,
    timestamp DateTime64(9),
    metric_type LowCardinality(String),
    value Float64,
    labels Nested (
        key String,
        value String
    )
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (org_id, metric_type, timestamp);

-- Customer Data Sources
CREATE TABLE IF NOT EXISTS data_sources (
    source_id UUID PRIMARY KEY,
    org_id UUID,
    name String,
    type Enum8(
        'web' = 1,
        'mobile' = 2,
        'server' = 3,
        'iot' = 4,
        'custom' = 5
    ),
    config JSON,
    enabled Bool DEFAULT true,
    created_at DateTime64(9),
    updated_at DateTime64(9)
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (org_id, source_id);

-- Add organization_id to all event tables
ALTER TABLE user_interaction_events ADD COLUMN IF NOT EXISTS org_id UUID AFTER event_id;
ALTER TABLE performance_events ADD COLUMN IF NOT EXISTS org_id UUID AFTER event_id;
ALTER TABLE video_events ADD COLUMN IF NOT EXISTS org_id UUID AFTER event_id;
ALTER TABLE application_metrics ADD COLUMN IF NOT EXISTS org_id UUID AFTER metric_id;
ALTER TABLE distributed_traces ADD COLUMN IF NOT EXISTS org_id UUID AFTER trace_id;
ALTER TABLE log_events ADD COLUMN IF NOT EXISTS org_id UUID AFTER log_id;
ALTER TABLE infrastructure_metrics ADD COLUMN IF NOT EXISTS org_id UUID AFTER metric_id;

-- Create materialized views for usage tracking
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_usage
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (org_id, metric_type, date)
AS SELECT
    org_id,
    toDate(timestamp) as date,
    metric_type,
    count() as event_count,
    sum(if(metric_type = 'data_ingestion', JSONLength(properties), 0)) as data_points,
    sum(if(metric_type = 'storage', JSONLength(properties), 0)) as storage_bytes
FROM (
    SELECT org_id, timestamp, 'user_interaction' as metric_type, properties FROM user_interaction_events
    UNION ALL
    SELECT org_id, timestamp, 'performance' as metric_type, NULL FROM performance_events
    UNION ALL
    SELECT org_id, timestamp, 'video' as metric_type, NULL FROM video_events
    UNION ALL
    SELECT org_id, timestamp, 'logs' as metric_type, NULL FROM log_events
)
GROUP BY org_id, date, metric_type; 
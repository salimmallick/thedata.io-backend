export interface TransformationRule {
    name: string;
    description?: string;
    type: string;
    input_table: string;
    output_table: string;
    transformation_sql: string;
    enabled: boolean;
    order: number;
    config: Record<string, any>;
    updated_at?: string;
}

export interface MaterializedView {
    name: string;
    query: string;
    refresh_interval: string;
    status: string;
    last_refresh: string;
}

export interface DataSinkMetrics {
    records_processed: number;
    bytes_processed: number;
    last_latency: number;
    last_error?: string;
}

export interface DataSink {
    name: string;
    type: string;
    status: string;
    config: Record<string, any>;
    metrics?: DataSinkMetrics;
}

export interface RetentionPolicy {
    table_name: string;
    retention_days: number;
    last_cleanup: string;
    rows_deleted: number;
}

export interface PipelineMetrics {
    throughput: number;
    latency: number;
    error_rate: number;
    queue_size: number;
    processing_time: number;
}

export interface PipelineComponent {
    id: string;
    name: string;
    status: 'running' | 'stopped' | 'error';
    health: 'healthy' | 'degraded' | 'unhealthy';
    metrics: PipelineMetrics;
    config: Record<string, any>;
    description?: string;
    version?: string;
    last_updated?: string;
}

export interface PipelineAlert {
    id: string;
    component_id: string;
    severity: 'info' | 'warning' | 'error' | 'critical';
    message: string;
    timestamp: string;
    acknowledged: boolean;
}

export interface DataPipeline {
    components: PipelineComponent[];
    alerts: PipelineAlert[];
    overall_health: 'healthy' | 'degraded' | 'unhealthy';
    metrics: {
        total_throughput: number;
        average_latency: number;
        total_errors: number;
    };
} 
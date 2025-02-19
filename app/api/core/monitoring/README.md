# Monitoring System Documentation

## Overview

This document describes the monitoring system implemented for the data sync API. The system provides comprehensive monitoring, metrics collection, and alerting capabilities to ensure reliable operation and quick problem resolution.

## Components

### 1. Metrics Collection

The monitoring system collects various metrics using Prometheus:

- **Sync Operations**
  - Operation counts by status
  - Duration of sync operations
  - Records processed
  - Error counts and types

- **Recovery Operations**
  - Recovery attempts
  - Success/failure rates
  - Recovery duration
  - Post-recovery error rates

- **Database Operations**
  - Connection pool status
  - Query durations
  - Error rates

- **Health Checks**
  - Component status
  - Response times
  - Error rates

### 2. Monitoring Service

The `MonitoringService` manages metric collection and reporting:

- Automatic startup/shutdown with the application
- Periodic health checks
- Regular metric collection
- Prometheus HTTP server for metrics exposure

### 3. Dashboards

Grafana dashboards are provided for visualization:

- **Data Sync Operations Dashboard**
  - Real-time sync operation monitoring
  - Error rate tracking
  - Duration percentiles
  - Recovery operation status

### 4. Alerting

Alert rules are configured for various scenarios:

- High error rates
- Extended sync durations
- Recovery failures
- System health issues

## Configuration

### Environment Variables

```env
# Prometheus settings
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_PATH=/metrics

# Grafana settings
GRAFANA_ENABLED=true
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=<your-password>

# Alert manager settings
ALERTMANAGER_ENABLED=true
ALERTMANAGER_PORT=9093

# Metric collection settings
METRIC_COLLECTION_INTERVAL=15
METRIC_RETENTION_DAYS=30

# Recovery metrics settings
RECOVERY_METRICS_ENABLED=true

# Health check settings
HEALTH_CHECK_INTERVAL=60
HEALTH_CHECK_TIMEOUT=10
```

## Metrics Reference

### Sync Metrics

- `sync_operations_total`: Counter of sync operations by status
- `sync_duration_seconds`: Histogram of sync operation durations
- `sync_records_processed_total`: Counter of processed records
- `sync_errors_total`: Counter of sync errors by type

### Recovery Metrics

- `sync_recovery_attempts_total`: Counter of recovery attempts
- `sync_recovery_success_total`: Counter of successful recoveries
- `sync_recovery_duration_seconds`: Histogram of recovery durations

### Health Check Metrics

- `health_check_status`: Gauge of component health status
- `health_check_duration_seconds`: Histogram of health check durations

## Alert Rules

### Critical Alerts

1. **High Error Rate**
   ```yaml
   alert: HighSyncErrorRate
   expr: rate(sync_errors_total[5m]) > 0.1
   for: 5m
   ```

2. **Recovery Failure**
   ```yaml
   alert: HighRecoveryFailureRate
   expr: (rate(sync_recovery_attempts_total[5m]) - rate(sync_recovery_success_total[5m])) / rate(sync_recovery_attempts_total[5m]) > 0.5
   for: 5m
   ```

3. **No Successful Syncs**
   ```yaml
   alert: NoSuccessfulSyncs
   expr: absent(rate(sync_operations_total{status="completed"}[30m]) > 0)
   for: 30m
   ```

### Warning Alerts

1. **Long Sync Duration**
   ```yaml
   alert: SyncDurationHigh
   expr: histogram_quantile(0.95, rate(sync_duration_seconds_bucket[5m])) > 300
   for: 5m
   ```

2. **High Recovery Duration**
   ```yaml
   alert: RecoveryDurationHigh
   expr: histogram_quantile(0.95, rate(sync_recovery_duration_seconds_bucket[5m])) > 60
   for: 5m
   ```

## Dashboard Setup

1. Import the provided dashboard JSON files into Grafana:
   - `dashboards/data_sync.json`: Data sync operations dashboard

2. Configure Prometheus as a data source in Grafana:
   - URL: `http://localhost:9090`
   - Access: `Browser`

## Maintenance

### Log Rotation

Metric logs are rotated based on:
- Size: 10MB per file
- Time: 30 days retention
- Maximum files: 5 backup files

### Backup

Regular backups of:
- Prometheus data directory
- Grafana dashboards
- Alert rules configuration

### Health Checks

The monitoring system performs regular health checks on:
- Database connections
- API endpoints
- Recovery system
- Metric collection

## Troubleshooting

### Common Issues

1. **Missing Metrics**
   - Check Prometheus server status
   - Verify metric collection interval
   - Check for collection errors in logs

2. **Alert Storm**
   - Review alert thresholds
   - Check for system-wide issues
   - Verify alert grouping configuration

3. **Dashboard Issues**
   - Verify Prometheus data source
   - Check time range selection
   - Review metric query syntax

### Recovery Procedures

1. **Prometheus Issues**
   ```bash
   # Restart Prometheus
   docker-compose restart prometheus
   
   # Verify metrics endpoint
   curl http://localhost:9090/metrics
   ```

2. **Grafana Issues**
   ```bash
   # Restart Grafana
   docker-compose restart grafana
   
   # Verify dashboard access
   curl http://localhost:3000/api/health
   ```

3. **Alert Manager Issues**
   ```bash
   # Restart Alert Manager
   docker-compose restart alertmanager
   
   # Verify configuration
   curl http://localhost:9093/-/healthy
   ```

## Best Practices

1. **Metric Naming**
   - Use consistent naming conventions
   - Include relevant labels
   - Document metric purpose

2. **Alert Configuration**
   - Set appropriate thresholds
   - Include clear descriptions
   - Configure proper routing

3. **Dashboard Organization**
   - Group related metrics
   - Use consistent time ranges
   - Include documentation links

## Support

For issues or questions:
- Create a ticket in the issue tracker
- Contact the monitoring team
- Review the troubleshooting guide

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Alert Manager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/) 
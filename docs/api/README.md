# theData.io API Documentation

## Overview
theData.io API provides a robust platform for data synchronization, pipeline management, and monitoring. This documentation covers the API endpoints, authentication, monitoring, and deployment procedures.

## Critical Prerequisites Before Starting API Services

### 1. Database Migration System ⚠️
Current Status: Pending
- Need to implement database migration system using Alembic
- Create initial migration scripts for all tables
- Test migration rollback procedures
- Document migration process

### 2. Integration Testing ⚠️
Current Status: Pending
- End-to-end API tests not implemented
- Database failover testing needed
- Monitoring integration tests required
- Recovery procedures need validation

### 3. Security Configuration ⚠️
Current Status: Partially Complete
- Rate limiting implementation needed
- Request validation to be enhanced
- SSL/TLS setup required
- CORS configuration to be finalized

### 4. Monitoring & Recovery
Current Status: ✅ Complete
- Prometheus, Grafana, AlertManager configured
- Metrics collection implemented
- Alert rules defined
- Recovery tracking in place

### 5. Error Handling
Current Status: ✅ Complete
- Centralized error handling implemented
- Retry mechanisms in place
- Circuit breaker patterns implemented
- Error tracking and logging configured

## API Components

### Authentication
- JWT-based authentication
- API key support
- Role-based access control
- Request signing

### Data Sources
Endpoints:
- GET /api/v1/sources
- POST /api/v1/sources
- GET /api/v1/sources/{id}
- PUT /api/v1/sources/{id}
- DELETE /api/v1/sources/{id}
- POST /api/v1/sources/{id}/sync
- GET /api/v1/sources/{id}/metrics

### Pipelines
Endpoints:
- GET /api/v1/pipelines
- POST /api/v1/pipelines
- GET /api/v1/pipelines/{id}
- PUT /api/v1/pipelines/{id}
- DELETE /api/v1/pipelines/{id}
- POST /api/v1/pipelines/{id}/start
- POST /api/v1/pipelines/{id}/stop
- GET /api/v1/pipelines/{id}/logs

## Deployment Instructions

### Environment Setup
Required environment variables:
```env
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key

# Database URLs
POSTGRES_URL=postgresql://user:pass@postgres/db
CLICKHOUSE_URL=clickhouse://clickhouse:9000
QUESTDB_URL=http://questdb:9000
REDIS_URL=redis://redis:6379/0
NATS_URL=nats://nats:4222

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=admin
METRICS_PORT=9090
```

### Docker Deployment
```bash
# Start all services
docker-compose up -d

# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d
```

## Next Steps Before Production

1. Database Migration (Priority: HIGH)
   - Implement Alembic migrations
   - Create initial schema
   - Test migration procedures

2. Integration Testing (Priority: HIGH)
   - Implement end-to-end tests
   - Add database failover tests
   - Test monitoring integration

3. Security (Priority: HIGH)
   - Implement rate limiting
   - Set up SSL/TLS
   - Configure CORS

4. Documentation
   - Add API endpoint details
   - Create deployment guides
   - Document recovery procedures

## Conclusion
While significant progress has been made in refactoring and implementing core functionality, **the API is not yet ready for production deployment**. The following critical items must be completed first:

1. Database migrations must be implemented to ensure data consistency
2. Integration tests must be added to validate system behavior
3. Security measures must be properly configured
4. Documentation must be completed for operations team

Once these items are completed, we can proceed with production deployment.

## Authentication

All API requests require authentication using an API key. Include your API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your_api_key" https://api.thedata.io/v1/health
```

## Rate Limiting

Rate limits are applied based on your subscription tier:

- Free: 100 requests/minute
- Basic: 1,000 requests/minute
- Pro: 10,000 requests/minute
- Enterprise: Custom limits

Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Total requests allowed per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

## Event Ingestion

### Single Event

```bash
curl -X POST https://api.thedata.io/v1/ingest/events \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "page_view",
    "timestamp": "2024-02-12T10:00:00Z",
    "source": "web",
    "user_id": "user_123",
    "properties": {
      "page": "/home",
      "referrer": "google.com"
    }
  }'
```

### Batch Events

```bash
curl -X POST https://api.thedata.io/v1/ingest/events/batch \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "event_type": "page_view",
      "timestamp": "2024-02-12T10:00:00Z",
      "source": "web",
      "user_id": "user_123",
      "properties": {
        "page": "/home"
      }
    },
    {
      "event_type": "button_click",
      "timestamp": "2024-02-12T10:00:01Z",
      "source": "web",
      "user_id": "user_123",
      "properties": {
        "button_id": "signup"
      }
    }
  ]'
```

## Analytics

### Event Analytics

```bash
curl "https://api.thedata.io/v1/analytics/events?start_time=2024-02-12T00:00:00Z&end_time=2024-02-12T23:59:59Z&event_type=page_view&aggregation=count" \
  -H "X-API-Key: your_api_key"
```

### Metric Analytics

```bash
curl "https://api.thedata.io/v1/analytics/metrics?start_time=2024-02-12T00:00:00Z&end_time=2024-02-12T23:59:59Z&metric_name=response_time&aggregation=avg" \
  -H "X-API-Key: your_api_key"
```

### Real-time Analytics

```bash
curl "https://api.thedata.io/v1/analytics/realtime?window=5m&metrics=active_users,page_views" \
  -H "X-API-Key: your_api_key"
```

## Error Handling

The API uses standard HTTP status codes and returns detailed error information:

```json
{
  "code": "validation_error",
  "message": "Invalid event data",
  "details": {
    "field": "timestamp",
    "error": "Invalid datetime format"
  }
}
```

Common status codes:
- 200: Success
- 202: Accepted for processing
- 400: Bad request
- 401: Unauthorized
- 429: Rate limit exceeded
- 500: Server error

## Best Practices

1. **Batch Processing**
   - Use batch endpoints for multiple events
   - Keep batch sizes between 100-1000 items
   - Include retry logic in your client

2. **Rate Limiting**
   - Implement exponential backoff
   - Monitor rate limit headers
   - Consider upgrading tier if consistently hitting limits

3. **Real-time Analytics**
   - Use appropriate time windows
   - Cache results when possible
   - Monitor data freshness

4. **Error Handling**
   - Implement proper error handling
   - Log error details for debugging
   - Set up alerts for error thresholds

## SDKs (Coming Soon)

Official SDKs will be available for:
- JavaScript/TypeScript
- Python
- Java
- Go
- Ruby
- PHP

## Support

For support:
- Email: support@thedata.io
- Documentation: https://docs.thedata.io
- Status: https://status.thedata.io 
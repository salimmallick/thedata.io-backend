# theData.io API Documentation

## Overview

theData.io provides a powerful API for event ingestion, metrics collection, and analytics. This documentation provides detailed information about using the API endpoints.

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
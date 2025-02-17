# Batch Processing API Documentation

## Overview

The Batch Processing API provides endpoints for efficient processing of large datasets through the transformation pipeline. It supports parallel processing, caching, and monitoring capabilities.

## Endpoints

### Process Batch

```http
POST /api/v1/transform/batch
```

Process a batch of data through the transformation pipeline.

#### Request Body

```json
{
  "data": [
    {
      "ts": "2024-01-01T00:00:00Z",
      "amt": "100.50",
      "email": "user@example.com",
      "phone": "555-0123"
    }
  ],
  "batch_size": 100,
  "parallel": true
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| data | array | Array of data items to process |
| batch_size | integer | Optional. Size of each batch (default: 100) |
| parallel | boolean | Optional. Enable parallel processing (default: true) |

#### Response

```json
{
  "status": "success",
  "processed": 1,
  "filtered": 0,
  "duration": 0.5,
  "results": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "amount": 100.50,
      "email": "u***r@example.com",
      "phone": "***-0123"
    }
  ]
}
```

### Get Batch Status

```http
GET /api/v1/transform/batch/{batch_id}
```

Get the status of a batch processing job.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| batch_id | string | ID of the batch job |

#### Response

```json
{
  "batch_id": "batch_123",
  "status": "completed",
  "progress": 100,
  "processed": 1000,
  "filtered": 50,
  "duration": 5.2,
  "started_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:00:05Z"
}
```

### Cancel Batch

```http
POST /api/v1/transform/batch/{batch_id}/cancel
```

Cancel a running batch processing job.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| batch_id | string | ID of the batch job to cancel |

#### Response

```json
{
  "status": "cancelled",
  "message": "Batch processing job cancelled successfully"
}
```

## Error Handling

The API uses standard HTTP status codes and includes detailed error messages:

- 400 Bad Request: Invalid request parameters
- 404 Not Found: Batch job not found
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Processing error

Example error response:

```json
{
  "error": "validation_error",
  "message": "Invalid data format in batch",
  "details": {
    "row": 5,
    "field": "amount",
    "reason": "Invalid number format"
  }
}
```

## Rate Limiting

- Default limit: 1000 requests per minute per API key
- Batch size limit: 10000 items per batch
- Parallel processing limit: 5 concurrent batches per API key

## Monitoring

The following metrics are available in Prometheus/Grafana:

- `batch_processed_total`: Total number of processed items
- `batch_processing_duration_seconds`: Processing duration histogram
- `batch_processing_errors_total`: Total number of processing errors
- `batch_memory_usage_bytes`: Memory usage during batch processing

## Best Practices

1. **Optimal Batch Size**
   - Use batch sizes between 100-1000 items for best performance
   - Adjust based on item complexity and size

2. **Parallel Processing**
   - Enable for large datasets
   - Monitor memory usage and adjust concurrency

3. **Error Handling**
   - Implement retry logic for failed batches
   - Use batch status endpoint to monitor progress

4. **Caching**
   - Similar items in a batch benefit from caching
   - Cache invalidation happens automatically

5. **Monitoring**
   - Monitor processing rates and error rates
   - Set up alerts for abnormal conditions 
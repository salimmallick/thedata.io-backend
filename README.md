# theData.io Platform Backend

This repository contains the backend services for the theData.io platform, a comprehensive data management and analytics solution.

## Status

🟢 **All backend services are up and running and healthy!**

## Architecture

The platform consists of multiple services working together:

- FastAPI-based REST API
- Multiple specialized databases (PostgreSQL, ClickHouse, QuestDB)
- Data pipeline orchestration with Dagster
- Real-time analytics with Materialize
- Message streaming with NATS
- Monitoring stack (Prometheus, Grafana, Jaeger)

For detailed information about each service, please see [SERVICES.md](SERVICES.md).

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend development)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/salimmallick/thedata.io-backend.git
   cd thedata.io-backend
   ```

2. Create and configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configurations
   ```

3. Start the services:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

4. Verify the services:
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   ```

## Service URLs

- API: http://localhost:8000
- Dagster: http://localhost:3002
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686
- Traefik Dashboard: http://localhost:8080

## Development

### API Development

The API service is built with FastAPI and provides:
- RESTful endpoints
- Real-time data processing
- Authentication and authorization
- Rate limiting and caching

### Data Pipeline Development

Dagster pipelines are located in `app/dagster/` and handle:
- Data ingestion
- Transformation
- Quality checks
- Scheduled jobs

### Frontend Development

The admin portal frontend (located in `app/frontend/`) will be developed using:
- React
- TypeScript
- Material-UI

## Monitoring

The platform includes comprehensive monitoring:
- Metrics collection with Prometheus
- Visualization with Grafana
- Distributed tracing with Jaeger
- Log aggregation

## Documentation

- [Services Documentation](SERVICES.md)
- [Database Migration System](docs/api/database/README.md)
- API Documentation: http://localhost:8000/docs
- Swagger UI: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary and confidential. All rights reserved.

## Contact

Salim Mallick - [@salimmallick](https://github.com/salimmallick) 
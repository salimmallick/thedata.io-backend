# theData.io Platform Services

This document provides a comprehensive overview of all services in the theData.io platform.

## Core Services

### 1. API Service (FastAPI)
- **Role**: Main application API service
- **Port**: 8000
- **Key Files**:
  - `app/api/`: Main API code directory
  - `app/api/main.py`: Application entry point
  - `app/api/Dockerfile`: API service container configuration
- **Configuration**: Environment variables in `.env`
- **Dependencies**: PostgreSQL, ClickHouse, QuestDB, NATS, Redis
- **Health Check**: `http://localhost:8000/health`

### 2. PostgreSQL
- **Role**: Primary relational database
- **Port**: 5432
- **Key Files**:
  - `scripts/init_db.py`: Database initialization script
- **Configuration**: 
  - Username: postgres
  - Database: postgres (default), thedata (application)
- **Health Check**: Built-in PostgreSQL health check

### 3. ClickHouse
- **Role**: Analytics and event data storage
- **Ports**: 8123 (HTTP), 9000 (Native)
- **Key Files**:
  - `config/clickhouse/`: Configuration files
  - `config/clickhouse/users.xml`: User configuration
  - `config/clickhouse/config.xml`: Server configuration
- **Configuration**: Default user with no password
- **Health Check**: `http://localhost:8123/ping`

### 4. QuestDB
- **Role**: Time-series database
- **Ports**: 
  - 8812 (PostgreSQL wire)
  - 9000 (REST API)
  - 9009 (ILP)
- **Configuration**: 
  - Admin user credentials in docker-compose.dev.yml
  - Optimized for time-series data
- **Health Check**: Built-in health check

### 5. NATS
- **Role**: Message queue and event streaming
- **Ports**: 
  - 4222 (Client)
  - 8222 (Monitoring)
- **Key Files**:
  - `config/nats/jetstream.conf`: NATS configuration
- **Configuration**:
  - JetStream enabled
  - Authentication token configured
- **Health Check**: `http://localhost:8222/healthz`

## Data Pipeline Services

### 6. Dagster
- **Role**: Data orchestration and pipeline management
- **Port**: 3002
- **Key Files**:
  - `app/dagster/`: Pipeline definitions
  - `Dockerfile.dagster`: Container configuration
  - `config/dagster/`: Configuration files
- **Configuration**:
  - Uses PostgreSQL for run storage
  - Workspace configuration in workspace.yaml
- **Access**: `http://localhost:3002`

### 7. Materialize
- **Role**: Real-time materialized views
- **Port**: 6875
- **Configuration**:
  - Memory limit: 4GB
  - Single worker configuration
- **Health Check**: PostgreSQL-compatible health check

## Monitoring & Observability

### 8. Prometheus
- **Role**: Metrics collection and storage
- **Port**: 9090
- **Key Files**:
  - `prometheus/prometheus.yml`: Prometheus configuration
- **Configuration**: Scrapes metrics from all services
- **Access**: `http://localhost:9090`

### 9. Grafana
- **Role**: Metrics visualization and dashboards
- **Port**: 3000
- **Key Files**:
  - `config/grafana/provisioning/`: Dashboard configurations
- **Configuration**:
  - Default admin credentials
  - Pre-configured data sources
- **Access**: `http://localhost:3000`

### 10. Jaeger
- **Role**: Distributed tracing
- **Ports**:
  - 6831 (UDP)
  - 16686 (UI)
- **Configuration**: All-in-one deployment for development
- **Access**: `http://localhost:16686`

## Infrastructure Services

### 11. Redis
- **Role**: Caching and rate limiting
- **Port**: 6379
- **Configuration**: Default configuration
- **Health Check**: Redis PING command

### 12. Traefik
- **Role**: Reverse proxy and load balancer
- **Ports**:
  - 80 (HTTP)
  - 8080 (Dashboard)
  - 8082 (Metrics)
- **Key Files**:
  - `config/traefik/`: Configuration files
- **Configuration**:
  - Automatic service discovery
  - Docker provider enabled
- **Access**: `http://traefik.localhost`

## Frontend Application

### 13. Admin Portal (React)
- **Location**: `app/frontend/`
- **Key Files**:
  - `app/frontend/src/`: Application source code
  - `app/frontend/package.json`: Dependencies
  - `app/frontend/tsconfig.json`: TypeScript configuration
- **Status**: To be started after backend services setup
- **Technology Stack**:
  - React
  - TypeScript
  - Material-UI

## Network Configuration

The platform uses two Docker networks:
1. `backend`: Internal service communication
2. `app_net`: External access and load balancing

## Data Flow

1. Client requests come through Traefik
2. API service processes requests
3. Data is stored in appropriate databases:
   - PostgreSQL: Relational data
   - ClickHouse: Analytics
   - QuestDB: Time-series data
4. Dagster orchestrates data pipelines
5. Materialize maintains real-time views
6. NATS handles event streaming
7. Monitoring stack tracks performance:
   - Prometheus collects metrics
   - Grafana visualizes data
   - Jaeger traces requests

## Health Status

All services are currently running and healthy. Each service has appropriate health checks and monitoring configured.

## Volume Management

Persistent data is stored in Docker volumes:
- `postgres_data`: PostgreSQL data
- `clickhouse_data`: ClickHouse data
- `questdb_data`: QuestDB data
- `grafana_data`: Grafana configurations
- `prometheus_data`: Prometheus data
- `redis_data`: Redis data
- `materialize_data`: Materialize data
- `nats_data`: NATS streams 
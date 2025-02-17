#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting theData.io Platform Development Environment${NC}"

# Start Docker services
echo -e "${YELLOW}Starting Docker services...${NC}"
docker-compose -f docker-compose.dev.yml up -d

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Start Dagster development server
echo -e "${YELLOW}Starting Dagster development server...${NC}"
dagster dev -f app/dagster/repository.py &

# Start frontend development server
echo -e "${YELLOW}Starting frontend development server...${NC}"
cd app/frontend && npm install && npm start &

echo -e "${GREEN}Development environment is starting up!${NC}"
echo -e "Access points:"
echo -e "- Frontend: http://localhost:3000"
echo -e "- API Docs: http://localhost:8000/docs"
echo -e "- Dagster UI: http://localhost:3001"
echo -e "- Grafana: http://localhost:3002"

# Keep script running
wait 
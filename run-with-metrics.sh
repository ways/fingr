#!/bin/bash
set -e

echo "Starting fingr with Prometheus and Grafana..."
echo ""
echo "Services will be available at:"
echo "  - Fingr (finger):    finger oslo@localhost"
echo "  - Prometheus:        http://localhost:9091"
echo "  - Grafana:           http://localhost:3000 (admin/admin)"
echo ""

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Check if using docker or podman
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v podman-compose &> /dev/null; then
    COMPOSE_CMD="podman-compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "Error: Neither 'docker compose', 'podman-compose', nor 'docker-compose' found"
    exit 1
fi

echo "Using: $COMPOSE_CMD"
echo ""

# Run compose
$COMPOSE_CMD up "$@"

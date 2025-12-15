# Quick Start Guide

## Running with Metrics (Recommended)

Simply run:
```bash
./run-with-metrics.sh
```

This will automatically detect whether you have Docker or Podman and start all services.

## What Gets Started

- **fingr** - Weather service on port 7979
- **redis** - Cache backend
- **prometheus** - Metrics collection on port 9091
- **grafana** - Visualization on port 3000

## Accessing Services

### Test fingr
```bash
finger oslo@localhost
finger "new york"@localhost
finger 59.9,10.7@localhost  # coordinates
```

### View Metrics Dashboard
1. Open http://localhost:3000 in your browser
2. Login with username: `admin`, password: `admin`
3. Navigate to "Dashboards" → "Fingr Weather Service"

### Query Raw Metrics
- Prometheus UI: http://localhost:9091
- Metrics endpoint: http://localhost:9090/metrics (fingr exports)

## Stopping Services

Press `Ctrl+C` or run:
```bash
podman-compose down
```

To also remove volumes:
```bash
podman-compose down -v
```

## Development

The branch `feature/prometheus-metrics` contains all the changes.

See `PROMETHEUS_METRICS.md` for detailed documentation on metrics and queries.

# Prometheus Metrics & Grafana Dashboard

This document describes the Prometheus metrics added to fingr and how to use the Grafana dashboard.

## Quick Start

```bash
# Start all services (fingr, redis, prometheus, grafana)
podman-compose up

# Access services:
# - Fingr: finger oslo@localhost (port 7979)
# - Prometheus: http://localhost:9091
# - Grafana: http://localhost:3000 (admin/admin)
```

## Metrics Collected

### Request Metrics
- `fingr_requests_total` - Total requests by status (success, help, blacklisted, etc.)
- `fingr_request_duration_seconds` - End-to-end request processing time

### API Performance
- `fingr_api_requests_total` - Total met.no API requests by status
- `fingr_api_request_duration_seconds` - Met.no API response time

### Location Cache
- `fingr_location_cache_operations_total` - Cache operations (hit, miss, direct_coordinates)

### Weather Data
- `fingr_weather_data_freshness_total` - Weather data status (updated, cached)

### Geographic Distribution
- `fingr_location_requests_total` - Requests by location with lat/lon buckets and address

### Processing Breakdown
- `fingr_location_resolution_duration_seconds` - Time spent resolving location
- `fingr_weather_fetch_duration_seconds` - Time spent fetching weather data
- `fingr_formatting_duration_seconds` - Time spent formatting response

## Grafana Dashboard

The pre-configured dashboard includes:

1. **Request Rate by Status** - Line chart showing request rates over time
2. **Request Duration** - p50 and p95 latency percentiles
3. **Met.no API Performance** - Upstream API latency tracking
4. **Location Cache Operations** - Pie chart of cache hits vs misses
5. **Weather Data Freshness** - Pie chart of updated vs cached data
6. **Top 10 Locations** - Table of most requested locations
7. **Geographic Distribution** - Map showing where requests are coming from
8. **Processing Time Breakdown** - Stacked view of processing stages

## Example Queries

### Top 5 locations by request count
```promql
topk(5, sum by(address) (rate(fingr_location_requests_total[5m])))
```

### Cache hit ratio
```promql
sum(rate(fingr_location_cache_operations_total{operation="hit"}[5m])) 
/ 
sum(rate(fingr_location_cache_operations_total[5m]))
```

### Average API response time
```promql
rate(fingr_api_request_duration_seconds_sum[5m]) 
/ 
rate(fingr_api_request_duration_seconds_count[5m])
```

## Architecture

- Fingr exposes metrics on port 9090
- Prometheus scrapes metrics every 15s
- Grafana queries Prometheus for visualization
- All services run in Docker Compose network

## Geographic Bucketing

Coordinates are bucketed into 5-degree increments to:
- Reduce cardinality in metrics
- Group nearby requests together
- Enable meaningful geographic visualization

For example, Oslo (59.9, 10.7) → bucket (55.0, 10.0)

## Troubleshooting

### Using Podman instead of Docker

If you're using podman, use `podman-compose` instead:

```bash
podman-compose up
```

### Permission/Mount Issues

The compose file includes `:z` flags for SELinux compatibility. If you still get mount errors:

1. Make sure you're running from the project root directory:
   ```bash
   cd /home/larsfp/workdir/fingr
   podman-compose up
   ```

2. Check that the config directories exist:
   ```bash
   ls -la etc/prometheus/
   ls -la etc/grafana/provisioning/
   ```

3. If using rootless podman, ensure proper permissions:
   ```bash
   chmod -R 755 etc/
   ```

### Container Not Starting

Check logs for specific services:
```bash
podman-compose logs fingr
podman-compose logs prometheus
podman-compose logs grafana
```

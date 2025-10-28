# Troubleshooting Fingr Metrics

## Issue 1: Location Cache Hit Rate shows 100% for new locations

### Expected Behavior:
- First lookup of "oslo": Cache miss (0% hit rate initially)
- Second lookup of "oslo": Cache hit (50% hit rate) 
- Third lookup of "oslo": Cache hit (67% hit rate)
- And so on...

### To Verify:
1. Start fresh: `docker compose down && docker compose up`
2. Check metrics: `curl http://localhost:8000/metrics | grep fingr_location_cache_total`
3. Make request: `echo oslo | nc localhost 7979`
4. Check metrics again - should see `fingr_location_cache_total{cached="False"}` increment
5. Make same request: `echo oslo | nc localhost 7979` 
6. Check metrics - should see `fingr_location_cache_total{cached="True"}` increment

### Possible Causes:
- **Prometheus scrape timing**: If Prometheus hasn't scraped since the last request, Grafana won't see new data
- **Grafana query range**: Check if the `[5m]` range in the query has any data
- **Counter reset**: If fingr restarts, counters reset to 0

### Debug Steps:
```bash
# 1. Check raw metrics
curl http://localhost:8000/metrics | grep location_cache_total

# 2. Check Prometheus is scraping
# Visit http://localhost:9090/targets
# fingr:8000 should show as "UP"

# 3. Query in Prometheus directly
# http://localhost:9090/graph
# Query: fingr_location_cache_total
# Should see both cached="True" and cached="False"

# 4. Calculate rate manually
# Query: rate(fingr_location_cache_total[5m])
# Should show non-zero rates for recent activity
```

## Issue 2: Map shows only 1 hit per location

### Expected Behavior:
- First request for "oslo": Counter = 1
- Second request for "oslo": Counter = 2
- Third request for "oslo": Counter = 3
- Map marker size should increase with counter value

### To Verify:
1. Check raw counter: `curl http://localhost:8000/metrics | grep fingr_location_requests`
2. You should see something like:
   ```
   fingr_location_requests{location_name="Oslo, Norway",latitude="59.9133",longitude="10.7461"} 3
   ```
   The number at the end should increment with each request

### Possible Causes:
- **Service restart**: Counters reset when fingr restarts
- **Different location strings**: "oslo", "Oslo", "OSLO" might create different metric series
- **Coordinate rounding**: Same location with slightly different coordinates creates different series
- **Prometheus not persisting**: Check if Prometheus volume is mounted correctly

### Debug Steps:
```bash
# 1. Make multiple requests for same location
for i in {1..5}; do echo oslo | nc localhost 7979; sleep 1; done

# 2. Check counter value immediately
curl http://localhost:8000/metrics | grep -A 5 fingr_location_requests | grep Oslo

# 3. Check if multiple series exist for same location
curl http://localhost:8000/metrics | grep fingr_location_requests | grep -i oslo

# 4. Verify Grafana query
# In Grafana, check the query is: fingr_location_requests
# With format: table
# And instant: true
```

## Common Issues

### Container Restarts
If the fingr container keeps restarting, counters will reset:
```bash
docker compose logs fingr | tail -20
```

### Prometheus Not Scraping
Check Prometheus targets:
```bash
curl http://localhost:9090/api/v1/targets | jq
```

### Redis Not Working
Check if location cache is actually working:
```bash
docker compose exec redis redis-cli KEYS "*oslo*"
```

### Time Series Cardinality
Too many unique label combinations can cause issues:
```bash
curl http://localhost:8000/metrics | grep fingr_location_requests | wc -l
```
If this number is very large (>1000), there might be cardinality issues.

## Manual Test Procedure

Run this step-by-step test:

```bash
# 1. Start fresh
docker compose down -v
docker compose up -d

# Wait for services to be ready
sleep 10

# 2. Check initial state
echo "=== Initial Metrics ===" 
curl -s http://localhost:8000/metrics | grep -E "(location_cache_total|location_requests)"

# 3. First request (should be cache miss)
echo "=== First Request: oslo ===" 
echo oslo | nc localhost 7979 > /dev/null
sleep 2
curl -s http://localhost:8000/metrics | grep location_cache_total

# 4. Second request (should be cache hit)
echo "=== Second Request: oslo ===" 
echo oslo | nc localhost 7979 > /dev/null
sleep 2
curl -s http://localhost:8000/metrics | grep location_cache_total

# 5. Check map counter
echo "=== Map Counter ===" 
curl -s http://localhost:8000/metrics | grep fingr_location_requests | grep -i oslo

# Expected output:
# fingr_location_cache_total{cached="False"} 1.0
# fingr_location_cache_total{cached="True"} 1.0
# fingr_location_requests{location_name="Oslo, Norway",...} 2.0
```

## Still Not Working?

Run the included test script:
```bash
python3 test_metrics.py
```

Check the logs:
```bash
docker compose logs fingr | grep -E "(cache|location)"
```

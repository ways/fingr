# Docker Setup Instructions

## The Problem You Encountered

The error:
```
error while creating mount source path '/home/larsfp/kiagent/fingr/etc/prometheus': 
mkdir /home/larsfp/kiagent: file exists
```

This happens because Docker is resolving the relative path incorrectly. The compose file now uses `${PWD}` to fix this.

## Solution

### Step 1: Navigate to the project directory

**THIS IS CRITICAL** - You MUST be in the fingr directory:

```bash
cd /home/larsfp/workdir/fingr
```

Verify you're in the right place:
```bash
pwd
# Should output: /home/larsfp/workdir/fingr

ls etc/prometheus/prometheus.yml
# Should output: etc/prometheus/prometheus.yml
```

### Step 2: Run Docker Compose

```bash
docker compose up
```

Or use the helper script which validates your location:
```bash
./run-with-metrics.sh
```

## Why This Happens

The compose file uses `${PWD}` to create absolute paths:
- `${PWD}/etc/prometheus` becomes `/home/larsfp/workdir/fingr/etc/prometheus`

If you run from a different directory, `${PWD}` will point to that directory instead, causing the mount to fail.

## Verification

Before running, verify your environment:
```bash
echo $PWD
# Must show /home/larsfp/workdir/fingr (or your actual fingr path)

ls -la etc/prometheus/prometheus.yml
# Should show the file exists

docker compose config | grep -A 2 "prometheus:"
# Should show the volumes with correct absolute paths
```

## If It Still Doesn't Work

1. Check for stale containers/volumes:
   ```bash
   docker compose down -v
   ```

2. Verify file permissions:
   ```bash
   ls -la etc/
   # Directories should be readable (755 or similar)
   ```

3. Check Docker context (if using multiple Docker hosts):
   ```bash
   docker context ls
   ```

4. View the actual error:
   ```bash
   docker compose up 2>&1 | tee error.log
   ```

## What Gets Started

- **redis** - Cache backend (internal only)
- **fingr** - Weather service (ports 7979, 9090)
- **prometheus** - Metrics collector (port 9091)
- **grafana** - Dashboard (port 3000, admin/admin)

## Testing

Once running:
```bash
# Test fingr
finger oslo@localhost

# View metrics
curl http://localhost:9090/metrics

# Open Grafana
open http://localhost:3000  # Login: admin/admin
```

## ✅ CONFIRMED WORKING WITH PODMAN

Tested and verified on 2025-12-15:

### Test Results

```bash
cd /home/larsfp/workdir/fingr
podman-compose up -d
```

✅ **All containers started successfully:**
- redis: Up and healthy
- fingr: Up on ports 7979 and 9090
- prometheus: Up on port 9091 - **Mounts working correctly!**
- grafana: Up on port 3000 - **Mounts working correctly!**

✅ **Volume mounts verified:**
- `/home/larsfp/workdir/fingr/etc/prometheus` → Container config loaded
- `/home/larsfp/workdir/fingr/etc/grafana/provisioning` → Dashboard provisioned

✅ **Services responding:**
- Prometheus: http://localhost:9091 (healthy)
- Grafana: http://localhost:3000 (version 12.3.0)

### Key Changes for Podman Compatibility

1. **Use `${PWD}` for absolute paths** - Resolves mount path correctly
2. **Fully qualified image names** - Required for podman:
   - `docker.io/prom/prometheus:latest`
   - `docker.io/grafana/grafana:latest`

### For Docker Users

Docker should also work with these same settings. The `${PWD}` variable and fully qualified image names are compatible with both Docker and Podman.

Just make sure you run from the project directory:
```bash
cd /path/to/fingr
docker compose up
```

#!/usr/bin/env python3
"""Test script to verify metrics are working correctly."""

import time
import requests

print("=== Testing Fingr Metrics ===\n")

# Function to get metrics
def get_metrics():
    try:
        response = requests.get("http://localhost:8000/metrics", timeout=5)
        return response.text
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return ""

# Function to parse metric value
def get_metric_value(metrics_text, metric_name, labels=None):
    """Extract metric value from Prometheus metrics output."""
    for line in metrics_text.split("\n"):
        if line.startswith("#"):
            continue
        if metric_name in line:
            if labels:
                # Check if all labels match
                if all(f'{k}="{v}"' in line for k, v in labels.items()):
                    try:
                        value = float(line.split()[-1])
                        return value
                    except:
                        pass
            elif "{" not in line:  # No labels in metric
                try:
                    value = float(line.split()[-1])
                    return value
                except:
                    pass
    return None

# Test 1: Check initial metrics
print("1. Fetching initial metrics...")
metrics = get_metrics()
if metrics:
    cache_true = get_metric_value(metrics, "fingr_location_cache_total", {"cached": "True"})
    cache_false = get_metric_value(metrics, "fingr_location_cache_total", {"cached": "False"})
    print(f"   Location cache hits (True): {cache_true}")
    print(f"   Location cache misses (False): {cache_false}")
    
    # Check location requests
    print(f"\n   Location request counters:")
    for line in metrics.split("\n"):
        if "fingr_location_requests{" in line and not line.startswith("#"):
            print(f"   {line}")
    
else:
    print("   ⚠️  Could not fetch metrics - is fingr running?")
    exit(1)

print("\n2. Instructions:")
print("   Run these commands in another terminal:")
print("   finger oslo@localhost")
print("   finger oslo@localhost")
print("   finger oslo@localhost")
print("   finger tokyo@localhost")
print("   finger london@localhost")
print("\n   Then run this script again to see the differences!")

print("\n3. Check Grafana:")
print("   http://localhost:3000")
print("   - Dashboard: 'Fingr Metrics' -> Check cache hit rate gauges")
print("   - Dashboard: 'Fingr Location Map' -> Check if markers accumulate")

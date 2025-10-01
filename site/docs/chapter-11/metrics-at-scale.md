# Metrics at Scale: Observing the Observable

## Introduction: The Aggregation Problem

Your system serves 10,000 requests per second. Each request generates metrics:

- Latency: 45ms
- Status code: 200
- User ID: user_12345
- Region: us-east-1
- Service: checkout-service
- Instance: i-0a1b2c3d4e5f6g7h8

If you store every data point:

- **10,000 req/s × 6 metrics × 8 bytes per metric = 480KB/s**
- **480KB/s × 86,400 seconds/day = 40GB/day**
- **40GB/day × 365 days = 14.6TB/year**

And that's just one service. At 100 services, you're storing **1.46PB/year** of raw metrics data.

**The insight**: You can't store every data point. You must **aggregate**. But aggregation loses information. The art of metrics at scale is choosing **what to keep** and **what to discard** while preserving the ability to answer critical questions.

This is the **cardinality problem**: the explosion of unique metric combinations that makes metrics economically infeasible without careful design.

### Why Metrics Matter

Metrics are the **health signals** of your system:

- **Latency**: Is the system fast enough?
- **Error rate**: Is the system working?
- **Throughput**: Is the system handling load?
- **Saturation**: Is the system about to fall over?

Unlike traces (which show individual requests) and logs (which show individual events), metrics show **aggregate behavior over time**. They answer questions like:

- "What is the p95 latency right now?" (current health)
- "Is error rate increasing?" (trending)
- "Did our deployment improve latency?" (comparison)
- "Should we alert on-call?" (thresholds)

### The Three Metric Types

**1. Counter**: Monotonically increasing value (total requests, total errors)

```python
requests_total.inc()  # 1, 2, 3, 4, 5, ...
```

**2. Gauge**: Point-in-time measurement (CPU usage, memory usage, queue depth)

```python
cpu_usage.set(0.75)  # 0.75 (current value, can go up or down)
```

**3. Histogram**: Distribution of values (latency, request size)

```python
request_latency.observe(0.045)  # Records 45ms, computes percentiles
```

**The core tension**: Counters and gauges are cheap (1 number per metric). Histograms are expensive (store full distribution → many numbers).

## Part 1: Time-Series Databases — Purpose-Built Storage

### What Makes Time-Series Data Special?

Time-series data has unique characteristics:

- **Append-only**: Data is always added, rarely updated (immutable)
- **Time-ordered**: Data arrives in chronological order
- **High write volume**: Millions of data points per second
- **Low update volume**: Once written, data is never modified
- **Range queries**: "Give me data from 10:00 to 11:00" (not "give me data where user_id=123")
- **Aggregations**: "What is the average over the last hour?" (not "show me every data point")

**Traditional databases** (PostgreSQL, MySQL) are optimized for:

- Random reads and writes
- Updates and deletes
- Complex joins
- Low write volume, high query complexity

**Time-series databases** (Prometheus, InfluxDB, TimescaleDB) are optimized for:

- Sequential writes (append-only)
- No updates or deletes
- Time-range queries
- Aggregations (mean, sum, percentiles)
- Compression (10× - 100× better than general-purpose databases)

### Prometheus: The Metrics Standard

**Prometheus** is the de facto standard for metrics in cloud-native systems. It's a CNCF graduated project (same status as Kubernetes) and powers metrics for thousands of companies.

**Architecture**:

```
[Application]
     │
     ├─ Exposes metrics endpoint: /metrics
     │
     ↓
[Prometheus Server]
     │
     ├─ Scrapes metrics every 15s (pull-based)
     ├─ Stores in local TSDB (time-series database)
     ├─ Evaluates alert rules
     ├─ Provides query API (PromQL)
     │
     ↓
[Grafana] (visualization)
[Alertmanager] (alerts)
```

### Instrumenting Code with Prometheus

**Python example**:

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Define metrics
requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'http_active_connections',
    'Number of active connections'
)

def handle_request(method: str, endpoint: str):
    active_connections.inc()  # Increment gauge

    start = time.time()
    try:
        # Process request
        result = process_request(endpoint)
        status = 200
        return result
    except Exception as e:
        status = 500
        raise
    finally:
        # Record latency
        duration = time.time() - start
        request_duration.labels(method=method, endpoint=endpoint).observe(duration)

        # Increment counter
        requests_total.labels(method=method, endpoint=endpoint, status=status).inc()

        # Decrement gauge
        active_connections.dec()

# Start metrics server (exposes /metrics endpoint on port 8000)
start_http_server(8000)
```

**Metrics exposed** (at `http://localhost:8000/metrics`):

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/checkout",status="200"} 1523
http_requests_total{method="GET",endpoint="/checkout",status="500"} 12
http_requests_total{method="POST",endpoint="/api/orders",status="200"} 8934

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/checkout",le="0.01"} 234
http_request_duration_seconds_bucket{method="GET",endpoint="/checkout",le="0.05"} 1203
http_request_duration_seconds_bucket{method="GET",endpoint="/checkout",le="0.1"} 1487
http_request_duration_seconds_bucket{method="GET",endpoint="/checkout",le="0.5"} 1520
http_request_duration_seconds_bucket{method="GET",endpoint="/checkout",le="1.0"} 1523
http_request_duration_seconds_bucket{method="GET",endpoint="/checkout",le="+Inf"} 1523
http_request_duration_seconds_sum{method="GET",endpoint="/checkout"} 68.3
http_request_duration_seconds_count{method="GET",endpoint="/checkout"} 1523

# HELP http_active_connections Number of active connections
# TYPE http_active_connections gauge
http_active_connections 42
```

### Prometheus Query Language (PromQL)

**Basic queries**:

```promql
# Current request rate (requests per second)
rate(http_requests_total[5m])

# Error rate (percentage)
rate(http_requests_total{status="500"}[5m])
  /
rate(http_requests_total[5m]) * 100

# p95 latency (95th percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# p99 latency
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Total requests in the last hour
sum(increase(http_requests_total[1h]))

# Requests per endpoint
sum by (endpoint) (rate(http_requests_total[5m]))
```

**Advanced queries**:

```promql
# Requests per second, averaged over 5 minutes, by region
sum by (region) (rate(http_requests_total[5m]))

# Latency comparison: this week vs last week
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
  /
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m] offset 7d))

# Apdex score (Application Performance Index)
# Counts requests: <100ms = satisfied, 100-400ms = tolerable, >400ms = frustrated
(
  sum(rate(http_request_duration_seconds_bucket{le="0.1"}[5m]))
  + 0.5 * sum(rate(http_request_duration_seconds_bucket{le="0.4"}[5m]))
)
/
sum(rate(http_request_duration_seconds_count[5m]))
```

### The Cardinality Explosion Problem

**Cardinality**: The number of unique combinations of label values.

**Example**:

```python
requests_total = Counter('http_requests_total', 'Total requests',
                         ['method', 'endpoint', 'status', 'user_id', 'region'])
```

**Cardinality calculation**:

- Methods: 5 (GET, POST, PUT, DELETE, PATCH)
- Endpoints: 100 (different API routes)
- Status codes: 10 (200, 201, 400, 401, 403, 404, 500, 502, 503, 504)
- User IDs: 1,000,000 (unique users)
- Regions: 10 (us-east-1, us-west-1, eu-west-1, ...)

**Total cardinality**: 5 × 100 × 10 × 1,000,000 × 10 = **50 billion unique time series**

**Storage cost**:

- Each time series: ~3KB (metadata + samples over 15 days)
- Total storage: 50 billion × 3KB = **150TB**

**Problem**: Prometheus will run out of memory and disk space. Queries will time out.

**Solution**: **Never use high-cardinality labels** (user IDs, request IDs, email addresses).

**Correct approach**:

```python
# Bad: user_id as label (millions of unique users)
requests_total.labels(method="GET", endpoint="/checkout", user_id="user_12345").inc()

# Good: user_id in logs/traces, not metrics
requests_total.labels(method="GET", endpoint="/checkout").inc()
# Log the user_id separately for debugging
logger.info("Request completed", extra={"user_id": "user_12345"})
```

**Rule of thumb**: Keep total cardinality under **10,000 unique time series per metric**. If cardinality exceeds this, redesign your labels.

## Part 2: The RED and USE Methods — What to Measure

### The RED Method (for Services)

**RED** stands for **Rate, Errors, Duration**. This method focuses on **user-facing metrics** (requests served).

**1. Rate**: Requests per second

```promql
rate(http_requests_total[5m])
```

**Why it matters**: Measures traffic load. Helps detect anomalies (sudden spike or drop).

**2. Errors**: Error rate (failed requests per second)

```promql
rate(http_requests_total{status=~"5.."}[5m])
```

**Why it matters**: Measures reliability. Errors directly impact users.

**3. Duration**: Latency (response time)

```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Why it matters**: Measures performance. Slow requests degrade user experience.

**Example dashboard**:

```
┌─────────────────────────────────────────┐
│ Checkout Service - RED Metrics          │
├─────────────────────────────────────────┤
│ Rate:       1,234 req/s                 │
│ Error Rate: 0.5% (6 errors/s)           │
│ P95 Latency: 234ms                      │
│ P99 Latency: 567ms                      │
└─────────────────────────────────────────┘
```

### The USE Method (for Resources)

**USE** stands for **Utilization, Saturation, Errors**. This method focuses on **infrastructure metrics** (CPU, memory, disk, network).

**1. Utilization**: Percentage of resource used

```promql
# CPU utilization
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory utilization
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

**Why it matters**: Shows how much capacity is consumed. Helps with capacity planning.

**2. Saturation**: Degree of queuing (waiting for resource)

```promql
# Disk I/O wait time
rate(node_disk_io_time_seconds_total[5m])

# CPU load average (processes waiting for CPU)
node_load1
```

**Why it matters**: Utilization can be 80%, but if there's no queuing, the system is fine. Saturation indicates the resource is a bottleneck.

**3. Errors**: Error count (hardware errors, failed operations)

```promql
# Disk read errors
rate(node_disk_read_errors_total[5m])

# Network errors
rate(node_network_receive_errs_total[5m])
```

**Why it matters**: Hardware failures manifest as errors (disk failures, packet loss).

**Example dashboard**:

```
┌─────────────────────────────────────────┐
│ Server i-0a1b2c3d4e5 - USE Metrics      │
├─────────────────────────────────────────┤
│ CPU:                                    │
│   Utilization: 65%                      │
│   Saturation (load): 2.3 (4 cores)     │
│   Errors: 0                             │
│                                         │
│ Memory:                                 │
│   Utilization: 72%                      │
│   Saturation (swap): 0 bytes            │
│   Errors: 0                             │
│                                         │
│ Disk:                                   │
│   Utilization: 48%                      │
│   Saturation (I/O wait): 5%             │
│   Errors: 0                             │
└─────────────────────────────────────────┘
```

### Combining RED and USE

**RED** tells you if the **application** is healthy. **USE** tells you if the **infrastructure** is healthy.

**Example correlation**:

- RED: Latency p95 increased from 100ms to 500ms
- USE: Disk I/O saturation increased from 10% to 90%
- **Root cause**: Application is waiting on disk (database queries slow due to disk bottleneck)

**Action**: Increase disk IOPS (move to SSD, provision faster storage) or optimize queries (add indexes, cache).

## Part 3: Aggregation Strategies — Keeping the Signal, Discarding the Noise

### The Fundamental Trade-Off

**Raw data**: Store every data point → high fidelity, expensive
**Aggregated data**: Store summaries → low cost, lose detail

**The question**: Which aggregations preserve the information you need?

### Aggregation Dimension 1: Time

**Challenge**: You collect metrics every second, but you can't store every second forever.

**Solution**: **Downsampling** — reduce resolution as data ages.

**Example retention policy**:

```
Last 1 hour:   1-second resolution (3,600 samples)
Last 6 hours:  10-second resolution (2,160 samples)
Last 1 day:    1-minute resolution (1,440 samples)
Last 7 days:   5-minute resolution (2,016 samples)
Last 30 days:  1-hour resolution (720 samples)
Older:         Delete (or archive to cold storage)
```

**Implementation in Prometheus**:

```yaml
# prometheus.yml
storage:
  tsdb:
    retention.time: 15d  # Keep raw data for 15 days

# Downsample with recording rules
groups:
  - name: downsample
    interval: 5m
    rules:
      # Store 5-minute averages
      - record: http_requests:rate5m
        expr: rate(http_requests_total[5m])

      # Store 5-minute p95 latency
      - record: http_request_duration:p95:5m
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Trade-off**: You can no longer zoom in to 1-second resolution after 1 hour, but you reduce storage by 90%.

### Aggregation Dimension 2: Labels

**Challenge**: You have 10 regions, 100 endpoints, 5 status codes. Do you need all combinations?

**Solution**: **Aggregation rules** — pre-compute common queries.

**Example**:

```yaml
# Store per-endpoint latency (high cardinality)
http_request_duration_seconds{endpoint="/checkout"} 0.045
http_request_duration_seconds{endpoint="/api/orders"} 0.032
# ... 100 endpoints

# Pre-aggregate: overall p95 latency (low cardinality)
- record: http_request_duration:p95:overall
  expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])))

# Pre-aggregate: p95 latency by region (medium cardinality)
- record: http_request_duration:p95:by_region
  expr: histogram_quantile(0.95, sum by (region) (rate(http_request_duration_seconds_bucket[5m])))
```

**Trade-off**: You can no longer query per-endpoint latency after the raw data expires, but you reduce query load by 90%.

### Aggregation Dimension 3: Percentiles

**Challenge**: Histograms store buckets (e.g., <10ms, <50ms, <100ms, <500ms). How do you aggregate percentiles across multiple instances?

**Problem**: **You cannot average percentiles**.

```
Instance 1 p95: 100ms
Instance 2 p95: 200ms

Average p95: ??? (NOT 150ms!)
```

**Reason**: p95 is not a linear metric. The correct aggregate p95 depends on the **full distribution** across both instances.

**Solution**: Aggregate **histogram buckets**, then compute percentile.

```promql
# Wrong: average the p95 from each instance
avg(histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])))

# Correct: aggregate buckets, then compute p95
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

**Why this works**: Summing histogram buckets preserves the distribution, allowing accurate percentile calculation.

### Real-World Example: Shopify's Aggregation Strategy

**Scale**:

- 1M+ merchants
- 100+ services
- 100B+ metrics per day

**Challenge**: Storing 100B raw data points per day = 3PB/year (at 10 bytes per data point).

**Solution**: Multi-tier aggregation

**Tier 1 (Real-time, high resolution)**:

- **Retention**: 1 hour
- **Resolution**: 1 second
- **Storage**: 360GB per hour (3.6TB/day)
- **Use case**: Live debugging, incident response

**Tier 2 (Short-term, medium resolution)**:

- **Retention**: 7 days
- **Resolution**: 1 minute
- **Storage**: 60GB per day (420GB/week)
- **Use case**: Post-incident analysis, weekly reviews

**Tier 3 (Long-term, low resolution)**:

- **Retention**: 1 year
- **Resolution**: 1 hour
- **Storage**: 2.5GB per day (900GB/year)
- **Use case**: Capacity planning, trend analysis

**Total storage**: 3.6TB (Tier 1) + 420GB (Tier 2) + 900GB (Tier 3) = **5TB** (vs 3PB raw)

**Savings**: 99.8% reduction in storage cost.

## Part 4: Alert Fatigue — From Symptom Alerts to Invariant Alerts

### The Alert Fatigue Problem

**Scenario**: Your team gets 50 alerts per day. 45 are false positives (system recovered before human intervention). 5 are real issues.

**Result**: **Alert fatigue** — on-call engineers ignore alerts, assuming they're false positives. Real issues go unnoticed.

**Root cause**: Alerting on **symptoms** (CPU >80%, latency >500ms) instead of **invariant violations** (service unavailable, SLO breach).

### The Symptom vs Invariant Distinction

**Symptom alert**: "CPU is high"

- **Problem**: High CPU might be fine (batch job running). Or high CPU might indicate a problem (infinite loop).
- **Result**: Alert fires in both cases, leading to false positives.

**Invariant alert**: "Service is not responding to health checks"

- **Problem**: Service is truly down (violates invariant: "service must respond to requests").
- **Result**: Alert fires only when there's a real issue.

### Designing Better Alerts

**Bad alert**:

```promql
# Alert if CPU >80% for 5 minutes
ALERT HighCPU
  IF avg(cpu_usage) > 0.8
  FOR 5m
  ANNOTATIONS {
    summary = "CPU is high"
  }
```

**Why it's bad**: High CPU might be normal (traffic spike, batch job). Alerts on symptom, not impact.

**Better alert**:

```promql
# Alert if error rate >1% for 5 minutes
ALERT HighErrorRate
  IF rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
  FOR 5m
  ANNOTATIONS {
    summary = "Error rate exceeded 1%"
  }
```

**Why it's better**: Errors directly impact users. High CPU alone doesn't.

**Best alert (SLO-based)**:

```promql
# Alert if error budget is exhausted (SLO: 99.9% availability over 30 days)
# Error budget: 0.1% of requests can fail = 43 minutes of downtime per month
ALERT ErrorBudgetExhausted
  IF (
    1 - (
      sum(rate(http_requests_total{status=~"2.."}[30d]))
      /
      sum(rate(http_requests_total[30d]))
    )
  ) > 0.001
  ANNOTATIONS {
    summary = "Error budget exhausted, SLO at risk"
  }
```

**Why it's best**: Ties alert to business-critical metric (SLO). Alerts only when SLO is at risk.

### The SLO Approach (Google SRE)

**SLO (Service Level Objective)**: Target for reliability (e.g., 99.9% uptime).

**Error budget**: Allowed failure (e.g., 0.1% downtime = 43 minutes/month).

**Key insight**: Don't alert when things go wrong. Alert when **error budget is at risk**.

**Example**:

- **SLO**: 99.9% of requests succeed (over 30 days)
- **Error budget**: 0.1% of requests can fail = 43,200 seconds of "failure" allowed per month
- **Current error rate**: 0.05% (consuming error budget at 50% rate)
- **Projected budget exhaustion**: 60 days (safe)
- **Action**: No alert (error budget healthy)

**If error rate spikes to 0.5%**:

- **Projected budget exhaustion**: 6 days (risk!)
- **Action**: Alert on-call, investigate immediately

**Implementation**:

```yaml
groups:
  - name: slo
    rules:
      # SLI (Service Level Indicator): success rate
      - record: sli:http_requests:success_rate
        expr: |
          sum(rate(http_requests_total{status=~"2.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))

      # Error budget remaining
      - record: slo:error_budget:remaining
        expr: |
          1 - (
            (1 - 0.999)  # SLO target (99.9%)
            - (1 - sli:http_requests:success_rate)
          ) / (1 - 0.999)

      # Alert if error budget <10% remaining
      - alert: ErrorBudgetLow
        expr: slo:error_budget:remaining < 0.1
        for: 5m
        annotations:
          summary: "Error budget below 10%, SLO at risk"
```

### Alert Fatigue: The Numbers

**Before SLO-based alerts** (Shopify, 2018):

- Alerts per day: 50
- False positives: 45 (90%)
- Mean time to acknowledge: 15 minutes (engineers ignored alerts)
- Incidents missed: 2 per month (alerts ignored)

**After SLO-based alerts** (Shopify, 2019):

- Alerts per day: 3
- False positives: 0.3 (10%)
- Mean time to acknowledge: 2 minutes (engineers trust alerts)
- Incidents missed: 0 per month

**Lesson**: Fewer, better alerts → faster response → higher reliability.

## Part 5: Real Production Examples and Mental Models

### Example 1: Netflix's Metric Cardinality Disaster (2018)

**Problem**: Engineers added a `device_id` label to a metrics counter, intending to track playback issues per device.

```python
playback_errors.labels(device_id=device_id, title_id=title_id).inc()
```

**Impact**:

- **Cardinality**: 200M unique devices × 100K titles = **20 trillion unique time series**
- **Prometheus memory usage**: 500GB → out of memory crash
- **All metrics lost**: Prometheus couldn't start (database corrupted)

**Root cause**: High-cardinality label (`device_id`) caused cardinality explosion.

**Fix**:

- Remove `device_id` from labels
- Log `device_id` in structured logs instead
- Use sampling: Record metrics for 0.1% of devices

**Lesson**: **Never use high-cardinality IDs as labels**. Use logs or traces for high-cardinality data.

### Example 2: Uber's Multi-Tier Metrics Architecture

**Scale**:

- 10,000+ services
- 1M+ metrics per second
- 50+ data centers globally

**Challenge**: Real-time metrics across 50 data centers = high network cost (cross-region bandwidth).

**Solution**: **Hierarchical aggregation**

**Tier 1 (Local aggregation)**:

- Each data center runs its own Prometheus instance
- Scrapes metrics from local services (low latency, no cross-region traffic)
- Stores 1-hour retention (real-time debugging)

**Tier 2 (Regional aggregation)**:

- Regional Prometheus instances scrape local Prometheus instances
- Aggregates metrics across data centers in the same region (e.g., all US data centers)
- Stores 7-day retention

**Tier 3 (Global aggregation)**:

- Global Prometheus instance scrapes regional instances
- Aggregates metrics globally
- Stores 30-day retention (low resolution)

**Result**:

- **Real-time metrics**: Available locally (low latency)
- **Cross-region queries**: Available globally (high latency, but acceptable for dashboards)
- **Cost savings**: 95% reduction in cross-region bandwidth

**Lesson**: Use **hierarchical aggregation** to reduce cross-region traffic at scale.

### Example 3: Google's Monarch (Internal Metrics System)

**Scale**:

- 1B+ time series
- 10M+ samples per second
- 20+ years of retention (exabytes of data)

**Innovations**:

**1. Global aggregation**: Metrics aggregated continuously across all data centers (eventual consistency).

**2. Delta encoding**: Store only changes (deltas) instead of absolute values.

```
Traditional: 100, 105, 110, 115, 120 (5 numbers)
Delta: 100, +5, +5, +5, +5 (1 number + 4 deltas, compress to 2 numbers)
```

**3. Columnar storage**: Store each label in a separate column (enables efficient compression).

**4. Lossy compression**: Acceptable to lose precision for old data (e.g., round to nearest 10ms after 30 days).

**Result**: Store exabytes of metrics data while keeping query latency under 100ms.

**Lesson**: At Google scale, even Prometheus isn't enough. Custom infrastructure required.

## Mental Model Summary

### The Metrics Hierarchy

```
Business Layer:        SLOs (99.9% availability)
                            ↓
Alert Layer:           Error budget exhausted
                            ↓
Signal Layer:          RED (Rate, Errors, Duration)
                            ↓
Resource Layer:        USE (Utilization, Saturation, Errors)
                            ↓
Infrastructure Layer:  Time-series database (Prometheus)
```

### The Three Metrics Truths

**1. Metrics are aggregates, not individuals**

- Use metrics for overall health (average latency, error rate)
- Use traces for individual requests (why is this specific request slow?)
- Use logs for individual events (what happened at this exact moment?)

**2. Cardinality is the enemy**

- High-cardinality labels (user IDs, request IDs) destroy metrics systems
- Keep cardinality under 10,000 unique combinations
- Use logs/traces for high-cardinality data

**3. Alert on invariants, not symptoms**

- Symptoms (high CPU, high memory) don't always indicate problems
- Invariants (service unavailable, SLO breached) always indicate problems
- Fewer, better alerts → faster response

### When to Use Metrics

**Use metrics when**:

- Monitoring overall system health (error rate, latency, throughput)
- Detecting trends (latency increasing over time)
- Alerting on SLO breaches (error budget exhausted)
- Capacity planning (CPU/memory utilization over months)

**Don't use metrics when**:

- Debugging a specific request (use traces)
- Finding a specific error message (use logs)
- Tracking individual users (use logs/traces)
- High-cardinality data (user IDs, request IDs)

---

**Next**: Understanding how to build a centralized logging pipeline that scales to billions of log lines per day.

Continue to [Logging Pipeline →](logging-pipeline.md)

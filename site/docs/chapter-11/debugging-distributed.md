# Debugging Distributed Systems: Chaos, Correlation, and War Stories

## Introduction: The Debugging Impossibility

A monolithic application fails. You attach a debugger, set breakpoints, step through code, inspect variables. Root cause found in 10 minutes.

A distributed system fails. You have:

- 100 services
- 1,000 instances
- 10 data centers
- Requests flowing across HTTP, gRPC, message queues
- Failures that only happen at 3 AM on Tuesdays
- Heisenbugs that disappear when you try to reproduce them

**The impossibility**: You cannot "attach a debugger" to a distributed system. There's no single process to debug. By the time you notice a failure, the state that caused it is gone. Services have restarted. Logs have rotated. Evidence has vanished.

Yet distributed systems *can* be debugged—if you design them for debuggability from day one.

This chapter covers:

1. **Correlation IDs**: How to track a request across 100 services
2. **Distributed debuggers**: Time-travel debugging at scale
3. **Chaos engineering**: Breaking things on purpose to learn how they fail
4. **Root cause analysis**: Structured investigation of incidents
5. **Post-mortems**: Learning from failures without blame
6. **War stories**: Real production debugging experiences

### The Core Insight

**Distributed debugging is not about preventing failures—it's about making failures observable, reproducible, and recoverable.**

## Part 1: Correlation IDs — The Thread Through the Maze

### The Problem: Lost in the Distributed Graph

**Scenario**: User reports "My order failed." Your system:

```
User → API Gateway → Order Service → Payment Service → Stripe API
                         ↓               ↓
                   Inventory Service   Fraud Service
                         ↓               ↓
                     Database         Database
```

**Without correlation IDs**:

```bash
# API Gateway logs
2024-01-15 10:23:45 INFO Received POST /checkout
2024-01-15 10:23:46 INFO Request completed with status 500

# Order Service logs
2024-01-15 10:23:45 INFO Processing order
2024-01-15 10:23:46 ERROR Database write failed

# Payment Service logs
2024-01-15 10:23:45 INFO Charging card
2024-01-15 10:23:46 INFO Payment succeeded
```

**Question**: Which API Gateway request corresponds to which Order Service request? **Impossible to tell** (timestamps alone are insufficient—multiple requests can have the same timestamp).

**With correlation IDs**:

```bash
# API Gateway logs
2024-01-15 10:23:45 INFO request_id=req_a7f3c2d1 Received POST /checkout user_id=user_789
2024-01-15 10:23:46 INFO request_id=req_a7f3c2d1 Request completed with status 500

# Order Service logs
2024-01-15 10:23:45 INFO request_id=req_a7f3c2d1 Processing order order_id=order_123
2024-01-15 10:23:46 ERROR request_id=req_a7f3c2d1 Database write failed: Deadlock detected

# Payment Service logs
2024-01-15 10:23:45 INFO request_id=req_a7f3c2d1 Charging card payment_id=pay_456
2024-01-15 10:23:46 INFO request_id=req_a7f3c2d1 Payment succeeded tx_id=tx_789
```

**Now you can query**: `request_id:req_a7f3c2d1` → All logs for this request, across all services.

### Implementing Correlation IDs

**1. Generate ID at entry point**:

```python
from flask import Flask, request, g
import uuid

app = Flask(__name__)

@app.before_request
def set_request_id():
    # Check if client provided request ID (useful for mobile/frontend retries)
    request_id = request.headers.get('X-Request-ID')

    # If not, generate one
    if not request_id:
        request_id = str(uuid.uuid4())

    # Store in request context (accessible throughout request lifecycle)
    g.request_id = request_id

    # Return in response headers (for debugging)
    @app.after_request
    def add_request_id_header(response):
        response.headers['X-Request-ID'] = g.request_id
        return response
```

**2. Propagate ID to downstream services**:

```python
import requests

def call_downstream_service():
    headers = {
        'X-Request-ID': g.request_id  # Propagate to downstream service
    }

    response = requests.post(
        'https://order-service/api/orders',
        headers=headers,
        json={'user_id': 'user_789'}
    )

    return response.json()
```

**3. Log ID in every log statement**:

```python
import structlog

logger = structlog.get_logger()

# Bind request_id to all logs in this request
structlog.contextvars.bind_contextvars(request_id=g.request_id)

logger.info("processing_order", user_id=user_id)
# Output: {"request_id": "req_a7f3c2d1", "event": "processing_order", "user_id": "user_789"}
```

**4. Include ID in traces**:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def checkout():
    # Use request_id as trace_id (links logs to traces)
    with tracer.start_as_current_span("checkout", trace_id=g.request_id):
        process_order()
```

### Advanced: Nested Correlation

**Problem**: A single user request triggers 10 downstream requests (fan-out pattern). How do you distinguish them?

**Solution**: **Parent-child correlation**:

```python
def checkout():
    # Parent request ID
    parent_id = g.request_id

    # Generate child IDs for parallel calls
    inventory_request_id = f"{parent_id}_inventory"
    payment_request_id = f"{parent_id}_payment"
    shipping_request_id = f"{parent_id}_shipping"

    # Make parallel calls
    with ThreadPoolExecutor() as executor:
        executor.submit(check_inventory, inventory_request_id)
        executor.submit(process_payment, payment_request_id)
        executor.submit(calculate_shipping, shipping_request_id)

def check_inventory(request_id):
    headers = {'X-Request-ID': request_id}
    requests.get('https://inventory-service/check', headers=headers)
```

**Result**:

```
Parent: req_a7f3c2d1
├─ Child: req_a7f3c2d1_inventory
├─ Child: req_a7f3c2d1_payment
└─ Child: req_a7f3c2d1_shipping
```

**Query**: `request_id:req_a7f3c2d1*` → All parent and child logs.

### Correlation Across Message Queues

**Challenge**: Async message processing breaks the request chain.

**Solution**: Embed correlation ID in message metadata:

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(bootstrap_servers=['kafka:9092'])

def publish_order_created_event(order_id):
    message = {
        'event_type': 'order_created',
        'order_id': order_id,
        'timestamp': time.time()
    }

    # Embed correlation ID in message headers
    headers = [
        ('request_id', g.request_id.encode()),
        ('user_id', user_id.encode())
    ]

    producer.send('orders', value=json.dumps(message).encode(), headers=headers)

# Consumer: Extract correlation ID
from kafka import KafkaConsumer

consumer = KafkaConsumer('orders', bootstrap_servers=['kafka:9092'])

for message in consumer:
    # Extract correlation ID from headers
    headers = dict(message.headers)
    request_id = headers.get('request_id', b'unknown').decode()

    # Bind to logs
    structlog.contextvars.bind_contextvars(request_id=request_id)

    # Process message
    logger.info("processing_order_created_event", order_id=message.value['order_id'])
```

**Result**: Logs from async workers are correlated with original request.

### Real Example: Uber's Request Tracing

**Scale**:

- 10,000+ services
- 1M+ RPC calls per second

**Implementation**:

- Every request assigned a **request_id** (128-bit UUID)
- Every RPC call includes request_id in gRPC metadata
- Every log statement includes request_id
- Every trace span tagged with request_id

**Use case**: User reports "ride request failed"

1. User provides request_id (shown in app UI)
2. Engineer queries: `request_id:req_12345`
3. Results: 200+ log lines across 15 services
4. Root cause identified in 2 minutes (vs 2 hours without correlation)

**Lesson**: Correlation IDs are the single most important debugging primitive in distributed systems.

## Part 2: Time-Travel Debugging — Record and Replay

### The Challenge

**Traditional debugger**:

- Set breakpoint
- Run code
- Step through, inspect variables

**Distributed system**:

- Failure happened 3 hours ago
- Can't "step through" the past
- State is gone (instances restarted, caches cleared)

### The Solution: Record and Replay

**Concept**: Record all inputs to a service (HTTP requests, database queries, message queue messages). Replay them later to reproduce the exact execution.

### Implementing Record and Replay

**1. Recording mode** (capture all inputs):

```python
from flask import Flask, request
import json
import time

app = Flask(__name__)

@app.before_request
def record_request():
    if os.getenv('RECORD_MODE') == 'true':
        recording = {
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'headers': dict(request.headers),
            'body': request.get_data(as_text=True),
            'query_params': dict(request.args)
        }

        # Write to file (or database)
        with open('/var/log/recordings/request.jsonl', 'a') as f:
            f.write(json.dumps(recording) + '\n')
```

**2. Replay mode** (replay recorded inputs):

```python
def replay_requests():
    with open('/var/log/recordings/request.jsonl', 'r') as f:
        for line in f:
            recording = json.loads(line)

            # Replay request
            with app.test_client() as client:
                response = client.open(
                    path=recording['path'],
                    method=recording['method'],
                    headers=recording['headers'],
                    data=recording['body'],
                    query_string=recording['query_params']
                )

                print(f"Replayed {recording['path']}, status: {response.status_code}")
```

**Use case**: Reproduce a bug that only happens in production.

1. Enable recording mode for 1 hour
2. Wait for failure to occur
3. Disable recording mode
4. Replay recorded requests locally (with debugger attached)
5. Root cause found

### Advanced: Distributed Replay

**Challenge**: Replaying one service isn't enough—you need to replay the entire distributed system.

**Solution**: **Record all inter-service calls**:

```python
import requests

# Monkey-patch requests.post to record all outgoing calls
original_post = requests.post

def recorded_post(*args, **kwargs):
    if os.getenv('RECORD_MODE') == 'true':
        recording = {
            'timestamp': time.time(),
            'url': args[0],
            'headers': kwargs.get('headers'),
            'body': kwargs.get('json')
        }

        with open('/var/log/recordings/outgoing.jsonl', 'a') as f:
            f.write(json.dumps(recording) + '\n')

    # Make actual request
    response = original_post(*args, **kwargs)

    # Record response
    if os.getenv('RECORD_MODE') == 'true':
        with open('/var/log/recordings/responses.jsonl', 'a') as f:
            f.write(json.dumps({
                'timestamp': time.time(),
                'url': args[0],
                'status_code': response.status_code,
                'body': response.text
            }) + '\n')

    return response

requests.post = recorded_post
```

**Replay**: Instead of calling real services, mock them with recorded responses.

```python
def replay_with_mocks():
    # Load recorded responses
    responses = {}
    with open('/var/log/recordings/responses.jsonl', 'r') as f:
        for line in f:
            r = json.loads(line)
            responses[r['url']] = r

    # Mock requests.post
    def mocked_post(url, *args, **kwargs):
        # Return recorded response
        recorded = responses.get(url)
        if recorded:
            return MockResponse(recorded['status_code'], recorded['body'])
        else:
            raise Exception(f"No recorded response for {url}")

    requests.post = mocked_post

    # Now replay requests (will use mocked responses)
    replay_requests()
```

**Result**: Full reproduction of distributed system behavior, without running actual services.

### Real Example: Twitter's Diffy

**Problem**: Deployments cause subtle regressions (API returns slightly different response).

**Solution**: Diffy (open-sourced by Twitter)

**How it works**:

1. **Primary**: Old version (stable)
2. **Candidate**: New version (being tested)
3. **Secondary**: Another old version (control)

**Traffic flow**:

```
User Request → Diffy Proxy
                  ├─ Forward to Primary (return response to user)
                  ├─ Forward to Candidate (discard response)
                  └─ Forward to Secondary (discard response)

Diffy compares responses:
  - Primary vs Secondary: Should be identical (both old versions)
  - Primary vs Candidate: Differences indicate regressions
```

**Example**:

```json
// Primary (old version) response
{"user_id": "123", "name": "Alice", "balance": 99.50}

// Candidate (new version) response
{"user_id": "123", "name": "Alice", "balance": 99.5}  // Lost trailing zero!

Diffy alert: Regression detected in /api/user endpoint
  - Field "balance" changed: 99.50 → 99.5
  - Impact: 100% of requests
```

**Lesson**: Replay traffic against multiple versions to detect regressions before production.

## Part 3: Chaos Engineering — Breaking Things on Purpose

### The Philosophy

**Traditional testing**: Test known failure modes (server crashes, network partitions).

**Chaos engineering**: **Discover unknown failure modes** by injecting random failures into production.

**Core insight**: You don't know how your system fails until you break it.

### The Netflix Chaos Monkey

**History**: Netflix invented chaos engineering in 2010 after migrating to AWS.

**Problem**: AWS instances can fail at any time (hardware failures, network issues). Netflix needed to ensure graceful degradation.

**Solution**: Chaos Monkey—randomly terminates instances in production during business hours.

**Result**: Engineers forced to design for failure (redundancy, retries, fallbacks). Netflix survived multiple AWS outages with zero user impact.

### Implementing Chaos Engineering

**1. Start small** (kill one instance):

```python
import random
import subprocess

def chaos_monkey():
    # Get list of instances
    instances = get_all_instances()

    # Randomly select one
    victim = random.choice(instances)

    print(f"Chaos Monkey: Terminating instance {victim.id}")

    # Terminate instance
    subprocess.run(['kubectl', 'delete', 'pod', victim.id])

    # Monitor impact
    time.sleep(60)
    error_rate = get_error_rate()

    if error_rate > 0.01:
        print(f"ERROR: Error rate increased to {error_rate*100}%")
        # Alert team, rollback chaos experiment
    else:
        print(f"SUCCESS: Error rate remained low ({error_rate*100}%)")
```

**2. Increase scope** (kill multiple instances):

```python
def chaos_gorilla():
    # Kill an entire availability zone
    az = random.choice(['us-east-1a', 'us-east-1b', 'us-east-1c'])

    print(f"Chaos Gorilla: Terminating all instances in {az}")

    instances = get_instances_in_az(az)
    for instance in instances:
        subprocess.run(['kubectl', 'delete', 'pod', instance.id])
```

**3. Chaos Kong** (kill an entire region):

```python
def chaos_kong():
    region = random.choice(['us-east-1', 'us-west-2', 'eu-west-1'])

    print(f"Chaos Kong: Terminating all instances in {region}")

    # Simulate region failure by blocking traffic
    subprocess.run(['iptables', '-A', 'OUTPUT', '-d', f'{region}-network', '-j', 'DROP'])
```

### Chaos Toolkit (Open Source)

**Installation**:

```bash
pip install chaostoolkit
```

**Experiment definition** (YAML):

```yaml
version: 1.0.0
title: What happens if payment service goes down?
description: Verify that checkout still works with fallback payment method

steady-state-hypothesis:
  title: Checkout success rate >99%
  probes:
    - type: probe
      name: checkout_success_rate
      provider:
        type: python
        module: metrics
        func: get_checkout_success_rate
      tolerance: [0.99, 1.0]

method:
  - type: action
    name: terminate_payment_service
    provider:
      type: process
      path: kubectl
      arguments: ["delete", "deployment", "payment-service"]

  - type: probe
    name: wait_for_recovery
    provider:
      type: python
      module: time
      func: sleep
      arguments: [60]

rollbacks:
  - type: action
    name: restore_payment_service
    provider:
      type: process
      path: kubectl
      arguments: ["apply", "-f", "payment-service.yaml"]
```

**Run experiment**:

```bash
chaos run experiment.yaml
```

**Result**:

```
[INFO] Steady state hypothesis: Checkout success rate >99%
[INFO] Running experiment: What happens if payment service goes down?
[INFO] Action: Terminate payment service
[INFO] Probe: Wait for recovery (60s)
[ERROR] Steady state hypothesis FAILED: Checkout success rate = 92%
[INFO] Rollback: Restore payment service
```

**Lesson**: System does NOT gracefully degrade when payment service fails. Need to add fallback.

### Chaos Experiments to Run

**1. Instance failure**:

- Kill a random instance
- Verify: Traffic automatically routed to healthy instances

**2. Network partition**:

- Block traffic between services
- Verify: Timeouts handled gracefully, retries succeed

**3. Latency injection**:

- Add 5-second delay to database queries
- Verify: Timeouts fire, circuit breakers open

**4. Resource exhaustion**:

- Fill disk to 100%
- Verify: Service stops accepting writes, alerts fire

**5. Dependency failure**:

- Make external API return 500 errors
- Verify: Fallback logic activates (cached data, default values)

**6. Clock skew**:

- Set instance clock 10 minutes ahead
- Verify: Distributed consensus still works (Raft, Paxos tolerates small skew)

**7. Data corruption**:

- Randomly flip bits in database
- Verify: Checksums detect corruption, backups restore data

### Real Example: Amazon Prime Day Chaos Drills

**Challenge**: Prime Day generates 10× normal traffic. Must ensure system handles load.

**Solution**: Chaos engineering drills 1 week before Prime Day:

1. **Kill 20% of instances** (simulate instance failures)
2. **Inject latency** (simulate slow database)
3. **Simulate region failure** (test multi-region failover)
4. **Load test at 15× normal traffic** (exceed expected peak)

**Result**: Discovered and fixed 12 critical issues before Prime Day. Prime Day succeeded with zero major incidents.

**Lesson**: Test in production, before the actual event.

## Part 4: Root Cause Analysis — Structured Investigation

### The Five Whys

**Technique**: Ask "why?" five times to uncover root cause.

**Example**:

1. **Problem**: Checkout is slow (latency increased from 200ms to 2,000ms)
2. **Why?** Payment service is slow
3. **Why?** Database queries are slow
4. **Why?** Database CPU is at 100%
5. **Why?** Vacuum process is running (reclaiming disk space)
6. **Why?** Vacuum was scheduled during peak hours (misconfiguration)

**Root cause**: Vacuum scheduled during peak hours.

**Fix**: Reschedule vacuum to off-peak hours (3 AM).

**Preventive measure**: Add alert for database CPU >80% during peak hours.

### Structured Investigation Process

**1. Gather evidence** (metrics, logs, traces):

```bash
# Metrics: When did latency increase?
p95_latency[1h] > 1000

# Logs: What errors occurred?
level:error AND @timestamp:[2024-01-15T10:00:00 TO 2024-01-15T11:00:00]

# Traces: Which service is slow?
trace_id:req_a7f3c2d1
```

**2. Form hypotheses**:

- Hypothesis 1: Database is slow (CPU at 100%)
- Hypothesis 2: Network partition (increased latency)
- Hypothesis 3: Code regression (recent deployment)

**3. Test hypotheses**:

```bash
# Test hypothesis 1: Check database CPU
database_cpu_usage[1h]
# Result: CPU spiked to 100% at 10:00 (correlates with latency increase)

# Test hypothesis 2: Check network latency
network_latency[1h]
# Result: No change (hypothesis rejected)

# Test hypothesis 3: Check recent deployments
git log --since="1 hour ago"
# Result: No deployments (hypothesis rejected)
```

**4. Identify root cause**:

- **Hypothesis 1 confirmed**: Database CPU at 100% caused by vacuum process

**5. Mitigate immediately**:

```bash
# Stop vacuum process
sudo -u postgres kill -SIGINT <vacuum_pid>

# Verify latency decreased
p95_latency[5m]
# Result: Latency back to 200ms
```

**6. Fix permanently**:

```sql
-- Reschedule vacuum to off-peak hours
ALTER TABLE payments SET (autovacuum_naptime = '1h');
ALTER TABLE payments SET (autovacuum_vacuum_cost_delay = '20ms');
```

**7. Prevent recurrence**:

```yaml
# Add alert for database vacuum during peak hours
- alert: VacuumDuringPeakHours
  expr: pg_stat_progress_vacuum AND hour() >= 9 AND hour() <= 17
  annotations:
    summary: "Database vacuum running during peak hours (9 AM - 5 PM)"
```

### Real Example: GitHub's 2018 Outage

**Incident**: GitHub experienced 24 hours of degraded service (October 21-22, 2018).

**Timeline**:

- **13:57 UTC**: Network partition between US East Coast and US West Coast data centers
- **14:00 UTC**: Both data centers elected themselves as primary (split-brain)
- **14:01 UTC**: Writes happened in both data centers (data diverged)
- **14:05 UTC**: Network partition healed
- **14:10 UTC**: System detected data conflicts, entered read-only mode (prevented further corruption)
- **16:00 UTC**: GitHub began manual reconciliation (merging conflicting data)
- **23:00 UTC (next day)**: Full write access restored

**Root cause**: Network partition caused split-brain (both data centers became primary). Data diverged during the 4-minute partition.

**Fix**:

1. **Immediate**: Manual data reconciliation (24 hours of work)
2. **Short-term**: Improved split-brain detection (faster failover)
3. **Long-term**: Implemented Raft consensus (prevents split-brain)

**Lesson**: Even giants fail. Post-mortems are how they learn.

## Part 5: Post-Mortems — Learning Without Blame

### The Blameless Post-Mortem

**Philosophy**: Incidents are caused by systems, not individuals. Focus on fixing systems, not punishing people.

**Bad post-mortem**:

> "Engineer X deployed bad code, causing the outage. X has been reprimanded."

**Good post-mortem**:

> "A code change caused the outage. Root cause: inadequate testing and lack of canary deployment. Action items: (1) Add integration test for this code path, (2) Require canary deployment for all changes, (3) Improve monitoring to detect similar issues earlier."

### Post-Mortem Template

**1. Summary**:

- **Incident**: Checkout API returned 500 errors
- **Duration**: 45 minutes (10:00 - 10:45 UTC)
- **Impact**: 5% of checkout requests failed (1,200 affected users, $50K estimated revenue loss)

**2. Timeline**:

| Time | Event |
|------|-------|
| 09:55 | Deployment of checkout-service v2.3.0 started |
| 10:00 | Deployment completed, new version serving 100% traffic |
| 10:02 | Error rate increased from 0.1% to 5% |
| 10:03 | On-call paged (alert: error rate >1%) |
| 10:05 | On-call identified recent deployment as likely cause |
| 10:10 | Rollback initiated |
| 10:15 | Rollback completed, v2.2.9 serving 100% traffic |
| 10:16 | Error rate decreased to 0.1% (normal) |
| 10:45 | Incident resolved |

**3. Root cause**:

- **Immediate cause**: Code regression in v2.3.0 (null pointer exception when processing orders with gift cards)
- **Contributing factors**:
  - Inadequate test coverage (gift card code path not tested)
  - No canary deployment (v2.3.0 deployed to 100% of traffic immediately)
  - Delayed detection (error rate threshold set too high: 1% instead of 0.5%)

**4. Resolution**:

- Rolled back to v2.2.9
- Fixed null pointer exception in v2.3.1
- Deployed v2.3.1 with canary (1% → 10% → 50% → 100%)

**5. Action items**:

| Action | Owner | Deadline | Status |
|--------|-------|----------|--------|
| Add test for gift card code path | Alice | 2024-01-20 | Done |
| Require canary deployment for all changes | Bob | 2024-01-25 | In Progress |
| Lower error rate alert threshold to 0.5% | Charlie | 2024-01-18 | Done |
| Add monitoring for null pointer exceptions | Dave | 2024-01-22 | Done |

**6. Lessons learned**:

- **Test coverage matters**: Untested code paths will fail in production
- **Canary deployments catch regressions**: Rolling out to 1% first would have limited impact to 12 users instead of 1,200
- **Alert thresholds need tuning**: 1% error rate threshold meant 1,200 users affected before alert fired

### Real Post-Mortem: Google's 2013 Gmail Outage

**Incident**: Gmail unavailable for 50 minutes (January 24, 2013).

**Impact**: 150 million users unable to access email.

**Root cause**: Software bug in load balancing system caused all traffic to be routed to a single data center (instead of distributing across multiple data centers). Single data center overloaded, became unavailable.

**Resolution**:

- Detected within 2 minutes (monitoring alerted)
- Engineers manually rerouted traffic to other data centers
- Service restored within 50 minutes

**Action items**:

1. **Improve load balancer testing**: Add integration test for single-data-center failure scenario
2. **Automatic failover**: Implement automatic traffic rerouting (instead of manual)
3. **Capacity headroom**: Increase capacity per data center (so single data center can handle 100% of traffic temporarily)

**Transparency**: Google published a public post-mortem, explaining what happened and how they'll prevent it in the future. Builds user trust.

**Lesson**: Even Google fails. The difference: they learn, improve, and communicate transparently.

## Part 6: War Stories — Debugging in the Trenches

### War Story 1: The Invisible Network Partition

**Company**: Unnamed social network (100M+ users)

**Incident**: API latency increased from 50ms to 500ms, but only for 10% of users.

**Investigation**:

1. **Metrics**: Latency increased only for users in specific geographic region (US West Coast)
2. **Traces**: Showed requests from US West Coast were being routed to US East Coast data center (cross-country latency)
3. **Root cause**: DNS misconfiguration. GeoDNS was routing some US West Coast users to US East Coast (incorrect routing rule)

**Fix**: Corrected GeoDNS configuration, latency returned to normal.

**Lesson**: Geographic routing is subtle. Test from multiple locations.

### War Story 2: The Intermittent Database Deadlock

**Company**: E-commerce platform (1M+ orders per day)

**Incident**: 0.01% of checkout requests failed with "Database deadlock" error (100 failures per day).

**Challenge**: Deadlocks were intermittent—couldn't reproduce locally.

**Investigation**:

1. **Logs**: Deadlocks always involved two tables (orders, inventory)
2. **Hypothesis**: Two transactions accessing tables in different order (classic deadlock scenario)
3. **Code review**: Found two code paths:
   - Code path A: Lock orders first, then inventory
   - Code path B: Lock inventory first, then orders
4. **Root cause**: Inconsistent lock ordering

**Fix**:

```python
# Before (deadlock possible)
def checkout_v1():
    with db.transaction():
        order = db.create_order()  # Locks orders table
        db.reserve_inventory()     # Locks inventory table

def refund_v1():
    with db.transaction():
        db.restore_inventory()     # Locks inventory table
        db.cancel_order()          # Locks orders table (DEADLOCK!)

# After (consistent lock ordering)
def checkout_v2():
    with db.transaction():
        db.reserve_inventory()     # Locks inventory first
        order = db.create_order()  # Locks orders second

def refund_v2():
    with db.transaction():
        db.restore_inventory()     # Locks inventory first
        db.cancel_order()          # Locks orders second (no deadlock)
```

**Lesson**: Always lock resources in a consistent order to prevent deadlocks.

### War Story 3: The Memory Leak That Wasn't

**Company**: SaaS platform (10,000+ tenants)

**Incident**: Memory usage increased steadily over days, eventually causing out-of-memory crashes.

**Investigation**:

1. **Heap dump**: Showed 10GB of cached data (cache should be max 1GB)
2. **Hypothesis**: Memory leak in caching library
3. **Cache inspection**: Cache had 1 million entries (expected: 100,000)
4. **Root cause**: Cache eviction policy was LRU (least recently used), but one tenant was making 10× more requests than others, filling cache with their data
5. **Secondary root cause**: No per-tenant cache size limit

**Fix**:

```python
# Before (global cache, no per-tenant limits)
cache = LRUCache(maxsize=100000)

def get_data(tenant_id, key):
    cache_key = f"{tenant_id}:{key}"
    return cache.get(cache_key)

# After (per-tenant cache with limits)
class TenantAwareLRUCache:
    def __init__(self, per_tenant_maxsize=1000):
        self.caches = {}
        self.per_tenant_maxsize = per_tenant_maxsize

    def get(self, tenant_id, key):
        if tenant_id not in self.caches:
            self.caches[tenant_id] = LRUCache(maxsize=self.per_tenant_maxsize)
        return self.caches[tenant_id].get(key)

cache = TenantAwareLRUCache(per_tenant_maxsize=1000)
```

**Lesson**: Multi-tenancy requires per-tenant resource limits to prevent noisy neighbor problems.

### War Story 4: The Case of the Disappearing Logs

**Company**: Healthcare platform (HIPAA-compliant)

**Incident**: Logs for specific user's requests were missing (compliance violation).

**Investigation**:

1. **Query**: `user_id:user_12345` → No results
2. **Hypothesis**: Logs not being written
3. **Application logs**: Confirmed logs were being written to file
4. **Filebeat logs**: Confirmed logs were being shipped to Logstash
5. **Logstash logs**: Found error: "Failed to parse JSON"
6. **Root cause**: User's name contained a double-quote character (`Alice "The Boss" Smith`), which broke JSON parsing

**Fix**:

```python
# Before (broken JSON when name contains quotes)
logger.info(f'{{"user_name": "{user.name}"}}')
# Output: {"user_name": "Alice "The Boss" Smith"}  (invalid JSON!)

# After (proper JSON escaping)
import json
logger.info(json.dumps({"user_name": user.name}))
# Output: {"user_name": "Alice \"The Boss\" Smith"}  (valid JSON)
```

**Lesson**: Always use JSON libraries for serialization, never string concatenation.

## Mental Model Summary

### The Debugging Hierarchy

```
Observability Layer:   Correlation IDs, Traces, Logs, Metrics
                              ↓
Investigation Layer:   Root cause analysis (Five Whys)
                              ↓
Reproduction Layer:    Record and replay, Chaos engineering
                              ↓
Learning Layer:        Post-mortems, Action items
                              ↓
Prevention Layer:      Tests, Monitoring, Alerts
```

### The Three Debugging Truths

**1. Debuggability is a design requirement**

- Can't add correlation IDs after launch
- Can't add logging after production failure
- Debuggability must be built in from day one

**2. Failures are learning opportunities**

- Every incident teaches you about your system
- Blameless post-mortems encourage learning
- Action items prevent recurrence

**3. Chaos is a feature, not a bug**

- Breaking things on purpose reveals weaknesses
- Better to discover failures during chaos experiments than during production incidents
- Chaos engineering is proactive debugging

### When to Use Each Technique

**Use correlation IDs when**:

- Tracking requests across services
- Correlating logs, traces, metrics
- Debugging specific user issues

**Use record and replay when**:

- Reproducing intermittent bugs
- Testing regression fixes
- Comparing old vs new versions

**Use chaos engineering when**:

- Validating failure handling
- Discovering unknown failure modes
- Preparing for high-stakes events (Black Friday, Prime Day)

**Use root cause analysis when**:

- Investigating production incidents
- Identifying systemic issues
- Preventing recurrence

**Use post-mortems when**:

- Documenting incidents
- Sharing lessons learned
- Building organizational knowledge

---

**Observability is the foundation of reliable distributed systems. Traces show you where, metrics show you what, logs show you why, and correlation IDs tie it all together. Debug with discipline, learn from failures, and build systems that reveal their own truth.**

Continue to [Chapter 12: Security and Trust →](/docs/chapter-12/)

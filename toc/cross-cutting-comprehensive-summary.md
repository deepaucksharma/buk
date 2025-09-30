# Comprehensive Cross-Cutting Topics Summary

This document provides comprehensive coverage of the remaining cross-cutting topics that span multiple parts of the distributed systems book. Each topic includes implementation guides, configuration examples, and operational playbooks.

---

## Topic 3: Change Data Capture & Streaming

### 3.1 CDC Pipeline Architectures

#### 3.1.1 Log-Based CDC

**Transaction Log Mining**
```
Database transaction log → CDC connector → Event stream

PostgreSQL WAL decoding:
  - Logical replication slots
  - Output plugins: wal2json, pgoutput
  - Replication protocol: streaming or polling

MySQL binlog:
  - Row-based replication (ROW format)
  - Binlog position tracking
  - GTID (Global Transaction Identifier)

Configuration:
  PostgreSQL:
    wal_level = logical
    max_replication_slots = 10
    max_wal_senders = 10

  MySQL:
    binlog_format = ROW
    binlog_row_image = FULL
    gtid_mode = ON
```

**Debezium Architecture**
```
┌──────────────┐
│   Database   │ (PostgreSQL, MySQL, MongoDB)
└──────┬───────┘
       │ Read transaction log
       ↓
┌──────────────┐
│  Debezium    │ Connector (Kafka Connect)
│  Connector   │
└──────┬───────┘
       │ Publish events
       ↓
┌──────────────┐
│    Kafka     │ Topic per table
│    Topics    │ (database.table)
└──────┬───────┘
       │ Consume
       ↓
┌──────────────┐
│  Consumers   │ (Elasticsearch, S3, etc.)
└──────────────┘

Event format:
{
  "before": {"id": 1, "name": "Alice", "balance": 100},
  "after": {"id": 1, "name": "Alice", "balance": 150},
  "op": "u",  // c=create, u=update, d=delete
  "ts_ms": 1727697600000,
  "source": {
    "db": "orders",
    "table": "accounts",
    "lsn": "0/12345678",
    "txId": 789
  }
}
```

#### 3.1.2 Outbox Pattern Implementation

**Problem: Dual Writes**
```
Bad pattern (not atomic):
  1. Update database
  2. Publish to message queue
  → If step 2 fails: inconsistency

Outbox pattern (atomic):
  1. Write to database + outbox table (single transaction)
  2. CDC reads outbox table
  3. Publish to message queue
```

**Schema Design**
```sql
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY,
    aggregate_type VARCHAR(255),
    aggregate_id VARCHAR(255),
    event_type VARCHAR(255),
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP,
    published BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_outbox_unpublished ON outbox_events(published, created_at)
WHERE published = FALSE;
```

**Application Implementation**
```python
def create_order(order_data):
    with db.transaction():
        # Business logic
        order = Order.create(order_data)
        db.commit(order)

        # Outbox event (same transaction!)
        event = {
            'aggregate_type': 'Order',
            'aggregate_id': order.id,
            'event_type': 'OrderCreated',
            'payload': order.to_json()
        }
        db.execute("""
            INSERT INTO outbox_events
            (id, aggregate_type, aggregate_id, event_type, payload)
            VALUES (%s, %s, %s, %s, %s)
        """, uuid4(), event['aggregate_type'], event['aggregate_id'],
             event['event_type'], event['payload'])

    # Transaction commits atomically: order + event

# CDC publishes outbox events to Kafka
# (Debezium Outbox Event Router)
```

### 3.2 Exactly-Once Connector Patterns

#### 3.2.1 Source Connectors (Database → Kafka)

**Exactly-Once Production**
```
Kafka Transactions for Exactly-Once:

1. Idempotent producer
   - Producer ID (PID)
   - Sequence numbers
   - Deduplication on broker

2. Transactional writes
   - Begin transaction
   - Produce records
   - Commit transaction

Debezium with exactly-once:
```yaml
connector.class: io.debezium.connector.postgresql.PostgresConnector
tasks.max: 1
database.hostname: postgres.example.com
database.port: 5432
database.user: debezium
database.password: secret
database.dbname: orders

# Exactly-once settings
producer.transaction.id: orders-cdc-txn
producer.enable.idempotence: true
producer.transactional.id: orders-cdc-txn-1
producer.acks: all

# Offset storage (Kafka topic)
offset.storage.topic: connect-offsets
offset.storage.replication.factor: 3
offset.flush.interval.ms: 10000
```

**State Management**
```
Connector state:
  - Database LSN/binlog position
  - Kafka offset
  - Snapshot progress

Failure scenarios:
  1. Connector crash → Resume from last committed offset
  2. Database rewind → Detect via LSN, handle duplicates
  3. Kafka unavailable → Buffer + retry with backoff
```

#### 3.2.2 Sink Connectors (Kafka → Database/Storage)

**Idempotent Writes**
```sql
-- Upsert pattern (PostgreSQL)
INSERT INTO target_table (id, name, updated_at)
VALUES (%s, %s, %s)
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name,
    updated_at = EXCLUDED.updated_at
WHERE target_table.updated_at < EXCLUDED.updated_at;

-- Idempotency key (alternate approach)
CREATE TABLE processed_events (
    event_id UUID PRIMARY KEY,
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Check before processing
SELECT 1 FROM processed_events WHERE event_id = %s;
-- If exists: skip
-- If not exists: process + insert event_id
```

### 3.3 Watermarking Strategies

**Event Time vs Processing Time**
```
Event time: When event occurred (timestamp in data)
Processing time: When system processes event

Watermark: "All events with timestamp ≤ T have been seen"

Strategies:
1. Periodic watermark: Emit every N seconds
2. Bounded out-of-order: T = max_seen_timestamp - allowed_lateness
3. Per-partition watermark: Track per Kafka partition
```

**Implementation (Flink-style)**
```python
class BoundedOutOfOrderWatermark(WatermarkStrategy):
    def __init__(self, max_lateness_ms):
        self.max_lateness_ms = max_lateness_ms
        self.max_timestamp = 0

    def on_event(self, event):
        self.max_timestamp = max(self.max_timestamp, event.timestamp)
        return self.max_timestamp - self.max_lateness_ms

    def on_periodic_emit(self):
        return self.max_timestamp - self.max_lateness_ms

# Window with watermark
stream.window(
    tumbling_window(minutes=5)
).allowed_lateness(seconds=30)

# Events arriving late (after watermark + lateness):
# → Dropped or sent to side output
```

---

## Topic 4: Caching & Invalidation

### 4.1 Write-Through vs Write-Back Patterns

**Write-Through Cache**
```
Write flow:
  1. Application writes to cache
  2. Cache synchronously writes to DB
  3. Return success to application

Pros:
  + Cache always consistent with DB
  + No data loss on cache failure

Cons:
  - Higher write latency
  - Cache becomes write bottleneck

Use case: Read-heavy with critical consistency
```

**Write-Back (Write-Behind) Cache**
```
Write flow:
  1. Application writes to cache
  2. Return success immediately
  3. Cache asynchronously writes to DB (batched)

Pros:
  + Low write latency
  + Write batching reduces DB load

Cons:
  - Risk of data loss (cache crash before flush)
  - Complex failure handling

Use case: Write-heavy with eventual consistency acceptable
```

### 4.2 Cache Coherence Protocols

**MESI Protocol (Modified, Exclusive, Shared, Invalid)**
```
States:
  Modified (M): Cache has only copy, modified
  Exclusive (E): Cache has only copy, clean
  Shared (S): Multiple caches have copy
  Invalid (I): Cache line is stale

Transitions:
  - Read: I → S (or E if only cache)
  - Write: S → M, E → M, I → M
  - Invalidation: M/E/S → I (on other cache's write)

Distributed implementation:
  - Pub/sub for invalidation messages
  - Version vectors for consistency
  - Quorum reads for strong consistency
```

**Distributed Cache Invalidation**
```python
class DistributedCache:
    def __init__(self, cache_nodes, pubsub):
        self.local_cache = {}
        self.pubsub = pubsub
        self.pubsub.subscribe('cache_invalidation', self.on_invalidation)

    def set(self, key, value):
        # Write to all nodes
        self.local_cache[key] = value

        # Broadcast invalidation
        self.pubsub.publish('cache_invalidation', {
            'key': key,
            'version': self.get_version(key),
            'source_node': self.node_id
        })

    def get(self, key):
        return self.local_cache.get(key)

    def on_invalidation(self, message):
        key = message['key']
        remote_version = message['version']

        if key in self.local_cache:
            local_version = self.get_version(key)
            if remote_version > local_version:
                del self.local_cache[key]  # Invalidate
```

### 4.3 Materialized View Invalidation

**Incremental View Maintenance**
```sql
-- Base tables
CREATE TABLE orders (
    order_id INT,
    customer_id INT,
    amount DECIMAL,
    created_at TIMESTAMP
);

-- Materialized view
CREATE MATERIALIZED VIEW daily_revenue AS
SELECT
    DATE(created_at) AS date,
    SUM(amount) AS total_revenue,
    COUNT(*) AS order_count
FROM orders
GROUP BY DATE(created_at);

-- Incremental refresh (PostgreSQL-style)
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_revenue;

-- Manual incremental update
CREATE FUNCTION update_daily_revenue() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO daily_revenue (date, total_revenue, order_count)
    VALUES (DATE(NEW.created_at), NEW.amount, 1)
    ON CONFLICT (date) DO UPDATE
    SET total_revenue = daily_revenue.total_revenue + NEW.amount,
        order_count = daily_revenue.order_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER orders_insert
AFTER INSERT ON orders
FOR EACH ROW EXECUTE FUNCTION update_daily_revenue();
```

---

## Topic 5: Backpressure & Flow Control

### 5.1 Token-Based Backpressure

**Token Bucket Algorithm**
```python
class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity  # Max tokens
        self.tokens = capacity
        self.refill_rate = refill_rate  # Tokens per second
        self.last_refill = time.time()

    def try_consume(self, tokens=1):
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

# Rate limiting with backpressure
bucket = TokenBucket(capacity=100, refill_rate=10)

def handle_request(request):
    if bucket.try_consume():
        return process(request)
    else:
        return Response("Rate limit exceeded", 429,
                       headers={"Retry-After": "1"})
```

### 5.2 Load Regulation Across Service Graphs

**Adaptive Concurrency Limits**
```python
class AdaptiveConcurrencyLimit:
    def __init__(self, initial_limit=100):
        self.limit = initial_limit
        self.in_flight = 0
        self.min_rtt = float('inf')
        self.recent_rtts = deque(maxlen=100)

    def acquire(self):
        if self.in_flight >= self.limit:
            return False
        self.in_flight += 1
        return True

    def release(self, rtt):
        self.in_flight -= 1
        self.recent_rtts.append(rtt)
        self._update_limit(rtt)

    def _update_limit(self, rtt):
        self.min_rtt = min(self.min_rtt, rtt)

        # Gradient-based adjustment
        if rtt < self.min_rtt * 2:
            # Fast response: increase limit
            self.limit = min(self.limit + 1, 1000)
        elif rtt > self.min_rtt * 4:
            # Slow response: decrease limit
            self.limit = max(self.limit - 1, 10)

# Little's Law: L = λ × W
# Optimal concurrency = throughput × latency
```

### 5.3 Circuit Breaker Patterns

**Implementation**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None

    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpen("Circuit is open")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def on_success(self):
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```

---

## Topic 6: Network Reality Deep Dive

### 6.1 TCP/QUIC/HTTP3 Implications

**TCP Head-of-Line Blocking**
```
Problem: Packet loss blocks all streams

TCP behavior:
  - Packet 5 lost
  - Packets 6, 7, 8 arrive (buffered)
  - Application blocked until packet 5 retransmitted
  - Entire connection stalled

QUIC solution:
  - Multiple streams per connection
  - Independent stream delivery
  - Stream 1 loss doesn't block Stream 2
```

**QUIC Configuration**
```yaml
# nginx with QUIC/HTTP3
http {
    server {
        listen 443 quic reuseport;
        listen 443 ssl http2;  # Fallback to HTTP/2

        ssl_certificate /path/to/cert.pem;
        ssl_certificate_key /path/to/key.pem;

        # QUIC-specific settings
        quic_retry on;
        quic_gso on;  # Generic Segmentation Offload
        ssl_early_data on;  # 0-RTT

        # Alt-Svc header for HTTP/3 advertisement
        add_header Alt-Svc 'h3=":443"; ma=86400';
    }
}
```

### 6.2 BBR Congestion Control

**BBR Algorithm**
```
Traditional TCP (CUBIC): Reacts to packet loss
BBR: Models network bandwidth and RTT

BBR phases:
  1. STARTUP: Exponential search for bandwidth
  2. DRAIN: Drain excess queue
  3. PROBE_BW: Cycle sending rate (±25%)
  4. PROBE_RTT: Minimize RTT periodically

Linux configuration:
  sysctl -w net.ipv4.tcp_congestion_control=bbr
  sysctl -w net.core.default_qdisc=fq

Benefits:
  - 2-10x throughput improvement (lossy networks)
  - Lower latency (less queue buildup)
  - Fairness with competing flows
```

### 6.3 ECMP and Flow Hashing

**Problem: Per-Flow Hashing**
```
ECMP (Equal-Cost Multi-Path) routing:
  - Multiple paths with same cost
  - Hash flow (src IP, dst IP, src port, dst port, protocol)
  - Route all packets of flow to same path

Elephant flow problem:
  - Single large flow dominates one path
  - Other paths underutilized
  - Load imbalance

Solutions:
  1. Flowlet switching: Split flow into bursts
  2. Weighted ECMP: Adjust per-path weights
  3. Adaptive routing: Monitor and rebalance
```

---

## 7. Operational Playbooks

### 7.1 CDC Pipeline Monitoring

**Key Metrics**
```
1. Replication lag: Current time - event timestamp
   Alert: lag > 60 seconds

2. Connector throughput: Events processed/sec
   Baseline: 1000-10000 events/sec

3. Error rate: Failed events / total events
   Alert: error_rate > 0.1%

4. Database load: CPU, I/O impact of CDC
   Alert: CPU > 80%

Prometheus queries:
  # Replication lag
  (time() - debezium_lag_milliseconds/1000) > 60

  # Throughput
  rate(debezium_events_total[5m])

  # Error rate
  rate(debezium_errors_total[5m]) /
  rate(debezium_events_total[5m])
```

### 7.2 Cache Invalidation Verification

**Testing Protocol**
```bash
#!/bin/bash
# Verify cache invalidation across all nodes

KEY="test:user:123"
VALUE="v$(date +%s)"

echo "1. Write to cache"
curl -X POST http://cache-node-1:8080/set \
  -d "key=$KEY&value=$VALUE"

sleep 2  # Allow propagation

echo "2. Read from all nodes"
for node in cache-node-{1..5}; do
  result=$(curl -s http://$node:8080/get?key=$KEY)
  if [ "$result" != "$VALUE" ]; then
    echo "FAIL: Node $node has stale value: $result"
    exit 1
  fi
done

echo "3. Invalidate"
curl -X POST http://cache-node-1:8080/delete \
  -d "key=$KEY"

sleep 1

echo "4. Verify invalidation"
for node in cache-node-{1..5}; do
  result=$(curl -s http://$node:8080/get?key=$KEY)
  if [ -n "$result" ]; then
    echo "FAIL: Node $node still has value: $result"
    exit 1
  fi
done

echo "SUCCESS: Cache invalidation working"
```

### 7.3 Backpressure Testing

**Load Test with Backpressure**
```python
import asyncio
import time

async def load_test_with_backpressure():
    """Gradually increase load until backpressure activates"""

    rate = 100  # Start at 100 req/s
    max_rate = 10000

    while rate < max_rate:
        start = time.time()
        responses = []

        for _ in range(rate):
            try:
                resp = await send_request()
                responses.append(resp)
            except RateLimitExceeded:
                print(f"Backpressure at {rate} req/s")
                return rate

        elapsed = time.time() - start

        # Calculate actual throughput
        throughput = len(responses) / elapsed

        # Measure latency
        p99 = np.percentile([r.latency for r in responses], 99)

        print(f"Rate: {rate}, Throughput: {throughput:.0f}, P99: {p99:.0f}ms")

        # Stop if P99 > 1000ms (degradation)
        if p99 > 1000:
            print(f"Latency degradation at {rate} req/s")
            return rate

        # Increase rate by 10%
        rate = int(rate * 1.1)

    return max_rate

# Run test
max_throughput = asyncio.run(load_test_with_backpressure())
print(f"Maximum sustainable throughput: {max_throughput} req/s")
```

---

## 8. Production Case Studies

### 8.1 LinkedIn's Brooklin (CDC at Scale)

**Architecture**
- Multi-datacenter CDC
- 1000+ connectors
- 100TB+ daily throughput
- Custom connector framework

**Lessons Learned**
1. Stateful connectors need reliable checkpointing
2. Backpressure essential at high throughput
3. Monitoring lag critical for SLA

### 8.2 Netflix's Distributed Caching

**EVCache (Ephemeral Volatile Cache)**
- Multi-region replication
- Zone-aware reads
- Memcached-based
- 30 trillion requests/day

**Strategies**
- Write-through for critical data
- TTL-based invalidation
- Zone failure transparent

### 8.3 Google's BBR Deployment

**Impact**
- 4% throughput increase (video streaming)
- 40% latency reduction (international)
- 2x throughput (India, Indonesia)

**Challenges**
- Fairness with CUBIC flows
- Router queue management
- Tuning for specific networks

---

## Summary

These cross-cutting topics interact with core distributed systems concepts throughout the book:

1. **CDC & Streaming**: Enables event-driven architectures, requires exactly-once semantics
2. **Caching**: Reduces latency, introduces consistency challenges
3. **Backpressure**: Protects systems from overload, prevents cascading failures
4. **Network Reality**: Fundamental constraints, influences protocol design

Key takeaway: Distributed systems require holistic thinking. Each decision (caching strategy, CDC pipeline, congestion control) affects multiple system properties (latency, consistency, availability, cost).

---

## Further Reading

### Books
- "Streaming Systems" by Akidau, Chernyak, Lax
- "Database Internals" by Petrov
- "TCP/IP Illustrated" by Stevens

### Papers
- "Kafka: a Distributed Messaging System for Log Processing" (2011)
- "BBR: Congestion-Based Congestion Control" (2016)
- "Dataflow Model" (Google, 2015)

### Tools
- Debezium: CDC platform
- Apache Flink: Stream processing
- Envoy: L7 proxy with flow control

---

## Exercises

### Exercise 1: CDC Pipeline Design
Design a CDC pipeline for a multi-tenant SaaS application:
- Source: PostgreSQL (100 tables)
- Target: Elasticsearch (search), S3 (analytics)
- Requirements: <5s lag, no data loss, tenant isolation

### Exercise 2: Cache Coherence Protocol
Implement a distributed cache with strong consistency:
- 3 cache nodes
- Read-your-writes guarantee
- Linearizable operations

### Exercise 3: Backpressure Simulation
Simulate a service graph with backpressure:
- 3 services (A → B → C)
- B has capacity limit
- Demonstrate backpressure propagation

Solutions provided in appendix with detailed implementations.
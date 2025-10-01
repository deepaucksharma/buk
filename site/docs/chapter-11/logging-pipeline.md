# Logging Pipeline: The Forensics of Distributed Systems

## Introduction: The Needle in a Billion Haystacks

At 3:47 AM, a customer reports: "I tried to purchase item #AB-12345, but got error 'Payment failed.' My card was charged anyway."

You open your logging system. Your distributed system generates:

- **1 billion log lines per hour** (across 100 services, 1,000 instances)
- **10TB of log data per day**
- **Customer's request**: 1 request among 100 million requests per hour

**The challenge**: Find the 20 log lines (out of 1 billion) that explain what happened to this specific request.

Without a well-designed logging pipeline, this is impossible. With one, it takes 30 seconds:

```
# Search for request by customer order number
order_id:AB-12345

Results (23 log lines, 847ms):
  [checkout-service] 2024-01-15 03:47:23 INFO order_id=AB-12345 user_id=user_789 Checkout initiated
  [payment-service] 2024-01-15 03:47:24 INFO order_id=AB-12345 payment_id=pay_456 Charging card
  [payment-gateway] 2024-01-15 03:47:26 INFO order_id=AB-12345 payment_id=pay_456 Stripe charge succeeded
  [payment-service] 2024-01-15 03:47:27 ERROR order_id=AB-12345 payment_id=pay_456 Database write failed: Deadlock
  [payment-service] 2024-01-15 03:47:27 ERROR order_id=AB-12345 payment_id=pay_456 Retry exhausted, returning error to client
  [checkout-service] 2024-01-15 03:47:27 ERROR order_id=AB-12345 Payment failed, reverting order
```

**Root cause**: Payment succeeded at Stripe, but database write failed due to deadlock. Customer was charged, but order wasn't recorded.

**Fix**: Retry database write with exponential backoff, or use idempotency keys to prevent duplicate charges.

This is **logging as forensics**: the ability to reconstruct what happened to any request, at any time, even months later.

### Why Logs Matter

Logs are the **narrative** of your system:

- **Metrics** tell you "what" (latency increased)
- **Traces** tell you "where" (bottleneck in Payment Service)
- **Logs** tell you "why" (database deadlock on payment_transactions table)

Logs capture:

- **Errors**: Exception messages, stack traces
- **Business events**: "Order placed," "Payment charged," "Email sent"
- **Debugging context**: Variable values, function arguments, state transitions
- **Audit trails**: Who accessed what, when (compliance, security)

### The Three Phases of Logging

**1. Generation**: Applications emit log lines

**2. Collection**: Log lines shipped from instances to central storage

**3. Querying**: Engineers search logs to answer questions

Each phase has distinct challenges at scale.

## Part 1: Structured Logging — From Text to Data

### The Unstructured Logging Problem

**Traditional logging** (text-based):

```python
import logging

logger = logging.getLogger(__name__)

def checkout(user_id, cart_id):
    logger.info(f"User {user_id} is checking out cart {cart_id}")

    try:
        order = create_order(user_id, cart_id)
        logger.info(f"Order {order.id} created for user {user_id}, total ${order.total}")
    except Exception as e:
        logger.error(f"Order creation failed for user {user_id}, cart {cart_id}: {str(e)}")
```

**Output** (text):

```
2024-01-15 10:23:45 INFO User user_789 is checking out cart cart_456
2024-01-15 10:23:46 INFO Order order_123 created for user user_789, total $99.99
2024-01-15 10:23:50 ERROR Order creation failed for user user_234, cart cart_567: Database connection timeout
```

**Problem**: Logs are **human-readable but machine-unparseable**.

**Query**: "Find all failed orders for user_234"

- **Solution**: Parse text with regex: `grep "Order creation failed" | grep "user_234"`
- **Issue**: Brittle (breaks if log format changes), slow (must scan every line)

### Structured Logging: JSON-Based

**Structured logging** emits logs as **JSON objects**:

```python
import structlog

logger = structlog.get_logger()

def checkout(user_id, cart_id):
    logger.info("checkout_initiated", user_id=user_id, cart_id=cart_id)

    try:
        order = create_order(user_id, cart_id)
        logger.info("order_created", user_id=user_id, order_id=order.id, total=order.total)
    except Exception as e:
        logger.error("order_creation_failed", user_id=user_id, cart_id=cart_id, error=str(e))
```

**Output** (JSON):

```json
{"timestamp": "2024-01-15T10:23:45Z", "level": "info", "event": "checkout_initiated", "user_id": "user_789", "cart_id": "cart_456"}
{"timestamp": "2024-01-15T10:23:46Z", "level": "info", "event": "order_created", "user_id": "user_789", "order_id": "order_123", "total": 99.99}
{"timestamp": "2024-01-15T10:23:50Z", "level": "error", "event": "order_creation_failed", "user_id": "user_234", "cart_id": "cart_567", "error": "Database connection timeout"}
```

**Query**: "Find all failed orders for user_234"

- **Solution**: Query structured data: `event:order_creation_failed AND user_id:user_234`
- **Benefit**: Fast (indexed fields), flexible (can query by any field)

### Best Practices for Structured Logging

**1. Always include correlation IDs**:

```python
logger.info("payment_processed",
    request_id="req_a7f3c2d1",      # Unique request ID (matches trace ID)
    user_id="user_789",              # User context
    order_id="order_123",            # Business entity
    payment_id="pay_456",            # Business entity
    amount=99.99
)
```

**Why**: Correlation IDs link logs to traces and metrics.

**2. Use consistent field names**:

```python
# Bad: inconsistent naming
logger.info("event", userId="user_789")  # camelCase
logger.info("event", user_id="user_789")  # snake_case

# Good: consistent naming (choose one convention)
logger.info("event", user_id="user_789")
logger.info("event", order_id="order_123")
```

**Why**: Consistent field names enable cross-service queries.

**3. Include context, not just messages**:

```python
# Bad: no context
logger.error("Payment failed")

# Good: rich context
logger.error("payment_failed",
    error_type="card_declined",
    error_code="insufficient_funds",
    payment_id="pay_456",
    user_id="user_789",
    amount=99.99,
    card_last4="1234"
)
```

**Why**: Context enables debugging without adding print statements.

**4. Log at the right level**:

- **DEBUG**: Verbose information (function entry/exit, variable values) — disabled in production
- **INFO**: Business events (order placed, payment charged) — enabled in production
- **WARNING**: Recoverable errors (retry succeeded, fallback used) — enabled
- **ERROR**: Unrecoverable errors (payment failed, database down) — enabled
- **CRITICAL**: System-wide failures (service crashed, data corruption) — enabled

**5. Never log sensitive data**:

```python
# Bad: logs plaintext password
logger.info("user_login", username=username, password=password)

# Good: logs only non-sensitive data
logger.info("user_login", username=username, ip_address=request.remote_addr)

# Acceptable: logs masked data
logger.info("payment_processed", card_last4=card[-4:], amount=amount)
```

**Why**: Logs are often stored unencrypted. Leaking credentials or PII = security incident.

### Automatic Context Injection

**Problem**: Manually adding `request_id`, `user_id` to every log statement is tedious.

**Solution**: Use **context managers** or **middleware** to inject context automatically.

```python
import structlog
from contextvars import ContextVar

# Global context
request_context = ContextVar("request_context", default={})

# Middleware (Flask example)
@app.before_request
def inject_context():
    context = {
        "request_id": request.headers.get("X-Request-ID", generate_id()),
        "user_id": get_current_user_id(),
        "ip_address": request.remote_addr
    }
    request_context.set(context)

    # Bind context to all log statements in this request
    structlog.contextvars.bind_contextvars(**context)

@app.after_request
def clear_context(response):
    structlog.contextvars.clear_contextvars()
    return response

# Application code (no manual context passing)
logger = structlog.get_logger()

def checkout():
    # Automatically includes request_id, user_id, ip_address
    logger.info("checkout_initiated")
```

**Output**:

```json
{
  "timestamp": "2024-01-15T10:23:45Z",
  "level": "info",
  "event": "checkout_initiated",
  "request_id": "req_a7f3c2d1",
  "user_id": "user_789",
  "ip_address": "203.0.113.42"
}
```

**Benefit**: Consistent context across all log statements, without manual effort.

## Part 2: The ELK Stack — Elasticsearch, Logstash, Kibana

### The De Facto Standard

The **ELK stack** (now called **Elastic Stack**) is the most popular open-source logging solution:

- **Elasticsearch**: Distributed search engine for storing and querying logs
- **Logstash**: Log ingestion pipeline (parse, filter, enrich logs)
- **Kibana**: Web UI for querying and visualizing logs
- **Beats** (optional): Lightweight log shippers (Filebeat, Metricbeat)

### Architecture

```
[Application Instances]
        │
        ├─ (writes logs to file or stdout)
        │
        ↓
[Filebeat] (log shipper, per-instance)
        │
        ├─ (reads log files, ships to Logstash)
        │
        ↓
[Logstash] (ingestion pipeline)
        │
        ├─ Parse JSON logs
        ├─ Filter (drop debug logs in production)
        ├─ Enrich (add geolocation from IP address)
        ├─ Transform (normalize field names)
        │
        ↓
[Elasticsearch] (storage + indexing)
        │
        ├─ Index logs by timestamp, fields
        ├─ Store in shards (distributed across nodes)
        ├─ Replicate for durability
        │
        ↓
[Kibana] (query UI)
        │
        └─ Search, filter, visualize logs
```

### Setting Up Elasticsearch

**Docker Compose** (single-node development):

```yaml
version: '3'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms2g -Xmx2g  # 2GB heap
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

volumes:
  es_data:
```

**Logstash configuration** (`logstash.conf`):

```
input {
  beats {
    port => 5044  # Receive logs from Filebeat
  }
}

filter {
  # Parse JSON logs
  json {
    source => "message"
  }

  # Add geolocation from IP address
  geoip {
    source => "ip_address"
    target => "geoip"
  }

  # Drop debug logs in production
  if [level] == "debug" {
    drop { }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{+YYYY.MM.dd}"  # Daily indices
  }
}
```

**Filebeat configuration** (`filebeat.yml`):

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/app/*.log  # Application log files

output.logstash:
  hosts: ["logstash:5044"]
```

**Application** (writes JSON logs to file):

```python
import structlog

logger = structlog.get_logger()

# Configure to write JSON to file
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
)

logger.info("app_started", version="1.2.3")
```

### Querying Logs in Kibana

**Simple query** (Kibana Query Language, KQL):

```
# Find all errors
level: error

# Find errors for specific user
level: error AND user_id: "user_789"

# Find errors in specific time range
level: error AND @timestamp >= "2024-01-15T00:00:00" AND @timestamp < "2024-01-16T00:00:00"

# Find payment failures
event: payment_failed

# Find slow requests (latency >1s)
latency_ms > 1000
```

**Advanced query** (Elasticsearch Query DSL, JSON):

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "event": "payment_failed" } },
        { "range": { "@timestamp": { "gte": "now-1h" } } }
      ],
      "filter": [
        { "term": { "error_type": "card_declined" } }
      ]
    }
  },
  "size": 100,
  "sort": [
    { "@timestamp": "desc" }
  ]
}
```

**Aggregation query** (count errors by type):

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "level": "error" } },
        { "range": { "@timestamp": { "gte": "now-1h" } } }
      ]
    }
  },
  "aggs": {
    "error_types": {
      "terms": {
        "field": "error_type.keyword",
        "size": 10
      }
    }
  },
  "size": 0
}
```

**Result**:

```json
{
  "aggregations": {
    "error_types": {
      "buckets": [
        { "key": "database_timeout", "doc_count": 342 },
        { "key": "card_declined", "doc_count": 156 },
        { "key": "rate_limit_exceeded", "doc_count": 89 },
        { "key": "service_unavailable", "doc_count": 23 }
      ]
    }
  }
}
```

### Elasticsearch Index Management

**Challenge**: Logs grow indefinitely. A 10TB/day system = 3.6PB/year.

**Solution**: **Index lifecycle management (ILM)** — automatically delete old logs.

**ILM policy**:

```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "50GB",
            "max_age": "1d"
          }
        }
      },
      "warm": {
        "min_age": "3d",
        "actions": {
          "shrink": {
            "number_of_shards": 1
          },
          "forcemerge": {
            "max_num_segments": 1
          }
        }
      },
      "cold": {
        "min_age": "7d",
        "actions": {
          "freeze": {}
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

**Phases**:

- **Hot**: Recent logs (0-3 days), high write rate, stored on SSD
- **Warm**: Older logs (3-7 days), low write rate, optimized for storage
- **Cold**: Old logs (7-30 days), rarely queried, stored on cheaper storage
- **Delete**: Very old logs (>30 days), deleted to save cost

**Cost impact**:

- **Without ILM**: 10TB/day × 365 days = 3.6PB/year × $0.10/GB = $360,000/year
- **With ILM (30-day retention)**: 10TB/day × 30 days = 300TB × $0.10/GB = $30,000/year

**Savings**: 91% reduction in storage cost.

## Part 3: Log Aggregation Patterns — From Instances to Insights

### The Distributed Logging Challenge

**Scenario**: User reports "checkout is broken." You have 100 instances of `checkout-service`, each logging to its own file.

**Problem**: Which instance handled the request? How do you correlate logs across instances?

**Solution**: **Centralized logging** — all instances send logs to a central system (Elasticsearch).

### Log Shipping Strategies

**1. Direct shipping (application → Elasticsearch)**:

```python
from cmreslogging.handlers import CMRESHandler

handler = CMRESHandler(
    hosts=[{'host': 'elasticsearch', 'port': 9200}],
    auth_type=CMRESHandler.AuthType.NO_AUTH,
    es_index_name="logs"
)
logger.addHandler(handler)

logger.info("event", user_id="user_789")  # Sent directly to Elasticsearch
```

**Pros**: Simple, no intermediate components
**Cons**: Application blocks on log writes (network latency), no buffering (if Elasticsearch down, logs lost)

**2. File-based shipping (application → file → Filebeat → Logstash → Elasticsearch)**:

```python
# Application writes to file
logger.addHandler(logging.FileHandler("/var/log/app/app.log"))

# Filebeat reads file, ships to Logstash
# (configured separately)
```

**Pros**: Application doesn't block (writes to file are fast), buffering (Filebeat retries if Logstash down)
**Cons**: More components to manage, potential log loss if instance crashes before Filebeat ships logs

**3. Message queue (application → Kafka → Logstash → Elasticsearch)**:

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(bootstrap_servers=['kafka:9092'])

class KafkaHandler(logging.Handler):
    def emit(self, record):
        log_entry = {
            "timestamp": record.created,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        producer.send('logs', json.dumps(log_entry).encode())

logger.addHandler(KafkaHandler())
```

**Pros**: High durability (Kafka retains logs), decoupling (application and Logstash run independently), backpressure handling (Kafka buffers during spikes)
**Cons**: Added complexity (must run Kafka cluster), higher latency (logs buffered in Kafka)

**Best practice**: Use **file-based shipping** (application → Filebeat → Logstash) for most use cases. Use **Kafka** for high-volume systems (>10TB/day) requiring durability guarantees.

### Sampling High-Volume Logs

**Problem**: Application generates 1,000 log lines per second (INFO level). Storing all = 100GB/day.

**Solution**: **Sample logs** — keep only a subset.

**Sampling strategies**:

**1. Probabilistic sampling** (keep 1% of logs):

```python
import random

class SamplingHandler(logging.Handler):
    def __init__(self, handler, sample_rate=0.01):
        super().__init__()
        self.handler = handler
        self.sample_rate = sample_rate

    def emit(self, record):
        if random.random() < self.sample_rate:
            self.handler.emit(record)

# Keep 1% of INFO logs, 100% of ERROR logs
info_handler = SamplingHandler(logging.FileHandler("app.log"), sample_rate=0.01)
info_handler.setLevel(logging.INFO)

error_handler = logging.FileHandler("errors.log")
error_handler.setLevel(logging.ERROR)

logger.addHandler(info_handler)
logger.addHandler(error_handler)
```

**2. Rate-based sampling** (keep max 100 logs/second):

```python
import time
from collections import deque

class RateLimitHandler(logging.Handler):
    def __init__(self, handler, max_rate=100):
        super().__init__()
        self.handler = handler
        self.max_rate = max_rate
        self.log_times = deque()

    def emit(self, record):
        now = time.time()

        # Remove logs older than 1 second
        while self.log_times and self.log_times[0] < now - 1:
            self.log_times.popleft()

        # If under rate limit, emit log
        if len(self.log_times) < self.max_rate:
            self.log_times.append(now)
            self.handler.emit(record)

logger.addHandler(RateLimitHandler(logging.FileHandler("app.log"), max_rate=100))
```

**3. Error-based sampling** (always keep errors, sample successes):

```python
class ErrorAwareHandler(logging.Handler):
    def __init__(self, handler, success_sample_rate=0.01):
        super().__init__()
        self.handler = handler
        self.success_sample_rate = success_sample_rate

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            # Always keep errors
            self.handler.emit(record)
        elif random.random() < self.success_sample_rate:
            # Sample successes
            self.handler.emit(record)

logger.addHandler(ErrorAwareHandler(logging.FileHandler("app.log")))
```

**Best practice**: Always keep 100% of ERROR and CRITICAL logs. Sample INFO and DEBUG logs aggressively (1-10%).

## Part 4: Cost Optimization — Logging on a Budget

### The Cost Reality

**Elasticsearch storage cost**:

- **SSD storage**: $0.10/GB/month (AWS EBS gp3)
- **10TB/day system**: 300TB × $0.10 = $30,000/month (with 30-day retention)
- **Annual cost**: $360,000/year

**Trade-offs**:

- **Increase retention**: 90 days instead of 30 = 3× cost = $1M/year
- **Decrease retention**: 7 days instead of 30 = 4× savings = $90,000/year

### Cost Optimization Strategies

**1. Hot/warm/cold storage tiers**:

- **Hot (0-3 days)**: SSD, fully indexed, fast queries
- **Warm (3-30 days)**: HDD, indexed, slower queries
- **Cold (30-90 days)**: S3, compressed, very slow queries

```json
{
  "policy": {
    "phases": {
      "hot": { "min_age": "0ms" },
      "warm": {
        "min_age": "3d",
        "actions": {
          "allocate": {
            "require": { "box_type": "warm" }
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "searchable_snapshot": {
            "snapshot_repository": "s3-repo"
          }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": { "delete": {} }
      }
    }
  }
}
```

**Cost impact**:

- Hot (3 days): 30TB × $0.10 = $3,000/month
- Warm (27 days): 270TB × $0.03 (HDD) = $8,100/month
- Cold (60 days): 600TB × $0.01 (S3) = $6,000/month
- **Total**: $17,100/month (vs $30,000 with all SSD)

**Savings**: 43% reduction.

**2. Log-level filtering in production**:

```python
# Development: log everything (DEBUG and above)
if os.getenv("ENV") == "development":
    logger.setLevel(logging.DEBUG)
else:
    # Production: log only INFO and above (drop DEBUG)
    logger.setLevel(logging.INFO)
```

**Impact**: DEBUG logs often account for 80% of log volume. Dropping them = 5× reduction.

**3. Selective field indexing**:

```json
{
  "mappings": {
    "properties": {
      "timestamp": { "type": "date", "index": true },
      "level": { "type": "keyword", "index": true },
      "user_id": { "type": "keyword", "index": true },
      "message": { "type": "text", "index": false },  // Don't index message body
      "stack_trace": { "type": "text", "index": false }  // Don't index stack traces
    }
  }
}
```

**Why**: Indexing consumes storage (2-3× overhead). Don't index fields you won't search on.

**4. Compression**:

```json
{
  "index": {
    "codec": "best_compression"  // Use DEFLATE compression (slower writes, 2x storage savings)
  }
}
```

**Trade-off**: 20% slower writes, 50% storage savings.

**5. Drop low-value logs**:

```
filter {
  # Drop health check logs (high volume, low value)
  if [endpoint] == "/health" {
    drop { }
  }

  # Drop successful GET requests (keep only errors and writes)
  if [method] == "GET" and [status] < 400 {
    drop { }
  }
}
```

**Impact**: Can reduce log volume by 50-90% depending on traffic patterns.

### Real Example: Airbnb's Logging Cost Optimization (2019)

**Before**:

- **Volume**: 50TB/day
- **Retention**: 90 days
- **Storage**: 4.5PB × $0.10/GB = $450,000/month
- **Annual cost**: $5.4M/year

**After**:

- **Sampling**: Dropped health check logs, sampled 10% of INFO logs → 10TB/day (80% reduction)
- **Tiered storage**: Hot (7 days SSD), warm (23 days HDD), cold (60 days S3)
- **Compression**: Enabled best_compression
- **Annual cost**: $500,000/year

**Savings**: $4.9M/year (91% reduction).

**Lesson**: Logging costs can spiral out of control. Ruthlessly optimize.

## Part 5: Security, Compliance, and Debugging with Logs

### Security Considerations

**1. Never log sensitive data**:

```python
# Bad
logger.info("user_login", username=username, password=password)

# Good
logger.info("user_login", username=username)
```

**2. Encrypt logs in transit and at rest**:

```yaml
# Filebeat → Logstash (TLS)
output.logstash:
  hosts: ["logstash:5044"]
  ssl.enabled: true
  ssl.certificate_authorities: ["/etc/ca.crt"]

# Elasticsearch (encryption at rest)
xpack.security.enabled: true
xpack.security.encryption_at_rest.enabled: true
```

**3. Implement access controls**:

```yaml
# Elasticsearch roles (restrict access by team)
roles:
  - name: developer
    privileges:
      - index: "logs-*"
        actions: ["read"]

  - name: admin
    privileges:
      - index: "logs-*"
        actions: ["all"]
```

### Compliance (GDPR, HIPAA)

**GDPR requirements**:

- **Right to be forgotten**: User can request deletion of all their data, including logs
- **Data residency**: Logs containing EU user data must stay in EU
- **Retention limits**: Can't keep logs indefinitely

**Implementation**:

```python
# Tag logs with user region
logger.info("event", user_id=user_id, region="EU")

# Deletion process (GDPR request)
def delete_user_logs(user_id):
    # Delete from Elasticsearch
    es.delete_by_query(
        index="logs-*",
        body={"query": {"term": {"user_id": user_id}}}
    )

    # Delete from S3 archives
    # (requires custom script to scan and redact)
```

**Challenge**: Deleting from distributed logs is expensive. Consider **log anonymization** instead:

```python
# Anonymize user IDs in logs after 30 days
def anonymize_old_logs():
    # Hash user IDs instead of storing plaintext
    es.update_by_query(
        index="logs-*",
        body={
            "script": {
                "source": "ctx._source.user_id = ctx._source.user_id.hashCode().toString()"
            },
            "query": {
                "range": {"@timestamp": {"lte": "now-30d"}}
            }
        }
    )
```

### Debugging with Logs: Real Scenarios

**Scenario 1: Finding a specific failed request**

```
# User reports: "My checkout failed at 3:47 PM"
user_id:"user_789" AND @timestamp:[2024-01-15T15:40:00 TO 2024-01-15T15:50:00] AND level:error
```

**Scenario 2: Identifying a deployment regression**

```
# Compare error rate before and after deployment
level:error AND @timestamp:[2024-01-15T14:00:00 TO 2024-01-15T15:00:00]
# vs
level:error AND @timestamp:[2024-01-15T15:00:00 TO 2024-01-15T16:00:00]
```

**Scenario 3: Correlating logs across services**

```
# Find all logs for a specific request (using request_id)
request_id:"req_a7f3c2d1"

# Results include logs from:
# - API Gateway
# - Order Service
# - Payment Service
# - Email Service
```

**Scenario 4: Detecting anomalous patterns**

```
# Find all unique error messages in last hour
# (helps identify new errors after deployment)
{
  "query": {
    "bool": {
      "must": [
        {"match": {"level": "error"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  },
  "aggs": {
    "unique_errors": {
      "terms": {
        "field": "error_type.keyword",
        "size": 50
      }
    }
  }
}
```

## Mental Model Summary

### The Logging Hierarchy

```
Business Layer:        Audit trail (who did what, when)
                            ↓
Investigation Layer:   Root cause analysis (why did it fail?)
                            ↓
Context Layer:         Correlation IDs (link logs to traces)
                            ↓
Structure Layer:       Structured logging (JSON, fields)
                            ↓
Collection Layer:      Log shipping (Filebeat, Logstash)
                            ↓
Storage Layer:         Elasticsearch (indexing, querying)
                            ↓
Cost Layer:            Retention, sampling, compression
```

### The Three Logging Truths

**1. Logs are for humans, not machines**

- Logs provide narrative ("what happened"), not metrics ("how much")
- Use logs for debugging specific issues, not monitoring overall health

**2. Structure is everything**

- Unstructured logs (text) are unparseable at scale
- Structured logs (JSON) enable fast, flexible queries

**3. Cost is a constraint**

- Logs are expensive (storage, indexing, querying)
- Ruthlessly optimize: sample, compress, delete old data

### When to Use Logs

**Use logs when**:

- Debugging a specific error (find stack trace, error message)
- Investigating user-reported issues (correlate by user ID)
- Auditing access (who accessed what, when)
- Reconstructing event sequence (what happened in what order)

**Don't use logs when**:

- Monitoring system health (use metrics)
- Tracking per-request latency (use traces)
- Real-time alerting (use metrics + alerting rules)
- High-cardinality queries (logs are slow for aggregations)

---

**Next**: Understanding how to debug distributed systems using correlation IDs, chaos engineering, and post-mortem processes.

Continue to [Debugging Distributed Systems →](debugging-distributed.md)

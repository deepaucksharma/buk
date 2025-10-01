# Chapter 15: Operating Distributed Systems

## Introduction: When Reality Calls at 3 AM

In production, there are no compiler errors—only 3 AM pages and angry customers.

You've built the perfect distributed system. The code is elegant. Tests pass. Load tests show it handles 100x current traffic. The architecture diagram is beautiful: microservices, distributed databases, message queues, caching layers. You deploy with confidence.

Then, two weeks later, your phone rings at 3:17 AM.

**"The site is slow. Users can't check out. Revenue is dropping."**

You open your laptop. Where do you even start? You have:
- 200 microservices across 5 data centers
- Logs scattered across 1,000 machines generating 100 GB/day
- Metrics in three different systems
- No idea which service is the problem
- No idea if this is load, a bug, a deployment, or infrastructure
- A VP asking for updates every 15 minutes
- Customers rage-tweeting

**This is the gap between building and operating.**

Building distributed systems is intellectually challenging. Operating them is existentially challenging. Building requires understanding consistency models, consensus algorithms, replication strategies. Operating requires knowing why the payment service latency spiked from 50ms to 5 seconds at 3:12 AM, and fixing it before the company loses $50,000.

The skills are different. Building is about correctness: does the system do what it should? Operating is about reliability: does the system keep doing what it should, despite failures, load spikes, bad deployments, network issues, cosmic rays, and that one engineer who ran a test in production?

**This chapter teaches you operational excellence.**

Not just monitoring and alerting—though we'll cover that. Not just incident response—though you'll learn that too. We're talking about the mindset shift from developer to operator, from "it works" to "it keeps working," from individual contributor to system steward.

### Why This Matters: The Operational Reality

**The uncomfortable truth**: Most distributed systems fail not because of algorithm bugs but because of operational failures:

- A deployment that seemed safe but cascaded into a total outage
- A database that ran out of disk space because nobody monitored it
- A cache invalidation bug that took a week to track down
- A configuration change that accidentally disabled circuit breakers
- A scaling event that exposed a race condition
- An incident that took 6 hours to resolve because runbooks were outdated

**The statistics are stark**:
- 70% of outages are caused by changes (deployments, configuration, infrastructure)
- Average time to detect an incident: 15 minutes
- Average time to resolve: 3.5 hours
- Cost of an hour of downtime: $100,000 to $5 million depending on company size
- Engineering time spent on operations: 40-60% for most teams

**The hidden costs**:
- Burnout from on-call rotations
- Lost innovation velocity (can't build features if you're firefighting)
- Attrition (people leave for better work-life balance)
- Customer trust erosion (every outage is remembered)
- Technical debt accumulation (quick fixes become permanent)

Operations is not separate from development. In distributed systems, they're inseparable. You can't build a reliable system without understanding operations. You can't operate effectively without understanding how it was built.

### The Operational Mindset Shift

Building distributed systems requires a certain mindset. Operating them requires a different one.

**From "it works" to "it will fail"**

Developers think in terms of happy paths. Operators think in terms of failure modes. It's not pessimism—it's realism. Everything eventually fails:
- Servers crash
- Networks partition
- Databases fill up
- Dependencies go down
- Load spikes happen
- Humans make mistakes

The question isn't "will it fail?" but "when it fails, what happens?" Good operators design for failure, monitor for failure, practice failure, and recover from failure gracefully.

**From fixing bugs to preventing outages**

In development, you write code, find bugs, fix them, repeat. In operations, you prevent bugs from becoming outages. The shift is from reactive to proactive:
- Instead of fixing crashes, you add health checks
- Instead of debugging logs, you add structured logging
- Instead of guessing load, you add metrics
- Instead of hoping for the best, you test failure modes
- Instead of manual fixes, you automate runbooks

**From perfect code to graceful degradation**

Developers want perfect code. Operators accept imperfect reality. Perfect code doesn't exist. Perfect infrastructure doesn't exist. The goal isn't perfection—it's resilience:
- When the cache fails, serve from database
- When the database is slow, return cached data
- When the third-party API is down, queue requests
- When load spikes, shed non-critical work
- When things break, fail gracefully with clear errors

**From features to reliability**

Developers are measured by features shipped. Operators are measured by uptime. The tension is real:
- Every feature is potential risk (new code = new bugs)
- Every deployment is potential downtime (changes cause outages)
- Every optimization is potential instability (performance vs safety)

The best teams balance both. They use error budgets: if reliability is good, ship faster; if reliability is bad, slow down and fix issues. They use progressive rollouts: deploy to 1%, then 10%, then 100%. They use feature flags: deploy code without activating it.

**From individual to team resilience**

A single server can be understood by one person. A distributed system requires a team. Operations is team sport:
- On-call rotations spread the burden
- Runbooks share knowledge
- Postmortems share lessons
- Blameless culture encourages honesty
- Automation reduces toil
- Documentation preserves context

The goal is team resilience, not hero culture. Systems should be operable by anyone on the team, not just the one person who built it.

### What This Chapter Will Teach You

**Part 1: INTUITION (First Pass)**—The experiences that change how you think
- Your first on-call experience and what it teaches
- The cascade failure you'll never forget
- When monitoring lies to you
- The rollback that made things worse
- Learning that everything breaks eventually

**Part 2: UNDERSTANDING (Second Pass)**—The practices that work
- Observability: How to see into the system (metrics, logs, traces)
- Incident Response: How to respond when things break
- Capacity Planning: How to stay ahead of growth
- Performance Management: How to define and meet SLOs
- Automation: How to reduce toil and scale operations

**Part 3: MASTERY (Third Pass)**—The patterns of operational excellence
- Advanced monitoring patterns (anomaly detection, synthetic monitoring)
- Chaos engineering (testing failure in production)
- Progressive delivery (deploying without risk)
- On-call excellence (sustainable operations)
- Disaster recovery (planning for the worst)

### The Evidence-Based Operations Framework

Throughout this book, we've framed distributed systems as evidence-generating machines. Operations is about continuously verifying that evidence:

1. **Observability is evidence generation**: Metrics, logs, and traces are evidence that the system is working
2. **Monitoring is evidence verification**: Alerts fire when evidence shows problems
3. **Incidents are evidence failures**: Something violated an invariant
4. **Postmortems are evidence analysis**: Understanding what went wrong
5. **Improvements are evidence strengthening**: Making failures less likely

The operational mindset is: "How do I know the system is working? How quickly can I detect when it's not? How fast can I recover?"

Let's begin with the experiences that teach you operational thinking.

---

## Part 1: INTUITION (First Pass)—The Experiences That Teach You

### The First On-Call Experience

You'll remember your first on-call week for the rest of your career.

**Monday, 9 AM**: You start your on-call rotation. You've read the runbooks. You've tested the paging system. You know how to access the monitoring dashboards. You're ready.

**Monday, 3 PM**: First page. "High error rate in payment service." You investigate. Turns out a third-party API is returning 500s. You route traffic to a backup provider. Fixed in 20 minutes. You feel competent.

**Tuesday, 2 AM**: Phone buzzes. "Database CPU at 95%." You're groggy. You log in, check metrics. There's a slow query consuming resources. You kill it. Add an index. CPU drops. Back to sleep. You feel capable.

**Wednesday, 3:17 AM**: "URGENT: Site is down. Revenue impact."

This is different. You're fully awake now. You open the incident Slack channel. Messages are flying:
- "Users reporting checkout failures"
- "API gateway returning 503s"
- "Load balancer health checks failing"
- "No recent deployments"
- "CPU and memory look normal"

You start investigating. Checkout service logs show database connection timeouts. Database metrics show... normal load? Connection pool is full. Why?

You dig deeper. There's a spike in long-running queries. Not slow queries—queries that are waiting. Waiting for what? Locks. Lock queue is growing. Why?

15 minutes in, you find it: A background job is doing a full table scan with a write lock. It's been running for 40 minutes. It's blocking all checkout writes. Why is it running now?

You check the job scheduler. Someone changed the schedule yesterday from 4 AM to 3 AM. But didn't test it. At 3 AM, there's still evening traffic in US timezones. The lock is blocking real users.

**The fix**: Kill the job. Lock releases. Backlog processes. Site recovers. Total downtime: 22 minutes. Revenue impact: $18,000.

**The lesson**: Everything is connected. A seemingly innocent schedule change cascaded into a site outage. Operations requires system-level thinking, not component-level thinking.

**What you learned**:
1. **Investigation process**: Symptoms → Hypothesis → Evidence → Root cause
2. **Tool proficiency**: You need to know your observability tools intimately
3. **Time pressure**: Every minute costs money and customer trust
4. **Communication**: Status updates calm the storm even when you don't have answers
5. **Humility**: You don't know what you don't know until production teaches you

### The "Site Is Slow" Incident

**Friday, 11 AM**: Slack message from support: "Customers reporting site is slow."

This is the worst type of incident. Not down—just slow. No clear error. No obvious spike. Just... slow.

**The investigation**:

You check response time metrics. P50 is normal (100ms). P95 is elevated (800ms, usually 200ms). P99 is terrible (3 seconds, usually 400ms). So most requests are fine, but some are very slow.

Which requests? You filter by endpoint. The search API. Specifically, searching for products with complex filters. Not all searches—just some patterns.

You check search service logs. Some queries are taking 2-3 seconds to execute. Looking at the query plans, they're doing full scans. Why? The database is supposed to use an index.

You check the database. The index exists. But it's not being used for certain query patterns. The query planner thinks a full scan is faster. Is it wrong?

You run EXPLAIN. The index statistics are stale. The database thinks the table has 10,000 rows. It actually has 10 million. The query planner is making bad decisions based on bad statistics.

**The fix**: Run ANALYZE to update statistics. Query planner starts using indexes. Response times return to normal.

**The aftermath**: How did statistics get stale? Auto-analyze should run automatically. You check configuration. Auto-analyze is disabled. Who disabled it? A performance optimization 6 months ago. Someone read that disabling auto-analyze reduces overhead. They didn't understand the tradeoff.

**The lessons**:
1. **"Slow" is harder than "down"**: Clear failures are easier to debug than performance degradation
2. **Percentiles matter**: P50 hides problems that P99 reveals
3. **Second-order effects**: A performance optimization caused a performance problem
4. **Documentation debt**: The change was made without documenting the tradeoff
5. **Ownership**: Nobody was monitoring database statistics freshness

### The Cascade Failure

**Sunday, 6 PM**: Normal evening traffic. Then your dashboard goes red across the board.

This is a cascade failure—the kind that teaches you humility.

**The timeline**:

**18:00:00**: One API server runs out of memory. Gets OOM-killed. Kubernetes restarts it.

**18:00:15**: During the 15-second restart, traffic redistributes to other servers. They're now at 85% capacity instead of 70%.

**18:01:30**: The restarted server is ready. But it has a cold cache. It's slower than usual. Requests time out. It gets marked unhealthy. Kubernetes restarts it again.

**18:02:00**: Now two servers are restarting. Traffic concentrates on remaining servers. They hit 95% capacity. Response times increase.

**18:03:00**: Slow responses trigger client-side timeouts. Clients retry. Request rate doubles. Now servers are at 190% of expected load.

**18:04:00**: Retry storm. Servers can't keep up. More servers become unhealthy. More restarts. Even more load concentration.

**18:05:00**: Database connection pool exhausted. All API servers start failing. Complete outage.

**18:06:00**: You're paged. You see a disaster.

**The response**:

Immediate instinct: Scale up! Add more servers! You request 50% more capacity.

But wait—new servers will have cold caches. They'll be slow. They might make it worse.

New strategy: Reduce load. You enable rate limiting. You shed non-critical requests. You disable expensive features.

Load drops to manageable levels. Servers stabilize. Connection pool recovers. You gradually re-enable features.

Total outage: 18 minutes.

**The root cause analysis**:

One server OOM-killed wasn't the root cause. It was the trigger. The root cause was:
1. **No cache warming**: Restarted servers had cold caches
2. **No backpressure**: Servers accepted more requests than they could handle
3. **Aggressive health checks**: Health checks were too sensitive
4. **No retry budget**: Clients retried without limits
5. **No circuit breakers**: Clients kept hitting failing servers
6. **Insufficient capacity margin**: 70% utilization left no room for failures

**The lessons**:
1. **Cascade failures are emergent**: No single component was obviously wrong
2. **System behavior ≠ component behavior**: Each component was "correctly" responding to load
3. **Feedback loops amplify**: Slow responses → timeouts → retries → more load → slower responses
4. **Resilience requires multiple layers**: Circuit breakers, rate limiting, backpressure, capacity margin
5. **Recovery is part of design**: Systems must be designed to recover, not just to run

### When Monitoring Lied to You

**Tuesday, 10 AM**: Everything looks green. Metrics are normal. Error rates are low. Response times are good.

**Tuesday, 10:15 AM**: Your CEO forwards a customer email. "Your site has been down for the past hour."

Wait, what? The monitoring says everything is fine.

**The investigation**:

You check from your desk. Site loads fine. You check from your phone. Fine. You ask the customer for details. They're in Australia. You VPN to an Australian server. Site times out.

Ah. Your monitoring is all in US data centers. It can't see what Australian users see.

You check CDN metrics. There's an elevated error rate from Australia. The origin server for Australian traffic is down. But it's not in your monitoring. It's a third-party CDN edge location.

**The fix**: Add synthetic monitoring from multiple global locations. Add third-party API monitoring. Add real user monitoring (RUM) to capture actual user experience.

**The lesson**: You can only see what you measure. If you only monitor your infrastructure, you can't see network issues, third-party failures, or regional problems. Observability requires multiple perspectives.

### The Rollback That Made Things Worse

**Thursday, 2 PM**: You deploy a new version. Gradually roll it out: 1%, 10%, 50%, 100%. Metrics look good at each stage. Success!

**Thursday, 8 PM**: Error rate spikes. The new version has a bug. It's not handling edge cases correctly. You need to rollback immediately.

**Thursday, 8:05 PM**: You rollback to the previous version. Error rate... increases? What?

**The nightmare scenario**:

The new version changed the database schema. It added a new column with a default value. The old version doesn't know about this column.

When you rolled forward, the new version wrote data in the new format. When you rolled back, the old version can't read that data. It crashes on records written by the new version.

Now you have a worse problem. You can't go forward (there's a bug). You can't go back (incompatible data). You're stuck.

**The recovery**:

You rush a hot fix. Patch the old version to tolerate the new column. Deploy the patched version. Finally, stability.

Total incident time: 2.5 hours.

**The lessons**:
1. **Rollback is not always safe**: Schema changes, data migrations, and API contracts can make rollback dangerous
2. **Forward and backward compatibility**: Changes must work with N-1 and N+1 versions
3. **Feature flags > deployments**: Decouple code deployment from feature activation
4. **Incremental migration**: Never change schema and behavior simultaneously
5. **Rollback testing**: Test rollback scenarios, not just forward scenarios

### Learning That Everything Breaks Eventually

After a few months of on-call, you've seen it all:
- Servers crash
- Networks partition
- Databases corrupt
- Dependencies fail
- Load spikes happen
- Configs get misconfigured
- Humans make mistakes
- Cosmic rays flip bits (seriously)

**The transformation**: You stop thinking "this will never happen" and start thinking "when this happens, what will we do?"

This is the operational mindset. Not pessimism. Preparation.

**The practices you adopt**:
1. **Design for failure**: Assume every component can fail
2. **Test failure modes**: Chaos engineering, game days, disaster recovery drills
3. **Automate recovery**: Runbooks become automated scripts
4. **Monitor everything**: If you can't measure it, you can't operate it
5. **Practice incidents**: Simulations build muscle memory
6. **Blameless postmortems**: Learn from failures without blame
7. **Continuous improvement**: Every incident teaches something

---

## Part 2: UNDERSTANDING (Second Pass)—The Practices That Work

### Observability: Seeing Into the System

You can't operate what you can't see. Observability is the foundation of operations.

**The definition**: Observability is the ability to understand system behavior from external outputs. In practice, it's the ability to ask and answer questions about your system:
- Why is this request slow?
- Which users are affected?
- When did this start?
- What changed?
- Is it getting better or worse?

**The three pillars**: Metrics, logs, traces.

#### Metrics: What Is Happening

Metrics are aggregated measurements over time. They answer "how much" and "how many."

**The golden signals** (from Google SRE):
1. **Latency**: How long do requests take?
2. **Traffic**: How many requests per second?
3. **Errors**: How many requests fail?
4. **Saturation**: How full are your resources?

**Metric types**:
- **Counter**: Monotonically increasing value (requests_total, errors_total)
- **Gauge**: Point-in-time value (memory_usage_bytes, active_connections)
- **Histogram**: Distribution of values (request_duration_seconds)
- **Summary**: Like histogram but with calculated percentiles

**Example: Setting up metrics**:

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
request_counter = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'http_active_connections',
    'Number of active HTTP connections'
)

# Instrument your code
@app.route('/api/users')
def get_users():
    active_connections.inc()
    start_time = time.time()

    try:
        users = fetch_users()
        request_counter.labels('GET', '/api/users', '200').inc()
        return users
    except Exception as e:
        request_counter.labels('GET', '/api/users', '500').inc()
        raise
    finally:
        duration = time.time() - start_time
        request_duration.labels('GET', '/api/users').observe(duration)
        active_connections.dec()

# Expose metrics endpoint
start_http_server(9090)
```

**Querying metrics** (Prometheus PromQL):

```promql
# Error rate: errors per second
rate(http_requests_total{status=~"5.."}[5m])

# P99 latency
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket[5m])
)

# Requests per second by endpoint
sum by (endpoint) (rate(http_requests_total[1m]))

# Error percentage
sum(rate(http_requests_total{status=~"5.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100
```

**What to monitor**:

```python
class ComprehensiveMetrics:
    def __init__(self):
        # Application metrics
        self.app_metrics = {
            'request_rate': Counter('requests per endpoint'),
            'error_rate': Counter('errors per type'),
            'latency': Histogram('request duration percentiles'),
            'active_users': Gauge('concurrent users'),
        }

        # Business metrics
        self.business_metrics = {
            'signups': Counter('new user registrations'),
            'purchases': Counter('completed purchases'),
            'revenue': Counter('revenue in dollars'),
            'cart_abandonment': Counter('abandoned carts'),
        }

        # System metrics
        self.system_metrics = {
            'cpu_usage': Gauge('CPU percentage'),
            'memory_usage': Gauge('memory bytes'),
            'disk_usage': Gauge('disk bytes used'),
            'network_io': Counter('network bytes sent/received'),
        }

        # Database metrics
        self.db_metrics = {
            'query_duration': Histogram('query execution time'),
            'connection_pool': Gauge('active connections'),
            'deadlocks': Counter('database deadlocks'),
            'slow_queries': Counter('queries over threshold'),
        }

        # Cache metrics
        self.cache_metrics = {
            'hit_rate': Gauge('cache hit percentage'),
            'miss_rate': Gauge('cache miss percentage'),
            'eviction_rate': Counter('cache evictions'),
            'size': Gauge('cache size in bytes'),
        }
```

#### Logs: What Happened

Logs are discrete events. They answer "what exactly occurred" and provide context.

**Structured logging**:

```python
import structlog
import json

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Log with context
@app.route('/api/purchase')
def make_purchase():
    logger.info(
        "purchase_started",
        user_id=request.user_id,
        product_id=request.json['product_id'],
        amount=request.json['amount'],
        request_id=request.id
    )

    try:
        result = process_purchase(request.json)
        logger.info(
            "purchase_completed",
            user_id=request.user_id,
            product_id=request.json['product_id'],
            transaction_id=result.transaction_id,
            request_id=request.id,
            duration_ms=(time.time() - start_time) * 1000
        )
        return result
    except PaymentFailure as e:
        logger.error(
            "purchase_failed",
            user_id=request.user_id,
            product_id=request.json['product_id'],
            error=str(e),
            error_code=e.code,
            request_id=request.id
        )
        raise
```

**Log output** (JSON for machine parsing):

```json
{
  "event": "purchase_completed",
  "user_id": "user_123",
  "product_id": "prod_456",
  "transaction_id": "txn_789",
  "request_id": "req_abc",
  "duration_ms": 245,
  "timestamp": "2025-10-01T15:30:22.123Z",
  "level": "info",
  "logger": "api.purchases"
}
```

**What to log**:

```python
# DO log:
logger.info("user_login", user_id=user.id, ip=request.ip)
logger.error("database_error", query=query, error=str(e), duration_ms=duration)
logger.warn("rate_limit_exceeded", user_id=user.id, endpoint=endpoint)

# DON'T log:
logger.info(f"User logged in")  # Unstructured
logger.debug(f"Password: {password}")  # Sensitive data
logger.info("Everything is fine")  # No useful information
```

**Log levels**:
- **DEBUG**: Detailed information for diagnosing problems (development only)
- **INFO**: Normal operations, business events
- **WARN**: Something unexpected but handled
- **ERROR**: Error that needs attention
- **FATAL**: System is about to crash

#### Traces: How It Happened

Traces show the path of a request through the system. They answer "where is time spent?"

**Distributed tracing**:

```python
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Export to backend (Jaeger, Tempo, etc.)
otlp_exporter = OTLPSpanExporter(endpoint="localhost:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Auto-instrument frameworks
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Manual instrumentation
@app.route('/api/order')
def create_order():
    with tracer.start_as_current_span("create_order") as span:
        span.set_attribute("user_id", request.user_id)
        span.set_attribute("order_value", request.json['total'])

        # Check inventory
        with tracer.start_as_current_span("check_inventory") as inv_span:
            inventory = inventory_service.check(request.json['items'])
            inv_span.set_attribute("items_checked", len(request.json['items']))

        # Process payment
        with tracer.start_as_current_span("process_payment") as pay_span:
            payment = payment_service.charge(request.json['payment'])
            pay_span.set_attribute("payment_method", request.json['payment']['method'])
            pay_span.set_attribute("transaction_id", payment.transaction_id)

        # Create order
        with tracer.start_as_current_span("save_order") as db_span:
            order = db.orders.create({
                'user_id': request.user_id,
                'items': request.json['items'],
                'payment_id': payment.id
            })
            db_span.set_attribute("order_id", order.id)

        return order
```

**What a trace shows**:

```
Request: POST /api/order [trace_id: abc123]
├─ create_order (200ms)
   ├─ check_inventory (50ms)
   │  └─ inventory_service.check (45ms)
   │     └─ http GET inventory-service/check (40ms)
   ├─ process_payment (120ms)
   │  └─ payment_service.charge (115ms)
   │     └─ http POST payment-gateway/charge (110ms)
   └─ save_order (30ms)
      └─ db.insert (25ms)
```

**Correlation**: Traces connect to logs:

```python
from opentelemetry import trace

def log_with_trace_context(message, **kwargs):
    span = trace.get_current_span()
    span_context = span.get_span_context()

    logger.info(
        message,
        trace_id=format(span_context.trace_id, '032x'),
        span_id=format(span_context.span_id, '016x'),
        **kwargs
    )
```

Now you can search logs by trace_id to see all logs for a specific request.

#### Building an Observable Service

```python
from prometheus_client import Counter, Histogram, Gauge
from opentelemetry import trace
import structlog

class ObservableService:
    def __init__(self, name):
        self.name = name
        self.tracer = trace.get_tracer(name)
        self.logger = structlog.get_logger(name)

        # Metrics
        self.request_counter = Counter(
            f'{name}_requests_total',
            'Total requests',
            ['method', 'status']
        )
        self.request_duration = Histogram(
            f'{name}_request_duration_seconds',
            'Request duration',
            ['method']
        )
        self.active_requests = Gauge(
            f'{name}_active_requests',
            'Active requests'
        )

    def handle_request(self, method, handler):
        """Wrap request handler with observability"""
        self.active_requests.inc()
        start_time = time.time()

        with self.tracer.start_as_current_span(f"{self.name}.{method}") as span:
            # Add trace context to logs
            trace_id = format(span.get_span_context().trace_id, '032x')

            self.logger.info(
                "request_started",
                method=method,
                trace_id=trace_id
            )

            try:
                result = handler()

                # Record success
                self.request_counter.labels(method=method, status='success').inc()
                span.set_attribute("status", "success")

                self.logger.info(
                    "request_completed",
                    method=method,
                    trace_id=trace_id,
                    duration_ms=(time.time() - start_time) * 1000
                )

                return result

            except Exception as e:
                # Record failure
                self.request_counter.labels(method=method, status='error').inc()
                span.set_attribute("status", "error")
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.record_exception(e)

                self.logger.error(
                    "request_failed",
                    method=method,
                    trace_id=trace_id,
                    error=str(e),
                    error_type=type(e).__name__
                )

                raise

            finally:
                duration = time.time() - start_time
                self.request_duration.labels(method=method).observe(duration)
                self.active_requests.dec()
```

### Incident Response

An incident is when an invariant is violated. Incident response is how you restore it.

**The incident lifecycle**:
1. Detection (0-5 minutes): Something is wrong
2. Triage (5-15 minutes): How bad is it? Who needs to respond?
3. Response (15+ minutes): Diagnose and mitigate
4. Recovery: Verify system is healthy
5. Analysis: Understand what happened
6. Improvement: Prevent recurrence

#### Detection: Knowing Something Is Wrong

**Alerting principles**:
1. **Alert on symptoms, not causes**: Alert on "users can't check out" not "CPU high"
2. **Alert on impact**: Only alert if it affects users or will soon
3. **Actionable alerts**: Every alert should have a clear action
4. **Reduce noise**: Frequent alerts train people to ignore them

**Alert examples**:

```yaml
# Good alert: User-facing symptom
- alert: HighErrorRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m]))
    /
    sum(rate(http_requests_total[5m])) > 0.05
  for: 5m
  annotations:
    summary: "High error rate ({{ $value }}%)"
    description: "5% of requests are failing"
    runbook: "https://runbooks.company.com/high-error-rate"

# Good alert: Leading indicator
- alert: ErrorBudgetBurnRate
  expr: |
    error_budget_remaining < 0.2 * error_budget_total
  annotations:
    summary: "Error budget 80% consumed"
    description: "At current rate, will exhaust budget in {{ $value }} hours"

# Bad alert: Low-level symptom
- alert: HighCPU
  expr: cpu_usage > 80
  # What should I do? Is this actually a problem?
```

#### Triage: Understanding Severity

Not all incidents are equal. Severity determines response.

**Severity levels**:

```python
class IncidentSeverity:
    SEV1 = {
        'name': 'Critical',
        'description': 'Complete outage or data loss',
        'examples': ['Site down', 'Payment processing broken', 'Data corruption'],
        'response': 'All hands on deck',
        'communication': 'Every 15 minutes',
        'escalation': 'Immediate to exec team',
        'sla': 'Acknowledge in 5 minutes, resolve ASAP'
    }

    SEV2 = {
        'name': 'High',
        'description': 'Major feature broken or severe degradation',
        'examples': ['Search not working', 'Slow page loads', 'High error rate'],
        'response': 'On-call + domain expert',
        'communication': 'Every 30 minutes',
        'escalation': 'To manager if > 1 hour',
        'sla': 'Acknowledge in 15 minutes, resolve in 4 hours'
    }

    SEV3 = {
        'name': 'Medium',
        'description': 'Minor feature broken or degraded',
        'examples': ['Analytics delayed', 'Non-critical API errors'],
        'response': 'On-call engineer',
        'communication': 'When resolved',
        'escalation': 'If becomes SEV2',
        'sla': 'Acknowledge in 30 minutes, resolve in 24 hours'
    }

    SEV4 = {
        'name': 'Low',
        'description': 'Minimal impact',
        'examples': ['Cosmetic issues', 'Internal tool glitch'],
        'response': 'Create ticket',
        'communication': 'Not required',
        'escalation': 'None',
        'sla': 'Resolve in next sprint'
    }
```

#### Response: The Incident Command Structure

Large incidents need coordination. The Incident Command System (ICS) provides structure.

**Roles**:

```python
class IncidentRoles:
    COMMANDER = {
        'responsibilities': [
            'Overall incident coordination',
            'Decision making',
            'Resource allocation',
            'External communication'
        ],
        'not_responsible_for': [
            'Technical debugging',
            'Writing code',
            'Implementing fixes'
        ],
        'who': 'Most experienced on-call or manager'
    }

    TECHNICAL_LEAD = {
        'responsibilities': [
            'Technical investigation',
            'Hypothesis formation',
            'Solution development',
            'Implementation coordination'
        ],
        'who': 'Domain expert or senior engineer'
    }

    COMMUNICATIONS_LEAD = {
        'responsibilities': [
            'Status page updates',
            'Customer communication',
            'Internal stakeholder updates',
            'Social media monitoring'
        ],
        'who': 'Support lead or product manager'
    }

    SCRIBE = {
        'responsibilities': [
            'Timeline documentation',
            'Action item tracking',
            'Decision recording',
            'Postmortem preparation'
        ],
        'who': 'Any available engineer'
    }
```

**Incident workflow**:

```python
class IncidentManager:
    def handle_incident(self, alert):
        # 1. Create incident
        incident = self.create_incident(
            title=alert.title,
            severity=self.assess_severity(alert),
            detected_at=time.now(),
            detection_method=alert.source
        )

        # 2. Assemble team
        incident.commander = self.assign_commander(incident.severity)
        incident.tech_lead = self.page_expert(alert.service)
        incident.comms_lead = self.assign_comms_lead(incident.severity)
        incident.scribe = self.assign_scribe()

        # 3. Create war room
        incident.slack_channel = self.create_channel(incident.id)
        incident.video_call = self.start_call(incident.severity)

        # 4. Investigation loop
        while not incident.resolved:
            # Gather evidence
            evidence = self.collect_evidence(incident)

            # Form hypothesis
            hypothesis = incident.tech_lead.analyze(evidence)

            # Test hypothesis
            result = self.test_hypothesis(hypothesis)

            # Communicate status
            incident.comms_lead.update_status(
                investigating=hypothesis,
                eta=self.estimate_resolution(incident)
            )

            # If hypothesis confirmed, implement fix
            if result.confirmed:
                fix = incident.tech_lead.develop_fix(hypothesis)
                self.implement_fix(fix)
                break

        # 5. Verify resolution
        self.verify_resolution(incident)

        # 6. Close incident
        self.close_incident(incident)

        # 7. Schedule postmortem
        self.schedule_postmortem(incident)
```

#### Recovery: Verifying Health

Don't declare victory too soon. Verify the system is actually healthy.

**Verification checklist**:

```python
class RecoveryVerification:
    def verify(self, incident):
        checks = [
            self.check_error_rate_normal(),
            self.check_latency_normal(),
            self.check_traffic_normal(),
            self.check_no_alerts_firing(),
            self.check_core_workflows_working(),
            self.check_business_metrics_recovered(),
            self.monitor_for_recurrence(duration=30*60)  # 30 minutes
        ]

        return all(checks)

    def check_core_workflows_working(self):
        """Verify critical paths with synthetic tests"""
        workflows = [
            self.test_user_signup(),
            self.test_user_login(),
            self.test_product_search(),
            self.test_add_to_cart(),
            self.test_checkout(),
        ]

        results = [workflow.run() for workflow in workflows]
        return all(r.success for r in results)
```

#### Analysis: The Postmortem

The goal of a postmortem is learning, not blame.

**Postmortem template**:

```markdown
# Incident Postmortem: [Title]

**Date**: 2025-10-01
**Duration**: 45 minutes (14:32 - 15:17 UTC)
**Severity**: SEV2
**Impact**: 12% of checkout requests failed, ~$25,000 revenue impact
**Root Cause**: Database connection pool exhaustion

## Timeline

**14:32** - Alert fired: High error rate in payment service
**14:35** - On-call engineer acknowledged, began investigation
**14:40** - Identified symptom: Database connection timeouts
**14:45** - Found root cause: Long-running query holding connections
**14:50** - Killed blocking query, connections recovered
**14:55** - Error rate returned to normal
**15:00** - Verified all workflows functioning
**15:17** - Incident closed

## What Happened

A background job ran a full table scan with a write lock. The job usually runs at 4 AM (low traffic), but the schedule was changed to 3 AM yesterday without testing. At 3 AM, there's still significant traffic in US evening timezones.

The long-running query (40+ minutes) held a write lock, blocking all checkout writes. The connection pool (max 100 connections) filled with waiting queries. New checkout requests timed out waiting for connections.

## Why It Happened

**Immediate cause**: Background job scheduled during high-traffic period

**Contributing factors**:
1. No testing of schedule change impact
2. No query timeout on background jobs
3. No connection pool monitoring/alerting
4. No max execution time on background jobs
5. Schedule change not reviewed by team

## What Went Well

1. Detection was quick (3 minutes from start to alert)
2. On-call engineer followed runbook effectively
3. Communication was clear and frequent
4. Recovery was verified before closing incident

## What Went Wrong

1. Schedule change had no review process
2. No monitoring caught the problem before user impact
3. Took 13 minutes to find root cause (should have been faster)
4. No automatic mitigation (should have killed long query automatically)

## Action Items

1. [P0] Implement query timeout on all background jobs (@alice, due: 2025-10-03)
2. [P0] Add connection pool monitoring and alerting (@bob, due: 2025-10-03)
3. [P1] Create schedule change review process (@charlie, due: 2025-10-10)
4. [P1] Add automatic query killing for long-running queries (@alice, due: 2025-10-15)
5. [P2] Improve connection pool size calculation (@bob, due: 2025-10-20)
6. [P2] Add load testing for background jobs (@charlie, due: 2025-10-30)

## Lessons Learned

1. **Test changes in production-like conditions**: Schedule changes affect load patterns
2. **Monitor resources, not just errors**: Connection pool exhaustion preceded errors
3. **Automate mitigation**: Humans are too slow for some failure modes
4. **Review operational changes**: Not just code changes need review
```

**Blameless postmortem culture**:
- Focus on systems and processes, not individuals
- Assume good intentions
- Ask "what" and "how," not "who" and "why"
- Identify contributing factors, not assign blame
- Learn from the incident to prevent recurrence

### Capacity Planning

Systems fail when they run out of resources. Capacity planning prevents that.

**The goal**: Have enough capacity to handle expected load plus safety margin, without over-provisioning and wasting money.

**The challenge**: Demand is unpredictable, growth is non-linear, resources are diverse (CPU, memory, disk, network, database connections, etc.).

#### Forecasting Demand

```python
import pandas as pd
from prophet import Prophet
import numpy as np

class CapacityPlanner:
    def __init__(self):
        self.resources = ['cpu', 'memory', 'disk', 'network']
        self.time_horizons = [30, 90, 365]  # days

    def forecast_demand(self, historical_data):
        """Forecast resource demand using time series analysis"""

        # Prepare data for Prophet
        df = pd.DataFrame({
            'ds': historical_data['timestamp'],
            'y': historical_data['cpu_usage']
        })

        # Configure model with seasonality
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05  # Flexibility for trend changes
        )

        # Add holidays (Black Friday, Christmas, etc.)
        model.add_country_holidays(country_name='US')

        # Add custom seasonality (e.g., business hours)
        model.add_seasonality(
            name='business_hours',
            period=1,  # Daily
            fourier_order=5
        )

        # Fit model
        model.fit(df)

        # Generate forecast
        future = model.make_future_dataframe(periods=365)
        forecast = model.predict(future)

        return {
            'predicted': forecast['yhat'],
            'lower_bound': forecast['yhat_lower'],
            'upper_bound': forecast['yhat_upper'],
            'trend': forecast['trend'],
            'seasonality': forecast['weekly'] + forecast['yearly']
        }

    def calculate_required_capacity(self, forecast, slo_target=0.999):
        """Calculate required capacity with safety margin"""

        # Get peak demand (P99 of forecasted demand)
        peak_demand = np.percentile(forecast['upper_bound'], 99)

        # Add safety margin for:
        # 1. Forecasting error
        # 2. Unexpected spikes
        # 3. Instance failures
        safety_factor = 1.5  # 50% headroom
        required_capacity = peak_demand * safety_factor

        # Consider target utilization
        # (Don't want to run at 100% - latency suffers)
        target_utilization = 0.70  # 70% target
        total_capacity = required_capacity / target_utilization

        return {
            'current_peak': peak_demand,
            'required_capacity': required_capacity,
            'total_capacity': total_capacity,
            'safety_margin': (total_capacity - peak_demand) / peak_demand,
            'target_utilization': target_utilization
        }

    def when_to_scale(self, current_capacity, forecast):
        """Determine when current capacity will be insufficient"""

        # Find when forecasted demand exceeds current capacity
        demand = forecast['upper_bound']
        exceed_date = demand[demand > current_capacity].index[0]

        days_until_scale = (exceed_date - pd.Timestamp.now()).days

        return {
            'scale_by': exceed_date,
            'days_remaining': days_until_scale,
            'urgency': 'critical' if days_until_scale < 30 else 'high' if days_until_scale < 90 else 'normal'
        }
```

**Capacity modeling example**:

```python
# Historical data
historical_data = {
    'timestamp': [...],  # Past 12 months
    'cpu_usage': [...],
    'memory_usage': [...],
    'request_rate': [...]
}

# Forecast demand
planner = CapacityPlanner()
forecast = planner.forecast_demand(historical_data)

# Current capacity
current_capacity = 1000  # CPU cores

# Calculate requirements
requirements = planner.calculate_required_capacity(forecast)

print(f"Current capacity: {current_capacity} cores")
print(f"Peak demand forecast: {requirements['current_peak']:.0f} cores")
print(f"Required capacity: {requirements['required_capacity']:.0f} cores")
print(f"Recommended capacity: {requirements['total_capacity']:.0f} cores")
print(f"Safety margin: {requirements['safety_margin']:.0%}")

# When to scale
scale_timing = planner.when_to_scale(current_capacity, forecast)
print(f"Scale by: {scale_timing['scale_by']}")
print(f"Days remaining: {scale_timing['days_remaining']}")
```

#### The Capacity Review Process

```python
class CapacityReviewProcess:
    """Quarterly capacity planning process"""

    def conduct_review(self):
        # 1. Collect data
        data = self.collect_historical_data(days=365)

        # 2. Forecast demand
        forecast = self.forecast_demand(data)

        # 3. Assess current capacity
        current = self.assess_current_capacity()

        # 4. Identify gaps
        gaps = self.identify_gaps(current, forecast)

        # 5. Cost analysis
        costs = self.analyze_costs(gaps)

        # 6. Create plan
        plan = self.create_scaling_plan(gaps, costs)

        # 7. Present to stakeholders
        self.present_plan(plan)

        return plan

    def identify_gaps(self, current, forecast):
        """Find resources that will be insufficient"""
        gaps = []

        for resource, capacity in current.items():
            demand = forecast[resource]['upper_bound'].max()
            required = demand * 1.5  # Safety factor

            if required > capacity:
                gaps.append({
                    'resource': resource,
                    'current': capacity,
                    'required': required,
                    'shortfall': required - capacity,
                    'when': forecast[resource]['exceed_date']
                })

        return gaps
```

### Performance Management: SLIs, SLOs, and Error Budgets

**The framework**:
- **SLI** (Service Level Indicator): What you measure
- **SLO** (Service Level Objective): Your internal target
- **SLA** (Service Level Agreement): Your customer promise

#### Defining SLIs

```python
class SLI:
    """Service Level Indicator definition"""

    def __init__(self, name, description, query, good_event, total_event):
        self.name = name
        self.description = description
        self.query = query
        self.good_event = good_event
        self.total_event = total_event

    def calculate(self, time_window):
        """Calculate SLI percentage for time window"""
        good = self.execute_query(self.good_event, time_window)
        total = self.execute_query(self.total_event, time_window)

        return (good / total) * 100 if total > 0 else 100

# Example SLIs
slis = {
    'availability': SLI(
        name='Availability',
        description='Percentage of requests that succeed',
        query='http_requests_total',
        good_event='status:2xx OR status:3xx',
        total_event='status:*'
    ),

    'latency': SLI(
        name='Latency',
        description='Percentage of requests under 100ms',
        query='http_request_duration_seconds',
        good_event='duration < 0.1',
        total_event='all requests'
    ),

    'freshness': SLI(
        name='Data Freshness',
        description='Percentage of data updated within 5 minutes',
        query='data_age_seconds',
        good_event='age < 300',
        total_event='all data'
    )
}
```

#### Setting SLOs

```python
class SLO:
    """Service Level Objective"""

    def __init__(self, sli, target, window):
        self.sli = sli
        self.target = target  # e.g., 99.9%
        self.window = window  # e.g., 30 days
        self.error_budget = 100 - target

    def current_performance(self):
        """Calculate current SLI performance"""
        return self.sli.calculate(self.window)

    def error_budget_remaining(self):
        """Calculate remaining error budget"""
        actual = self.current_performance()
        errors_allowed = self.error_budget
        errors_actual = 100 - actual
        budget_remaining = errors_allowed - errors_actual

        return {
            'total_budget': errors_allowed,
            'consumed': errors_actual,
            'remaining': budget_remaining,
            'remaining_pct': (budget_remaining / errors_allowed) * 100,
            'status': 'healthy' if budget_remaining > 0 else 'exhausted'
        }

    def burn_rate(self):
        """Calculate how fast we're consuming error budget"""
        # Compare recent period to window
        recent = self.sli.calculate(time_window='1h')
        recent_errors = 100 - recent

        # Normalize to window
        window_hours = self.window_to_hours()
        burn_rate = (recent_errors / window_hours)

        # Time until budget exhausted at current rate
        budget = self.error_budget_remaining()
        if burn_rate > 0:
            hours_remaining = budget['remaining'] / burn_rate
        else:
            hours_remaining = float('inf')

        return {
            'rate': burn_rate,
            'hours_remaining': hours_remaining,
            'severity': self.assess_burn_rate_severity(burn_rate)
        }

    def assess_burn_rate_severity(self, burn_rate):
        """Alert severity based on burn rate"""
        budget = self.error_budget_remaining()

        # If we'll exhaust budget in < 2 hours, critical
        if burn_rate * 2 > budget['remaining']:
            return 'critical'
        # If we'll exhaust in < 6 hours, high
        elif burn_rate * 6 > budget['remaining']:
            return 'high'
        # If we'll exhaust in < 24 hours, medium
        elif burn_rate * 24 > budget['remaining']:
            return 'medium'
        else:
            return 'low'

# Example SLOs
slos = [
    SLO(slis['availability'], target=99.9, window='30d'),
    SLO(slis['latency'], target=99.0, window='30d'),
    SLO(slis['freshness'], target=99.5, window='7d')
]
```

#### Using Error Budgets

```python
class ErrorBudgetPolicy:
    """Policy for using error budget"""

    def can_deploy(self, slo):
        """Determine if it's safe to deploy"""
        budget = slo.error_budget_remaining()

        # Don't deploy if budget is critically low
        if budget['remaining_pct'] < 10:
            return False, "Error budget critically low (<10%)"

        # Don't deploy if burning too fast
        burn = slo.burn_rate()
        if burn['severity'] in ['critical', 'high']:
            return False, f"Error budget burning too fast ({burn['severity']})"

        return True, "Safe to deploy"

    def response_to_budget_status(self, slo):
        """What should the team do based on budget status?"""
        budget = slo.error_budget_remaining()

        if budget['remaining_pct'] > 80:
            return {
                'action': 'innovate',
                'description': 'Plenty of budget - take risks, ship features',
                'deployment_frequency': 'multiple per day',
                'testing_rigor': 'standard'
            }
        elif budget['remaining_pct'] > 50:
            return {
                'action': 'normal',
                'description': 'Normal operations',
                'deployment_frequency': 'daily',
                'testing_rigor': 'standard'
            }
        elif budget['remaining_pct'] > 20:
            return {
                'action': 'caution',
                'description': 'Be careful - budget running low',
                'deployment_frequency': 'few times per week',
                'testing_rigor': 'enhanced'
            }
        else:
            return {
                'action': 'freeze',
                'description': 'Stop feature work - focus on reliability',
                'deployment_frequency': 'emergency fixes only',
                'testing_rigor': 'exhaustive'
            }
```

**Error budget dashboard**:

```python
def create_error_budget_dashboard(slos):
    """Generate dashboard showing error budget status"""

    dashboard = []

    for slo in slos:
        budget = slo.error_budget_remaining()
        burn = slo.burn_rate()
        policy = ErrorBudgetPolicy()
        can_deploy, reason = policy.can_deploy(slo)

        dashboard.append({
            'slo': slo.sli.name,
            'target': f"{slo.target}%",
            'actual': f"{slo.current_performance():.3f}%",
            'budget_remaining': f"{budget['remaining_pct']:.1f}%",
            'burn_rate': burn['severity'],
            'can_deploy': can_deploy,
            'recommendation': policy.response_to_budget_status(slo)['action']
        })

    return dashboard
```

### Automation and Tooling

Manual operations don't scale. Automation is essential.

**Toil**: Manual, repetitive, automatable work with no lasting value.

**Types of toil**:
- Manual deployments
- Restarting services
- Acknowledging alerts
- Running the same debug commands
- Applying the same fixes
- Resetting passwords
- Provisioning resources

**The automation ladder**:
1. **Manual**: Human performs task each time
2. **Documented**: Runbook describes steps
3. **Semi-automated**: Script assists human
4. **Automated**: Script runs without human
5. **Self-healing**: System detects and fixes automatically

#### Runbook Automation

```python
class Runbook:
    """Automated runbook with safety checks"""

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.steps = []
        self.rollback_steps = []

    def add_step(self, name, check_fn, action_fn, rollback_fn=None):
        """Add a step to the runbook"""
        self.steps.append({
            'name': name,
            'check': check_fn,
            'action': action_fn,
            'rollback': rollback_fn
        })

    def execute(self, context, dry_run=False):
        """Execute runbook with safety checks"""
        executed_steps = []

        print(f"Executing runbook: {self.name}")
        print(f"Description: {self.description}")
        print(f"Dry run: {dry_run}")

        try:
            for i, step in enumerate(self.steps):
                print(f"\nStep {i+1}: {step['name']}")

                # Check if step should run
                if not step['check'](context):
                    print(f"  Skipping (check failed)")
                    continue

                # Execute action
                print(f"  Executing...")
                if not dry_run:
                    result = self.execute_with_timeout(
                        step['action'],
                        context,
                        timeout=300  # 5 minute timeout
                    )

                    # Verify success
                    if not self.verify_step(result):
                        raise StepFailure(f"Step {i+1} failed verification")

                    executed_steps.append((i, result))
                    print(f"  Success")
                else:
                    print(f"  Would execute: {step['action'].__name__}")

            print(f"\nRunbook completed successfully")
            return True

        except Exception as e:
            print(f"\nRunbook failed: {e}")

            if not dry_run:
                print("Rolling back...")
                self.rollback(executed_steps, context)

            raise

    def rollback(self, executed_steps, context):
        """Rollback executed steps in reverse order"""
        for step_index, result in reversed(executed_steps):
            step = self.steps[step_index]
            if step['rollback']:
                print(f"Rolling back step {step_index+1}: {step['name']}")
                try:
                    step['rollback'](context, result)
                except Exception as e:
                    print(f"Rollback failed: {e}")

# Example: Restart service runbook
restart_runbook = Runbook(
    name="Restart Service",
    description="Safely restart a service with health checks"
)

restart_runbook.add_step(
    name="Check if service is unhealthy",
    check_fn=lambda ctx: not is_service_healthy(ctx.service),
    action_fn=lambda ctx: print("Service confirmed unhealthy"),
    rollback_fn=None
)

restart_runbook.add_step(
    name="Remove from load balancer",
    check_fn=lambda ctx: True,
    action_fn=lambda ctx: remove_from_lb(ctx.service),
    rollback_fn=lambda ctx, result: add_to_lb(ctx.service)
)

restart_runbook.add_step(
    name="Stop service",
    check_fn=lambda ctx: True,
    action_fn=lambda ctx: stop_service(ctx.service),
    rollback_fn=lambda ctx, result: start_service(ctx.service)
)

restart_runbook.add_step(
    name="Start service",
    check_fn=lambda ctx: True,
    action_fn=lambda ctx: start_service(ctx.service),
    rollback_fn=lambda ctx, result: stop_service(ctx.service)
)

restart_runbook.add_step(
    name="Wait for health check",
    check_fn=lambda ctx: True,
    action_fn=lambda ctx: wait_for_healthy(ctx.service, timeout=60),
    rollback_fn=None
)

restart_runbook.add_step(
    name="Add back to load balancer",
    check_fn=lambda ctx: is_service_healthy(ctx.service),
    action_fn=lambda ctx: add_to_lb(ctx.service),
    rollback_fn=lambda ctx, result: remove_from_lb(ctx.service)
)

# Execute
context = {'service': 'payment-service'}
restart_runbook.execute(context, dry_run=False)
```

---

## Part 3: MASTERY (Third Pass)—Operational Excellence

### Advanced Monitoring Patterns

#### Synthetic Monitoring

Don't wait for users to report issues. Test proactively.

```python
class SyntheticMonitor:
    """Proactive monitoring via automated tests"""

    def __init__(self):
        self.scenarios = []

    def add_scenario(self, name, steps, frequency='5m', regions=['us-east', 'us-west', 'eu-west']):
        """Add a monitoring scenario"""
        self.scenarios.append({
            'name': name,
            'steps': steps,
            'frequency': frequency,
            'regions': regions,
            'timeout': '30s'
        })

    async def run_scenario(self, scenario, region):
        """Execute one scenario from one region"""
        start_time = time.time()

        try:
            # Execute each step
            for i, step in enumerate(scenario['steps']):
                step_start = time.time()

                result = await asyncio.wait_for(
                    step.execute(),
                    timeout=30
                )

                step_duration = time.time() - step_start

                # Record step metrics
                self.record_step_metric(
                    scenario=scenario['name'],
                    step=i,
                    region=region,
                    duration=step_duration,
                    success=result.success
                )

                # If step fails, alert and stop
                if not result.success:
                    self.alert(
                        severity='high',
                        message=f"Synthetic test failed: {scenario['name']} step {i} in {region}",
                        details=result.error
                    )
                    return False

            # Record overall success
            total_duration = time.time() - start_time
            self.record_scenario_metric(
                scenario=scenario['name'],
                region=region,
                duration=total_duration,
                success=True
            )

            return True

        except asyncio.TimeoutError:
            self.alert(
                severity='critical',
                message=f"Synthetic test timeout: {scenario['name']} in {region}",
                details=f"Exceeded {scenario['timeout']} timeout"
            )
            return False

# Example: User journey synthetic test
monitor = SyntheticMonitor()

monitor.add_scenario(
    name='critical_user_journey',
    steps=[
        HttpStep('GET', '/'),  # Homepage loads
        HttpStep('POST', '/api/login', body={'username': 'test', 'password': 'test'}),  # Login works
        HttpStep('GET', '/api/products'),  # Product listing works
        HttpStep('POST', '/api/cart', body={'product_id': '123'}),  # Add to cart works
        HttpStep('POST', '/api/checkout', body={'payment': 'test'}),  # Checkout works
    ],
    frequency='1m',  # Run every minute
    regions=['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
)

# Run continuously
async def run_monitors():
    while True:
        for scenario in monitor.scenarios:
            for region in scenario['regions']:
                await monitor.run_scenario(scenario, region)

        await asyncio.sleep(60)  # Wait 1 minute
```

#### Anomaly Detection

Not all problems trigger simple threshold alerts. Anomaly detection catches subtle issues.

```python
from sklearn.ensemble import IsolationForest
import numpy as np

class AnomalyDetector:
    """ML-based anomaly detection"""

    def __init__(self):
        self.models = {}
        self.baselines = {}

    def train_baseline(self, metric_name, historical_data, lookback_days=30):
        """Train anomaly detection model on historical data"""

        # Feature engineering
        features = self.extract_features(historical_data)

        # Train Isolation Forest
        model = IsolationForest(
            contamination=0.01,  # Expect 1% of data to be anomalies
            random_state=42
        )
        model.fit(features)

        # Store model
        self.models[metric_name] = model

        # Calculate baseline statistics
        self.baselines[metric_name] = {
            'mean': historical_data.mean(),
            'std': historical_data.std(),
            'median': historical_data.median(),
            'p95': historical_data.quantile(0.95),
            'p99': historical_data.quantile(0.99)
        }

    def extract_features(self, data):
        """Extract features for anomaly detection"""
        features = []

        for i in range(len(data)):
            # Value
            value = data[i]

            # Moving averages
            ma_5 = data[max(0, i-5):i+1].mean() if i >= 5 else value
            ma_15 = data[max(0, i-15):i+1].mean() if i >= 15 else value

            # Rate of change
            prev_value = data[i-1] if i > 0 else value
            rate_of_change = (value - prev_value) / prev_value if prev_value != 0 else 0

            # Time-based features (hour of day, day of week)
            hour = i % 24
            day_of_week = (i // 24) % 7

            features.append([value, ma_5, ma_15, rate_of_change, hour, day_of_week])

        return np.array(features)

    def detect_anomaly(self, metric_name, current_value):
        """Detect if current value is anomalous"""

        if metric_name not in self.models:
            return False, None, "No baseline trained"

        model = self.models[metric_name]
        baseline = self.baselines[metric_name]

        # Statistical anomaly detection
        z_score = (current_value - baseline['mean']) / baseline['std']
        if abs(z_score) > 3:  # 3 sigma
            return True, 'statistical', f"Value {current_value} is {abs(z_score):.1f} standard deviations from mean"

        # ML-based detection
        features = self.extract_features([current_value])
        prediction = model.predict(features)

        if prediction[0] == -1:  # Anomaly
            return True, 'ml_model', f"ML model detected anomaly: {current_value}"

        return False, None, None

    def continuous_monitoring(self, metric_name, data_stream):
        """Monitor stream of data for anomalies"""

        for timestamp, value in data_stream:
            is_anomaly, method, reason = self.detect_anomaly(metric_name, value)

            if is_anomaly:
                self.alert(
                    severity='medium',
                    metric=metric_name,
                    value=value,
                    baseline=self.baselines[metric_name],
                    method=method,
                    reason=reason
                )

# Example usage
detector = AnomalyDetector()

# Train on historical data
historical_latency = fetch_metric_history('p99_latency', days=30)
detector.train_baseline('p99_latency', historical_latency)

# Monitor in real-time
latency_stream = subscribe_to_metric('p99_latency')
detector.continuous_monitoring('p99_latency', latency_stream)
```

### Chaos Engineering

Test failure before it happens in production.

**Principles**:
1. Build a hypothesis about steady state
2. Inject real-world failures
3. Observe system behavior
4. Verify steady state is maintained (or not)
5. Learn and improve

```python
class ChaosExperiment:
    """Framework for chaos engineering experiments"""

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.hypothesis = None
        self.failures = []
        self.safety_checks = []

    def set_hypothesis(self, steady_state_metrics):
        """Define what "normal" looks like"""
        self.hypothesis = steady_state_metrics

    def add_failure(self, failure):
        """Add a failure to inject"""
        self.failures.append(failure)

    def add_safety_check(self, check_fn):
        """Add safety check that must pass before experiment"""
        self.safety_checks.append(check_fn)

    def run(self):
        """Execute chaos experiment"""

        # Pre-flight safety checks
        print("Running safety checks...")
        if not all(check() for check in self.safety_checks):
            print("Safety checks failed. Aborting experiment.")
            return

        # Measure steady state
        print("Measuring steady state...")
        before = self.measure_steady_state()

        # Inject failure
        print(f"Injecting failure: {self.failures[0].description}")
        failure = self.failures[0]
        failure.inject()

        try:
            # Monitor system
            print("Monitoring system response...")
            impact = self.monitor_impact(
                baseline=before,
                duration=failure.duration
            )

            # Analyze results
            print("Analyzing results...")
            results = self.analyze_results(before, impact)

            # Auto-rollback if severe
            if impact.severity > failure.max_severity:
                print("Impact too severe. Rolling back immediately.")
                failure.rollback()

            return results

        finally:
            # Always clean up
            failure.rollback()

            # Verify recovery
            after = self.measure_steady_state()
            if not self.verify_recovery(before, after):
                self.alert("System did not fully recover from chaos experiment")

    def measure_steady_state(self):
        """Measure hypothesis metrics"""
        return {
            metric: self.query_metric(metric)
            for metric in self.hypothesis
        }

    def monitor_impact(self, baseline, duration):
        """Monitor impact of failure injection"""
        start = time.time()
        samples = []

        while time.time() - start < duration:
            current = self.measure_steady_state()
            samples.append(current)
            time.sleep(10)

        return self.calculate_impact(baseline, samples)

    def calculate_impact(self, baseline, samples):
        """Calculate impact severity"""
        # Compare metrics to baseline
        impact = {}

        for metric in baseline:
            baseline_value = baseline[metric]
            current_values = [s[metric] for s in samples]

            # Calculate degradation
            degradation = [
                abs(v - baseline_value) / baseline_value
                for v in current_values
            ]

            impact[metric] = {
                'max_degradation': max(degradation),
                'avg_degradation': sum(degradation) / len(degradation)
            }

        # Overall severity
        max_impact = max(i['max_degradation'] for i in impact.values())
        severity = (
            'critical' if max_impact > 0.5 else
            'high' if max_impact > 0.2 else
            'medium' if max_impact > 0.1 else
            'low'
        )

        return {
            'metrics': impact,
            'severity': severity
        }

class ChaosFailure:
    """A failure to inject"""

    def __init__(self, description, inject_fn, rollback_fn, duration=300):
        self.description = description
        self.inject_fn = inject_fn
        self.rollback_fn = rollback_fn
        self.duration = duration
        self.max_severity = 'high'  # Maximum acceptable impact

    def inject(self):
        self.inject_fn()

    def rollback(self):
        self.rollback_fn()

# Example: Kill random instance
experiment = ChaosExperiment(
    name="Instance Failure",
    description="What happens when a random instance dies?"
)

experiment.set_hypothesis({
    'error_rate': 0.001,  # 0.1% errors
    'p99_latency': 200,   # 200ms P99
    'success_rate': 0.999  # 99.9% success
})

experiment.add_safety_check(lambda: no_ongoing_incidents())
experiment.add_safety_check(lambda: error_budget_available() > 0.5)
experiment.add_safety_check(lambda: is_business_hours() == False)

experiment.add_failure(ChaosFailure(
    description="Kill random instance",
    inject_fn=lambda: kill_random_instance('payment-service'),
    rollback_fn=lambda: None,  # Auto-recovery via orchestrator
    duration=300  # 5 minutes
))

results = experiment.run()
```

**Common chaos experiments**:
- Instance failure (kill random pod/instance)
- Network latency (add 100ms latency)
- Network partition (split cluster)
- Dependency failure (block third-party API)
- Resource exhaustion (consume CPU/memory)
- Clock skew (adjust system time)
- Disk failure (fill disk to 100%)
- Configuration corruption (change config to invalid state)

### Progressive Delivery

Deploy without fear.

#### Canary Deployments

```python
class CanaryDeployment:
    """Gradual rollout with automatic rollback"""

    def __init__(self, service, new_version):
        self.service = service
        self.new_version = new_version
        self.old_version = get_current_version(service)

        self.stages = [
            {'name': 'canary', 'traffic': 1, 'duration': 600},    # 1%, 10 min
            {'name': 'small', 'traffic': 10, 'duration': 1800},   # 10%, 30 min
            {'name': 'half', 'traffic': 50, 'duration': 3600},    # 50%, 1 hour
            {'name': 'full', 'traffic': 100, 'duration': 0}       # 100%
        ]

    def deploy(self):
        """Execute progressive rollout"""

        print(f"Starting deployment: {self.old_version} → {self.new_version}")

        for stage in self.stages:
            print(f"\nStage: {stage['name']} ({stage['traffic']}% traffic)")

            # Update traffic split
            self.update_traffic_split(
                old_version=self.old_version,
                old_traffic=100 - stage['traffic'],
                new_version=self.new_version,
                new_traffic=stage['traffic']
            )

            # Monitor for duration
            if not self.monitor_stage(stage):
                print("Regression detected! Rolling back...")
                self.rollback()
                return False

            print(f"Stage {stage['name']} completed successfully")

        print("\nDeployment completed successfully!")
        return True

    def monitor_stage(self, stage):
        """Monitor metrics during stage"""
        start = time.time()

        # Get baseline metrics from old version
        baseline = self.get_version_metrics(self.old_version)

        while time.time() - start < stage['duration']:
            # Compare new version to old version
            new_metrics = self.get_version_metrics(self.new_version)
            old_metrics = self.get_version_metrics(self.old_version)

            # Check for regressions
            if self.detect_regression(new_metrics, old_metrics, baseline):
                return False

            time.sleep(30)  # Check every 30 seconds

        return True

    def detect_regression(self, new_metrics, old_metrics, baseline):
        """Check if new version is worse than old version"""

        # Error rate regression
        if new_metrics['error_rate'] > old_metrics['error_rate'] * 1.5:
            print(f"Error rate regression: {new_metrics['error_rate']} > {old_metrics['error_rate']}")
            return True

        # Latency regression
        if new_metrics['p99_latency'] > old_metrics['p99_latency'] * 1.3:
            print(f"Latency regression: {new_metrics['p99_latency']} > {old_metrics['p99_latency']}")
            return True

        # Success rate regression
        if new_metrics['success_rate'] < old_metrics['success_rate'] * 0.95:
            print(f"Success rate regression: {new_metrics['success_rate']} < {old_metrics['success_rate']}")
            return True

        return False

    def rollback(self):
        """Rollback to old version"""
        self.update_traffic_split(
            old_version=self.old_version,
            old_traffic=100,
            new_version=self.new_version,
            new_traffic=0
        )

# Deploy with canary
deployment = CanaryDeployment('payment-service', 'v2.5.0')
success = deployment.deploy()
```

#### Feature Flags

Decouple deployment from activation.

```python
class FeatureFlag:
    """Feature flag with gradual rollout"""

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.enabled = False
        self.rollout_percentage = 0
        self.whitelist_users = []
        self.blacklist_users = []

    def is_enabled_for_user(self, user_id):
        """Check if feature is enabled for user"""

        # Blacklist takes precedence
        if user_id in self.blacklist_users:
            return False

        # Whitelist
        if user_id in self.whitelist_users:
            return True

        # Not enabled at all
        if not self.enabled:
            return False

        # Percentage rollout (deterministic based on user_id)
        hash_value = hash(f"{self.name}:{user_id}") % 100
        return hash_value < self.rollout_percentage

# Example usage
new_checkout_flow = FeatureFlag('new_checkout_flow', 'Redesigned checkout experience')
new_checkout_flow.enabled = True
new_checkout_flow.rollout_percentage = 10  # 10% of users
new_checkout_flow.whitelist_users = ['beta_user_1', 'beta_user_2']

@app.route('/checkout')
def checkout():
    if new_checkout_flow.is_enabled_for_user(request.user_id):
        return render_new_checkout()
    else:
        return render_old_checkout()
```

### On-Call Excellence

Sustainable on-call requires systems, not heroes.

#### The On-Call Handbook

```python
class OnCallKit:
    """Everything you need for effective on-call"""

    def __init__(self):
        self.tools = self.setup_tools()
        self.runbooks = self.load_runbooks()
        self.contacts = self.load_contacts()

    def pre_oncall_checklist(self):
        """Run before starting on-call shift"""
        return [
            self.verify_access_to_all_systems(),
            self.test_paging_system(),
            self.review_recent_incidents(),
            self.check_runbooks_are_updated(),
            self.verify_escalation_paths(),
            self.setup_monitoring_dashboards(),
            self.test_vpn_access()
        ]

    def oncall_workflow(self, alert):
        """Standard workflow for handling alerts"""

        # 1. Acknowledge quickly (within 5 minutes)
        self.acknowledge(alert)

        # 2. Assess severity
        severity = self.assess_severity(alert)

        # 3. Communicate
        self.create_incident_channel(alert, severity)
        self.update_status_page(alert, severity)

        # 4. Investigation
        if self.has_runbook(alert.type):
            # Follow runbook
            self.execute_runbook(alert.type)
        elif severity >= 'HIGH':
            # Escalate immediately
            self.escalate(alert)
        else:
            # Debug manually
            self.debug(alert)

        # 5. Mitigation
        self.implement_fix(alert)

        # 6. Verification
        self.verify_resolution(alert)

        # 7. Communication
        self.update_status_page_resolved(alert)
        self.close_incident_channel(alert)

        # 8. Documentation
        self.document_incident(alert)
        self.schedule_postmortem_if_needed(alert)
```

**On-call best practices**:

```yaml
on_call_principles:
  before_shift:
    - Verify access to all systems
    - Review recent changes/deployments
    - Check current system health
    - Read recent incident reports

  during_shift:
    - Acknowledge alerts within 5 minutes
    - Communicate early and often
    - Follow runbooks when available
    - Escalate when uncertain
    - Document actions taken

  after_incident:
    - Verify full recovery
    - Document what happened
    - Update runbooks
    - Schedule postmortem for SEV1/SEV2

  handoff:
    - Brief next on-call about current state
    - Mention any ongoing investigations
    - Share any anticipated issues
    - Transfer any in-progress tickets
```

### Disaster Recovery

Hope for the best, plan for the worst.

#### Disaster Recovery Plan

```python
class DisasterRecoveryPlan:
    """DR plan with RTO and RPO targets"""

    def __init__(self):
        self.rto = 3600  # Recovery Time Objective: 1 hour
        self.rpo = 300   # Recovery Point Objective: 5 minutes

    def backup_strategy(self):
        """Multi-layered backup approach"""
        return {
            'database': {
                'method': 'continuous_replication',
                'frequency': 'realtime',
                'replication_lag_target': '<5s',
                'retention': '30_days',
                'verification': 'daily_restore_test',
                'location': 'different_region'
            },

            'files': {
                'method': 's3_versioning_replication',
                'frequency': 'continuous',
                'retention': '90_days',
                'versioning': True,
                'cross_region': True
            },

            'configuration': {
                'method': 'git_repository',
                'frequency': 'on_change',
                'retention': 'forever',
                'location': 'github'
            },

            'secrets': {
                'method': 'encrypted_backup',
                'frequency': 'on_change',
                'retention': 'forever',
                'location': 'vault'
            }
        }

    def failover_procedure(self):
        """Steps to failover to DR site"""

        steps = [
            # 1. Verify primary is really down
            "Verify primary region is actually failed (not false alarm)",

            # 2. Prevent split brain
            "Disable writes to primary database",
            "Disable primary application servers",

            # 3. Promote secondary
            "Promote secondary database to primary",
            "Verify replication lag is acceptable",

            # 4. Update DNS
            "Update DNS to point to secondary region",
            "Wait for DNS propagation (5-10 minutes)",

            # 5. Verify data integrity
            "Run data integrity checks",
            "Verify no data loss",

            # 6. Enable traffic
            "Enable application servers in secondary region",
            "Verify health checks passing",

            # 7. Monitor
            "Monitor error rates, latency, throughput",
            "Verify core workflows functioning",

            # 8. Communicate
            "Update status page",
            "Notify customers of region failover",

            # 9. Post-failover
            "Investigate primary failure",
            "Plan failback when safe",
        ]

        return steps

    def test_dr(self):
        """Regularly test DR procedures"""

        print("Running DR test...")

        # 1. Backup verification
        assert self.verify_backups_exist(), "Backups missing"
        assert self.verify_backups_restorable(), "Backups not restorable"

        # 2. Failover test (in test environment)
        assert self.test_failover_procedure(), "Failover failed"

        # 3. Measure RTO
        rto_actual = self.measure_failover_time()
        assert rto_actual < self.rto, f"RTO exceeded: {rto_actual}s > {self.rto}s"

        # 4. Measure RPO
        rpo_actual = self.measure_data_loss()
        assert rpo_actual < self.rpo, f"RPO exceeded: {rpo_actual}s > {self.rpo}s"

        print("DR test passed!")
```

---

## Synthesis: The Operational Excellence Journey

### The Maturity Model

Operations maturity evolves through stages:

#### Level 1: Reactive (Fire Fighting)
- **Characteristics**:
  - Manual everything
  - No monitoring or alerting
  - Learn from outages
  - Hero culture
- **Pain points**:
  - Frequent outages
  - Long recovery times
  - Burnout
- **Investment needed**:
  - Basic monitoring
  - Runbooks
  - On-call rotation

#### Level 2: Proactive (Managed Chaos)
- **Characteristics**:
  - Basic monitoring and alerting
  - Some automation
  - Runbooks exist
  - Regular incident reviews
- **Pain points**:
  - Alert fatigue
  - Siloed knowledge
  - Inconsistent processes
- **Investment needed**:
  - Comprehensive observability
  - SLOs
  - Automated runbooks

#### Level 3: Managed (Under Control)
- **Characteristics**:
  - Comprehensive observability
  - SLOs and error budgets
  - Automated responses
  - Chaos engineering
  - Blameless culture
- **Pain points**:
  - Still reactive to new failure modes
  - Manual capacity planning
- **Investment needed**:
  - Predictive analytics
  - Self-healing
  - Advanced automation

#### Level 4: Optimized (Predictive)
- **Characteristics**:
  - Self-healing systems
  - Predictive capacity planning
  - Automated remediation
  - Continuous improvement
- **Pain points**:
  - Complacency
  - Over-automation complexity
- **Investment needed**:
  - AIOps
  - Business alignment

#### Level 5: Transformative (Innovation Platform)
- **Characteristics**:
  - Operations enables innovation
  - Near-zero manual toil
  - Reliability is default
  - Operations is product
- **Achievement**: Operations becomes competitive advantage

### Key Principles of Operational Excellence

1. **Assume everything will fail**: Design, test, and practice failure
2. **Make systems observable**: You can't fix what you can't see
3. **Automate toil away**: Humans for judgment, computers for execution
4. **Practice failure regularly**: Chaos engineering, game days, DR drills
5. **Learn from every incident**: Blameless postmortems with action items
6. **Invest in tooling**: Good tools multiply effectiveness
7. **Build team resilience**: Sustainable on-call, knowledge sharing, documentation
8. **Measure what matters**: SLIs/SLOs, error budgets, business metrics
9. **Communicate clearly**: During incidents, status pages, postmortems
10. **Improve continuously**: Small improvements compound over time

### The Operations Mindset

Operating distributed systems successfully requires thinking differently:

**From perfect to resilient**: Accept that failures will happen, design for them
**From blame to learning**: Every incident is an opportunity to improve
**From heroics to systems**: Build systems that anyone can operate
**From reactive to proactive**: Prevent fires instead of fighting them
**From features to reliability**: Reliability is the most important feature

---

## Exercises

### Operational Scenarios

**Exercise 1: Design Observability**

You're launching a new ride-sharing service. Design the observability strategy:
1. What SLIs would you measure?
2. What SLOs would you set?
3. What alerts would you create?
4. What dashboards would you build?
5. How would you trace a ride from request to completion?

**Exercise 2: Incident Response**

It's 3 AM. Your payment service error rate just spiked from 0.1% to 15%. Walk through:
1. First steps (0-5 minutes)
2. Investigation approach
3. Communication plan
4. Mitigation strategies
5. Verification steps
6. Postmortem outline

**Exercise 3: Capacity Planning**

Your service has grown 300% this year. You need to plan capacity for next year:
1. What data do you need?
2. How would you forecast demand?
3. What safety margins would you include?
4. When would you scale?
5. How would you validate the plan?

**Exercise 4: Chaos Engineering**

Design a chaos experiment:
1. What failure would you inject?
2. What's your hypothesis?
3. What safety checks would you include?
4. How would you measure impact?
5. What would you learn?

**Exercise 5: Disaster Recovery**

Your primary data center just caught fire. Walk through:
1. How do you verify it's really down?
2. What's your failover procedure?
3. How do you prevent data loss?
4. How do you verify recovery?
5. How do you fail back?

### Hands-On Practice

**Practice 1: Set Up Observability**
- Deploy Prometheus, Grafana, and Jaeger
- Instrument a simple service with metrics, logs, and traces
- Create a dashboard showing golden signals
- Set up an alert that fires on high error rate
- Generate a trace and follow a request through the system

**Practice 2: Run an Incident Simulation**
- Form teams (commander, tech lead, comms, scribe)
- Inject a failure into a test system
- Follow incident response process
- Write a postmortem
- Identify improvements

**Practice 3: Automate a Runbook**
- Choose a common operational task
- Write a manual runbook
- Implement as an automated script
- Add safety checks and rollback
- Test in a staging environment

**Practice 4: Conduct a Game Day**
- Schedule a chaos experiment
- Inject a realistic failure
- Observe team response
- Measure impact on SLOs
- Document lessons learned

**Practice 5: Build a Progressive Deployment**
- Implement canary deployment for a service
- Add automatic rollback on regression
- Monitor metrics during rollout
- Test with an intentionally bad deployment
- Verify automatic rollback works

---

## Key Takeaways

**Operating distributed systems is not separate from building them**. Operations must be designed in from the start, not bolted on after deployment.

**Observability is foundational**. You cannot operate what you cannot see. Metrics, logs, and traces are not optional—they're essential.

**Incidents are opportunities**. Every outage is a chance to learn, improve, and strengthen the system. Blameless culture encourages honesty and learning.

**Automation scales operations**. Manual processes don't scale. Automate toil, automate runbooks, automate everything repetitive.

**Team culture matters as much as technology**. Sustainable on-call, knowledge sharing, blameless postmortems, and continuous improvement create operational excellence.

**Prevention is cheaper than recovery**. Investing in chaos engineering, synthetic monitoring, and proactive capacity planning prevents outages that are far more expensive to fix.

**Complexity is the enemy of reliability**. Every new service, feature, and dependency makes operations harder. Choose simplicity when possible.

**Operational excellence is a journey, not a destination**. There's always room to improve. Small, continuous improvements compound into major advances.

The gap between building and operating distributed systems is real. This chapter has given you the mental models, practices, and tools to bridge that gap. The experiences, patterns, and principles you've learned will serve you whether you're operating a three-server startup or a thousand-server enterprise system.

Operations is where theory meets reality. Where algorithms meet infrastructure. Where code meets customers. It's challenging, demanding, and sometimes frustrating. But it's also where you learn the deepest lessons about distributed systems—lessons that can only be learned by keeping systems alive under pressure.

Welcome to operations. Your phone is about to ring.

### Building an Operations Culture

Technical practices alone don't create operational excellence. You need a culture that values reliability.

#### The Blameless Culture

```python
class BlamelessPostmortem:
    """Framework for learning from incidents without blame"""

    def __init__(self, incident):
        self.incident = incident
        self.principles = [
            "Assume good intentions",
            "Focus on systems, not individuals",
            "Ask 'what' and 'how', not 'who' and 'why'",
            "Identify contributing factors, not assign blame",
            "Learn to prevent, not punish"
        ]

    def conduct_postmortem(self):
        """Structured postmortem process"""

        # 1. Gather participants
        participants = self.gather_participants()

        # 2. Build timeline collaboratively
        timeline = self.build_timeline(participants)

        # 3. Identify contributing factors
        factors = self.identify_contributing_factors()

        # 4. Ask "Five Whys"
        root_causes = self.five_whys(factors)

        # 5. Identify action items
        actions = self.identify_actions(root_causes)

        # 6. Assign owners and due dates
        assigned_actions = self.assign_actions(actions)

        # 7. Share widely
        self.publish_postmortem(timeline, factors, actions)

        # 8. Track completion
        self.track_action_items(assigned_actions)

    def five_whys(self, initial_problem):
        """Root cause analysis technique"""
        current = initial_problem
        whys = []

        for i in range(5):
            why = f"Why did {current} happen?"
            answer = self.investigate(why)
            whys.append({'question': why, 'answer': answer})
            current = answer

        return whys

# Example: Five Whys for database outage
"""
Problem: Database ran out of disk space

Why #1: Why did database run out of disk space?
Answer: Logs were not being rotated

Why #2: Why were logs not being rotated?
Answer: Log rotation was disabled in configuration

Why #3: Why was log rotation disabled?
Answer: It was disabled during a debugging session 6 months ago

Why #4: Why was it not re-enabled after debugging?
Answer: No process to review temporary configuration changes

Why #5: Why is there no review process?
Answer: We never defined operational change management process

Root cause: Lack of change management process
Action: Implement configuration change review process
"""
```

#### Sustainable On-Call

Burnout destroys teams. Sustainable on-call preserves them.

```python
class OnCallPolicy:
    """Policies for sustainable on-call"""

    def __init__(self):
        self.policies = {
            'rotation_length': '1_week',  # Not too long (burnout) or short (context switching)
            'minimum_team_size': 6,  # Need 6+ people for healthy rotation
            'handoff_time': '30_minutes',  # Proper context transfer
            'escalation_path': 'defined',  # Clear escalation
            'compensation': 'time_off_or_pay',  # Compensate on-call time
            'alert_budget': 'max_5_per_week',  # Limit alert noise
            'incident_count': 'max_2_sev1_per_quarter',  # Reliability threshold
        }

    def rotation_schedule(self, team_size):
        """Calculate on-call frequency"""
        weeks_per_person = team_size  # Each person on-call once every N weeks

        # If someone is on-call more than once per month, team is too small
        if weeks_per_person < 4:
            return {
                'status': 'unhealthy',
                'frequency': f'Once every {weeks_per_person} weeks',
                'recommendation': 'Hire more engineers or reduce service count'
            }

        return {
            'status': 'healthy',
            'frequency': f'Once every {weeks_per_person} weeks',
            'recommendation': 'Current rotation is sustainable'
        }

    def alert_load_analysis(self, alerts_per_week):
        """Analyze if alert load is sustainable"""
        if alerts_per_week > 10:
            return {
                'status': 'critical',
                'problem': 'Alert fatigue - too many alerts',
                'impact': 'Engineers will start ignoring alerts',
                'action': 'Reduce alert noise by 50%+ immediately'
            }
        elif alerts_per_week > 5:
            return {
                'status': 'warning',
                'problem': 'High alert volume',
                'action': 'Review alerts and eliminate false positives'
            }
        else:
            return {
                'status': 'healthy',
                'action': 'Monitor alert trends'
            }
```

**On-call checklist for managers**:

```yaml
sustainable_oncall_checklist:
  team_size:
    - "Do we have 6+ people for rotation?"
    - "Are we hiring if team is too small?"

  alert_quality:
    - "Are alerts actionable?"
    - "Are we seeing <5 alerts per week?"
    - "Are false positive rate <10%?"

  runbook_quality:
    - "Does every alert have a runbook?"
    - "Are runbooks tested quarterly?"
    - "Are runbooks kept up to date?"

  incident_load:
    - "Are we seeing <2 SEV1 incidents per quarter?"
    - "Are incidents resolved within SLA?"
    - "Are we preventing recurrence?"

  compensation:
    - "Do engineers get comp time or pay for on-call?"
    - "Are we recognizing good on-call work?"

  morale:
    - "Are engineers burned out?"
    - "Are people leaving due to on-call?"
    - "Are we measuring on-call satisfaction?"
```

#### The Toil Budget

Not all work is equal. Toil is repetitive work that should be automated.

```python
class ToilTracker:
    """Track and reduce operational toil"""

    def __init__(self):
        self.toil_budget = 0.50  # No more than 50% of time should be toil
        self.toil_categories = {
            'manual_deployments': 0,
            'restarting_services': 0,
            'responding_to_alerts': 0,
            'manual_scaling': 0,
            'data_fixes': 0,
            'customer_support_escalations': 0,
            'other': 0
        }

    def measure_toil(self, team, time_period='week'):
        """Measure what percentage of time is toil"""
        total_hours = self.get_total_hours(team, time_period)
        toil_hours = self.get_toil_hours(team, time_period)

        toil_percentage = toil_hours / total_hours

        if toil_percentage > self.toil_budget:
            return {
                'status': 'over_budget',
                'toil_percentage': toil_percentage,
                'toil_hours': toil_hours,
                'recommendation': 'Focus on automation - toil is preventing feature work'
            }

        return {
            'status': 'healthy',
            'toil_percentage': toil_percentage,
            'engineering_hours': total_hours - toil_hours
        }

    def prioritize_automation(self, toil_categories):
        """What should we automate first?"""
        # Calculate ROI of automating each category
        priorities = []

        for category, hours_per_week in toil_categories.items():
            # Estimate automation effort
            automation_effort = self.estimate_automation_effort(category)

            # Calculate payback period
            payback_weeks = automation_effort / hours_per_week

            # Complexity
            complexity = self.estimate_complexity(category)

            priorities.append({
                'category': category,
                'hours_per_week': hours_per_week,
                'automation_effort': automation_effort,
                'payback_weeks': payback_weeks,
                'complexity': complexity,
                'priority': self.calculate_priority(hours_per_week, payback_weeks, complexity)
            })

        # Sort by priority
        priorities.sort(key=lambda x: x['priority'], reverse=True)

        return priorities
```

### Security Operations

Security is not separate from operations—it's integral.

#### Secrets Management

```python
class SecretsManager:
    """Secure secrets management practices"""

    def __init__(self):
        self.principles = [
            "Never commit secrets to git",
            "Rotate secrets regularly",
            "Use different secrets per environment",
            "Encrypt secrets at rest",
            "Audit secret access",
            "Expire secrets automatically"
        ]

    def secret_rotation_policy(self):
        """Define rotation schedule for different secret types"""
        return {
            'database_passwords': {
                'rotation': '90_days',
                'automation': 'required',
                'zero_downtime': True
            },
            'api_keys': {
                'rotation': '180_days',
                'automation': 'recommended',
                'overlap_period': '7_days'  # Both old and new work during transition
            },
            'tls_certificates': {
                'rotation': '90_days',
                'automation': 'required',  # Let's Encrypt
                'expiry_alert': '30_days_before'
            },
            'ssh_keys': {
                'rotation': '365_days',
                'automation': 'recommended',
                'principle': 'one_key_per_person'
            }
        }

    def access_audit(self):
        """Audit who accessed what secrets when"""
        # Log every secret access
        # Alert on unusual patterns
        # Review access logs regularly
        pass
```

#### Security Monitoring

```python
class SecurityMonitoring:
    """Monitor for security threats"""

    def __init__(self):
        self.monitors = []

    def add_monitors(self):
        """Critical security monitors"""
        self.monitors = [
            {
                'name': 'Failed login attempts',
                'query': 'rate(login_failures[5m]) > 10',
                'severity': 'high',
                'action': 'Investigate potential brute force attack'
            },
            {
                'name': 'Unusual data access patterns',
                'query': 'detect anomalies in database query patterns',
                'severity': 'medium',
                'action': 'Review access logs for data exfiltration'
            },
            {
                'name': 'Privilege escalation attempts',
                'query': 'sudo commands from non-approved users',
                'severity': 'critical',
                'action': 'Immediate investigation'
            },
            {
                'name': 'Unusual network traffic',
                'query': 'outbound connections to unexpected IPs',
                'severity': 'high',
                'action': 'Check for compromised instances'
            },
            {
                'name': 'Secret access from unusual locations',
                'query': 'secret access from non-production IPs',
                'severity': 'critical',
                'action': 'Rotate secrets immediately'
            }
        ]
```

### Cost Optimization

Operations includes managing cloud costs.

```python
class CostOptimization:
    """Monitor and optimize infrastructure costs"""

    def __init__(self):
        self.cost_per_request_target = 0.001  # $0.001 per request
        self.cost_per_user_target = 0.50  # $0.50 per active user per month

    def analyze_costs(self):
        """Break down where money is going"""
        return {
            'compute': {
                'ec2_instances': '$50,000/month',
                'optimization': 'Use spot instances for non-critical workloads',
                'potential_savings': '30%'
            },
            'storage': {
                's3': '$20,000/month',
                'optimization': 'Move old data to Glacier, enable lifecycle policies',
                'potential_savings': '40%'
            },
            'database': {
                'rds': '$30,000/month',
                'optimization': 'Rightsize instances, use read replicas efficiently',
                'potential_savings': '20%'
            },
            'network': {
                'data_transfer': '$15,000/month',
                'optimization': 'Use CloudFront for static content, optimize API payloads',
                'potential_savings': '25%'
            },
            'unused_resources': {
                'orphaned_ebs': '$5,000/month',
                'optimization': 'Delete unused volumes and snapshots',
                'potential_savings': '100%'
            }
        }

    def cost_anomaly_detection(self, daily_costs):
        """Detect unusual cost spikes"""
        # Calculate baseline
        baseline_mean = np.mean(daily_costs[-30:])
        baseline_std = np.std(daily_costs[-30:])

        # Today's cost
        today_cost = daily_costs[-1]

        # Check for anomaly
        z_score = (today_cost - baseline_mean) / baseline_std

        if z_score > 3:  # 3 sigma
            return {
                'anomaly': True,
                'cost': today_cost,
                'baseline': baseline_mean,
                'increase': (today_cost - baseline_mean) / baseline_mean * 100,
                'action': 'Investigate cost spike immediately'
            }

        return {'anomaly': False}

    def showback_by_team(self):
        """Show each team their infrastructure costs"""
        # Tag resources by team
        # Generate monthly cost reports per team
        # Encourage cost awareness
        pass
```

### Multi-Region Operations

Operating across regions adds complexity.

```python
class MultiRegionOperations:
    """Patterns for operating across regions"""

    def __init__(self):
        self.regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']

    def deployment_strategy(self):
        """How to deploy across regions"""
        return {
            'strategy': 'rolling_by_region',
            'order': [
                'ap-southeast-1',  # Smallest region first
                'eu-west-1',
                'us-west-2',
                'us-east-1'  # Largest region last
            ],
            'pause_between_regions': '2_hours',  # Monitor for issues
            'rollback_trigger': 'error_rate > 1.5x baseline',
            'rollback_scope': 'current_region_only'  # Don't rollback successful regions
        }

    def monitoring_strategy(self):
        """Monitor across regions"""
        return {
            'per_region_dashboards': True,
            'global_aggregate_dashboard': True,
            'regional_alerts': 'Fire when single region degrades',
            'global_alerts': 'Fire when multiple regions degrade',
            'correlation': 'Detect issues spreading across regions'
        }

    def incident_response(self, incident):
        """Handle multi-region incidents"""
        if incident.scope == 'single_region':
            # Failover traffic to other regions
            self.failover_region(incident.region)

        elif incident.scope == 'multiple_regions':
            # Global issue - investigate common cause
            self.investigate_global_issue(incident)

        elif incident.scope == 'all_regions':
            # Complete outage - disaster recovery
            self.activate_disaster_recovery()

    def data_consistency_across_regions(self):
        """Ensure data consistency"""
        return {
            'user_data': 'Multi-region active-active with conflict resolution',
            'transactions': 'Single-region (routed by user location)',
            'analytics': 'Eventually consistent (acceptable staleness)',
            'configuration': 'Strongly consistent (global consensus)'
        }
```

### Compliance and Audit Operations

Regulated industries have additional operational requirements.

```python
class ComplianceOperations:
    """Operations for regulated environments"""

    def __init__(self):
        self.frameworks = ['SOC2', 'HIPAA', 'PCI-DSS', 'GDPR']

    def audit_logging(self):
        """Comprehensive audit trail"""
        return {
            'what_to_log': [
                'All data access',
                'All configuration changes',
                'All deployments',
                'All secret access',
                'All privilege escalations',
                'All user authentications',
                'All failed authorization attempts'
            ],
            'retention': '7_years',  # Compliance requirement
            'immutability': True,  # Cannot modify logs
            'encryption': True,  # Encrypt logs at rest
            'access_control': 'Strict RBAC on audit logs'
        }

    def change_management(self):
        """Formal change management process"""
        return {
            'change_types': {
                'standard': 'Pre-approved, low-risk (e.g., scaling)',
                'normal': 'Requires approval, most changes',
                'emergency': 'Expedited approval for incidents'
            },
            'approval_process': {
                'requester': 'Engineer requesting change',
                'reviewer': 'Senior engineer or tech lead',
                'approver': 'Manager or change advisory board',
                'testing': 'Must be tested in staging',
                'rollback_plan': 'Must have documented rollback'
            },
            'documentation': {
                'what_changed': 'Detailed description',
                'why_changed': 'Business justification',
                'testing_done': 'Test results',
                'rollback_procedure': 'Step-by-step rollback',
                'communication_plan': 'Who to notify'
            }
        }

    def access_control(self):
        """Principle of least privilege"""
        return {
            'production_access': 'Minimal, time-limited, audited',
            'just_in_time': 'Request access for specific time period',
            'break_glass': 'Emergency access with automatic alerts',
            'regular_review': 'Quarterly access review',
            'revocation': 'Immediate revocation when leaving team'
        }
```

### Performance Tuning at Scale

Operations includes performance optimization.

```python
class PerformanceTuning:
    """Systematic performance optimization"""

    def __init__(self):
        self.methodology = [
            'Measure baseline',
            'Identify bottleneck',
            'Form hypothesis',
            'Implement fix',
            'Measure improvement',
            'Repeat'
        ]

    def identify_bottleneck(self, service):
        """Find the limiting factor"""

        # Measure each component
        measurements = {
            'cpu': self.measure_cpu_usage(service),
            'memory': self.measure_memory_usage(service),
            'disk_io': self.measure_disk_io(service),
            'network_io': self.measure_network_io(service),
            'database': self.measure_database_latency(service),
            'external_apis': self.measure_external_api_latency(service),
        }

        # Find the bottleneck (highest utilization or latency)
        bottleneck = max(measurements.items(), key=lambda x: x[1]['utilization'])

        return {
            'bottleneck': bottleneck[0],
            'utilization': bottleneck[1]['utilization'],
            'recommendation': self.get_optimization_for(bottleneck[0])
        }

    def get_optimization_for(self, resource):
        """Get optimization recommendations"""
        optimizations = {
            'cpu': [
                'Profile application to find hot paths',
                'Optimize algorithms',
                'Add caching',
                'Scale horizontally'
            ],
            'memory': [
                'Check for memory leaks',
                'Optimize data structures',
                'Implement memory pooling',
                'Scale vertically'
            ],
            'disk_io': [
                'Add caching layer',
                'Optimize queries',
                'Use SSD instead of HDD',
                'Implement read replicas'
            ],
            'network_io': [
                'Reduce payload size',
                'Enable compression',
                'Use connection pooling',
                'Implement CDN'
            ],
            'database': [
                'Add indexes',
                'Optimize queries',
                'Implement caching',
                'Add read replicas',
                'Shard database'
            ],
            'external_apis': [
                'Implement caching',
                'Reduce call frequency',
                'Use batch APIs',
                'Implement circuit breakers'
            ]
        }

        return optimizations.get(resource, [])

    def database_optimization(self):
        """Common database optimizations"""
        return {
            'query_optimization': {
                'analyze_slow_queries': 'Find queries taking >100ms',
                'add_indexes': 'Index columns used in WHERE, JOIN, ORDER BY',
                'update_statistics': 'Keep query planner statistics current',
                'rewrite_queries': 'Simplify complex queries',
            },
            'connection_pooling': {
                'pool_size': 'Size based on workload',
                'connection_reuse': 'Reuse connections instead of creating new',
                'timeout_settings': 'Appropriate timeouts'
            },
            'caching': {
                'query_result_cache': 'Cache frequently accessed data',
                'connection_cache': 'Cache database connections',
                'prepared_statements': 'Reuse query plans'
            },
            'schema_optimization': {
                'denormalization': 'Reduce joins for read-heavy workloads',
                'partitioning': 'Partition large tables',
                'archiving': 'Move old data to archive tables'
            }
        }
```

### Observability at Scale

As systems grow, observability must scale too.

```python
class ObservabilityAtScale:
    """Observability for large-scale systems"""

    def __init__(self):
        self.scale_challenges = [
            'Millions of metrics',
            'Terabytes of logs daily',
            'Billions of traces',
            'High cardinality data',
            'Cost of storage'
        ]

    def metric_sampling_strategy(self):
        """How to sample metrics at scale"""
        return {
            'high_value_metrics': {
                'sampling': '100%',  # Keep all
                'retention': '13_months',
                'examples': ['error_rate', 'latency', 'availability']
            },
            'medium_value_metrics': {
                'sampling': '10%',
                'retention': '3_months',
                'examples': ['per_endpoint_latency', 'cache_hit_rate']
            },
            'low_value_metrics': {
                'sampling': '1%',
                'retention': '1_month',
                'examples': ['debug_counters', 'experimental_metrics']
            }
        }

    def log_sampling_strategy(self):
        """How to sample logs at scale"""
        return {
            'errors': {
                'sampling': '100%',  # Keep all errors
                'retention': '90_days'
            },
            'warnings': {
                'sampling': '100%',
                'retention': '30_days'
            },
            'info': {
                'sampling': '10%',  # Sample info logs
                'retention': '7_days'
            },
            'debug': {
                'sampling': '0%',  # Disabled in production
                'retention': '0_days'
            }
        }

    def trace_sampling_strategy(self):
        """How to sample traces at scale"""
        return {
            'errors': {
                'sampling': '100%',  # Trace all errors
                'reason': 'Need full context for errors'
            },
            'slow_requests': {
                'sampling': '100%',  # Trace all slow requests
                'threshold': 'p95_latency',
                'reason': 'Understand performance issues'
            },
            'normal_requests': {
                'sampling': '1%',  # Sample normal requests
                'method': 'probabilistic',
                'reason': 'Reduce storage costs'
            },
            'adaptive_sampling': {
                'enabled': True,
                'method': 'Sample more when error rate increases',
                'reason': 'Increase sampling during incidents'
            }
        }

    def high_cardinality_handling(self):
        """Handle high-cardinality dimensions"""
        return {
            'problem': 'user_id as metric label creates millions of time series',
            'solutions': [
                'Use logs for high-cardinality data, not metrics',
                'Aggregate by low-cardinality dimensions',
                'Use exemplars (sample high-cardinality values)',
                'Use different storage for high-cardinality (e.g., Elasticsearch)'
            ],
            'example': {
                'bad': 'error_count{user_id="123456"}',
                'good': 'error_count{error_type="payment_failed"}'
            }
        }
```

---

## Further Reading

**Books**:
- *Site Reliability Engineering* (Google) - The foundational SRE book
- *The Site Reliability Workbook* (Google) - Practical SRE implementation
- *Observability Engineering* (Majors et al.) - Modern observability practices
- *Chaos Engineering* (Rosenthal & Jones) - Comprehensive chaos engineering guide
- *The DevOps Handbook* (Kim et al.) - DevOps practices and culture
- *Seeking SRE* (Blank-Edelman) - Diverse perspectives on SRE
- *Database Reliability Engineering* (Campbell & Majors) - Database operations
- *The Phoenix Project* (Kim et al.) - DevOps novel

**Papers**:
- "The Calculus of Service Availability" (Shapiro)
- "Observability for Emerging Infrastructure" (Majors)
- "Principled Chaos Engineering" (Netflix)
- "Large-scale cluster management at Google with Borg" (Verma et al.)

**Resources**:
- Google SRE books (free online)
- Increment magazine (distributed systems issue)
- SREcon presentations
- Kubernetes production readiness checklist
- AWS Well-Architected Framework
- Azure Architecture Center

**Tools to explore**:
- **Metrics**: Prometheus, Datadog, New Relic
- **Dashboards**: Grafana, Kibana
- **Logs**: Loki, Elasticsearch, Splunk
- **Tracing**: Jaeger, Tempo, Zipkin
- **Instrumentation**: OpenTelemetry
- **Chaos Engineering**: Chaos Toolkit, Gremlin, Chaos Monkey
- **Incident Management**: PagerDuty, Opsgenie, VictorOps
- **Cost Management**: CloudHealth, Kubecost

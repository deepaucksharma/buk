# Distributed Tracing: Following Requests Across the Abyss

## Introduction: The Visibility Problem

At 2:47 AM, your phone buzzes. A customer reports that checkout is taking 30 seconds instead of the usual 2 seconds. You open your monitoring dashboard and see:

- API Gateway: 200ms average latency (normal)
- Order Service: 150ms average latency (normal)
- Payment Service: 180ms average latency (normal)
- Inventory Service: 120ms average latency (normal)
- Database: 50ms average query time (normal)

Every component looks healthy. Yet users are experiencing 30-second delays. **Where are those 28 seconds hiding?**

This is the distributed systems visibility problem: in a system composed of dozens of microservices, each request touches multiple services, and understanding the end-to-end flow requires **distributed tracing**—the ability to follow a single request's journey through the entire system.

### Why Traditional Monitoring Fails

Traditional monitoring gives you **per-service metrics** (averages, percentiles), but:

- **Hides sequential delays**: If Request A takes 100ms in Service 1, then 100ms in Service 2, then 100ms in Service 3, the total is 300ms—but each service reports only 100ms
- **Obscures parallel inefficiency**: If Service 1 fans out to 10 parallel calls, one slow call (5s) blocks the entire request while the other 9 finish in 100ms
- **Misses cross-cutting issues**: A specific user ID, region, or feature flag might trigger a pathological code path that only affects 0.1% of requests (hidden in averages)
- **Lacks causality**: You see "Database is slow" and "API is slow," but you don't know if the API is slow *because* the database is slow, or if they're independent issues

### The Tracing Insight

Distributed tracing treats **each request as a unit of observation**. Instead of aggregating metrics across all requests, tracing:

1. **Assigns a unique ID** to each incoming request (trace ID)
2. **Propagates that ID** to every service the request touches
3. **Records timing and metadata** for each step (span)
4. **Assembles the full picture** after the request completes

With distributed tracing, that 30-second checkout request reveals:

```
Trace ID: a7f3c2d1-8b9e-4f1a-a2b3-c4d5e6f7a8b9

API Gateway                     [0ms ─────────────── 200ms]
  ├─ Order Service              [50ms ──────────── 150ms]
  │   ├─ Validate cart          [50ms ─ 80ms]
  │   └─ Create order           [80ms ────── 150ms]
  │       └─ Database write     [90ms ── 145ms]
  ├─ Inventory Service          [150ms ──────── 270ms]
  │   ├─ Check stock            [150ms ─ 200ms]
  │   └─ Reserve items          [200ms ─── 270ms]
  └─ Payment Service            [270ms ───────────────────── 30,200ms] ⚠️
      ├─ Validate payment       [270ms ─ 320ms]
      └─ Charge card            [320ms ────────────────── 30,200ms] ⚠️
          └─ External API call  [500ms ──────────────── 30,200ms] ⚠️
              (Retry loop: 10 attempts × 3s timeout each)

Total: 30,200ms
```

**The culprit**: Payment Service is retrying a failing external API call 10 times with a 3-second timeout each, blocking the entire checkout flow.

This is invisible in average metrics (Payment Service's median latency is still 180ms—most requests succeed quickly), but **visible in per-request traces**.

### The Evidence Flow

Distributed tracing is **evidence infrastructure** for answering:

- **Why is this specific request slow?** (trace the request, find the bottleneck)
- **What percentage of requests hit the slow path?** (sample traces, analyze patterns)
- **How do failures cascade?** (trace error propagation across services)
- **What's on the critical path?** (identify dependencies blocking request completion)

The core invariant: **CAUSALITY** — We must be able to reconstruct the causal chain of events for any request, across all services, at any time.

## Part 1: Spans and Traces — The Fundamental Primitives

### What Is a Span?

A **span** represents a single unit of work in a distributed system. Each span records:

```python
@dataclass
class Span:
    trace_id: str        # Unique ID for the entire request
    span_id: str         # Unique ID for this specific span
    parent_span_id: str  # ID of the parent span (null for root)
    operation_name: str  # Human-readable name ("GET /checkout")
    start_time: int      # Nanoseconds since epoch
    duration: int        # Nanoseconds elapsed
    tags: dict          # Key-value metadata (service, HTTP status, user ID)
    logs: list          # Timestamped events within the span
```

**Example span** (JSON representation):

```json
{
  "traceId": "a7f3c2d1-8b9e-4f1a-a2b3-c4d5e6f7a8b9",
  "spanId": "b1c2d3e4-f5a6-b7c8-d9e0-f1a2b3c4d5e6",
  "parentSpanId": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
  "operationName": "payment_service.charge_card",
  "startTime": 1704067200000000000,
  "duration": 29900000000,
  "tags": {
    "service.name": "payment-service",
    "service.version": "v2.3.1",
    "http.method": "POST",
    "http.url": "/api/v1/payments",
    "http.status_code": 500,
    "error": true,
    "user.id": "user_12345",
    "payment.amount": 99.99,
    "payment.currency": "USD"
  },
  "logs": [
    {
      "timestamp": 1704067200500000000,
      "event": "calling_external_api",
      "api.provider": "stripe"
    },
    {
      "timestamp": 1704067203500000000,
      "event": "external_api_timeout",
      "error.message": "Timeout after 3000ms"
    },
    {
      "timestamp": 1704067203600000000,
      "event": "retry_attempt",
      "retry.count": 1
    }
  ]
}
```

### What Is a Trace?

A **trace** is a collection of spans representing a single request's journey through the system. Spans form a **directed acyclic graph (DAG)** based on parent-child relationships:

```
Trace: a7f3c2d1-8b9e-4f1a-a2b3-c4d5e6f7a8b9

Root Span (API Gateway)
├─ Child Span (Order Service)
│  ├─ Grandchild Span (Database: validate cart)
│  └─ Grandchild Span (Database: create order)
├─ Child Span (Inventory Service)
│  ├─ Grandchild Span (Database: check stock)
│  └─ Grandchild Span (Database: reserve items)
└─ Child Span (Payment Service)
   ├─ Grandchild Span (Validate payment method)
   └─ Grandchild Span (External API: charge card)
      └─ Great-grandchild Span (HTTP call to Stripe)
```

### The Three Relationships

Spans relate to each other in three ways:

**1. Parent-Child (Sequential)**: Span B starts after Span A finishes

```
[Span A: Validate cart] → [Span B: Create order]
```

**2. Parent-Children (Parallel)**: Multiple spans start simultaneously

```
                    ┌─ [Span B: Check inventory]
[Span A: Process] ──┼─ [Span C: Validate payment]
                    └─ [Span D: Calculate shipping]
```

**3. Follows-From (Asynchronous)**: Span B is triggered by Span A but executes independently

```
[Span A: Order placed] ──→ [Span B: Send confirmation email]
                            (happens later, doesn't block A)
```

### Instrumenting Code with Spans

**Manual instrumentation** (explicit span creation):

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

def checkout(cart_id: str, user_id: str) -> dict:
    # Create root span for the checkout operation
    with tracer.start_as_current_span("checkout") as span:
        span.set_attribute("cart.id", cart_id)
        span.set_attribute("user.id", user_id)

        try:
            # Child span: validate cart
            with tracer.start_as_current_span("validate_cart") as validate_span:
                cart = validate_cart(cart_id)
                validate_span.set_attribute("cart.item_count", len(cart.items))
                validate_span.set_attribute("cart.total", cart.total)

            # Child span: process payment
            with tracer.start_as_current_span("process_payment") as payment_span:
                payment_span.set_attribute("amount", cart.total)
                payment_span.set_attribute("currency", "USD")

                payment_result = charge_card(user_id, cart.total)

                payment_span.set_attribute("payment.status", payment_result.status)
                payment_span.set_attribute("payment.transaction_id", payment_result.tx_id)

            # Child span: create order
            with tracer.start_as_current_span("create_order") as order_span:
                order = create_order(cart_id, user_id, payment_result.tx_id)
                order_span.set_attribute("order.id", order.id)

            span.set_status(Status(StatusCode.OK))
            return {"order_id": order.id, "status": "success"}

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
```

**What this generates**:

```
Trace: checkout_12345
├─ checkout [0ms ─────────────── 1200ms] ✓
   ├─ validate_cart [10ms ─ 150ms] ✓
   ├─ process_payment [150ms ──── 1050ms] ✓
   └─ create_order [1050ms ── 1200ms] ✓
```

### Automatic Instrumentation

**Problem**: Manually adding spans to every function is tedious and error-prone.

**Solution**: Automatic instrumentation via **libraries and middleware** that inject spans for common operations:

```python
# Automatically instrument HTTP requests
from opentelemetry.instrumentation.requests import RequestsInstrumentor
RequestsInstrumentor().instrument()

# Automatically instrument database queries
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
Psycopg2Instrumentor().instrument()

# Automatically instrument Flask web framework
from opentelemetry.instrumentation.flask import FlaskInstrumentor
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# Now every HTTP request, database query, and Flask route automatically creates spans
import requests
response = requests.get("https://api.example.com/users")
# Automatically creates span: "HTTP GET https://api.example.com/users"
```

**Automatic instrumentation captures**:

- **HTTP requests**: URL, method, status code, latency
- **Database queries**: Query text, execution time, rows returned
- **RPC calls**: gRPC, Thrift, custom protocols
- **Message queues**: Kafka, RabbitMQ, SQS
- **Caching**: Redis, Memcached

**Trade-off**: Automatic instrumentation gives broad coverage but lacks business context. Combine with manual spans for critical business logic.

## Part 2: Context Propagation — The Distributed Challenge

### The Fundamental Problem

In a monolithic application, tracing is easy: every function call shares the same memory space, so passing trace context is trivial.

In a distributed system, **requests cross process boundaries** (via HTTP, gRPC, message queues), and each service runs in a separate process with separate memory. How do we propagate trace context?

### The W3C Trace Context Standard

The **W3C Trace Context** standard defines how to propagate trace context across services via HTTP headers:

```
traceparent: 00-a7f3c2d18b9e4f1aa2b3c4d5e6f7a8b9-b1c2d3e4f5a6b7c8-01

Format:
  00: Version
  a7f3c2d18b9e4f1aa2b3c4d5e6f7a8b9: Trace ID (128-bit)
  b1c2d3e4f5a6b7c8: Parent Span ID (64-bit)
  01: Trace flags (sampled=true)
```

**How it works**:

1. **Service A** creates a trace and span
2. **Service A** calls **Service B** via HTTP, injecting trace context in headers
3. **Service B** extracts trace context from headers, creates a child span
4. **Service B** calls **Service C**, propagating trace context
5. All spans share the same trace ID, forming a complete trace

### Implementing Context Propagation

**Service A (caller)**:

```python
from opentelemetry import trace
from opentelemetry.propagate import inject
import requests

tracer = trace.get_tracer(__name__)

def call_service_b():
    with tracer.start_as_current_span("call_service_b") as span:
        # Prepare HTTP headers
        headers = {}

        # Inject trace context into headers
        inject(headers)

        # Headers now contain: {"traceparent": "00-...", "tracestate": "..."}
        response = requests.post(
            "https://service-b/api/process",
            headers=headers,
            json={"data": "value"}
        )

        span.set_attribute("http.status_code", response.status_code)
        return response.json()
```

**Service B (callee)**:

```python
from opentelemetry import trace
from opentelemetry.propagate import extract
from flask import Flask, request

app = Flask(__name__)
tracer = trace.get_tracer(__name__)

@app.route("/api/process", methods=["POST"])
def process():
    # Extract trace context from incoming HTTP headers
    context = extract(request.headers)

    # Create span as child of extracted context
    with tracer.start_as_current_span("process_request", context=context) as span:
        data = request.json
        span.set_attribute("request.data", str(data))

        # Do work
        result = perform_processing(data)

        return {"result": result}
```

**What happens**:

- Service A's span ID becomes Service B's parent span ID
- Both spans share the same trace ID
- Service B's span is correctly nested under Service A's span in the trace

### Propagation Across Different Protocols

**HTTP**: Use headers (`traceparent`, `tracestate`)

**gRPC**: Use metadata

```python
import grpc
from opentelemetry.propagate import inject

def call_grpc_service():
    with tracer.start_as_current_span("grpc_call") as span:
        metadata = {}
        inject(metadata)

        # Convert to gRPC metadata format
        grpc_metadata = [(k, v) for k, v in metadata.items()]

        with grpc.insecure_channel("service-b:50051") as channel:
            stub = MyServiceStub(channel)
            response = stub.Process(request, metadata=grpc_metadata)
```

**Message Queues (Kafka, RabbitMQ)**: Embed in message headers

```python
from kafka import KafkaProducer
from opentelemetry.propagate import inject

def publish_message():
    with tracer.start_as_current_span("publish_message") as span:
        headers = {}
        inject(headers)

        # Kafka headers
        kafka_headers = [(k, v.encode()) for k, v in headers.items()]

        producer.send(
            "orders",
            value=message.encode(),
            headers=kafka_headers
        )
```

**Async/Background Jobs**: Embed in job metadata

```python
from celery import Celery
from opentelemetry.propagate import inject

app = Celery("tasks")

def enqueue_task():
    with tracer.start_as_current_span("enqueue_task") as span:
        headers = {}
        inject(headers)

        # Pass trace context as task argument
        process_order.delay(order_id, trace_context=headers)

@app.task
def process_order(order_id, trace_context):
    context = extract(trace_context)
    with tracer.start_as_current_span("process_order", context=context):
        # Task executes with proper trace context
        pass
```

### The Lost Context Problem

**Scenario**: Service A calls Service B, which enqueues a message to Kafka. A background worker consumes the message and processes it.

**Problem**: If trace context isn't propagated through the message queue, the worker's spans will start a **new, disconnected trace** instead of being part of the original trace.

**Solution**: Always propagate trace context through **every** inter-process boundary:

```python
# Producer: Inject context into message
headers = {}
inject(headers)
producer.send("orders", value=message, headers=headers)

# Consumer: Extract context from message
for message in consumer:
    context = extract(dict(message.headers))
    with tracer.start_as_current_span("process_message", context=context):
        handle_message(message.value)
```

**Evidence**: Complete traces spanning synchronous calls, asynchronous messages, and background jobs.

## Part 3: Sampling Strategies — Managing the Data Deluge

### The Scalability Problem

At scale, **tracing every request is prohibitively expensive**:

- **High-volume system**: 1 million requests/second
- **Average trace size**: 50 spans × 1KB per span = 50KB per trace
- **Total data**: 1M req/s × 50KB = 50GB/second = 4.3PB/day

**Cost**: Storing, transmitting, and querying 4PB/day of trace data is economically infeasible for most organizations.

**Solution**: **Sampling** — record only a subset of traces while still gaining visibility.

### Sampling Strategies

#### 1. Head-Based Sampling (Probabilistic)

**Definition**: Decide whether to record a trace **at the beginning** of the request (at the "head"), based on probability.

**Implementation**:

```python
import random

def should_sample(trace_id: str, sample_rate: float = 0.01) -> bool:
    """Sample 1% of traces."""
    return random.random() < sample_rate

def handle_request(request):
    trace_id = generate_trace_id()
    sampled = should_sample(trace_id, sample_rate=0.01)

    if sampled:
        with tracer.start_as_current_span("handle_request") as span:
            # Trace is recorded
            process_request(request)
    else:
        # Trace is not recorded (but trace_id still propagated for logging)
        process_request(request)
```

**Advantages**:

- Simple to implement
- Predictable storage cost (sample 1% → reduce data by 99%)
- Low overhead (sampling decision made once per trace)

**Disadvantages**:

- **Misses rare errors**: If only 0.01% of requests fail, and you sample 1%, you'll only capture 1 in 10,000 failures
- **Unbiased but uninteresting**: Captures a representative sample, but representative ≠ useful (most traces are boring; the interesting ones are rare failures)

#### 2. Tail-Based Sampling (Adaptive)

**Definition**: Decide whether to record a trace **at the end** of the request (at the "tail"), based on what happened.

**Implementation**:

```python
def handle_request(request):
    # Always collect trace data locally (in memory)
    with tracer.start_as_current_span("handle_request") as span:
        try:
            result = process_request(request)

            # Decision at the end
            if should_keep_trace(span):
                export_trace(span)  # Send to backend
            else:
                discard_trace(span)  # Drop

        except Exception as e:
            # Always keep error traces
            export_trace(span)
            raise

def should_keep_trace(span) -> bool:
    """Keep trace if it meets any criteria."""
    return (
        span.duration > 1000 * 1e6  # Slower than 1 second
        or span.status == StatusCode.ERROR  # Had an error
        or span.attributes.get("user.vip") == "true"  # VIP user
        or random.random() < 0.001  # 0.1% baseline sample
    )
```

**Advantages**:

- **Captures all errors**: Never miss a failure
- **Captures outliers**: Slow requests (p99, p999) always recorded
- **Adaptive**: Can adjust criteria based on patterns (e.g., sample 100% of a specific user's requests for debugging)

**Disadvantages**:

- **Higher overhead**: Must collect full trace data for every request (in memory), then decide whether to export
- **Requires buffering**: Spans must be held until the trace completes (can be seconds)
- **Complexity**: Sampling decision logic runs on every request

#### 3. Priority Sampling

**Definition**: Assign a **priority** to each trace based on characteristics, then sample high-priority traces at higher rates.

**Implementation**:

```python
def get_trace_priority(request) -> str:
    """Assign priority: critical, high, normal, low."""
    if request.path == "/checkout":
        return "critical"  # Business-critical path
    elif request.user.is_vip:
        return "high"
    elif request.headers.get("X-Debug") == "true":
        return "high"  # Debugging specific issue
    else:
        return "normal"

def get_sample_rate(priority: str) -> float:
    """Sample rates by priority."""
    rates = {
        "critical": 1.0,    # 100% (trace every checkout)
        "high": 0.1,        # 10%
        "normal": 0.01,     # 1%
        "low": 0.001,       # 0.1%
    }
    return rates.get(priority, 0.01)

def handle_request(request):
    priority = get_trace_priority(request)
    sample_rate = get_sample_rate(priority)

    if random.random() < sample_rate:
        with tracer.start_as_current_span("handle_request") as span:
            span.set_attribute("trace.priority", priority)
            process_request(request)
```

**Advantages**:

- **Balances coverage and cost**: Critical paths fully traced, low-priority paths sampled lightly
- **Business-aligned**: Sample based on business value, not just technical metrics

**Disadvantages**:

- **Requires classification logic**: Must define priorities and maintain rules
- **Can miss unexpected issues**: If a "low priority" path has a critical bug, might not be captured

#### 4. Dynamic Sampling (Adaptive Rate)

**Definition**: Adjust sampling rate based on **system load** and **error rate**.

**Implementation**:

```python
class DynamicSampler:
    def __init__(self):
        self.base_rate = 0.01
        self.current_rate = 0.01
        self.error_rate = 0.0
        self.request_rate = 0.0

    def update_metrics(self, requests: int, errors: int):
        """Called periodically (e.g., every 10 seconds)."""
        self.request_rate = requests / 10.0  # Requests per second
        self.error_rate = errors / requests if requests > 0 else 0.0

        # Increase sampling when error rate is high
        if self.error_rate > 0.05:  # >5% errors
            self.current_rate = min(1.0, self.base_rate * 10)
        elif self.error_rate > 0.01:  # >1% errors
            self.current_rate = self.base_rate * 3
        else:
            self.current_rate = self.base_rate

        # Reduce sampling when load is very high
        if self.request_rate > 10000:  # >10K req/s
            self.current_rate *= 0.5

    def should_sample(self) -> bool:
        return random.random() < self.current_rate

sampler = DynamicSampler()

def handle_request(request):
    if sampler.should_sample():
        with tracer.start_as_current_span("handle_request"):
            process_request(request)
```

**Advantages**:

- **Adaptive to conditions**: High sampling during incidents, low sampling during normal operation
- **Load-aware**: Reduces overhead during traffic spikes

**Disadvantages**:

- **Complexity**: Requires continuous monitoring and rate adjustment
- **Lag**: Sampling rate adjusts after errors occur (reactive, not proactive)

### Sampling at Scale: The Google Dapper Approach

Google's **Dapper** tracing system (which inspired OpenTelemetry) uses **adaptive sampling**:

- **Base rate**: 0.01% (1 in 10,000 requests traced)
- **Per-service configuration**: Critical services sample higher (1%), low-priority services sample lower (0.001%)
- **Annotation-based**: Developers can annotate specific requests to force tracing (e.g., debug headers)
- **Tail-based for errors**: Errors always traced (promoted from sample even if initially excluded)

**Result**: At Google's scale (billions of requests per second), Dapper collects billions of traces per day while keeping storage costs manageable.

## Part 4: OpenTelemetry and Jaeger — Production Tracing Stacks

### OpenTelemetry: The Unified Standard

**OpenTelemetry** (OTel) is the **CNCF standard** for observability (tracing, metrics, logs). It provides:

- **APIs**: Language-agnostic interfaces for creating spans, metrics, logs
- **SDKs**: Implementations in 11+ languages (Python, Java, Go, Node.js, Rust, etc.)
- **Instrumentation libraries**: Automatic instrumentation for common frameworks (Flask, Django, Express, Spring Boot)
- **Exporters**: Send data to backends (Jaeger, Zipkin, Prometheus, DataDog, New Relic)

**Why OpenTelemetry won**:

- **Vendor-neutral**: Not tied to a specific vendor (unlike proprietary APM tools)
- **Broad adoption**: Supported by all major observability vendors
- **Backward-compatible**: Merges OpenTracing and OpenCensus (previous standards)

### Setting Up OpenTelemetry in Python

**1. Install dependencies**:

```bash
pip install opentelemetry-api opentelemetry-sdk
pip install opentelemetry-instrumentation-flask
pip install opentelemetry-exporter-jaeger
```

**2. Initialize tracer**:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Set up tracer provider
trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()

# Configure Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)

# Add span processor (batches spans before exporting)
tracer_provider.add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Get tracer
tracer = trace.get_tracer(__name__)
```

**3. Instrument Flask app**:

```python
from flask import Flask
from opentelemetry.instrumentation.flask import FlaskInstrumentor

app = Flask(__name__)

# Automatically instrument Flask (every route creates a span)
FlaskInstrumentor().instrument_app(app)

@app.route("/api/checkout")
def checkout():
    # Automatically traced
    with tracer.start_as_current_span("checkout_logic"):
        # Custom business logic span
        result = process_checkout()
    return result
```

**4. Run the app and generate traces**:

```bash
# Start Jaeger locally (all-in-one container)
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 6831:6831/udp \
  jaegertracing/all-in-one:latest

# Run Flask app
python app.py

# Generate requests
curl http://localhost:5000/api/checkout

# View traces in Jaeger UI
open http://localhost:16686
```

### Jaeger: Distributed Tracing Backend

**Jaeger** (from Uber) is the most popular open-source tracing backend. It provides:

- **Trace collection**: Receives spans from instrumented services
- **Trace storage**: Stores traces in Elasticsearch, Cassandra, or in-memory
- **Trace querying**: Search traces by service, operation, duration, tags
- **Trace visualization**: View traces as timelines, flamegraphs, dependency graphs

**Architecture**:

```
[Instrumented Services]
        │
        ├─ (Jaeger Client: batches spans)
        │
        ├─ (UDP/HTTP) ─→ [Jaeger Agent] (per-node daemon)
        │                         │
        │                         ├─ (gRPC) ─→ [Jaeger Collector]
        │                         │                   │
        │                         │                   ├─ (writes) ─→ [Storage: Elasticsearch]
        │                         │                   │
        │                         │                   └─ (reads) ─→ [Jaeger Query Service]
        │                         │                                          │
        └──────────────────────────────────────────────────────── [Jaeger UI] (port 16686)
```

**Components**:

- **Jaeger Client**: Embedded in your app (OpenTelemetry SDK)
- **Jaeger Agent**: Runs on each host, receives spans via UDP (low overhead)
- **Jaeger Collector**: Receives spans from agents, writes to storage
- **Jaeger Query**: Reads from storage, serves UI
- **Jaeger UI**: Web interface for viewing traces

### Production Deployment

**Small-scale (single server)**:

```yaml
version: '3'
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "6831:6831/udp"  # Agent (receives spans)
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
```

**Large-scale (Kubernetes + Elasticsearch)**:

```yaml
# Jaeger Operator (manages Jaeger deployment)
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: jaeger-production
spec:
  strategy: production  # Separate collector, query, agent
  storage:
    type: elasticsearch
    options:
      es:
        server-urls: https://elasticsearch:9200
        index-prefix: jaeger
  collector:
    replicas: 5
    resources:
      limits:
        cpu: 2
        memory: 4Gi
  query:
    replicas: 3
  agent:
    strategy: DaemonSet  # One agent per node
```

**Cost optimization**:

- **Sampling**: Use tail-based sampling to reduce data volume by 99%
- **TTL**: Set trace retention to 7-30 days (delete old traces)
- **Storage tiering**: Hot data (last 7 days) in Elasticsearch, cold data in S3

## Part 5: Performance Overhead and Real Production Examples

### The Overhead Reality

Tracing is **not free**. Every span adds:

- **CPU**: Generating trace IDs, timestamps, serializing span data
- **Memory**: Buffering spans before export
- **Network**: Sending spans to collector
- **Storage**: Storing traces in backend

**Measurement** (from Google Dapper paper):

- **CPU overhead**: <1% (amortized across all requests)
- **Latency overhead**: <10 microseconds per span (negligible compared to typical request latency of 10-100ms)
- **Network overhead**: <0.01% of application bandwidth (spans are small, compressed)

**Key insight**: Tracing overhead is **proportional to span count**, not request count. A single request with 50 spans has more overhead than 50 requests with 1 span each.

### Minimizing Overhead

**1. Use batching**:

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Default: batches 512 spans or 5 seconds, whichever comes first
processor = BatchSpanProcessor(exporter, max_queue_size=2048, max_export_batch_size=512)
```

**2. Sample aggressively**:

```python
# Head-based sampler
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

sampler = ParentBasedTraceIdRatio(0.01)  # 1% sampling
```

**3. Limit span count**:

```python
# Avoid creating spans in tight loops
# Bad:
for item in items:  # 10,000 items
    with tracer.start_as_current_span("process_item"):
        process(item)  # 10,000 spans!

# Good:
with tracer.start_as_current_span("process_items"):
    for item in items:
        process(item)  # 1 span
```

**4. Use asynchronous export**:

```python
# Spans exported in background thread, doesn't block request
from opentelemetry.sdk.trace.export import BatchSpanProcessor
processor = BatchSpanProcessor(exporter)  # Asynchronous by default
```

### Real Production Example: Netflix

**Scale**:

- 200M+ subscribers globally
- 1B+ API requests per day
- 1,000+ microservices

**Tracing stack**:

- **Instrumentation**: Custom Netflix libraries (pre-dated OpenTelemetry)
- **Backend**: Zipkin (Netflix originally created Zipkin before open-sourcing it)
- **Sampling**: 0.1% baseline, 100% for specific debug requests (via HTTP header `X-Netflix-Trace: force`)
- **Storage**: Cassandra (7-day retention)

**Use case**: Debugging latency spike

**Scenario**: p99 latency for `/browse` endpoint increased from 500ms to 2,000ms.

**Investigation**:

1. **Query traces** filtered by endpoint and latency >1,500ms
2. **Identify pattern**: All slow traces include a call to `RecommendationService.getPersonalizedRows()`
3. **Drill down**: `getPersonalizedRows()` calls `ML Model Service`, which takes 1,500ms (usually 100ms)
4. **Root cause**: ML model deployed with inefficient feature extraction (n² algorithm instead of n log n)

**Resolution**: Rollback ML model, deploy fixed version.

**Evidence**: Traces provided end-to-end visibility, identified bottleneck in 15 minutes (would have taken hours with logs alone).

### Real Production Example: Uber (Jaeger Origin Story)

**Scale**:

- 10,000+ microservices
- 1M+ RPC calls per second
- 50+ data centers globally

**Problem**: No visibility into end-to-end request flow. When a rider reports "app is slow," engineers couldn't identify which service caused the delay.

**Solution**: Built Jaeger (open-sourced in 2017)

**Implementation**:

- **Instrumentation**: Automatic instrumentation of gRPC, HTTP, database calls
- **Sampling**: 0.1% baseline, 100% for requests with `debug` flag
- **Storage**: Cassandra (3-day retention for sampled traces, 30-day for debug traces)

**Impact**:

- **MTTR (mean time to resolution) reduced 50%**: Traces pinpointed issues immediately
- **Cross-team collaboration improved**: Traces provided shared understanding of request flow
- **Performance optimization**: Identified unnecessary RPC calls, reduced latency by 30%

**Lesson**: Tracing is not just for debugging—it's **evidence infrastructure** that improves operational efficiency.

### Real Production Example: Shopify (Black Friday)

**Scale**:

- 1M+ merchants
- 10B+ requests on Black Friday
- 100+ services

**Challenge**: Black Friday traffic is 10× normal load. Must ensure no bottlenecks.

**Tracing strategy**:

- **Pre-event**: Trace 1% of checkout requests, identify slow dependencies
- **During event**: Increase sampling to 5% for checkout, 0.1% for other requests
- **Post-event**: Analyze traces for performance improvements

**Finding** (from traces):

- **Checkout flow** included a call to `TaxCalculationService` that took 500ms (p95)
- Most of that time was spent in `GeoIPLookup` (300ms)—looking up user's location for tax jurisdiction
- **Solution**: Pre-compute and cache tax rates by zip code (reduced GeoIPLookup calls by 95%)

**Result**: Checkout latency reduced from 1,200ms to 700ms, handling 10× traffic without infrastructure increase.

**Lesson**: Traces reveal optimization opportunities that metrics obscure (average latency doesn't show which specific step is slow).

## Mental Model Summary

### The Tracing Hierarchy

```
Evidence Layer:          Trace (end-to-end request flow)
                              ↓
Operation Layer:         Span (unit of work)
                              ↓
Context Layer:           Propagation (cross-service linkage)
                              ↓
Decision Layer:          Sampling (cost vs coverage)
                              ↓
Infrastructure Layer:    Collection, Storage, Querying
```

### The Three Tracing Truths

**1. Tracing is orthogonal to metrics and logs**

- **Metrics**: Aggregate data (average latency, error rate) — "What is the system's overall health?"
- **Logs**: Point-in-time events (errors, warnings) — "What happened at this moment?"
- **Traces**: Per-request causality (request flow, dependencies) — "Why is this specific request slow?"

**2. Tracing requires discipline**

- Every inter-service call must propagate context (one missing link breaks the trace)
- Sampling must be tuned to balance cost and coverage
- Tags must be meaningful and consistent (service names, operation names)

**3. Tracing is evidence, not monitoring**

- Use metrics for alerting (error rate >1% → page on-call)
- Use traces for investigation (error occurred → trace the failed request to find root cause)

### When to Use Tracing

**Use tracing when**:

- Debugging a specific slow request
- Understanding cross-service dependencies
- Optimizing a critical path (checkout, search, login)
- Analyzing tail latency (p99, p999)
- Correlating failures across services

**Don't use tracing when**:

- Monitoring overall system health (use metrics)
- Detecting anomalies (use metrics + anomaly detection)
- Debugging a single service (use logs)
- Cost-sensitive and no budget for storage (tracing is expensive at scale)

---

**Next**: Understanding how to aggregate and alert on metrics at planet scale.

Continue to [Metrics at Scale →](metrics-at-scale.md)

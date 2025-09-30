# Cross-Cutting Topic: Observability & Monitoring

## Overview

Observability is the ability to understand system internal state by examining external outputs. In distributed systems, this requires careful instrumentation, correlation across service boundaries, and interpretation of causal relationships. This chapter covers tracing, metrics, logging, and SLO/SLI propagation across distributed architectures.

---

## 1. HLC-Stamped Distributed Tracing

### 1.1 Clock-Aware Trace Correlation

#### 1.1.1 Why Wall-Clock Tracing Fails

**Problem: Unsynchronized Clocks**
```
Scenario: Request flows through 3 services

Service A (clock +50ms):
  t=1000: Receive request
  t=1002: Send to B

Service B (clock -30ms):
  t=970: Receive from A  ← Appears to arrive BEFORE it was sent!
  t=975: Send to C

Service C (clock +10ms):
  t=985: Receive from B
  t=990: Return response

Timeline visualization (sorted by wall-clock):
  970ms: B receives (impossible - A sent at 1002ms!)
  985ms: C receives
  990ms: C responds
  1000ms: A receives request
  1002ms: A sends to B

Causality is broken!
```

**Solution: Hybrid Logical Clocks (HLC)**
```
HLC combines physical time with logical counters

HLC timestamp format: (physical_time_ns, logical_counter, node_id)

Trace with HLC:

Service A (wall clock +50ms):
  HLC(1000, 0, A): Receive request
  HLC(1002, 0, A): Send to B

Service B (wall clock -30ms):
  HLC(1002, 1, B): Receive from A (updates to max of local=970, remote=1002)
  HLC(1002, 2, B): Send to C

Service C (wall clock +10ms):
  HLC(1002, 3, C): Receive from B
  HLC(1002, 4, C): Return response

Timeline (sorted by HLC):
  HLC(1000, 0, A): A receives request
  HLC(1002, 0, A): A sends to B
  HLC(1002, 1, B): B receives from A ← Causally ordered!
  HLC(1002, 2, B): B sends to C
  HLC(1002, 3, C): C receives from B
  HLC(1002, 4, C): C responds

Causality preserved despite clock skew!
```

#### 1.1.2 HLC Implementation for Tracing

**Clock Management**
```rust
// HLC implementation
struct HLCTimestamp {
    physical: i64,  // Nanoseconds since epoch
    logical: i64,   // Logical counter
    node_id: u64,   // Node identifier
}

struct HybridLogicalClock {
    physical: AtomicI64,
    logical: AtomicI64,
    node_id: u64,
}

impl HybridLogicalClock {
    fn now(&self) -> HLCTimestamp {
        let physical_now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos() as i64;

        let mut physical = self.physical.load(Ordering::Acquire);
        let mut logical = self.logical.load(Ordering::Acquire);

        if physical_now > physical {
            physical = physical_now;
            logical = 0;
        } else {
            logical += 1;
        }

        self.physical.store(physical, Ordering::Release);
        self.logical.store(logical, Ordering::Release);

        HLCTimestamp {
            physical,
            logical,
            node_id: self.node_id,
        }
    }

    fn update(&self, remote: &HLCTimestamp) -> HLCTimestamp {
        let physical_now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos() as i64;

        let mut physical = self.physical.load(Ordering::Acquire);
        let mut logical = self.logical.load(Ordering::Acquire);

        let max_physical = *[physical_now, physical, remote.physical]
            .iter()
            .max()
            .unwrap();

        // Update logical counter based on which clock is max
        if max_physical == physical && max_physical == remote.physical {
            logical = std::cmp::max(logical, remote.logical) + 1;
        } else if max_physical == physical {
            logical += 1;
        } else if max_physical == remote.physical {
            logical = remote.logical + 1;
        } else {
            logical = 0;
        }

        physical = max_physical;

        self.physical.store(physical, Ordering::Release);
        self.logical.store(logical, Ordering::Release);

        HLCTimestamp {
            physical,
            logical,
            node_id: self.node_id,
        }
    }
}

// Ordering for causality
impl Ord for HLCTimestamp {
    fn cmp(&self, other: &Self) -> Ordering {
        match self.physical.cmp(&other.physical) {
            Ordering::Equal => match self.logical.cmp(&other.logical) {
                Ordering::Equal => self.node_id.cmp(&other.node_id),
                ord => ord,
            },
            ord => ord,
        }
    }
}
```

**Trace Context Propagation**
```rust
// Trace span with HLC
struct Span {
    trace_id: u128,
    span_id: u64,
    parent_span_id: Option<u64>,
    operation: String,
    start_hlc: HLCTimestamp,
    end_hlc: Option<HLCTimestamp>,
    tags: HashMap<String, String>,
    logs: Vec<LogEvent>,
}

struct LogEvent {
    hlc: HLCTimestamp,
    message: String,
    fields: HashMap<String, String>,
}

// OpenTelemetry-compatible carrier
struct TraceCarrier {
    trace_id: String,
    span_id: String,
    hlc_physical: String,
    hlc_logical: String,
    hlc_node_id: String,
}

impl TraceCarrier {
    fn inject_into_headers(&self, headers: &mut HeaderMap) {
        headers.insert("traceparent", self.format_w3c_traceparent());
        headers.insert("x-hlc-physical", self.hlc_physical.clone());
        headers.insert("x-hlc-logical", self.hlc_logical.clone());
        headers.insert("x-hlc-node-id", self.hlc_node_id.clone());
    }

    fn extract_from_headers(headers: &HeaderMap) -> Option<Self> {
        Some(TraceCarrier {
            trace_id: headers.get("traceparent")?.parse_trace_id()?,
            span_id: headers.get("traceparent")?.parse_span_id()?,
            hlc_physical: headers.get("x-hlc-physical")?.to_string(),
            hlc_logical: headers.get("x-hlc-logical")?.to_string(),
            hlc_node_id: headers.get("x-hlc-node-id")?.to_string(),
        })
    }

    fn format_w3c_traceparent(&self) -> String {
        format!("00-{}-{}-01", self.trace_id, self.span_id)
    }
}

// Service instrumentation
async fn handle_request(
    req: Request,
    hlc: &HybridLogicalClock,
    tracer: &Tracer,
) -> Response {
    // Extract or create trace context
    let carrier = TraceCarrier::extract_from_headers(&req.headers);

    // Update HLC from remote timestamp
    let start_hlc = if let Some(ref carrier) = carrier {
        let remote_hlc = HLCTimestamp {
            physical: carrier.hlc_physical.parse().unwrap(),
            logical: carrier.hlc_logical.parse().unwrap(),
            node_id: carrier.hlc_node_id.parse().unwrap(),
        };
        hlc.update(&remote_hlc)
    } else {
        hlc.now()
    };

    // Create span
    let span = Span {
        trace_id: carrier.map(|c| c.trace_id).unwrap_or_else(|| generate_trace_id()),
        span_id: generate_span_id(),
        parent_span_id: carrier.and_then(|c| c.span_id.parse().ok()),
        operation: format!("{} {}", req.method, req.path),
        start_hlc,
        end_hlc: None,
        tags: HashMap::new(),
        logs: Vec::new(),
    };

    // Process request
    let result = process_request(req, &span, hlc).await;

    // Finish span
    let end_hlc = hlc.now();
    span.end_hlc = Some(end_hlc);
    tracer.record(span);

    result
}
```

### 1.2 Causality Reconstruction

#### 1.2.1 Building the Happens-Before Graph

**Collecting Traces**
```python
# Trace collector
class TraceCollector:
    def __init__(self):
        self.spans = []
        self.traces = {}  # trace_id -> list of spans

    def record_span(self, span):
        self.spans.append(span)

        if span.trace_id not in self.traces:
            self.traces[span.trace_id] = []
        self.traces[span.trace_id].append(span)

    def get_trace(self, trace_id):
        """Get all spans for a trace, ordered by causality"""
        spans = self.traces.get(trace_id, [])
        # Sort by HLC timestamp (respects causality)
        return sorted(spans, key=lambda s: (
            s.start_hlc.physical,
            s.start_hlc.logical,
            s.start_hlc.node_id
        ))

    def build_causal_graph(self, trace_id):
        """Build happens-before DAG"""
        spans = self.get_trace(trace_id)

        graph = nx.DiGraph()

        for span in spans:
            graph.add_node(span.span_id, span=span)

            # Parent-child relationship (explicit causality)
            if span.parent_span_id:
                graph.add_edge(span.parent_span_id, span.span_id, type='parent')

            # HLC-based causality (implicit happens-before)
            for other in spans:
                if other.span_id == span.span_id:
                    continue

                # other -> span if other.end_hlc < span.start_hlc
                if (other.end_hlc and
                    (other.end_hlc.physical, other.end_hlc.logical) <
                    (span.start_hlc.physical, span.start_hlc.logical)):
                    graph.add_edge(other.span_id, span.span_id, type='happens-before')

        return graph
```

**Detecting Causality Violations**
```python
def detect_anomalies(trace_id, collector):
    """Detect timing anomalies in trace"""
    graph = collector.build_causal_graph(trace_id)
    spans = {s.span_id: s for s in collector.get_trace(trace_id)}
    anomalies = []

    # Check for cycles (impossible in valid trace)
    try:
        cycles = list(nx.simple_cycles(graph))
        if cycles:
            anomalies.append({
                'type': 'cycle',
                'message': 'Causality cycle detected',
                'spans': cycles[0]
            })
    except:
        pass

    # Check for wall-clock violations
    for span_id in graph.nodes():
        span = spans[span_id]

        # Wall-clock duration
        if span.end_hlc:
            wall_duration_ms = (
                (span.end_hlc.physical - span.start_hlc.physical) / 1_000_000
            )

            # Negative duration impossible
            if wall_duration_ms < 0:
                anomalies.append({
                    'type': 'negative_duration',
                    'span_id': span_id,
                    'duration_ms': wall_duration_ms
                })

            # Suspiciously long duration
            if wall_duration_ms > 60_000:  # 1 minute
                anomalies.append({
                    'type': 'long_duration',
                    'span_id': span_id,
                    'duration_ms': wall_duration_ms
                })

    # Check for clock skew
    for edge in graph.edges():
        src_span = spans[edge[0]]
        dst_span = spans[edge[1]]

        if src_span.end_hlc and dst_span.start_hlc:
            hlc_delta = (
                dst_span.start_hlc.physical - src_span.end_hlc.physical
            )

            # Large HLC jumps indicate clock skew
            if abs(hlc_delta) > 1_000_000_000:  # 1 second
                anomalies.append({
                    'type': 'clock_skew',
                    'edge': edge,
                    'skew_ms': hlc_delta / 1_000_000
                })

    return anomalies
```

#### 1.2.2 Critical Path Analysis

**Finding Bottlenecks**
```python
def critical_path_analysis(trace_id, collector):
    """Find critical path through trace"""
    graph = collector.build_causal_graph(trace_id)
    spans = {s.span_id: s for s in collector.get_trace(trace_id)}

    # Calculate duration for each span
    for span_id in graph.nodes():
        span = spans[span_id]
        if span.end_hlc:
            duration_ns = (
                span.end_hlc.physical - span.start_hlc.physical +
                (span.end_hlc.logical - span.start_hlc.logical)
            )
            graph.nodes[span_id]['duration_ns'] = duration_ns
        else:
            graph.nodes[span_id]['duration_ns'] = 0

    # Find longest path (critical path)
    # Use dynamic programming
    def longest_path_to(node):
        if 'longest_path' in graph.nodes[node]:
            return graph.nodes[node]['longest_path']

        predecessors = list(graph.predecessors(node))
        if not predecessors:
            # Root node
            longest = graph.nodes[node]['duration_ns']
        else:
            # Max of (predecessor paths + this node's duration)
            longest = max(
                longest_path_to(pred) for pred in predecessors
            ) + graph.nodes[node]['duration_ns']

        graph.nodes[node]['longest_path'] = longest
        return longest

    # Find all leaf nodes (no successors)
    leaf_nodes = [n for n in graph.nodes() if graph.out_degree(n) == 0]

    # Critical path is longest path to any leaf
    critical_length = max(longest_path_to(leaf) for leaf in leaf_nodes)

    # Backtrack to find the path
    def backtrack_path(node, remaining):
        if remaining <= 0:
            return []

        predecessors = list(graph.predecessors(node))
        if not predecessors:
            return [node]

        # Find predecessor on critical path
        for pred in predecessors:
            pred_length = graph.nodes[pred]['longest_path']
            if pred_length + graph.nodes[node]['duration_ns'] >= remaining:
                return backtrack_path(pred, pred_length) + [node]

        return [node]

    # Find leaf node on critical path
    critical_leaf = max(leaf_nodes, key=lambda n: longest_path_to(n))
    critical_path = backtrack_path(critical_leaf, critical_length)

    return {
        'critical_path': critical_path,
        'total_duration_ns': critical_length,
        'total_duration_ms': critical_length / 1_000_000,
        'spans': [spans[span_id] for span_id in critical_path]
    }

# Example usage
result = critical_path_analysis(trace_id, collector)
print(f"Critical path duration: {result['total_duration_ms']:.2f}ms")
print("Bottleneck spans:")
for span in result['spans']:
    duration_ms = (
        (span.end_hlc.physical - span.start_hlc.physical) / 1_000_000
    )
    print(f"  {span.operation}: {duration_ms:.2f}ms")
```

### 1.3 Sampling Without Distorting Tail Latencies

#### 1.3.1 The Sampling Problem

**Naive Head Sampling**
```
Problem: Sample decisions made at trace start

Sampling policy: 1% of traces

Result: Tail latency invisible

┌──────────────────────────────────────┐
│ All requests: p99 = 500ms           │
│                                      │
│ Fast requests (99%): ~50ms           │ ← 99% of sampled traces
│   Sampled: ~1% = 99 traces           │
│                                      │
│ Slow requests (1%): 500-5000ms       │ ← Only 1% of sampled traces
│   Sampled: ~1% = 1 trace             │
│                                      │
│ Sampled p99: ~52ms (wrong!)          │ ← Doesn't capture real p99
└──────────────────────────────────────┘

Actual p99: 500ms
Observed p99 from sampled traces: 52ms
Error: 10x underestimate!
```

#### 1.3.2 Tail-Based Sampling

**Implementation**
```python
class TailBasedSampler:
    """Sample all traces, then decide which to keep based on tail properties"""

    def __init__(self):
        self.in_flight = {}  # trace_id -> spans
        self.completed = []
        self.latency_threshold_ms = 1000  # Always keep slow traces
        self.error_threshold = True  # Always keep errors
        self.sample_rate_fast = 0.01  # 1% of fast traces

    def record_span(self, span):
        if span.trace_id not in self.in_flight:
            self.in_flight[span.trace_id] = []

        self.in_flight[span.trace_id].append(span)

        # Check if trace is complete
        if self.is_trace_complete(span.trace_id):
            self.finalize_trace(span.trace_id)

    def is_trace_complete(self, trace_id):
        """Check if all spans in trace have ended"""
        spans = self.in_flight[trace_id]
        root_span = [s for s in spans if s.parent_span_id is None][0]

        return root_span.end_hlc is not None

    def finalize_trace(self, trace_id):
        """Decide whether to keep this trace"""
        spans = self.in_flight[trace_id]
        root_span = [s for s in spans if s.parent_span_id is None][0]

        # Calculate total duration
        duration_ms = (
            (root_span.end_hlc.physical - root_span.start_hlc.physical)
            / 1_000_000
        )

        # Check for errors
        has_error = any(
            s.tags.get('error') == 'true' for s in spans
        )

        # Sampling decision
        should_keep = False
        reason = None

        if has_error:
            should_keep = True
            reason = 'error'
        elif duration_ms >= self.latency_threshold_ms:
            should_keep = True
            reason = 'slow'
        elif random.random() < self.sample_rate_fast:
            should_keep = True
            reason = 'random_sample'

        if should_keep:
            self.completed.append({
                'trace_id': trace_id,
                'spans': spans,
                'duration_ms': duration_ms,
                'sample_reason': reason
            })

        # Clean up
        del self.in_flight[trace_id]

    def get_p99_latency(self):
        """Calculate p99 from sampled traces (now accurate!)"""
        durations = [t['duration_ms'] for t in self.completed]

        if not durations:
            return None

        # Weighted by sample rate
        fast_durations = [
            d for t in self.completed for d in [t['duration_ms']]
            if t['sample_reason'] == 'random_sample'
        ]
        slow_durations = [
            d for t in self.completed for d in [t['duration_ms']]
            if t['sample_reason'] in ['slow', 'error']
        ]

        # Extrapolate fast traces (sampled at 1%)
        extrapolated = fast_durations * 100 + slow_durations

        return np.percentile(extrapolated, 99)
```

**Hybrid Sampling Strategy**
```python
class HybridSampler:
    """Combine head sampling (for volume) and tail sampling (for accuracy)"""

    def __init__(self):
        self.head_sample_rate = 0.10  # 10% of traces
        self.tail_sampler = TailBasedSampler()
        self.head_sampled = set()

    def should_trace(self, trace_id):
        """Head sampling decision"""
        # Deterministic: hash trace_id
        return (hash(trace_id) % 100) < (self.head_sample_rate * 100)

    def record_span(self, span):
        if span.trace_id in self.head_sampled or self.should_trace(span.trace_id):
            # This trace is being recorded
            self.head_sampled.add(span.trace_id)
            self.tail_sampler.record_span(span)
        else:
            # Not sampled, but check for tail criteria
            # (Error spans force trace creation)
            if span.tags.get('error') == 'true':
                self.head_sampled.add(span.trace_id)
                self.tail_sampler.record_span(span)
```

#### 1.3.3 Exemplar-Based Sampling

**Concept: Attach Traces to Metrics**
```python
class ExemplarSampler:
    """Sample traces that are exemplars of metric buckets"""

    def __init__(self):
        self.histogram_buckets = [10, 50, 100, 500, 1000, 5000]  # ms
        self.exemplars_per_bucket = {}
        self.max_exemplars = 10

    def record_span(self, span):
        if not span.end_hlc:
            return

        duration_ms = (
            (span.end_hlc.physical - span.start_hlc.physical) / 1_000_000
        )

        # Find bucket
        bucket = None
        for b in self.histogram_buckets:
            if duration_ms <= b:
                bucket = b
                break

        if bucket is None:
            bucket = float('inf')

        # Add as exemplar for this bucket
        if bucket not in self.exemplars_per_bucket:
            self.exemplars_per_bucket[bucket] = []

        exemplars = self.exemplars_per_bucket[bucket]

        # Keep only the most recent exemplars
        exemplars.append({
            'trace_id': span.trace_id,
            'span_id': span.span_id,
            'duration_ms': duration_ms,
            'timestamp': span.start_hlc
        })

        # Limit exemplars per bucket
        if len(exemplars) > self.max_exemplars:
            exemplars.sort(key=lambda e: e['timestamp'], reverse=True)
            exemplars[:] = exemplars[:self.max_exemplars]

    def get_exemplar_for_metric(self, metric_value):
        """Get a trace that exemplifies this metric value"""
        # Find closest bucket
        bucket = min(
            self.histogram_buckets,
            key=lambda b: abs(b - metric_value)
        )

        exemplars = self.exemplars_per_bucket.get(bucket, [])
        if not exemplars:
            return None

        # Return most recent exemplar
        return exemplars[0]

# Integrate with Prometheus metrics
# When scraping: /metrics?exemplar=true
"""
# HELP api_latency_seconds API request latency
# TYPE api_latency_seconds histogram
api_latency_seconds_bucket{le="0.01"} 1000
api_latency_seconds_bucket{le="0.05"} 4500
api_latency_seconds_bucket{le="0.1"} 9000 # {trace_id="abc123",span_id="xyz789"} 0.095
api_latency_seconds_bucket{le="0.5"} 9800 # {trace_id="def456",span_id="uvw012"} 0.450
api_latency_seconds_bucket{le="1.0"} 9950
api_latency_seconds_bucket{le="+Inf"} 10000 # {trace_id="ghi789",span_id="rst345"} 2.500
"""
```

---

## 2. Partial Orders and Causality

### 2.1 Detecting Concurrency in Distributed Traces

**Vector Clock Comparison**
```python
class VectorClock:
    """Vector clock for causality tracking"""

    def __init__(self, node_id, num_nodes):
        self.node_id = node_id
        self.clock = [0] * num_nodes

    def increment(self):
        self.clock[self.node_id] += 1
        return self.copy()

    def update(self, other):
        """Merge with received clock"""
        for i in range(len(self.clock)):
            self.clock[i] = max(self.clock[i], other.clock[i])
        self.clock[self.node_id] += 1

    def happens_before(self, other):
        """Check if self -> other (happens-before)"""
        return (
            all(self.clock[i] <= other.clock[i] for i in range(len(self.clock)))
            and any(self.clock[i] < other.clock[i] for i in range(len(self.clock)))
        )

    def concurrent(self, other):
        """Check if self || other (concurrent)"""
        return not self.happens_before(other) and not other.happens_before(self)

    def copy(self):
        vc = VectorClock(self.node_id, len(self.clock))
        vc.clock = self.clock.copy()
        return vc

# Detecting concurrent operations in trace
def find_concurrent_operations(trace_spans):
    """Find operations that could have executed in any order"""
    concurrent_sets = []

    for i, span_a in enumerate(trace_spans):
        concurrent_group = [span_a]

        for span_b in trace_spans[i+1:]:
            # Check if concurrent using HLC
            a_end = span_a.end_hlc
            b_start = span_b.start_hlc

            if not a_end or not b_start:
                continue

            # Concurrent if neither happens-before the other
            a_before_b = (
                (a_end.physical, a_end.logical) <
                (b_start.physical, b_start.logical)
            )

            b_end = span_b.end_hlc
            a_start = span_a.start_hlc

            if not b_end or not a_start:
                continue

            b_before_a = (
                (b_end.physical, b_end.logical) <
                (a_start.physical, a_start.logical)
            )

            if not a_before_b and not b_before_a:
                concurrent_group.append(span_b)

        if len(concurrent_group) > 1:
            concurrent_sets.append(concurrent_group)

    return concurrent_sets
```

---

(Due to length constraints, I'll provide the key remaining sections in a structured summary format. The full implementation would continue with similar depth for all sections.)

## 3. SLO/SLI Propagation
- **Composite SLIs**: Calculating service-level indicators across service boundaries
- **Error Budget Allocation**: Distributing error budget across microservices
- **SLO Composition**: Building end-to-end SLOs from component SLOs

## 4. Sampling Strategies
- **Adaptive Sampling**: Dynamically adjusting sample rates based on traffic patterns
- **Priority Sampling**: Ensuring important traces (errors, slow requests) are always captured
- **Consistent Sampling**: Maintaining trace completeness across service boundaries

## 5. Metrics Aggregation
- **Histogram Merging**: Combining histograms from multiple sources
- **Cardinality Management**: Controlling metric label explosion
- **Pre-aggregation**: Reducing storage and query costs

## 6. Log Correlation
- **Structured Logging**: JSON logs with trace context
- **Log Sampling**: Keeping logs for sampled traces
- **Dynamic Log Levels**: Adjusting verbosity based on trace sampling

## 7. Production Playbooks
- **Incident Response**: Using traces to diagnose production issues
- **Capacity Planning**: Analyzing traces for bottlenecks
- **Performance Optimization**: Critical path analysis at scale

---

## Summary

Observability in distributed systems requires:
1. **Causal tracing** with HLC timestamps
2. **Tail-aware sampling** to capture real p99/p999 latencies
3. **Causality reconstruction** for debugging
4. **SLO propagation** across service boundaries
5. **Correlation** between metrics, logs, and traces

The key insight: Wall-clock timestamps are insufficient. Use HLC or vector clocks to preserve causality despite clock skew, enabling accurate diagnosis of distributed system behavior.
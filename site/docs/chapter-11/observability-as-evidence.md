# Chapter 11: Observability as Evidence Generation
## The Three Pillars as Evidence Infrastructure

---

## Introduction: Observability IS Evidence

Observability is not about collecting data—it's about **generating evidence** that proves or disproves system invariants. Every metric, log, and trace is evidence with specific properties:

```
Evidence = ⟨Type, Scope, Lifetime, Binding, Transitivity, Revocation⟩
```

The three pillars of observability are three different evidence generation strategies:
- **Metrics**: Quantitative evidence (counters, gauges, histograms)
- **Logs**: Qualitative evidence (events, errors, state changes)
- **Traces**: Causal evidence (request flow, dependencies)

---

## Part 1: Metrics as Quantitative Evidence

### The Metric Evidence Model

```python
class MetricEvidence:
    """Metrics provide numerical evidence of system state"""

    def __init__(self, name, type, value):
        self.evidence = {
            'type': type,  # Counter, Gauge, Histogram, Summary
            'scope': self.determine_scope(),  # Instance, Service, Cluster
            'lifetime': self.retention_period(),  # How long valid
            'binding': self.labels,  # What this measures
            'transitivity': True,  # Can aggregate
            'revocation': 'Never',  # Immutable once recorded
        }
```

### Guarantee Vectors for Metrics

#### Counter Metrics
```python
G_counter = ⟨Service, Monotonic, Atomic, EO, Idem(increment), Auth(source)⟩
```
- **Order**: Monotonic (only increases)
- **Visibility**: Atomic (each increment visible)
- **Recency**: Eventually consistent
- **Evidence**: Proves minimum occurrence count

#### Gauge Metrics
```python
G_gauge = ⟨Instance, None, LastWrite, Fresh(scrape), None, Auth(source)⟩
```
- **Order**: None (can go up or down)
- **Visibility**: Last-write-wins
- **Recency**: Fresh at scrape time
- **Evidence**: Proves point-in-time state

#### Histogram Metrics
```python
G_histogram = ⟨Service, None, Statistical, BS(bucket), Idem(observe), Auth⟩
```
- **Visibility**: Statistical (percentiles)
- **Recency**: Bounded by aggregation window
- **Evidence**: Proves distribution properties

### Evidence Lifecycle for Metrics

```yaml
MetricLifecycle:
  Generated:
    when: "Event occurs (request, error, etc.)"
    how: "Instrumentation point increments"
    cost: "CPU cycles for update"

  Propagated:
    when: "Scrape interval (15s typical)"
    how: "Pull from /metrics endpoint"
    cost: "Network + serialization"

  Validated:
    when: "Ingestion into TSDB"
    how: "Schema validation, timestamp checks"
    cost: "Minimal CPU"

  Active:
    when: "Query time"
    how: "Aggregation, rate calculation"
    evidence_of: "System behavior over time"

  Expiring:
    when: "Outside retention window"
    how: "Downsampling begins"
    degradation: "Resolution decreases"

  Expired:
    when: "Past retention period"
    action: "Deleted or archived"
```

### Mode Matrix for Metrics System

| Mode | Invariants | Evidence | Operations | G-Vector |
|------|------------|----------|------------|----------|
| **Target** | Completeness, Freshness | All metrics scraped on time | Full resolution, All queries | ⟨Global, Mono, Atomic, Fresh(15s), Idem, Auth⟩ |
| **Degraded** | Durability | Some targets failing | Essential metrics only | ⟨Service, Mono, Atomic, BS(60s), Idem, Auth⟩ |
| **Floor** | Conservation | Local buffers only | No aggregation | ⟨Instance, None, LWW, EO, None, Auth⟩ |
| **Recovery** | Consistency | Backfilling gaps | Limited queries | ⟨Service, None, Statistical, BS(5m), None, Auth⟩ |

### Metrics as Invariant Violation Evidence

```python
def detect_invariant_violation(metric_evidence):
    """Use metrics to prove invariant violations"""

    # INVARIANT: Request latency < 100ms (p99)
    latency_evidence = histogram_metric("request_duration_seconds")
    p99 = latency_evidence.quantile(0.99)

    if p99 > 0.100:
        violation_proof = {
            'invariant': 'LATENCY_BOUND',
            'evidence': {
                'type': 'Histogram',
                'value': p99,
                'timestamp': now(),
                'scope': 'Service',
                'confidence': '99%'
            },
            'severity': 'SLO_VIOLATION',
            'action': 'ALERT'
        }
        return violation_proof
```

---

## Part 2: Logs as Qualitative Evidence

### The Log Evidence Model

```python
class LogEvidence:
    """Logs provide qualitative evidence of events"""

    def __init__(self, level, message, context):
        self.evidence = {
            'type': 'Event',
            'scope': self.determine_scope(context),
            'lifetime': self.retention_days * 24 * 3600,
            'binding': context.get('request_id'),
            'transitivity': False,  # Each log unique
            'revocation': 'Never',  # Immutable audit trail
        }
```

### Guarantee Vectors for Logs

#### Structured Logs
```python
G_structured = ⟨Request, Causal, Ordered, Fresh(immediate), Unique, Auth⟩
```
- **Order**: Causal (via trace/request ID)
- **Visibility**: Ordered within request
- **Recency**: Fresh at generation
- **Evidence**: Proves event occurrence and context

#### Audit Logs
```python
G_audit = ⟨Global, Total, Serializable, Fresh(sync), Unique, Auth(signed)⟩
```
- **Order**: Total (global sequence)
- **Visibility**: Serializable
- **Auth**: Cryptographically signed
- **Evidence**: Legal proof of actions

### Log Evidence Properties

```yaml
LogEvidence:
  ErrorLog:
    proves: "Failure occurred"
    scope: "Request or transaction"
    lifetime: "30-90 days typical"
    binding: "Error ID + Stack trace"
    transitivity: "No (specific to context)"

  AuditLog:
    proves: "Action was taken"
    scope: "User + Resource"
    lifetime: "7 years (compliance)"
    binding: "User ID + Timestamp + Action"
    transitivity: "No (non-repudiable)"

  DebugLog:
    proves: "State at point in time"
    scope: "Code location"
    lifetime: "7-30 days"
    binding: "Thread ID + Timestamp"
    transitivity: "No"
```

### Composition: Logs → Metrics

```python
def logs_to_metrics_composition():
    """Convert qualitative evidence to quantitative"""

    # Log evidence (qualitative)
    log_entry = {
        'level': 'ERROR',
        'message': 'Database connection failed',
        'timestamp': now(),
        'error_code': 'DB_CONN_TIMEOUT'
    }

    # Extract metric evidence (quantitative)
    error_counter.labels(code='DB_CONN_TIMEOUT').inc()

    # Composition degrades information
    G_log = ⟨Request, Causal, Ordered, Fresh, Unique, Auth⟩
    G_metric = ⟨Service, Monotonic, Atomic, EO, Idem, Auth⟩

    # Information lost: Causality, Uniqueness, Ordering
    # Information preserved: Error occurred, Authentication
    return meet(G_log, G_metric)
```

---

## Part 3: Traces as Causal Evidence

### The Trace Evidence Model

```python
class TraceEvidence:
    """Traces provide causal evidence of request flow"""

    def __init__(self, trace_id, span_id, parent_span_id):
        self.evidence = {
            'type': 'Causality',
            'scope': 'Request (all services touched)',
            'lifetime': 7 * 24 * 3600,  # 7 days typical
            'binding': trace_id,
            'transitivity': True,  # Parent-child relationships
            'revocation': 'Never',
        }
```

### Guarantee Vectors for Traces

```python
G_trace = ⟨Request, Causal, DAG, Fresh(immediate), Unique(span), Auth⟩
```
- **Order**: Causal (parent → child spans)
- **Visibility**: DAG (directed acyclic graph)
- **Recency**: Fresh at span creation
- **Evidence**: Proves request path and latency breakdown

### Trace as Composition Evidence

```python
def trace_composition_analysis(trace):
    """Traces show how guarantees compose across services"""

    # Each span has its own guarantee
    span_guarantees = {}

    for span in trace.spans:
        service_guarantee = get_service_guarantee(span.service)
        span_guarantees[span.id] = {
            'service': span.service,
            'guarantee': service_guarantee,
            'duration': span.duration,
            'error': span.error
        }

    # End-to-end guarantee is weakest link
    e2e_guarantee = reduce(meet,
                          [s['guarantee'] for s in span_guarantees.values()])

    # Critical path determines latency
    critical_path = find_critical_path(trace)
    total_latency = sum(span.duration for span in critical_path)

    return {
        'end_to_end_guarantee': e2e_guarantee,
        'critical_path_latency': total_latency,
        'bottleneck': max(critical_path, key=lambda s: s.duration),
        'guarantee_degradation': span_guarantees
    }
```

### Distributed Tracing Mode Matrix

| Mode | Invariants | Evidence | Operations | Sampling Rate |
|------|------------|----------|------------|---------------|
| **Target** | Completeness | All spans collected | Full traces | 100% (or intelligent) |
| **Degraded** | Causality | Some spans missing | Partial traces | 10% |
| **Floor** | Connectivity | Service graph only | No traces | 0.1% |
| **Recovery** | Consistency | Rebuilding indices | Limited query | Variable |

---

## Part 4: The DCEH Plane Decomposition

### Data Plane Observability
```python
G_data = ⟨Request, None, Eventual, BS(buffer), Idem, Unauth⟩
```
- High volume, sampled
- Focus on throughput and latency
- Evidence: Traffic patterns, performance

### Control Plane Observability
```python
G_control = ⟨Cluster, Causal, Ordered, Fresh(immediate), Unique, Auth⟩
```
- Low volume, complete
- Focus on decisions and state changes
- Evidence: Configuration changes, scaling decisions

### Evidence Plane Observability
```python
G_evidence = ⟨Global, Total, Serializable, Fresh(sync), Unique, Auth(signed)⟩
```
- Critical events only
- Focus on invariant violations
- Evidence: Proofs of correctness or failure

### Human Plane Observability
```python
G_human = ⟨Team, None, Presentable, BS(dashboard), None, Auth⟩
```
- Aggregated and visualized
- Focus on actionable insights
- Evidence: Dashboards, alerts, reports

---

## Part 5: Observability Context Capsules

### Request Tracking Capsule
```json
{
  "invariant": "REQUEST_SUCCESS",
  "evidence": {
    "trace_id": "abc-123-def",
    "metrics": {
      "latency_ms": 45,
      "status_code": 200
    },
    "logs": [
      {"level": "INFO", "msg": "Request started"},
      {"level": "INFO", "msg": "Request completed"}
    ]
  },
  "boundary": "service_api",
  "mode": "target",
  "fallback": "retry_with_backoff"
}
```

### Alert Capsule
```json
{
  "invariant": "ERROR_RATE_BOUND",
  "evidence": {
    "metric": "error_rate",
    "value": 0.15,
    "threshold": 0.01,
    "duration": "5m",
    "confidence": "99.9%"
  },
  "boundary": "monitoring_system",
  "mode": "degraded",
  "fallback": "circuit_breaker_activated"
}
```

---

## Part 6: Evidence Correlation

### Multi-Pillar Correlation
```python
def correlate_evidence(time_window, service):
    """Correlate evidence across all three pillars"""

    # Gather evidence from each pillar
    metric_evidence = query_metrics(service, time_window)
    log_evidence = query_logs(service, time_window)
    trace_evidence = query_traces(service, time_window)

    # Find correlation
    correlation = {
        'spike_detected': metric_evidence['error_rate'] > threshold,
        'errors_logged': len(log_evidence['errors']) > 0,
        'slow_traces': trace_evidence['p99_latency'] > slo,

        'root_cause': None
    }

    # Evidence correlation reveals root cause
    if correlation['spike_detected'] and correlation['errors_logged']:
        # Check which errors correlate with metric spike
        error_times = [e['timestamp'] for e in log_evidence['errors']]
        spike_time = metric_evidence['spike_timestamp']

        correlated_errors = [e for e in log_evidence['errors']
                            if abs(e['timestamp'] - spike_time) < 5]

        if correlated_errors:
            # Find traces containing these errors
            error_traces = [t for t in trace_evidence['traces']
                          if t.contains_error(correlated_errors[0])]

            if error_traces:
                # Root cause found through correlation
                correlation['root_cause'] = {
                    'error': correlated_errors[0],
                    'trace': error_traces[0],
                    'service': error_traces[0].error_span.service,
                    'evidence_chain': [
                        metric_evidence,
                        correlated_errors[0],
                        error_traces[0]
                    ]
                }

    return correlation
```

---

## Part 7: Observability Mode Transitions

### Unified Observability Mode Matrix

```python
class ObservabilityModes:
    def __init__(self):
        self.modes = {
            'target': {
                'metrics': {'rate': '15s', 'retention': '30d'},
                'logs': {'level': 'INFO', 'sampling': '100%'},
                'traces': {'sampling': 'intelligent', 'retention': '7d'},
                'guarantee': ⟨Global, Causal, Complete, Fresh(15s), Unique, Auth⟩
            },
            'degraded': {
                'metrics': {'rate': '60s', 'retention': '7d'},
                'logs': {'level': 'WARN', 'sampling': '10%'},
                'traces': {'sampling': '1%', 'retention': '1d'},
                'guarantee': ⟨Service, Monotonic, Sampled, BS(60s), Idem, Auth⟩
            },
            'floor': {
                'metrics': {'rate': 'none', 'retention': 'buffer'},
                'logs': {'level': 'ERROR', 'sampling': '1%'},
                'traces': {'sampling': 'none', 'retention': 'none'},
                'guarantee': ⟨Instance, None, Minimal, EO, None, Unauth⟩
            },
            'recovery': {
                'metrics': {'rate': 'variable', 'backfill': True},
                'logs': {'level': 'DEBUG', 'replay': True},
                'traces': {'sampling': 'increasing', 'rebuild': True},
                'guarantee': ⟨Service, None, Rebuilding, BS(5m), None, Auth⟩
            }
        }
```

### Evidence-Based Mode Transitions

```python
def observability_mode_transition(current_mode, system_state):
    """Transition modes based on evidence availability"""

    evidence_health = {
        'metrics_available': check_prometheus_health(),
        'logs_flowing': check_log_pipeline_health(),
        'traces_complete': check_tracing_health(),
        'storage_available': check_storage_capacity()
    }

    if all(evidence_health.values()):
        return 'target'

    elif evidence_health['metrics_available']:
        # Can maintain degraded with just metrics
        return 'degraded'

    elif evidence_health['storage_available']:
        # Floor mode - local buffering only
        return 'floor'

    else:
        # Complete observability failure
        return 'blind'  # Special critical mode
```

---

## Part 8: SLO Verification Through Evidence

### SLO as Invariant
```python
class SLOEvidence:
    """SLOs are invariants that observability must prove"""

    def __init__(self, slo_definition):
        self.slo = slo_definition
        self.required_evidence = self.determine_evidence_requirements()

    def verify_slo(self, time_window):
        """Gather evidence to prove/disprove SLO"""

        evidence = {
            'metric_evidence': self.gather_metric_evidence(time_window),
            'log_evidence': self.gather_error_logs(time_window),
            'trace_evidence': self.gather_trace_evidence(time_window)
        }

        # SLO: 99.9% availability
        availability_proof = {
            'good_minutes': evidence['metric_evidence']['success_minutes'],
            'total_minutes': evidence['metric_evidence']['total_minutes'],
            'measured_availability': good_minutes / total_minutes,
            'meets_slo': measured_availability >= 0.999,
            'confidence': self.calculate_confidence(evidence),
            'evidence_quality': self.assess_evidence_quality(evidence)
        }

        return availability_proof
```

---

## Transfer Tests

### Near Transfer: CI/CD Pipeline Observability
How would you apply observability-as-evidence to CI/CD pipelines?

**Answer:**
```python
G_cicd = ⟨Pipeline, Causal, DAG, Fresh(immediate), Unique, Auth⟩
```
- Build metrics = quantitative evidence (duration, success rate)
- Build logs = qualitative evidence (test results, errors)
- Pipeline traces = causal evidence (stage dependencies)

### Medium Transfer: Database Query Performance
How does database observability generate evidence?

**Answer:**
- Query metrics: Execution time histograms
- Slow query logs: Qualitative evidence of problematic queries
- Query traces: Execution plan as causal evidence
- Evidence proves: Index usage, lock contention, resource consumption

### Far Transfer: Medical Monitoring
How do medical monitoring systems parallel observability?

**Answer:**
- Metrics = Vital signs (heart rate, blood pressure)
- Logs = Medical chart entries (symptoms, treatments)
- Traces = Patient journey (admission → treatment → discharge)
- Evidence proves: Health invariants maintained or violated

---

## Key Insights: Observability as Evidence Infrastructure

1. **Observability generates evidence, not data**
   - Every metric, log, trace has evidence properties
   - Evidence proves or disproves system invariants
   - Quality of evidence determines confidence in system state

2. **Three pillars = Three evidence types**
   - Metrics: Quantitative evidence (how much/many)
   - Logs: Qualitative evidence (what happened)
   - Traces: Causal evidence (why/how it happened)

3. **Evidence correlation reveals truth**
   - Single pillar = partial evidence
   - Multiple pillars = correlated evidence
   - Full correlation = root cause identification

4. **Observability has modes**
   - Target: Full evidence generation
   - Degraded: Sampled evidence
   - Floor: Minimal evidence
   - Recovery: Evidence reconstruction

5. **SLOs are invariants requiring evidence**
   - Define what evidence proves SLO
   - Monitor evidence quality
   - Alert on evidence degradation before SLO violation

---

## Summary: The Evidence-Generating Observable System

```
Observable System = Evidence Generator + Evidence Store + Evidence Analyzer

Where:
- Evidence Generator: Instrumentation (metrics, logs, traces)
- Evidence Store: Time-series DB, Log storage, Trace storage
- Evidence Analyzer: Queries, Correlation, Alerting

Producing:
- Proofs of correctness
- Proofs of failure
- Proofs of performance
- Proofs of causality
```

This framework transforms observability from a data collection exercise into a **systematic evidence generation infrastructure** that proves system behavior and enables evidence-based operations.
# Cross-Cutting Topics: Master Index

## Overview

This collection covers comprehensive cross-cutting topics that span multiple parts of the distributed systems book. Each topic provides implementation guides, configuration examples, operational playbooks, and production case studies.

---

## Topic Organization

### 1. Data Governance & Privacy
**File**: `cross-cutting-data-governance.md` (57KB)

**Coverage**:
- Retention & TTL across distributed systems
  - Local TTL implementation
  - Distributed TTL challenges
  - Cascading deletion patterns
- Right-to-be-forgotten implementation
  - GDPR Article 17 compliance
  - CCPA/CPRA compliance
  - Cross-system deletion orchestration
  - Backup and archive deletion
- Encryption at rest and in transit
  - Block device, filesystem, and application-level encryption
  - Hierarchical key management
  - Envelope encryption patterns
  - TLS configuration and mTLS
- Deletion verification
  - Cryptographic deletion
  - Tamper-evident deletion logs
  - Multi-system verification
  - Sampling and spot checks
- GDPR/CCPA compliance patterns
  - Data inventory and classification
  - Consent management and enforcement
  - Cross-border data residency
- Production playbooks
  - Data breach response
  - Audit preparation
  - Continuous compliance

**Key Implementations**:
- HLC-based TTL for clock skew tolerance
- Saga-based cross-service deletion
- Per-user encryption keys with KMS
- Outbox pattern for atomic deletion events
- Region-locked data architecture

---

### 2. Observability & Monitoring
**File**: `cross-cutting-observability.md` (26KB)

**Coverage**:
- HLC-stamped distributed tracing
  - Clock-aware trace correlation
  - Causality reconstruction
  - Happens-before graph construction
- Sampling without distorting tail latencies
  - Tail-based sampling
  - Hybrid sampling strategies
  - Exemplar-based sampling
- Partial orders and causality
  - Vector clock comparison
  - Concurrent operation detection
  - Critical path analysis
- SLO/SLI propagation
  - Composite SLIs across service boundaries
  - Error budget allocation
  - SLO composition
- Metrics aggregation
  - Histogram merging
  - Cardinality management
  - Pre-aggregation strategies
- Log correlation
  - Structured logging with trace context
  - Dynamic log levels
  - Log sampling

**Key Implementations**:
- Rust HLC implementation for tracing
- Tail-based sampler (Python)
- Critical path algorithm with dynamic programming
- Exemplar attachment to Prometheus metrics

---

### 3. Change Data Capture & Streaming
**File**: `cross-cutting-comprehensive-summary.md` (Section 3)

**Coverage**:
- CDC pipeline architectures
  - Log-based CDC (WAL, binlog)
  - Debezium connector patterns
  - Outbox pattern implementation
- Exactly-once connector patterns
  - Source connectors (Database → Kafka)
  - Sink connectors (Kafka → Database)
  - Idempotent writes
- Watermarking strategies
  - Event time vs processing time
  - Bounded out-of-order watermarks
  - Per-partition watermarks
- Late data handling
  - Allowed lateness windows
  - Side outputs for late data
  - Reprocessing strategies

**Key Implementations**:
- PostgreSQL logical replication with Debezium
- Outbox table schema and CDC routing
- Kafka transactions for exactly-once
- Flink-style watermark strategy

**Production Metrics**:
- Replication lag: <60s (alert threshold)
- Throughput: 1000-10000 events/sec
- Error rate: <0.1%

---

### 4. Caching & Invalidation
**File**: `cross-cutting-comprehensive-summary.md` (Section 4)

**Coverage**:
- Write-through vs write-back patterns
  - Synchronous vs asynchronous persistence
  - Consistency vs latency tradeoffs
  - Failure handling
- Cache coherence protocols
  - MESI protocol (Modified, Exclusive, Shared, Invalid)
  - Distributed cache invalidation
  - Version vectors for consistency
- Negative caching strategies
  - Caching absence of data
  - TTL for negative entries
  - Bloom filters for existence checks
- Near-cache coherency
  - Local cache invalidation
  - Pub/sub for invalidation messages
  - Lease-based coherence
- Materialized view invalidation
  - Incremental view maintenance
  - Trigger-based updates
  - Batch refresh strategies
- Stale-while-revalidate patterns
  - Serving stale data during refresh
  - Background refresh
  - Graceful degradation

**Key Implementations**:
- Distributed cache with pub/sub invalidation
- Materialized view with triggers (PostgreSQL)
- Cache stampede protection
- Jittered cache expiration

---

### 5. Backpressure & Flow Control
**File**: `cross-cutting-comprehensive-summary.md` (Section 5)

**Coverage**:
- Token-based backpressure
  - Token bucket algorithm
  - Leaky bucket algorithm
  - Sliding window rate limiting
- Load regulation across service graphs
  - Adaptive concurrency limits
  - Little's Law application
  - Gradient-based adjustment
- Queue collapse prevention
  - Load shedding strategies
  - Priority queues
  - Head-of-line blocking mitigation
- Fairness vs priority inversion
  - Weighted fair queuing
  - Dominant resource fairness
  - Priority inheritance
- Circuit breaker patterns
  - State machine (CLOSED, OPEN, HALF_OPEN)
  - Failure threshold configuration
  - Timeout and retry policies
- Bulkhead isolation
  - Resource pool isolation
  - Failure containment
  - Capacity reservation

**Key Implementations**:
- Token bucket rate limiter (Python)
- Adaptive concurrency limit with RTT tracking
- Circuit breaker with timeout
- Admission controller with Little's Law

**Production Patterns**:
- Retry budgets (10% of requests)
- Brownout mode (degraded functionality)
- Emergency mode (30% load shedding)

---

### 6. Network Reality Deep Dive
**File**: `cross-cutting-comprehensive-summary.md` (Section 6)

**Coverage**:
- TCP/QUIC/HTTP3 implications
  - Head-of-line blocking in TCP
  - Independent stream delivery in QUIC
  - 0-RTT connection establishment
  - QUIC configuration and deployment
- BBR congestion control
  - Bandwidth and RTT modeling
  - BBR phases (STARTUP, DRAIN, PROBE_BW, PROBE_RTT)
  - Linux kernel configuration
  - Performance improvements
- ECMP and flow hashing
  - Equal-cost multi-path routing
  - Flow hash calculation
  - Elephant flow problem
  - Flowlet switching
- Anycast considerations
  - Anycast routing behavior
  - Connection disruption on route change
  - Health check strategies
  - Use cases (CDN, DDoS mitigation)
- NAT traversal
  - STUN/TURN/ICE protocols
  - Hole punching techniques
  - Symmetric NAT challenges
- MTU discovery issues
  - Path MTU discovery
  - Fragmentation problems
  - MSS clamping
  - Black hole detection

**Key Implementations**:
- nginx QUIC/HTTP3 configuration
- BBR sysctl settings
- ECMP weighted routing

**Production Metrics**:
- BBR: 2-10x throughput improvement (lossy networks)
- QUIC: 30-50% latency reduction (mobile networks)
- HTTP/3: 2x faster page loads (high packet loss)

---

## Integration with Book Structure

### How Cross-Cutting Topics Map to Parts

**Part I: Fundamental Reality**
- Network reality informs impossibility results
- Clock synchronization affects observability

**Part II: Evolution of Solutions**
- CDC evolved from database replication
- Caching strategies developed over decades

**Part III: 2025 Architecture**
- HLC-based tracing enables causality
- Backpressure essential for reactive systems

**Part IV: Planet-Scale Patterns**
- Data residency requires governance
- Multi-region adds latency, needs caching

**Part V: The Practice**
- All cross-cutting topics are operational concerns
- Production playbooks are essential

**Part VI: Composition and Reality**
- Observability across service boundaries
- Backpressure propagation in service graphs

**Part VII: The Future**
- Privacy regulations will tighten
- Network protocols continue evolving

---

## Usage Guidelines

### For Instructors

**Suggested Integration**:
1. Introduce cross-cutting topics early (Week 2-3)
2. Revisit in context of each main chapter
3. Assign implementation exercises from each topic
4. Use production playbooks for incident simulation

**Lab Exercises**:
- Week 4: Implement HLC-based distributed tracing
- Week 6: Build CDC pipeline with exactly-once semantics
- Week 8: Design multi-tier cache with invalidation
- Week 10: Implement backpressure across service graph
- Week 12: Configure QUIC/HTTP3 with BBR

### For Practitioners

**Recommended Reading Order**:
1. Start with Observability & Monitoring (understand your system)
2. Move to Backpressure & Flow Control (protect your system)
3. Then Caching & Invalidation (optimize your system)
4. Follow with CDC & Streaming (evolve your system)
5. Finally Data Governance & Privacy (comply with regulations)
6. End with Network Reality (optimize at lower layers)

**Production Checklist**:
- [ ] Distributed tracing with HLC timestamps deployed
- [ ] Tail-based sampling configured (capture p99/p999)
- [ ] Circuit breakers on all external dependencies
- [ ] Token bucket rate limiting at API gateway
- [ ] CDC pipeline for audit trail and analytics
- [ ] Cache invalidation verified across all regions
- [ ] GDPR deletion workflow tested and documented
- [ ] Certificate rotation automated with alerts
- [ ] BBR enabled on all load balancers
- [ ] QUIC/HTTP3 available for modern clients

### For Researchers

**Open Problems**:
1. Causality inference without explicit tracing
2. Optimal sampling for arbitrary distributions
3. Formal verification of backpressure propagation
4. Privacy-preserving CDC (GDPR-compliant streaming)
5. Self-tuning cache coherence protocols
6. Congestion control for multi-path protocols

**Research Directions**:
- Machine learning for adaptive sampling
- Zero-knowledge proofs for deletion verification
- Quantum-resistant cryptography for data at rest
- Formal methods for cache coherence at scale

---

## Metrics and SLOs

### Observability
- Trace sampling rate: 1-10% (head) + 100% (errors/slow)
- Trace retention: 7-30 days
- P99 latency accuracy: ±5%
- Causality reconstruction: 100% of traces

### CDC & Streaming
- Replication lag: <60s (p99)
- Exactly-once guarantees: 100% (no duplicates/loss)
- Event ordering: 100% per partition
- Throughput: 1000-10000 events/sec per connector

### Caching
- Cache hit rate: 80-95% (depends on workload)
- Invalidation propagation: <1s (p99)
- Consistency: 99.9% (occasional stale reads acceptable)
- Negative cache TTL: 60s

### Backpressure
- Admission rate: 100% at target load
- Queue depth: <100 items (prevents memory explosion)
- Circuit breaker trip rate: <0.1% of requests
- Load shedding: only during overload (>110% capacity)

### Data Governance
- Deletion completion: <30 days (GDPR) / <45 days (CCPA)
- Deletion verification: 99.9% accuracy
- Encryption coverage: 100% of PII at rest
- Certificate rotation: 60 days before expiry

---

## Production War Stories

### Story 1: The Tail Latency Mystery (Observability)
**Problem**: P99 latency 10x higher than P50, but head-sampled traces showed everything fast.

**Root Cause**: Head sampling (1%) missed slow requests. Only 1 in 1000 slow requests was sampled.

**Solution**: Implemented tail-based sampling. Captured 100% of requests >1s. Discovered database lock contention on hot keys.

**Lesson**: Never rely on head sampling for tail latency analysis.

---

### Story 2: The Deletion That Wasn't (Data Governance)
**Problem**: Users reported seeing deleted data 3 months after deletion request.

**Root Cause**: Backup restoration process didn't apply deletion log. Deleted users resurrected from backup.

**Solution**: Added deletion log reconciliation to post-restore process. Verified deletion in all backups.

**Lesson**: Deletion is not complete until verified in all storage systems, including backups.

---

### Story 3: The Cache Stampede (Caching & Invalidation)
**Problem**: Popular cache key expiry caused 10000 simultaneous database queries, overwhelming the database.

**Root Cause**: No stampede protection. All requests tried to refresh cache simultaneously.

**Solution**: Implemented per-key locking + probabilistic early expiration + background refresh.

**Lesson**: Cache misses on popular keys can amplify to denial of service.

---

### Story 4: The Backpressure Cascade (Backpressure & Flow Control)
**Problem**: One slow downstream service caused entire system to fail.

**Root Cause**: No backpressure. Upstream services queued infinitely, ran out of memory, crashed.

**Solution**: Implemented bounded queues + circuit breakers + adaptive concurrency limits.

**Lesson**: Backpressure is essential. Unbounded queues lead to cascading failures.

---

### Story 5: The Duplicate Events (CDC & Streaming)
**Problem**: Users charged twice for orders. CDC pipeline delivered duplicates.

**Root Cause**: Connector retried after timeout, but original attempt succeeded. No idempotency.

**Solution**: Enabled Kafka transactions (exactly-once) + idempotency keys in sink.

**Lesson**: At-least-once delivery requires idempotent processing. Exactly-once requires transactions.

---

### Story 6: The Cross-Region Replication Bill (Network Reality)
**Problem**: Cloud bill 10x higher than expected. Root cause: full-mesh replication across 10 regions.

**Root Cause**: Every write replicated to 9 other regions. 100 GB/day × 9 × $0.08/GB = $72k/month.

**Solution**: Changed to hierarchical replication (primary + regional secondaries). Cost reduced to $8k/month.

**Lesson**: Cross-region egress is expensive. Topology matters.

---

## Further Reading

### Books
- "Designing Data-Intensive Applications" by Martin Kleppmann
- "Site Reliability Engineering" by Google
- "Database Internals" by Alex Petrov
- "Streaming Systems" by Akidau, Chernyak, Lax
- "TCP/IP Illustrated" by Stevens

### Papers
- "Hybrid Logical Clocks" (Kulkarni et al., 2014)
- "Unicorn: A System for Searching the Social Graph" (Facebook, 2013)
- "Kafka: a Distributed Messaging System for Log Processing" (LinkedIn, 2011)
- "BBR: Congestion-Based Congestion Control" (Google, 2016)
- "The Dataflow Model" (Google, 2015)
- "Elle: Inferring Isolation Anomalies from Experimental Observations" (Kingsbury, 2020)

### Standards and Specifications
- GDPR Official Text: https://gdpr-info.eu/
- CCPA Full Text: https://oag.ca.gov/privacy/ccpa
- OpenTelemetry Specification: https://opentelemetry.io/docs/specs/
- W3C Trace Context: https://www.w3.org/TR/trace-context/
- QUIC RFC 9000: https://www.rfc-editor.org/rfc/rfc9000.html

### Tools and Platforms
- Debezium: CDC platform (https://debezium.io/)
- Apache Flink: Stream processing (https://flink.apache.org/)
- Jaeger: Distributed tracing (https://www.jaegertracing.io/)
- Prometheus: Metrics and alerting (https://prometheus.io/)
- Envoy: L7 proxy with observability (https://www.envoyproxy.io/)

---

## Appendix: Quick Reference Tables

### Latency Budget Breakdown (Typical 100ms API)
| Component | Latency | % of Budget |
|-----------|---------|-------------|
| Client → LB | 5ms | 5% |
| LB → Service | 2ms | 2% |
| Service logic | 10ms | 10% |
| Cache lookup | 1ms | 1% |
| Database query | 50ms | 50% |
| Serialization | 5ms | 5% |
| Network overhead | 10ms | 10% |
| Tracing overhead | 1ms | 1% |
| Reserve | 16ms | 16% |

### Cost Comparison (per 1M requests)
| Component | Cost | Notes |
|-----------|------|-------|
| Compute (serverless) | $0.20 | AWS Lambda 1GB-sec |
| Database reads | $0.25 | DynamoDB on-demand |
| Database writes | $1.25 | DynamoDB on-demand |
| Cross-region egress | $0.80 | 10 KB × 100K × $0.08/GB |
| Tracing (10% sample) | $0.05 | Jaeger + S3 storage |
| Logs | $0.50 | CloudWatch Logs |
| Metrics | $0.10 | CloudWatch Metrics |
| **Total** | **$3.15** | Per million requests |

### Failure Mode Impact Matrix
| Failure | Observability | CDC | Caching | Backpressure | Data Gov | Network |
|---------|---------------|-----|---------|--------------|----------|---------|
| Region outage | Partial traces | Replication lag | Stale data | Overload | Delayed deletion | Failover |
| Network partition | Lost traces | Duplicate events | Inconsistent | Backpressure | Split brain | Retries |
| Clock skew | Causality errors | Out-of-order | Premature expire | No impact | TTL errors | Timeout |
| Disk full | No traces | Connector stall | Eviction | Queue full | Deletion fail | Buffering |
| Memory exhaustion | Trace loss | OOM crash | Eviction | Admission control | Process crash | Connection limit |

---

## Conclusion

These cross-cutting topics are essential for building production-grade distributed systems. They interact with every layer of the architecture:

1. **Observability**: Understand what's happening (HLC tracing, tail sampling, causality)
2. **Resilience**: Protect from failure (backpressure, circuit breakers, admission control)
3. **Performance**: Optimize for speed (caching, CDN, BBR, QUIC)
4. **Compliance**: Meet regulations (GDPR, CCPA, encryption, deletion)
5. **Evolution**: Enable change (CDC, streaming, schema evolution)
6. **Reality**: Work with constraints (network latency, congestion, packet loss)

Master these topics, and you'll be well-equipped to design, build, and operate systems that scale to billions of users while remaining observable, resilient, compliant, and performant.

---

## Document Metadata

**Total Coverage**: 103KB across 3 files
- `cross-cutting-data-governance.md`: 57KB
- `cross-cutting-observability.md`: 26KB
- `cross-cutting-comprehensive-summary.md`: 20KB

**Topics Covered**: 6 major cross-cutting concerns
**Implementations**: 30+ code examples (Python, Rust, SQL, YAML, Bash)
**Production Metrics**: 50+ real-world measurements
**Case Studies**: 10+ production systems analyzed
**Playbooks**: 15+ operational procedures
**Exercises**: 20+ hands-on assignments

**Audience**: Graduate students, senior engineers, architects, SREs
**Difficulty**: Intermediate to Advanced
**Prerequisites**: Understanding of basic distributed systems concepts (consensus, replication, consistency models)

**Version**: 1.0 (2025 Edition)
**Last Updated**: 2025-09-30
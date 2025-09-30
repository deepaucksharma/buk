# Part VI: Composition and Reality - Ultra-Detailed Expanded Table of Contents

## Overview
Part VI synthesizes theory and practice, showing how distributed systems compose in production environments. This part bridges the gap between isolated guarantees and real-world system behavior, covering composition rules, failure modes, economic decision-making, and production war stories.

---

## Chapter 17: Composition and Adaptation

### 17.1 Composition Rules

#### 17.1.1 Formal Guarantee Algebra
- **Mathematical Foundation**
  - Consistency level ordering (lattice structure)
    - Strict Serializable (strongest)
    - Serializable
    - Snapshot Isolation
    - Read Committed
    - Eventually Consistent (weakest)
    - Partial ordering properties
    - Meet and join operations
  - Composition laws
    - Identity law: SS ∘ I = SS
    - Associativity: (A ∘ B) ∘ C = A ∘ (B ∘ C)
    - Degradation rule: A ∘ B = min(A, B)
    - No automatic upgrade property
    - Proof of laws using lattice theory
  - Guarantee preservation theorems
    - When guarantees strengthen (never automatically)
    - When guarantees weaken (composition chains)
    - Proof-carrying context requirements
    - Evidence accumulation rules

- **Proof-Carrying Context Implementation**
  - Context structure design
    - Guarantee level field
    - Evidence dictionary (timestamps, transaction IDs, versions)
    - Composition chain history
    - Certification checkpoints
  - Header propagation
    - HTTP header format (X-Consistency-Level, X-Consistency-Chain)
    - gRPC metadata format
    - Message queue attribute format (Kafka, RabbitMQ)
    - Protobuf/JSON serialization
  - Chain tracking
    - Recording each service's guarantee
    - Detecting guarantee downgrades
    - Alerting on unexpected weakening
    - Audit trail for compliance
  - Certification checking
    - Required guarantee validation
    - GuaranteeViolation exception handling
    - Graceful degradation strategies
    - Fallback mechanisms

- **Python Implementation Details**
  - ConsistencyContext class design
    - Constructor parameters
    - State management (guarantee, evidence, chain)
    - Thread-safety considerations
  - Composition method
    - Taking minimum guarantee level
    - Appending to chain history
    - Returning self for method chaining
  - Certification method
    - Comparing current vs required
    - Raising typed exceptions
    - Logging certification failures
    - Metrics emission
  - Serialization methods
    - to_headers() for HTTP/gRPC
    - from_headers() for deserialization
    - JSON encoding of evidence
    - Enum string conversion
  - Service handler integration
    - Middleware for automatic context extraction
    - Decorator for certification requirements
    - Error handling in application code
    - Testing strategies

- **Upgrade Gates**
  - When upgrades are possible
    - Re-reading from authoritative source
    - Conflict detection before upgrade
    - Version comparison mechanisms
    - Transaction re-execution
  - ConsistencyGate implementation
    - Target guarantee level
    - Authoritative source configuration
    - Conflict detection algorithms
    - Evidence generation
  - Re-certification process
    - Reading with strong consistency
    - Comparing weak vs strong data
    - Detecting version mismatches
    - Handling conflicts (abort vs retry)
  - Performance implications
    - Latency cost of upgrade
    - Cache invalidation
    - Additional database load
    - When to avoid upgrades
  - Use cases
    - Cache-to-database upgrade pattern
    - Eventually consistent read → critical operation
    - Replica read → primary write
    - Multi-region to single-region upgrade

#### 17.1.2 Service Mesh Patterns

- **Sidecar Proxy Architecture**
  - Envoy proxy design
    - Listener filters for incoming traffic
    - Network filters for L4 operations
    - HTTP filters for L7 operations
    - Lua filter for custom logic
  - Consistency enforcement filter
    - Extracting consistency headers
    - Validating against service requirements
    - Composing guarantees across calls
    - Updating headers for upstream
  - Configuration management
    - Static configuration in YAML
    - Dynamic configuration via xDS protocol
    - Metadata for service-specific rules
    - Hot reload without downtime

- **Envoy Lua Filter Implementation**
  - Request phase handling
    - envoy_on_request callback
    - Header extraction and parsing
    - Metadata lookup for requirements
    - Early rejection for insufficient guarantees
  - Composition logic
    - Getting service's own guarantee from metadata
    - Computing result guarantee (minimum)
    - Updating consistency headers
    - Appending to chain
  - Response phase handling
    - envoy_on_response callback
    - Adding timing metrics
    - Recording actual guarantee achieved
    - Tracing integration
  - Error handling
    - Invalid header values
    - Missing required headers
    - Service configuration errors
    - Graceful fallback behavior

- **Istio Integration**
  - VirtualService configuration
    - HTTP match rules based on consistency headers
    - Routing to different service subsets
    - Primary vs replica selection
    - Weight-based traffic splitting
  - DestinationRule configuration
    - Subset definitions (primary, replica)
    - Load balancing policies per subset
    - Connection pool settings
    - Circuit breaker configuration
  - ServiceEntry for external services
    - Declaring consistency guarantees
    - Location (mesh internal vs external)
    - Port specifications
    - TLS settings
  - Header manipulation
    - Request header injection
    - Response header removal
    - Dynamic header values from metadata
    - Template-based header generation

- **End-to-End SLO Composition**
  - SLOChain class design
    - List of services with their SLOs
    - Availability and latency tracking
    - Error budget computation
  - Serial composition
    - Availability: product of all service availabilities
    - Latency: sum of P99 latencies
    - Example: 5 services × 99.9% each = 99.5% end-to-end
  - Parallel composition
    - Availability: 1 - product(1 - A_i) for redundant paths
    - Latency: max of P99 latencies (slowest wins)
    - Fan-out pattern analysis
  - Computing required per-service SLO
    - Given target end-to-end availability
    - Formula: per_service = target^(1/N)
    - Example: 99.9% target, 3 services → 99.97% each
  - Error budget allocation
    - Total budget: (1 - target_availability) × time
    - Splitting budget across services
    - Tracking budget consumption
    - Alerting on budget exhaustion
  - Latency budgets
    - P50, P95, P99 budget allocation
    - Critical path identification
    - Optimizing slowest service
    - Trade-offs: consistency vs latency

- **Service Mesh Observability**
  - Distributed tracing
    - OpenTelemetry integration
    - Consistency level in span attributes
    - Composition chain visualization
    - Latency breakdown by guarantee
  - Metrics collection
    - Prometheus exposition format
    - Consistency-aware metric labels
    - Request rate by guarantee level
    - Error rate by certification failure
  - Access logs
    - Consistency headers in log format
    - JSON structured logging
    - Log aggregation patterns
    - Compliance audit trails

#### 17.1.3 Certainty Labels and Proof Propagation

- **Type-Level Consistency (Rust)**
  - Phantom types for zero-cost abstractions
    - PhantomData<C: ConsistencyLevel>
    - No runtime overhead
    - Compile-time guarantee checking
    - Type inference in handlers
  - ConsistencyLevel trait hierarchy
    - StrictSerializable: 'static
    - Serializable: 'static
    - SnapshotIsolation: 'static
    - ReadCommitted: 'static
    - EventuallyConsistent: 'static
  - ConsistentData<T, C> wrapper
    - Generic over data type T and consistency C
    - Value field of type T
    - Evidence field with proofs
    - Phantom marker for consistency

- **Evidence Structure**
  - Hybrid Logical Clock timestamp
    - Physical time component
    - Logical counter component
    - Node ID for disambiguation
    - Causality tracking
  - Transaction ID (optional)
    - UUID for distributed transactions
    - Coordinator information
    - Participant list
    - Transaction state
  - Read version
    - Snapshot timestamp for SI
    - MVCC version number
    - Vector clock for causality
    - Commit timestamp
  - Linearization point (optional for SS)
    - Global timestamp when operation took effect
    - Proof of total order
    - Witness node information
    - Certificate from coordinator

- **Type-Safe Operations**
  - Operations requiring StrictSerializable
    - use_in_transaction: only SS data allowed
    - Financial operations (payments, transfers)
    - Critical state mutations
    - Compile-time enforcement
  - Downgrade operation (always safe)
    - Generic over target consistency level C2
    - Type bound: C2: WeakerThan<C>
    - Preserves value and evidence
    - Zero runtime cost
  - Upgrade operation (requires re-certification)
    - Generic over target consistency level C2
    - Type bound: C2: StrongerThan<C>
    - Async operation (hits database)
    - Returns Result<ConsistentData<T, C2>>
  - Type-level guarantee chains
    - Function signatures encode requirements
    - Caller must provide correct guarantee
    - Composition checked at compile time
    - No runtime consistency errors

- **Practical Example: Payment Processing**
  - Function signature enforcement
    - process_payment requires SS account
    - Compiler rejects weaker guarantees
    - No need for runtime checks
    - Self-documenting code
  - Database read with typed guarantees
    - get_account returns ConsistentData<Account, SS>
    - Evidence populated by database driver
    - Type proves correctness to compiler
  - Upgrade pattern
    - Read from cache (EC guarantee)
    - Upgrade to SS before payment
    - Gate.certify_upgrade async call
    - Handle conflicts gracefully

- **Advanced Type System Patterns**
  - Effect systems
    - Tracking side effects in types
    - Distinguishing reads vs writes
    - Idempotent vs non-idempotent operations
    - Algebraic effects and handlers
  - Linear types for resources
    - Use-once semantics for critical operations
    - Preventing double-spend at type level
    - Affine types for optional cleanup
    - Session types for protocols
  - Dependent types (future work)
    - Types parameterized by values
    - Expressing invariants in types
    - Refinement types for constraints
    - Proof obligations at compile time

### 17.2 Adaptation Patterns

#### 17.2.1 Operational Modes

- **Floor Mode (Minimum Viable)**
  - Definition and triggers
    - Absolute minimum functionality to avoid total outage
    - Triggered by: cascading failures, resource exhaustion
    - Goal: keep system alive, even if degraded
  - Reduced functionality
    - Read-only operations only
    - Serve stale cache data (EC guarantee)
    - Disable non-essential features
    - Static content fallback
  - Consistency downgrades
    - From SS to SI or RC
    - From SI to EC
    - Explicit user notification of degraded service
  - Example configurations
    - Database: read from replicas only
    - Cache: accept any staleness
    - API: return 503 for writes, allow reads
    - UI: show "Limited Functionality" banner
  - Monitoring in floor mode
    - Track time spent in floor mode
    - Measure recovery progress
    - Alert when floor mode triggered
    - Automatic escalation if prolonged

- **Target Mode (Normal Operation)**
  - Expected steady-state behavior
    - All features enabled
    - Stated SLOs met
    - Optimal resource utilization
    - Consistency guarantees as designed
  - Performance characteristics
    - P50 latency: 20ms
    - P99 latency: 100ms
    - Availability: 99.99%
    - Error rate: < 0.01%
  - Resource allocation
    - CPU: 60% average utilization
    - Memory: 70% average utilization
    - Disk I/O: within IOPS limits
    - Network: under bandwidth cap
  - Configuration parameters
    - Cache TTL: 5 minutes
    - Connection pool size: 100
    - Request timeout: 5 seconds
    - Retry limit: 3 attempts

- **Degraded Mode (Survival)**
  - Partial failure scenarios
    - One availability zone down
    - Database replica lag > 60s
    - High error rate from dependency
    - Elevated latencies (P99 > 2x normal)
  - Graceful degradation strategies
    - Reduce non-critical load
    - Extend timeouts slightly
    - Increase cache TTLs (accept staleness)
    - Disable expensive features
  - Consistency trade-offs
    - From SS to SI (allow some anomalies)
    - From SI to RC (allow non-repeatable reads)
    - From synchronous to asynchronous
    - From cross-region to single-region
  - User experience impact
    - Longer load times
    - Stale data warnings
    - Feature unavailability notices
    - Retry prompts
  - Automatic vs manual triggers
    - Automatic: SLO burn rate > threshold
    - Manual: operator intervention
    - Playbook-driven decisions
    - Approval workflows for critical systems

- **Recovery Mode (Restoration Path)**
  - Transitioning from floor to target
    - Incremental re-enabling of features
    - Canary deployments for stability
    - Gradual traffic increase
    - Monitoring for regression
  - Consistency upgrades
    - Upgrading from EC to RC
    - Upgrading from RC to SI
    - Upgrading from SI to SS
    - Validation after each step
  - Backfill and catch-up operations
    - Replaying queued writes
    - Syncing lagged replicas
    - Reprocessing failed transactions
    - Consistency audits
  - Validation gates
    - Error rate must drop below X%
    - Latency must stabilize below Y ms
    - Resource utilization must be sustainable
    - No new alerts fired
  - Communication protocols
    - Status page updates
    - Internal stakeholder notifications
    - Customer communications
    - Post-recovery report

#### 17.2.2 Control Loops

- **Input Signals**
  - SLO burn rate
    - Formula: error_budget_consumed / time_elapsed
    - Example: 10% budget used in 5% of month = 2x burn rate
    - Alerting thresholds: 2x (warning), 10x (critical)
    - Forecasting budget exhaustion
  - Error budgets
    - Remaining budget = initial_budget - consumed_budget
    - Time until exhaustion: remaining / current_burn_rate
    - Visual dashboard (progress bars, graphs)
    - Per-SLI tracking (availability, latency, correctness)
  - Resource utilization
    - CPU: average, P50, P99 across fleet
    - Memory: RSS, heap, GC pressure
    - Disk: IOPS, throughput, queue depth
    - Network: bandwidth, packet rate, drops
  - Dependency health
    - Downstream service latencies
    - Error rates from dependencies
    - Circuit breaker states
    - Queue depths to external services
  - Request characteristics
    - Request rate (QPS)
    - Request size distribution
    - Slow query identification
    - Expensive operation frequency

- **Control Actions**
  - Cache TTL adjustment
    - Increase TTL to reduce database load
    - Decrease TTL to improve freshness
    - Per-key TTL policies
    - Dynamic TTL based on access patterns
  - Closed timestamp tuning (CockroachDB)
    - Decreasing interval for lower latency reads
    - Increasing interval for higher write throughput
    - Target: 2s for OLTP, 10s for analytics
    - Monitoring: follower read cache hit rate
  - Escrow rebalancing
    - Moving reserved capacity between nodes
    - Rebalancing based on hot spots
    - Triggering split/merge of ranges
    - Load shedding to underutilized nodes
  - Admission control
    - Rejecting low-priority requests
    - Rate limiting per tenant/user
    - Backpressure propagation to clients
    - Priority queues for critical operations
  - Connection pool resizing
    - Increasing size to reduce contention
    - Decreasing size to reduce memory
    - Dynamic sizing based on latency
  - Timeout adjustments
    - Extending timeouts under load
    - Shortening timeouts to fail fast
    - Per-operation timeout tuning
    - Retry backoff parameter changes

- **Control Loop Implementation (PID)**
  - Proportional term
    - Error = setpoint - current_value
    - P_term = K_p × error
    - Immediate response to deviation
  - Integral term
    - Accumulated error over time
    - I_term = K_i × ∫ error dt
    - Corrects steady-state error
    - Anti-windup mechanisms
  - Derivative term
    - Rate of change of error
    - D_term = K_d × d(error)/dt
    - Dampens oscillations
    - Smoothing/filtering
  - Output calculation
    - Output = P_term + I_term + D_term
    - Clamping to valid ranges
    - Slew rate limiting
  - Tuning PID parameters
    - K_p: aggressive response
    - K_i: eliminate offset
    - K_d: reduce overshoot
    - Ziegler-Nichols method
    - Manual tuning in production
  - Example: auto-scaling based on latency
    - Setpoint: P99 latency = 100ms
    - Current: P99 latency = 150ms
    - Error: 50ms
    - Action: scale out by 2 instances

- **Feedback Loop Stability**
  - Avoiding oscillations
    - Hysteresis in thresholds
    - Cooldown periods between actions
    - Rate limiting control actions
    - Exponential backoff
  - Convergence analysis
    - Lyapunov stability theory
    - Ensuring bounded output
    - Detecting limit cycles
  - Multi-loop interactions
    - Coordinating multiple control loops
    - Avoiding conflicting actions
    - Hierarchical control structures
    - Master controller coordination

#### 17.2.3 Mode Transitions

- **Trigger Conditions**
  - Automatic triggers
    - SLO violation for X consecutive minutes
    - Error rate exceeds threshold
    - Latency P99 > 3x target
    - Resource exhaustion imminent
  - Manual triggers
    - Operator decision during incident
    - Planned maintenance
    - Capacity planning actions
    - Testing/game day exercises
  - External triggers
    - Upstream service degradation
    - Cloud provider issues
    - DDoS attack detected
    - Scheduled traffic surge (Black Friday)

- **Hysteresis Prevention**
  - Problem: flapping between modes
    - Rapidly switching degrades experience
    - Increases operational load
    - Confuses monitoring/alerting
  - Solution: different thresholds for transitions
    - Enter degraded: P99 > 200ms
    - Exit degraded: P99 < 150ms for 5 minutes
    - Minimum time in mode: 10 minutes
  - Cooldown periods
    - After entering degraded, wait 15 minutes before recovery
    - After recovery, wait 30 minutes before next degradation
    - Exponential backoff on repeated transitions
  - State machine design
    - Explicit states: Target, Degraded, Floor, Recovery
    - Transitions with guards (conditions)
    - Entry/exit actions for each state
    - Forbidden transitions (Floor → Target directly)

- **Smooth Transitions**
  - Gradual parameter changes
    - Ramping cache TTL from 5min to 30min over 10 minutes
    - Slowly closing circuit breakers
    - Incremental timeout extensions
  - Canary deployments of configuration
    - Apply new mode to 1% of traffic
    - Monitor for 10 minutes
    - Expand to 10%, 50%, 100%
    - Rollback if issues detected
  - Traffic shifting strategies
    - Weighted round-robin
    - Percentage-based routing
    - Session affinity during transition
  - User communication
    - Gradual UI changes (banners, warnings)
    - Progressive feature disabling
    - Clear messaging about mode

- **Rollback Capabilities**
  - Fast rollback mechanisms
    - Configuration snapshots
    - One-click revert to previous mode
    - Automated rollback on alert
  - Rollback decision criteria
    - Error rate spike > 5x
    - P99 latency > 5x
    - New alert types appearing
    - User complaints spike
  - Preserving state during rollback
    - Queue pending operations
    - Sync data before transition
    - Idempotency for replayed operations
  - Testing rollback paths
    - Chaos engineering: force mode transitions
    - Game day exercises
    - Automated rollback drills

### 17.3 Multi-System Coordination

#### 17.3.1 Protocol Standardization

- **Idempotency Keys**
  - Purpose and benefits
    - Preventing duplicate operations
    - Safe retry semantics
    - Exactly-once delivery guarantee
  - Key generation
    - Client-generated UUIDs
    - Hash of request payload
    - Combining user ID + timestamp + nonce
  - Server-side tracking
    - DynamoDB idempotency table
      - Partition key: idempotency_key
      - Attributes: status, result, ttl
    - Redis cache for recent keys
      - Expiration after 24 hours
    - Postgres with UNIQUE constraint
  - Handling duplicate requests
    - Check idempotency table before processing
    - Return cached result if key exists
    - Store result after successful processing
    - Atomic check-and-set operation
  - TTL and cleanup
    - Keep keys for 24 hours (common retry window)
    - Background job to purge expired keys
    - Archive old keys for audit
  - Example: payment processing
    - Client generates UUID for payment
    - Server checks if payment already processed
    - Returns existing result if duplicate
    - Prevents double-charging

- **Exactly-Once Semantics**
  - At-least-once vs at-most-once vs exactly-once
    - At-least-once: may deliver duplicates (Kafka default)
    - At-most-once: may drop messages (UDP)
    - Exactly-once: no duplicates, no drops (expensive!)
  - Kafka transactional producer
    - Transactional ID for producer
    - Atomic writes across partitions
    - Fencing out zombie producers
    - Consumer reads committed messages only
  - Idempotency + deduplication = exactly-once
    - Producer assigns sequence numbers
    - Broker detects duplicates by sequence
    - Consumer tracks offsets transactionally
  - End-to-end exactly-once pattern
    - Read message from queue (at-least-once)
    - Process with idempotency key
    - Commit offset after successful processing
    - Transactional outbox for side effects
  - Cost and trade-offs
    - Performance overhead (~30% throughput loss)
    - Increased latency (coordination)
    - Complexity in error handling
    - When to use: financial transactions, critical updates

- **Outbox Pattern**
  - Problem: atomic update + message send
    - Want to update database AND send message
    - Can't use distributed transaction (2PC too slow)
    - Risk: update succeeds but message send fails
  - Solution: transactional outbox
    - Insert message into outbox table in same transaction as business logic
    - Background poller reads outbox and sends to queue
    - Mark as sent after successful queue publish
  - Implementation details
    - Outbox table schema
      - id (PK), aggregate_id, event_type, payload, status, created_at
    - Transaction boundary
      - BEGIN; UPDATE accounts; INSERT INTO outbox; COMMIT;
    - Poller design
      - SELECT * FROM outbox WHERE status='pending' LIMIT 100
      - FOR UPDATE SKIP LOCKED (PostgreSQL)
      - Send to Kafka/RabbitMQ
      - UPDATE outbox SET status='sent'
  - Ordering guarantees
    - Per-aggregate ordering (same aggregate_id)
    - Use aggregate_id as Kafka partition key
    - Outbox poller processes sequentially per aggregate
  - Failure handling
    - Retry failed sends with exponential backoff
    - Dead letter queue for permanent failures
    - Alerting on old pending messages
  - Cleanup and archival
    - Delete sent messages after 7 days
    - Archive to cold storage for audit
    - Partition table by timestamp

- **Dead Letter Queues (DLQ)**
  - Purpose
    - Handle messages that can't be processed
    - Prevent blocking of queue by poison messages
    - Allow manual inspection and recovery
  - When to move to DLQ
    - After N retry attempts (typically 3-5)
    - On deserialization errors
    - On permanent business logic errors (invalid data)
    - Not on transient errors (timeout → retry)
  - DLQ structure
    - Separate queue/topic per source
    - Metadata: original queue, retry count, error reason
    - Original message payload preserved
  - Processing DLQ messages
    - Manual inspection and fix
    - Automated recovery workflows
    - Replay after fixing bug
    - Archive and discard if unrecoverable
  - Alerting and monitoring
    - Alert when DLQ depth > 0
    - Track DLQ arrival rate
    - Age of oldest message in DLQ
    - Dashboard for DLQ across all queues
  - Example configurations
    - Kafka: separate DLQ topic
    - RabbitMQ: DLX (Dead Letter Exchange)
    - SQS: DLQ linked to source queue
    - Custom: database table as DLQ

#### 17.3.2 Cross-System Invariants

- **Distributed Sagas**
  - Definition
    - Long-running transaction across microservices
    - Series of local transactions
    - Compensating transactions for rollback
  - Choreography vs Orchestration
    - Choreography: services listen to events, no central coordinator
    - Orchestration: central saga coordinator directs flow
  - Saga execution example: order placement
    - Step 1: Reserve inventory (local txn)
    - Step 2: Charge payment (local txn)
    - Step 3: Create shipment (local txn)
    - Compensation: unreserve inventory, refund payment
  - Saga state machine
    - States: NotStarted, InProgress, Completed, Compensating, Compensated, Failed
    - Transitions triggered by service responses
    - Timeout handling for each step
  - Compensation chains
    - Reverse order of forward operations
    - Idempotent compensations (may be retried)
    - Partial compensation on failure
  - Saga persistence
    - Store saga state in database
    - Event log for all state transitions
    - Recovery after coordinator crash
  - Failure modes
    - Forward recovery: retry failed step
    - Backward recovery: compensate completed steps
    - Manual intervention: pause for investigation

- **Saga Orchestration Implementation**
  - Saga coordinator service
    - REST API to start sagas
    - State machine engine
    - Retry and timeout logic
    - Persistence layer (Postgres)
  - Participant services
    - Execute local transaction
    - Return success/failure to coordinator
    - Implement compensation endpoint
    - Idempotency for retries
  - Step definition
    - Service name and endpoint
    - Input payload template
    - Compensation endpoint
    - Timeout duration
    - Retry policy (max attempts, backoff)
  - Saga DSL example (YAML)
    ```yaml
    saga: order_placement
    steps:
      - name: reserve_inventory
        service: inventory-service
        endpoint: /reserve
        compensation: /unreserve
        timeout: 5s
      - name: charge_payment
        service: payment-service
        endpoint: /charge
        compensation: /refund
        timeout: 10s
    ```
  - Error handling
    - Transient errors: retry with backoff
    - Permanent errors: trigger compensation
    - Timeout: treat as failure, compensate
    - Partial failures: compensate completed steps

- **Two-Phase Protocols**
  - Classic 2PC (Two-Phase Commit)
    - Phase 1: Prepare (coordinator asks participants to vote)
    - Phase 2: Commit/Abort (coordinator tells result)
    - Blocking protocol: coordinator failure blocks participants
  - Non-blocking alternatives
    - 3PC (Three-Phase Commit): adds pre-commit phase
    - Paxos Commit: uses consensus for commit decision
    - Percolator: optimistic concurrency control
  - 2PC implementation
    - Coordinator role
      - Send PREPARE to all participants
      - Collect votes (YES/NO)
      - Decide: COMMIT if all YES, else ABORT
      - Send decision to all participants
    - Participant role
      - Receive PREPARE
      - Write undo/redo logs
      - Vote YES if ready, NO if conflict
      - Wait for decision
      - Commit or abort locally
  - Transaction log for recovery
    - Coordinator log: transaction ID, participants, decision
    - Participant log: transaction ID, local updates, vote
    - Recovery: replay log after crash
  - Timeouts and failures
    - Participant timeout on PREPARE: abort locally
    - Coordinator timeout on votes: abort transaction
    - Coordinator crash: participants block (classic 2PC problem)
    - Resolution: participants ask other participants or wait for coordinator recovery

- **Escrow Federation**
  - Problem: sharing reserved resources across systems
    - Inventory reserved in warehouse system
    - Need to make reservation visible to order system
    - Avoid double-booking across systems
  - Escrow account pattern
    - Central escrow service holds reservations
    - Systems borrow capacity from escrow
    - Return unused capacity
  - Implementation
    - Escrow table per resource type
      - resource_id, total_capacity, available, reservations (JSONB)
    - Reserve operation
      - BEGIN; SELECT ... FOR UPDATE; check capacity; UPDATE; INSERT reservation; COMMIT;
    - Release operation
      - DELETE reservation; UPDATE escrow (increment available)
    - Rebalancing
      - Periodic job to move capacity between regions
      - Based on demand patterns
  - Failure handling
    - Timeouts on reservations (TTL)
    - Automatic release after expiration
    - Explicit release on transaction abort
  - Monitoring
    - Capacity utilization per resource
    - Reservation duration distribution
    - Expiration rate (timeouts)

#### 17.3.3 Observability Integration

- **Trace Correlation**
  - Distributed tracing fundamentals
    - Trace: end-to-end request flow
    - Span: single operation (service call, DB query)
    - Trace ID: unique identifier for entire trace
    - Span ID: unique identifier for span
    - Parent span ID: for hierarchical structure
  - OpenTelemetry integration
    - Context propagation (W3C Trace Context)
    - Span creation in each service
    - Span attributes (consistency level, guarantee chain)
    - Span events (certification checks, upgrades)
  - Consistency-aware tracing
    - Add consistency_level attribute to spans
    - Add composition_chain attribute
    - Add certification_failures events
    - Trace upgrade operations separately
  - Visualization
    - Jaeger UI with custom attributes
    - Flame graphs colored by consistency level
    - Critical path analysis with guarantee requirements
    - Anomaly detection: unexpected guarantee changes
  - Sampling strategies
    - Head-based sampling: 1% of traces
    - Tail-based sampling: 100% of slow/errored traces
    - Consistency-based: 100% of traces with guarantee violations

- **Metric Aggregation**
  - Prometheus metric types
    - Counter: monotonically increasing (requests, errors)
    - Gauge: current value (queue depth, memory usage)
    - Histogram: distribution (latency, request size)
    - Summary: quantiles (P50, P95, P99)
  - Consistency-aware metrics
    - Request rate by consistency level
      - `requests_total{consistency="strict_serializable"}`
    - Latency histograms per guarantee
      - `request_duration_seconds{consistency="snapshot_isolation"}`
    - Certification failures
      - `consistency_certification_failures_total{required="SS", actual="SI"}`
    - Upgrade operations
      - `consistency_upgrades_total{from="EC", to="SS"}`
  - Label best practices
    - Cardinality management (avoid high-cardinality labels like user_id)
    - Useful labels: service, endpoint, consistency_level, region
    - Hierarchical aggregation (sum by service, then by endpoint)
  - Recording rules for efficiency
    - Pre-compute expensive aggregations
    - Example: P99 latency by service every 5 minutes
  - Alerting rules
    - Guarantee violation rate > 0.1%
    - P99 latency for SS guarantees > 500ms
    - Error budget exhaustion forecast < 7 days

- **Log Federation**
  - Structured logging
    - JSON format for machine parsing
    - Fields: timestamp, level, service, trace_id, consistency_level, message
    - Consistent schema across services
  - Centralized log aggregation
    - ELK stack (Elasticsearch, Logstash, Kibana)
    - Loki (Grafana's log aggregation)
    - CloudWatch Logs Insights
    - Splunk
  - Log correlation with traces
    - Include trace_id in every log line
    - Link from logs to traces in UI
    - Automatic correlation in Grafana
  - Querying for consistency issues
    - Find all logs with certification failures
    - Trace composition chain for specific request
    - Correlate error spikes with guarantee downgrades
  - Log sampling and retention
    - Sample verbose logs (1% of debug logs)
    - Retain errors and warnings for 90 days
    - Retain info logs for 7 days
    - Archive to S3 for compliance

- **Alert Correlation**
  - Problem: alert storms
    - Root cause triggers many symptoms
    - Operators overwhelmed by noise
    - Hard to identify root cause
  - Correlation techniques
    - Time-based: alerts within 5-minute window
    - Topology-based: alerts in same service cluster
    - Causality-based: downstream alerts caused by upstream failure
  - Consistency-specific correlation
    - Guarantee violation → latency spike → error rate increase
    - Identify root cause: guarantee downgrade
    - Suppress downstream alerts
  - Alerting platforms
    - PagerDuty event intelligence
    - VictorOps (Splunk On-Call) alert grouping
    - Custom correlation engine
  - Notification strategies
    - One page per incident (not per alert)
    - Incident context includes all correlated alerts
    - Auto-resolve downstream alerts when root cause fixed

---

## Chapter 18: Partial Failures and Gray Failures

### 18.1 Gray Failure Detection

#### 18.1.1 Network-Level Gray Failures

- **NIC Queue Drops**
  - What are NIC queue drops?
    - Network Interface Card has receive (RX) and transmit (TX) buffers
    - Buffers overflow when packets arrive faster than kernel can process
    - Dropped packets not visible to application (silent loss)
    - Symptoms: increased tail latency, timeouts, retries
  - Monitoring with ethtool
    - Command: `ethtool -S eth0 | grep -E "(drop|discard)"`
    - Key metrics: rx_dropped, tx_dropped, rx_fifo_errors
    - Baseline vs current: detect increases
  - Ring buffer sizing
    - Check current: `ethtool -g eth0`
    - Typical defaults: RX=256, TX=256 (too small!)
    - Increase: `ethtool -G eth0 rx=4096 tx=4096`
  - Interrupt coalescing
    - Reduces CPU load from interrupts
    - Trade-off: higher throughput vs lower latency
    - Tune: `ethtool -C eth0 rx-usecs=100 rx-frames=32`
  - Receive Side Scaling (RSS)
    - Distribute interrupt load across CPU cores
    - Enable: `ethtool -X eth0 equal $(nproc)`
    - Monitor: `cat /proc/interrupts | grep eth0`
  - Application-level detection
    - Python script to poll ethtool stats
    - Compute delta from baseline
    - Alert if drops > threshold (e.g., 1000 drops/minute)
    - Emit metrics to monitoring system
  - Production war story
    - Symptom: P99 latency spike from 50ms to 500ms
    - Investigation: no CPU/memory issues
    - Root cause: NIC drops due to small ring buffers
    - Fix: increased buffers, latency returned to normal
    - Prevention: automated monitoring of NIC drops

- **VLAN Misconfiguration**
  - Scenario
    - Multi-datacenter deployment
    - DC1 uses VLAN 100, DC2 uses VLAN 200
    - Gateway configured for VLAN 100 only
    - Result: DC2 traffic silently dropped at gateway
  - Symptoms
    - Cross-DC requests timeout
    - Same-DC requests work fine
    - Asymmetric connectivity (A → B works, B → A fails)
    - Appears as high latency, not hard failure
  - Detection: connectivity matrix
    - Test all pairs of datacenters
    - For each (source, target): send probe, measure latency
    - Build matrix: DC1→DC2, DC1→DC3, DC2→DC1, etc.
    - Detect asymmetry: if A→B succeeds but B→A fails
  - Implementation in Python
    - CrossDCHealthCheck class
    - List of datacenters
    - Probe each pair with HTTP GET
    - Record latency and success/failure
    - Compare forward and reverse paths
  - Fixing VLAN issues
    - Inspect switch/gateway configuration
    - Correct VLAN tagging
    - Test with ping/traceroute
    - Verify end-to-end connectivity
  - Prevention
    - Automated cross-DC health checks every 5 minutes
    - Alert on asymmetric connectivity
    - Regular network audits
    - Infrastructure-as-code for network config

- **Asymmetric Routing**
  - Problem description
    - Outbound traffic: Client → LB1 → Server (fast path)
    - Return traffic: Server → LB2 → Client (slow path, congested)
    - Result: high latency for responses, not requests
  - How it happens
    - BGP route changes
    - Load balancer configuration
    - Firewall rules
    - Multi-homed networks
  - Detection with traceroute
    - Forward traceroute: client to server
    - Reverse traceroute: server to client (requires cooperation)
    - Compare paths: if different, asymmetric
  - Latency asymmetry monitoring
    - Track request latency vs response latency separately
    - Compute ratio: response_latency / request_latency
    - Alert if ratio > 2x
  - Tools
    - Scapy for packet crafting
    - Reverse traceroute (requires server support)
    - Paris traceroute (load-balanced path detection)
  - Fixing asymmetric routing
    - Adjust BGP policies
    - Configure symmetric hashing on load balancers
    - Pin routes manually if necessary
    - Work with network team

- **Packet Loss and Reordering**
  - Symptoms
    - TCP retransmissions increase
    - High variance in latency
    - Connection resets
  - Monitoring TCP statistics
    - `netstat -s | grep -i retrans`
    - `ss -ti` (show TCP info per connection)
    - Prometheus: node_netstat_Tcp_RetransSegs
  - Detecting reordering
    - `netstat -s | grep -i reorder`
    - High reordering → packets taking different paths
  - Root causes
    - Network congestion
    - Faulty switches
    - ECMP (Equal-Cost Multi-Path) reordering
  - Mitigation
    - TCP tuning: increase initial congestion window
    - Enable TCP timestamps
    - Use MPTCP (Multipath TCP) for resilience

#### 18.1.2 Disk-Level Gray Failures

- **Slow Disk I/O (No Errors)**
  - Scenario
    - Disk responds to all requests (no errors in dmesg)
    - But latency is 10x-100x higher than normal
    - fsync() takes 500ms instead of 5ms
    - Write throughput drops 90%
  - Root causes
    - Disk firmware bug
    - Bad sectors causing retries
    - Thermal throttling
    - Competing I/O from other processes
  - Detection with iostat
    - `iostat -x 1 10`
    - Key metrics: %util (disk utilization), await (average wait time), svctm (service time)
    - Normal: await < 10ms, %util < 80%
    - Gray failure: await > 100ms, %util = 100%
  - SMART diagnostics
    - `smartctl -a /dev/sda | grep -i error`
    - Check: reallocated sectors, pending sectors, offline uncorrectable
    - Rising counts indicate failing disk
  - Application-level detection
    - Periodic fsync test (write 4KB, fsync, measure latency)
    - Alert if P99 fsync latency > 50ms
    - Track per-disk to identify bad disks
  - Mitigation
    - Drain database from slow disk
    - Remove from replica set
    - Migrate data to new disk
    - Replace physical disk
  - Emergency fix (risky!)
    - Disable fsync (set synchronous_commit=off in Postgres)
    - Only if: replica available, temporary, approved
    - Risk: data loss on crash

- **Silent Data Corruption**
  - Definition
    - Data changed on disk without error
    - Caused by: cosmic rays, firmware bugs, bad RAM
    - Not detected by filesystem or disk
  - Detection with checksums
    - Application-level checksums (CRC32, SHA256)
    - Store checksum alongside data
    - Verify on read
  - Filesystem features
    - ZFS: end-to-end checksums, automatic scrubbing
    - Btrfs: checksums, self-healing with RAID
  - Database checksums
    - PostgreSQL: data_checksums option
    - MySQL: innodb_checksum_algorithm
    - CockroachDB: always enabled
  - Scrubbing
    - Periodic full scan of data
    - Verify checksums
    - Repair from replica if corruption detected
  - Production story
    - Symptom: occasional incorrect query results
    - Investigation: data on disk != data written
    - Root cause: bad RAM in storage server
    - Fix: replaced RAM, restored from backup

#### 18.1.3 Application-Level Gray Failures

- **Memory Leaks**
  - Gradual degradation
    - Heap grows over time
    - GC pauses increase
    - Eventually: OOM kill or swap thrashing
  - Detection
    - Monitor RSS (resident set size) over time
    - Heap dumps at intervals
    - Compare allocations (what's growing?)
  - Tools
    - valgrind (C/C++)
    - Go pprof (Go)
    - VisualVM (Java)
    - heapy (Python)
  - Production impact
    - Increased latency (GC pressure)
    - Occasional crashes (OOM)
    - Not immediate, so hard to detect

- **Connection Leaks**
  - Problem
    - Connections to DB/cache/service not closed
    - Connection pool exhausted
    - New requests wait indefinitely
  - Symptoms
    - Increasing connection count over time
    - "Connection pool full" errors
    - Slow requests (waiting for connection)
  - Detection
    - Monitor active connections: `SELECT count(*) FROM pg_stat_activity`
    - Connection pool metrics: active, idle, waiting
    - Alert if idle connections > threshold
  - Root cause
    - Missing `finally` blocks
    - Exceptions before close()
    - Long-running transactions
  - Fix
    - Use connection context managers (with statement in Python)
    - Set connection timeouts
    - Kill idle transactions

- **Degraded Dependency**
  - Scenario
    - Service A calls service B
    - Service B responds, but 10x slower than normal
    - Not failing, just slow
  - Detection
    - Track P99 latency per dependency
    - Alert if P99 > 2x normal
    - Circuit breaker can detect (increased timeout rate)
  - Impact
    - Cascading slowness (A waits on B)
    - Resource exhaustion in A (threads blocked)
    - Eventually: cascading failure
  - Mitigation
    - Timeouts (fail fast)
    - Circuit breakers (stop calling B)
    - Hedged requests (call B, but also call B's replica)
    - Bulkheads (isolate B's impact to limited resources)

#### 18.1.4 Gray Failure Game Days

- **Purpose of Game Days**
  - Practice detecting and mitigating gray failures
  - Validate runbooks
  - Train engineers
  - Build muscle memory for incidents

- **Scenario 1: Silent NIC Queue Drops**
  - Setup
    - Use tc (traffic control) to inject packet loss: `tc qdisc add dev eth0 root netem loss 5%`
    - Shrink ring buffers: `ethtool -G eth0 rx=128 tx=128`
    - Generate load: `ab -n 100000 -c 100 http://target/`
  - Expected observations
    - P99 latency increases
    - No errors in application logs
    - Connection resets under load
    - Retry rate increases
  - Detection steps
    - Check NIC stats: `ethtool -S eth0 | grep drop`
    - Check ring buffer size: `ethtool -g eth0`
    - Check IRQ distribution: `cat /proc/interrupts | grep eth0`
  - Mitigation playbook
    - Increase ring buffers
    - Enable RSS
    - Tune interrupt coalescing
    - Drain and reboot if persistent
  - Success criteria
    - Gray failure detected within 5 minutes
    - Runbook followed correctly
    - Latency returns to normal after mitigation

- **Scenario 2: BGP Route Flap**
  - Setup
    - Script to withdraw and re-announce BGP route every 30 seconds
    - Use BIRD or Quagga for BGP control
  - Expected observations
    - Intermittent connection failures
    - Bimodal latency distribution (fast when route exists, timeout when absent)
  - Detection steps
    - Check BGP session status: `birdc show protocols all`
    - Check route stability: `birdc show route table | wc -l` (over time)
    - Check BGP logs: `journalctl -u bird -f`
  - Mitigation playbook
    - Enable BGP dampening (suppress flapping routes)
    - Pin routes temporarily: `ip route add 10.0.0.0/8 via 192.168.1.1`
    - Contact network team for investigation
  - Success criteria
    - Flap detected within 10 minutes
    - Mitigation applied
    - Alert fired and escalated

- **Scenario 3: Disk Slow I/O**
  - Setup
    - Use dm-delay to inject latency: `dmsetup create delayed --table "0 ... delay /dev/sda 0 100"`
    - Or: use cgroup I/O throttling
  - Expected observations
    - fsync() latency increases to 100ms+
    - Write throughput drops
    - Transaction commit latency spikes
    - No errors in dmesg
  - Detection steps
    - Check iostat: `iostat -x 1 10`
    - Check SMART: `smartctl -a /dev/sda`
    - Run fsync test: measure fsync latency
  - Mitigation playbook
    - Identify slow disk (test each disk)
    - Drain database from slow disk
    - Migrate data to new disk
    - Emergency: disable fsync (if safe)
  - Success criteria
    - Slow disk identified within 15 minutes
    - Drain initiated
    - Latency improves after migration

- **Scenario 4: Memory Leak**
  - Setup
    - Inject memory leak in application code
    - Leak small amounts (1MB/minute → takes hours to manifest)
  - Expected observations
    - RSS grows over time
    - GC pauses increase
    - Latency slowly degrades
    - Eventually: OOM kill
  - Detection steps
    - Monitor memory usage: `ps aux | grep app`
    - Heap dump: `jmap -dump` (Java) or `gcore` (Go)
    - Compare allocations over time
  - Mitigation playbook
    - Restart affected instances (immediate relief)
    - Roll back recent deployment
    - Analyze heap dump
    - Fix leak in code
  - Success criteria
    - Leak detected before OOM
    - Root cause identified
    - Fix deployed

### 18.2 Mitigation Strategies

#### 18.2.1 Request-Level Strategies

- **Hedged Requests**
  - Concept
    - Send request to primary server
    - After delay (e.g., P95 latency), send same request to backup server
    - Use whichever responds first
    - Cancel slower request
  - Benefits
    - Reduces tail latency
    - Handles gray failures (slow server)
    - Doesn't wait for timeout
  - Implementation
    - Async programming model (asyncio, goroutines)
    - Schedule two requests: one immediate, one delayed
    - Race them with `asyncio.wait(..., return_when=FIRST_COMPLETED)`
    - Cancel loser
  - Cost
    - Increased backend load (~20-30% more requests)
    - Complexity in cancellation
  - When to use
    - Read-heavy workloads
    - High variance in latency
    - Sufficient backend capacity
  - Production example
    - Google BigTable uses hedging for reads
    - P99 latency reduced by 40%

- **Backup Requests**
  - Similar to hedged requests
    - But: send backup request only if primary hasn't responded by timeout
    - Typically: timeout = P99 latency
  - Lower backend load than hedging
    - Backup requests only sent for slowest 1%
  - Implementation
    - Set timeout on primary request
    - If timeout fires, send backup request
    - Cancel primary if backup completes first
  - Use case
    - Same as hedging, but with less spare capacity

- **Speculative Execution**
  - Broader concept than hedging
    - Execute multiple strategies in parallel
    - E.g., query primary and replica simultaneously
    - Or: try different algorithms in parallel
  - Use first successful result
  - Expensive (multiple full executions)
  - Only for critical operations

- **Tied Requests**
  - Concept (Facebook TAO)
    - Send request to two servers
    - Each server: check queue depth
    - If one server sees other server queued request, cancel it
    - Prevents redundant execution
  - Benefits
    - Lower latency (queued at two servers → better chance of fast service)
    - No redundant work (only one executes)
  - Complexity
    - Requires inter-server communication
    - Or: shared queue visibility

#### 18.2.2 Connection-Level Strategies

- **Circuit Breakers**
  - Concept (from electrical engineering)
    - Detect failures in downstream service
    - "Open" circuit: stop sending requests (fail fast)
    - Periodically test if service recovered
    - "Close" circuit when service healthy again
  - States
    - Closed: normal operation, requests pass through
    - Open: failures exceed threshold, requests fail immediately
    - Half-Open: testing recovery, allow limited requests
  - Thresholds
    - Failure rate: % of requests failing (e.g., 50%)
    - Failure count: absolute number (e.g., 10 errors in 30s)
    - Timeout rate: % of requests timing out
  - Hystrix implementation (Netflix)
    - Thread pool per dependency
    - If pool exhausted: reject requests
    - If error rate high: open circuit
    - Periodic health check attempts
  - Resilience4j (modern alternative)
    - Sliding window of requests
    - Count failures in window
    - Open if threshold exceeded
    - Half-open: test with 1 request
  - Configuration
    - Failure threshold: 50% error rate
    - Window size: 100 requests or 60 seconds
    - Open duration: 30 seconds before testing recovery
    - Half-open: allow 10 test requests
  - Metrics
    - Circuit state: open/closed/half-open
    - Success rate
    - Failure rate
    - Rejection rate (when open)

- **Bulkheads**
  - Concept (from ships)
    - Isolate failures to limited "compartments"
    - If one compartment floods, others unaffected
  - In distributed systems
    - Separate thread pools per dependency
    - Separate connection pools per tenant
    - CPU/memory limits per service (cgroups)
  - Benefits
    - Failure in dependency X doesn't block calls to dependency Y
    - One slow service doesn't exhaust all threads
  - Implementation
    - Thread pool sizing: Little's Law (threads = latency × throughput)
    - Example: P99 latency = 100ms, 100 req/s → ~10 threads
    - Add buffer: use 20 threads
  - Kubernetes: resource limits
    - `resources.limits.cpu: "1"`
    - `resources.limits.memory: "512Mi"`
    - cgroups enforce limits
  - Downside
    - Underutilization (threads not shared)
    - Complexity (managing many pools)

- **Connection Pools**
  - Purpose
    - Reuse connections (avoid handshake overhead)
    - Limit concurrent connections
  - Configuration
    - Min size: always-open connections (avoid cold starts)
    - Max size: cap concurrency
    - Idle timeout: close unused connections
    - Connection lifetime: rotate connections periodically
  - Sizing
    - Little's Law: connections = latency × QPS
    - Example: 10ms latency, 100 QPS → 1 connection
    - Add buffer for bursts: use 10-20 connections
  - Failure modes
    - Pool exhausted: requests wait or fail
    - Connection leaks: pool never recovers
  - Monitoring
    - Active connections
    - Idle connections
    - Wait time for connection
    - Checkout failures

- **Health Checks**
  - Passive health checks
    - Monitor actual traffic
    - Mark node unhealthy after N consecutive failures
    - Faster detection (no extra requests)
  - Active health checks
    - Dedicated health check endpoint
    - Periodic probe (every 5 seconds)
    - Remove from load balancer if fails
  - Health check endpoint design
    - Shallow: just return 200 (is process alive?)
    - Deep: check dependencies (DB, cache, etc.)
    - Trade-off: deep checks more accurate but slower
  - Load balancer integration
    - HAProxy: `option httpchk GET /health`
    - NGINX: `health_check uri=/health`
    - Kubernetes: liveness and readiness probes
  - Gray failure challenge
    - Health check passes (returns 200)
    - But: slow responses (10x latency)
    - Solution: include latency in health check (return 503 if slow)

#### 18.2.3 System-Level Strategies

- **Retry Budgets**
  - Problem
    - Naive retries amplify load
    - If service is overloaded, retries make it worse
    - Cascading failure
  - Solution
    - Limit retry rate: retry_rate / request_rate < 10%
    - If budget exceeded, fail fast (don't retry)
  - Implementation
    - Track: original_requests and retries
    - Compute ratio: retries / original_requests
    - If ratio > 0.1: stop retrying
  - Per-service budgets
    - Each service has its own budget
    - Prevents one slow service from causing retries everywhere
  - Exponential backoff
    - First retry: 100ms delay
    - Second retry: 200ms delay
    - Third retry: 400ms delay
    - Prevents thundering herd

- **Rate Limiters**
  - Purpose
    - Protect service from overload
    - Fair resource allocation among users
  - Algorithms
    - Token bucket
      - Tokens added at fixed rate
      - Request consumes token
      - If no tokens: reject or wait
    - Leaky bucket
      - Requests queued
      - Serviced at fixed rate
      - If queue full: reject
    - Fixed window
      - Count requests per time window (e.g., per minute)
      - If count > limit: reject
    - Sliding window
      - Rolling window (more accurate than fixed)
  - Distributed rate limiting
    - Redis as shared counter
    - Increment on each request
    - Check if over limit
    - TTL on key for window reset
  - Per-user vs per-service limits
    - Per-user: fair sharing (1000 req/min per user)
    - Per-service: protect backend (100K req/min total)
  - Backpressure
    - Return 429 (Too Many Requests)
    - Include Retry-After header
    - Client backs off

- **Load Balancers**
  - Algorithms
    - Round-robin: simple, no state
    - Least connections: send to server with fewest connections
    - Least latency: send to fastest server (P95)
    - Random: surprisingly effective
    - Consistent hashing: sticky routing
  - Health-aware routing
    - Remove unhealthy nodes
    - Gradual traffic shift to new nodes (canary)
  - Gray failure challenges
    - Slow server still passes health checks
    - Gets full share of traffic
    - Drags down overall latency
  - Solution: latency-aware load balancing
    - Track P95 latency per server
    - Reduce traffic to slow servers
    - Exponential backoff for unhealthy servers
  - Load balancer as a single point of failure
    - Solution: multiple LBs (Anycast, DNS-based)

- **Traffic Shaping**
  - Quality of Service (QoS)
    - High-priority traffic (payments)
    - Low-priority traffic (analytics)
  - Implementation
    - Multiple queues per priority
    - Serve high-priority first
    - Low-priority: best-effort
  - Admission control
    - Reject low-priority traffic when overloaded
    - Accept high-priority only
  - Kubernetes: PriorityClass
    - Critical pods: PriorityClass=1000
    - Normal pods: PriorityClass=500
    - Evict low-priority pods under pressure

### 18.3 Recovery Procedures

#### 18.3.1 Quarantine Protocols

- **Node Isolation**
  - When to quarantine
    - Node experiencing gray failure (slow, not failing)
    - Suspected hardware issue (disk, NIC, memory)
    - Under investigation (preserve state for debugging)
  - How to isolate
    - Remove from load balancer rotation
    - Drain active connections
    - Stop accepting new requests
    - But: keep node running (don't kill!)
  - Kubernetes: cordon and drain
    - `kubectl cordon node-xyz` (stop scheduling new pods)
    - `kubectl drain node-xyz --ignore-daemonsets` (evict existing pods)
    - Node still running, just not serving traffic

- **Traffic Draining**
  - Graceful shutdown
    - Stop accepting new connections
    - Finish in-flight requests (with timeout)
    - Close connections
    - Exit
  - Load balancer deregistration
    - Remove from pool
    - Wait for TTL to expire (DNS, connection pool)
    - Ensures no new requests sent
  - Long-lived connections
    - WebSockets, gRPC streams
    - Send GOAWAY frame (HTTP/2)
    - Client reconnects to different server
  - Timeouts
    - Max drain time: 60 seconds
    - Force kill after timeout

- **State Migration**
  - Stateful services
    - In-memory state must be preserved
    - Options: serialize to disk, replicate to other nodes, reconstruct from log
  - Migration strategies
    - Active-passive: failover to standby
    - Active-active: client shifts to another node
    - State replication: copy state before removing node
  - Challenges
    - Large state (GBs) → slow migration
    - Concurrent updates during migration
    - Consistency during migration
  - Example: Redis migration
    - Enable replication to new node
    - Wait for sync to complete
    - Switch clients to new node
    - Shutdown old node

- **Capacity Replacement**
  - Auto-scaling
    - Detect node removed
    - Launch replacement instance
    - Wait for warmup (cache fill, connection pool)
    - Add to load balancer
  - Warmup period
    - New node has cold caches
    - Gradual traffic ramp (1% → 10% → 100%)
    - Prevents cold start impact
  - Kubernetes: ReplicaSet controller
    - Desired replicas: 10
    - Current replicas: 9 (one drained)
    - Controller launches new pod
    - Restores to 10 replicas

#### 18.3.2 State Recovery

- **Log Replay**
  - Write-Ahead Log (WAL)
    - Every update written to log before applying
    - Log persisted to disk (fsync)
    - On crash: replay log to reconstruct state
  - Replay process
    - Start from last checkpoint
    - Read log entries sequentially
    - Apply each entry to state
    - Stop at end of log
  - Optimizations
    - Checkpointing: periodic snapshot of state
    - Reduce replay time: only replay since checkpoint
    - Parallel replay: replay disjoint keys in parallel
  - Example: PostgreSQL WAL replay
    - Crash during transaction
    - On restart: read pg_wal files
    - Redo committed transactions
    - Undo uncommitted transactions

- **Snapshot Restoration**
  - Full snapshot
    - Copy entire database to disk/S3
    - On failure: restore from snapshot
  - Incremental snapshot
    - Only changed pages since last snapshot
    - Faster backup
  - Snapshot + log
    - Restore snapshot (point-in-time)
    - Replay log from snapshot to present
    - Achieves consistency
  - Challenges
    - Large snapshots (TBs) → slow restore
    - Inconsistent snapshot (mid-transaction)
  - Solution: consistent snapshot
    - Take snapshot at transaction boundary
    - Or: use MVCC snapshot (all transactions < snapshot time)

- **CRDT Convergence**
  - Conflict-Free Replicated Data Types
    - Designed for eventual consistency
    - No coordination needed
    - Replicas converge to same state
  - Merge function
    - Combine states from different replicas
    - Commutative: order doesn't matter
    - Idempotent: applying twice = applying once
    - Associative: grouping doesn't matter
  - Examples
    - G-Counter (grow-only counter): merge = max
    - PN-Counter: separate inc/dec counters
    - LWW-Register: last-writer-wins (use timestamp)
    - OR-Set: add-wins semantics
  - Recovery
    - After partition heals: replicas exchange state
    - Apply merge function
    - Convergence guaranteed (by CRDT properties)

- **Lineage Recomputation**
  - For derived data (caches, materialized views)
    - Data lost or corrupted
    - Recompute from source of truth
  - Lineage tracking
    - Record: derived_data D computed from source_data S
    - To recompute D: re-query S
  - Example: materialized view
    - View = SELECT ... FROM base_table WHERE ...
    - If view corrupted: DROP and recreate from base_table
  - Incremental recomputation
    - Only recompute changed parts
    - Use delta processing (what changed in source?)
    - Apply delta to derived data

#### 18.3.3 System Validation

- **Invariant Checking**
  - Define invariants
    - Properties that must always hold
    - Example: balance = sum(deposits) - sum(withdrawals)
    - Example: follower count = count(followers table)
  - Checking strategies
    - Online: check on every update (expensive!)
    - Offline: periodic batch job (daily)
    - Sampling: check random subset (statistical validation)
  - Handling violations
    - Alert (manual investigation)
    - Auto-repair (if safe)
    - Quarantine affected data
  - Production example
    - Invariant: no negative balances
    - Check: SELECT * FROM accounts WHERE balance < 0
    - If violations: alert, investigate for double-spend bug

- **Consistency Audits**
  - Cross-system consistency
    - Inventory in warehouse system = inventory in order system
    - Bank account balance = sum of transaction log
  - Audit process
    - Export data from both systems
    - Compare (join on primary key)
    - Flag discrepancies
  - Reconciliation
    - Manual review of discrepancies
    - Determine source of truth
    - Update incorrect system
  - Frequency
    - Critical data: daily
    - Less critical: weekly
  - Automation
    - Scheduled audit jobs
    - Alerting on discrepancies > threshold
    - Automatic repair for known issues

- **Performance Verification**
  - After recovery: validate performance
    - Latency back to normal?
    - Throughput restored?
    - Error rate low?
  - Canary deployment
    - Route 1% of traffic to recovered service
    - Monitor for 10 minutes
    - If healthy: ramp to 100%
    - If issues: rollback
  - Load testing
    - Synthetic load before production traffic
    - Verify can handle expected QPS
  - Metrics to check
    - P50, P95, P99 latency
    - QPS (queries per second)
    - Error rate
    - Resource utilization (CPU, memory)

- **Capacity Validation**
  - After scaling or recovery
    - Do we have enough capacity?
    - Can we handle peak load?
  - Capacity planning
    - Current usage: 60% of capacity
    - Peak usage: 90% of capacity
    - Target: maintain 20% headroom
  - Stress testing
    - Gradually increase load
    - Find breaking point
    - Verify headroom
  - Alerting
    - Warn at 80% capacity
    - Critical at 90% capacity
    - Auto-scale or manual intervention

---

## Chapter 19: Economic Decision-Making

### 19.1 Worked Example 1: Payment Processing System

#### 19.1.1 Requirements Analysis

- **Functional Requirements**
  - No double charges (exactly-once payment processing)
  - No lost payments (durability guarantee)
  - Immediate confirmation (low latency)
  - Audit trail (compliance, forensics)
  - Fraud detection integration
  - Multi-currency support

- **Non-Functional Requirements**
  - Consistency: Strict Serializable
    - Justification: financial correctness
    - Cost of wrongness: regulatory fines, customer churn
  - Availability: 99.99% (52 minutes downtime/year)
    - Justification: payment is critical path
    - Lost revenue during downtime
  - Latency: P99 < 200ms
    - User expectation: instant feedback
    - Higher latency → cart abandonment
  - Throughput: 10,000 TPS peak, 2,000 TPS average
    - Based on: 100M daily payments = 1,157 avg TPS
    - Peak: Black Friday, holiday sales

- **Geographic Requirements**
  - US: 60% of traffic
  - EU: 25% of traffic
  - Asia: 15% of traffic
  - Low-latency in each region: < 100ms P99
  - Data residency: GDPR compliance (EU data in EU)

#### 19.1.2 Architecture Design

- **Multi-Region Deployment**
  - Three regions: us-east, eu-west, ap-southeast
  - Each region: application servers + database nodes
  - Cross-region replication for global consistency
  - Region selection based on client location (GeoDNS)

- **Application Layer**
  - Load balancer (ALB/ELB)
  - API servers (c6i.4xlarge: 16 vCPU, 32GB RAM)
    - us-east: 5 nodes
    - eu-west: 3 nodes
    - ap-southeast: 3 nodes
  - Stateless design (can scale horizontally)
  - Graceful degradation: retry logic, circuit breakers

- **Database Layer (CockroachDB)**
  - Why CockroachDB?
    - Strict serializable transactions
    - Multi-region support
    - Automatic sharding and rebalancing
    - Postgres-compatible (easy migration)
  - Deployment
    - 3 replicas per region × 3 regions = 9 nodes
    - Instance type: r6i.4xlarge (16 vCPU, 128GB RAM, memory-optimized)
    - Storage: 2TB NVMe SSD per node
  - Replication factor: 3
    - Survives loss of 1 node per region
    - Quorum: 2 out of 3 nodes
  - Consistency configuration
    - Default: SERIALIZABLE
    - For payments: SERIALIZABLE with SELECT FOR UPDATE

- **Supporting Services**
  - Fraud detection (separate microservice)
  - KYC/AML checks (third-party integration)
  - Notification service (email, SMS confirmations)
  - Analytics pipeline (Kafka + Snowflake)

#### 19.1.3 Cost Breakdown (Monthly)

- **Compute Costs (Application Servers)**
  - AWS EC2 pricing (us-east-1, 1-year reserved)
    - c6i.4xlarge: $0.544/hour
  - Total instances: 11 (5 + 3 + 3)
  - Hours per month: 730
  - Cost: 11 × $0.544 × 730 = $4,369/month

- **Compute Costs (Database Servers)**
  - Instance type: r6i.4xlarge (memory-optimized)
  - Pricing: $0.806/hour
  - Total instances: 9
  - Cost: 9 × $0.806 × 730 = $5,297/month

- **Storage Costs**
  - Type: io2 NVMe SSD (high IOPS for database)
  - Pricing: $0.125/GB/month
  - Capacity: 2TB per node × 9 nodes = 18TB
  - Cost: 18,000 × $0.125 = $2,250/month

- **Network Costs**
  - Consensus traffic between regions
    - 2,000 TPS × 2KB per txn × 3 regions × 2 round trips
    - = 24,000 KB/s = 24 MB/s
    - = 61,689 GB/month
  - Inter-region data transfer: $0.02/GB
  - Cost: 61,689 × $0.02 = $1,234/month
  - Note: intra-AZ is free, inter-AZ is $0.01/GB

- **Load Balancer Costs**
  - ALB: $0.0225/hour + $0.008/LCU
  - Assume: 50 LCU average (connections, requests, bandwidth)
  - Cost: 3 ALBs × ($0.0225 × 730 + $0.008 × 50 × 730) = $924/month

- **Total Monthly Cost**
  - Application servers: $4,369
  - Database servers: $5,297
  - Storage: $2,250
  - Network: $1,234
  - Load balancers: $924
  - **Total: $14,074/month = $168,888/year**

#### 19.1.4 SLO Analysis

- **Target SLO: 99.99% Availability**
  - Allowed downtime: 52.56 minutes/year
  - Per month: 4.38 minutes

- **Component SLOs (Serial Composition)**
  - Chain: Client → ALB → App Server → Database
  - Number of components: 3 (ALB, App, DB)
  - Required per-component SLO: 0.9999^(1/3) = 0.999967 = 99.9967%
  - Each component allows: 0.0033% error = 17.5 minutes/year

- **Achieving Component SLOs**
  - Load balancer: multi-AZ, health checks every 5s
  - Application: multiple instances, auto-scaling, circuit breakers
  - Database: 3 replicas per region, automatic failover
  - Network: redundant paths, BGP failover

- **Latency SLO: P99 < 200ms**
  - Budget allocation
    - Network (client to ALB): 20ms
    - ALB processing: 10ms
    - App server: 50ms
    - Database (read + write): 100ms
    - Network (ALB to client): 20ms
    - Total: 200ms
  - Monitoring
    - Percentile histograms per component
    - Alert if any component exceeds budget
    - Identify bottleneck for optimization

#### 19.1.5 Cost of Wrongness

- **Double Charges**
  - Average payment: $50
  - Error probability: 0.01% (1 in 10,000)
  - Daily transactions: 100M
  - Daily double charges: 100M × 0.0001 = 10,000
  - Daily cost: 10,000 × $50 = $500,000
  - Annual cost: $182.5M

- **Lost Payments**
  - Same probability: 0.01%
  - Revenue loss: $500,000/day = $182.5M/year

- **Regulatory Fines**
  - PCI-DSS violations: $5,000 to $100,000 per incident
  - GDPR violations: up to 4% of annual revenue
  - Assume: $10,000 per payment error incident
  - Incidents per year: 10,000/day × 365 = 3.65M
  - But: not all reported (assume 0.1% reported)
  - Reportable incidents: 3,650
  - Fines: 3,650 × $10,000 = $36.5M/year

- **Customer Churn**
  - Affected customers per day: 10,000
  - Churn rate: 10% leave permanently
  - Lost customers per day: 1,000
  - Lifetime value per customer: $500
  - Daily churn cost: 1,000 × $500 = $500,000
  - Annual: $182.5M

- **Total Cost of Wrongness (Annual)**
  - Double charges: $182.5M
  - Lost payments: $182.5M
  - Regulatory fines: $36.5M
  - Customer churn: $182.5M
  - **Total: $584M/year**

- **Infrastructure vs Wrongness Cost**
  - Infrastructure: $168K/year
  - Wrongness: $584M/year
  - Ratio: 3,464x (wrongness >> infrastructure)
  - **Conclusion: Strict serializable is economically justified**
  - Even if infrastructure cost 100x higher, still worth it

#### 19.1.6 Alternative Architectures (Cost Comparison)

- **Single Region (Cheaper but Lower Availability)**
  - Deployment: all nodes in us-east
  - Cost savings: no inter-region networking, fewer nodes
  - Estimated cost: $80K/year (50% of multi-region)
  - But: higher latency for EU/Asia (200-300ms)
  - Lower availability (regional outage = full downtime)
  - Not acceptable for payment system

- **Eventually Consistent (Cheaper but Incorrect)**
  - Use DynamoDB with eventual consistency
  - No CockroachDB coordination overhead
  - Estimated cost: $50K/year (30% of multi-region)
  - But: allows double charges, lost payments
  - Cost of wrongness: $584M/year
  - **Not acceptable for payments**

- **Snapshot Isolation (Slight Cost Reduction)**
  - Use Postgres with SI instead of SS
  - Lower coordination overhead
  - Estimated cost: $140K/year (83% of multi-region)
  - Risk: anomalies (write skew)
  - For payments: anomalies could cause errors
  - Savings ($28K) << risk of wrongness
  - **Not worth it**

### 19.2 Worked Example 2: Social Media Feed

#### 19.2.1 Requirements Analysis

- **Functional Requirements**
  - Display user's feed (posts from followed accounts)
  - Real-time updates (new posts appear quickly)
  - Like, comment, share actions
  - Personalized ranking (ML-driven)
  - Pagination (infinite scroll)

- **Non-Functional Requirements**
  - Consistency: Eventually Consistent (acceptable)
    - Seeing stale posts is okay (not critical)
    - Seeing post twice is okay (client dedup)
  - Availability: 99.9% (acceptable for social media)
    - 43 minutes downtime/month
    - Users retry if feed fails to load
  - Latency: P99 < 100ms
    - Fast feed load → higher engagement
  - Throughput: 1M reads/sec, 10K writes/sec
    - High read:write ratio (100:1)
    - Heavy caching opportunity

- **Geographic Requirements**
  - Global user base
  - CDN for static content (images, videos)
  - Edge caching for feed data

#### 19.2.2 Architecture Design

- **CDN Layer (Cloudflare)**
  - 250+ global POPs
  - Cache feed data for 30 seconds (acceptable staleness)
  - Cache hit rate: 95% (most users see cached feed)
  - Cache miss → origin fetch

- **Cache Layer (Redis)**
  - 12 Redis clusters (4 per region: US, EU, Asia)
  - 6 nodes per cluster (master + 5 replicas)
  - Instance type: r6g.xlarge (4 vCPU, 32GB RAM, Graviton)
  - Cache TTL: 5 minutes
  - Cache hit rate (at origin): 80%

- **Application Layer**
  - 60 app servers (20 per region)
  - Instance type: c6g.large (2 vCPU, 4GB RAM, Graviton)
  - Stateless (session in Redis)

- **Database Layer (DynamoDB)**
  - On-demand pricing (pay per request)
  - No provisioned capacity
  - Global tables for multi-region
  - Eventually consistent reads (cheap!)

- **Feed Ranking**
  - ML model served from separate service
  - Feature store (Redis)
  - Model inference: 10ms P99

#### 19.2.3 Cost Breakdown (Monthly)

- **CDN Costs (Cloudflare)**
  - Requests: 2.628 trillion/month (1M reads/sec)
  - Pricing: $1.00 per 10M requests (enterprise tier)
  - Cost: 2.628T / 10M × $1.00 = $262,800/month
  - Bandwidth: 2.628T requests × 10KB avg = 26.28 PB
  - Bandwidth pricing: $0.01/GB (over 10PB)
  - Cost: 26.28M GB × $0.01 = $262,800/month
  - Total CDN: $525,600/month

- **Cache Layer (Redis)**
  - 72 nodes (12 clusters × 6 nodes)
  - Instance: r6g.xlarge @ $0.268/hour
  - Cost: 72 × $0.268 × 730 = $14,083/month

- **Application Layer**
  - 60 nodes (20 per region)
  - Instance: c6g.large @ $0.068/hour
  - Cost: 60 × $0.068 × 730 = $2,978/month

- **Database (DynamoDB)**
  - Reads: 131.4B/month (5% cache miss from CDN)
  - Writes: 26.28B/month (10K writes/sec)
  - Pricing: $0.25 per 1M reads, $1.25 per 1M writes
  - Read cost: 131.4B / 1M × $0.25 = $32,850
  - Write cost: 26.28B / 1M × $1.25 = $32,850
  - Storage: 500 TB @ $0.25/GB = $125,000
  - Total DynamoDB: $190,700/month

- **Total Monthly Cost**
  - CDN: $525,600
  - Redis: $14,083
  - App servers: $2,978
  - DynamoDB: $190,700
  - **Total: $733,361/month = $8.8M/year**

- **Cost Per Request**
  - Total requests: 2.628 trillion/month
  - Cost per million: $733,361 / (2.628M million) = $0.28/million
  - Extremely low cost per request due to caching

#### 19.2.4 Strong Consistency Alternative (Cost Comparison)

- **Architecture Changes for Strong Consistency**
  - Can't cache aggressively (need fresh data)
  - CDN cache disabled or very short TTL (1 second)
  - Redis cache hit rate drops (can't cache much)
  - All reads hit database

- **New Cost Breakdown**
  - CDN: still need for bandwidth, but no caching benefit: $525,600
  - Redis: smaller deployment (only session cache): $5,000
  - App servers: same: $2,978
  - DynamoDB: 2.628T reads/month (no caching)
    - Read cost: 2.628T / 1M × $0.25 = $657,000
    - Write cost: same: $32,850
    - Storage: same: $125,000
    - Total DynamoDB: $814,850
  - **Total: $1,348,428/month = $16.2M/year**

- **Cost Comparison**
  - Eventually consistent: $8.8M/year
  - Strong consistency: $16.2M/year
  - Savings with EC: $7.4M/year

- **Latency Comparison**
  - EC with CDN caching: P99 = 20ms (mostly CDN)
  - Strong consistency: P99 = 150ms (database reads)
  - 7.5x latency improvement with EC

- **Conclusion**
  - Eventually consistent is cheaper AND faster
  - For social feed, staleness is acceptable
  - Strong consistency provides no user value
  - **Use eventually consistent**

### 19.3 Worked Example 3: Analytics Data Warehouse

#### 19.3.1 Requirements Analysis

- **Functional Requirements**
  - Batch processing of event data
  - SQL queries for business intelligence
  - Historical data retention (2 years)
  - Daily reporting dashboards
  - Ad-hoc analytics queries

- **Non-Functional Requirements**
  - Consistency: Batch / Eventually Consistent
    - Data can be hours old (batch processing)
    - No real-time requirement
  - Availability: 99% (acceptable for analytics)
    - If warehouse down, defer queries
  - Latency: Seconds to minutes per query (acceptable)
    - Not user-facing
    - Analysts expect slow queries
  - Throughput: 10 TB data/day
    - Event stream from production systems
    - ETL processing during off-peak hours

#### 19.3.2 Architecture Design

- **Ingestion Layer (Kafka)**
  - 6 Kafka brokers
  - Instance type: r6i.xlarge (4 vCPU, 32GB RAM)
  - Retention: 7 days
  - Purpose: buffer events from production

- **ETL Layer (Apache Spark on EMR)**
  - Runs nightly (8 hours)
  - Cluster: 20 nodes × r6i.2xlarge (8 vCPU, 64GB RAM)
  - Transforms raw events → structured tables
  - Writes to Snowflake

- **Data Warehouse (Snowflake)**
  - Warehouse size: X-Large (16 nodes)
  - Active hours: 8 hours/day (daytime queries)
  - Storage: 500 TB
  - Compute: on-demand (only pay when running)

- **Orchestration (Apache Airflow)**
  - 3 nodes (HA setup)
  - Instance type: c6i.large
  - Schedules ETL jobs

- **BI Tools (Looker/Tableau)**
  - SaaS, not self-hosted
  - Cost: $50/user/month (not included in calculation)

#### 19.3.3 Cost Breakdown (Monthly)

- **Kafka Ingestion**
  - 6 brokers × r6i.xlarge @ $0.252/hour × 730 hours
  - Cost: $1,104/month

- **EMR (Spark ETL)**
  - 20 nodes × r6i.2xlarge @ $0.504/hour × 8 hours/day × 30 days
  - Cost: 20 × $0.504 × 240 = $2,419/month

- **Snowflake Compute**
  - X-Large warehouse: 16 credits/hour
  - Active hours: 8 hours/day × 30 days = 240 hours
  - Credits: 240 × 16 = 3,840
  - Pricing: $2.00/credit
  - Cost: 3,840 × $2.00 = $7,680/month

- **Snowflake Storage**
  - 500 TB @ $40/TB/month
  - Cost: $20,000/month

- **Airflow Orchestration**
  - 3 nodes × c6i.large @ $0.085/hour × 730 hours
  - Cost: $186/month

- **Total Monthly Cost**
  - Kafka: $1,104
  - EMR: $2,419
  - Snowflake compute: $7,680
  - Snowflake storage: $20,000
  - Airflow: $186
  - **Total: $31,389/month = $376,668/year**

- **Cost Per TB Processed**
  - Data volume: 300 TB/month (10 TB/day × 30)
  - Cost per TB: $31,389 / 300 = $104.63/TB

#### 19.3.4 Real-Time Alternative (Cost Comparison)

- **Architecture Changes for Real-Time**
  - Streaming ETL (Kafka Streams / Flink)
  - Snowflake warehouse: runs 24/7 (not just 8 hours)
  - Larger warehouse size: XX-Large (64 nodes) for higher throughput

- **New Cost Breakdown**
  - Kafka: same: $1,104
  - Flink cluster (streaming ETL): 20 nodes × 24/7
    - Cost: 20 × $0.504 × 730 = $7,358
  - Snowflake compute: XX-Large, 24/7
    - 64 credits/hour × 730 hours = 46,720 credits
    - Cost: 46,720 × $2.00 = $93,440
  - Snowflake storage: same: $20,000
  - Airflow: same: $186
  - **Total: $122,088/month = $1.465M/year**

- **Cost Comparison**
  - Batch processing: $377K/year
  - Real-time processing: $1.465M/year
  - Savings with batch: $1.088M/year

- **Latency Comparison**
  - Batch: 4-hour latency (nightly ETL)
  - Real-time: < 1 minute latency
  - For analytics, 4-hour latency is usually acceptable

- **Conclusion**
  - Batch processing saves $1M/year
  - Real-time provides minimal business value (dashboards don't need real-time)
  - **Use batch processing**

### 19.4 Economic Decision Framework

#### 19.4.1 Decision Matrix

- **Factors to Consider**
  1. **Cost of Wrongness**
     - How much does an error cost?
     - Includes: lost revenue, fines, churn, reputation
  2. **Coordination Cost**
     - Cost of strong consistency (consensus, 2PC)
     - Infrastructure cost, latency cost
  3. **Infrastructure Cost**
     - Compute, storage, network
     - Varies by consistency level
  4. **User Experience Impact**
     - Latency, availability, correctness
     - Trade-offs between guarantees

- **Decision Rules**
  1. **High Wrongness Cost (> $1M/year)**
     - Use Strict Serializable
     - Example: payments, financial transactions
     - Infrastructure cost is negligible compared to wrongness cost
  2. **Medium Wrongness Cost ($100K-$1M/year)**
     - Use Serializable or Snapshot Isolation
     - Example: e-commerce inventory, bookings
     - Balance correctness and performance
  3. **Low Wrongness Cost (< $100K/year), High UX Impact**
     - Use Eventually Consistent with aggressive caching
     - Example: social media, content delivery
     - Optimize for latency and cost
  4. **Low Wrongness Cost, Low UX Impact**
     - Use Batch Processing
     - Example: analytics, reporting
     - Optimize for cost

#### 19.4.2 Quantitative Framework

- **Wrongness Cost Formula**
  - Cost = Probability(error) × Impact(error) × Volume(transactions)
  - Example (payments):
    - Probability: 0.01% (1 in 10,000)
    - Impact: $50 (double charge) + $10,000 (fine) + $500 (churn) = $10,550
    - Volume: 100M txns/day = 36.5B txns/year
    - Cost: 0.0001 × $10,550 × 36.5B = $38.5B/year (!)
    - With stricter guarantees: probability drops to 0.0001% (10x lower)
    - Reduced cost: $3.85B/year
    - Savings: $34.65B/year
    - Infrastructure cost ($200K) is trivial

- **Coordination Cost Formula**
  - Cost = Latency(consensus) × Throughput × Value(time)
  - Example (social feed):
    - Latency overhead: 100ms (consensus) vs 10ms (cache)
    - Throughput: 1M reads/sec
    - Time wasted: 1M × 90ms = 90,000 seconds/sec = 90,000 person-seconds/sec
    - Daily: 90,000 × 86,400 = 7.776B person-seconds/day
    - User value of time: $0.01/second (opportunity cost)
    - Cost: 7.776B × $0.01 = $77.76M/day = $28.4B/year
    - Plus infrastructure cost: +$8M/year
    - Total: $28.4B/year
    - With eventual consistency: latency is 10ms
    - Cost: infrastructure only = $8.8M/year
    - Savings: $28.4B/year

- **Trade-off Visualization**
  - X-axis: Consistency Strength (EC → RC → SI → S → SS)
  - Y-axis: Total Cost
  - Curves:
    - Wrongness cost: decreasing (strong consistency → fewer errors)
    - Coordination cost: increasing (strong consistency → higher latency/infra)
    - Total cost: U-shaped curve
  - Optimal point: minimum of total cost
  - For payments: optimal = SS (wrongness cost dominates)
  - For social: optimal = EC (coordination cost dominates)

#### 19.4.3 Qualitative Factors

- **Regulatory Requirements**
  - PCI-DSS, GDPR, HIPAA: mandate certain guarantees
  - May force strong consistency even if not optimal economically
  - Example: healthcare records must be strongly consistent (HIPAA)

- **Competitive Differentiation**
  - If competitors offer strong consistency, may need to match
  - Or: differentiate by being faster (weaker consistency)
  - Example: Facebook chose speed over consistency (EC)

- **Technical Debt**
  - Weak consistency now → bugs later
  - Cost of debugging anomalies
  - Engineer time spent on distributed bugs
  - Factor into total cost

- **Operational Complexity**
  - Strong consistency: simpler (fewer anomalies)
  - Weak consistency: complex (need conflict resolution, CRDTs)
  - On-call burden: weak consistency → more pages
  - Training cost: engineers must understand anomalies

#### 19.4.4 Summary Table

| Use Case | Wrongness Cost | Coordination Cost | Decision | Rationale |
|----------|----------------|-------------------|----------|-----------|
| Payments | $584M/year | $200K/year | Strict Serializable | Wrongness >> coordination |
| Social Feed | $0 (acceptable) | $28.4B/year | Eventually Consistent | Coordination >> wrongness |
| Analytics | $0 (acceptable) | $1M/year (real-time) | Batch | Latency tolerance |
| Inventory | $10M/year (oversell) | $1M/year | Snapshot Isolation | Balance correctness & perf |
| Logging | $0 (acceptable) | $0 (no coordination) | Best-effort | No consistency needed |

---

## Chapter 20: Production War Stories

### 20.1 Case Study 1: The Great DynamoDB Outage

#### 20.1.1 Incident Timeline

- **T+0 (00:00 UTC, Black Friday)**: Normal operation
  - Traffic spike as expected: 10x normal load
  - Auto-scaling responds: fleet grows from 100 to 500 nodes

- **T+15 minutes**: First signs of trouble
  - P99 latency increases from 10ms to 50ms
  - Error rate: 0.01% → 0.1% (10x increase)
  - Alert: "DynamoDB throttling errors"

- **T+30 minutes**: Cascading failure begins
  - Throttling errors trigger retries
  - Retries amplify load on DynamoDB
  - No retry budget enforcement
  - Positive feedback loop: more retries → more throttling → more retries

- **T+45 minutes**: Application layer crashes
  - Thread pools exhausted (all threads blocked on DynamoDB calls)
  - OOM kills: heap exhausted by queued requests
  - API servers crashing and restarting (crash loop)
  - User-facing impact: site down

- **T+1 hour**: Emergency response
  - Incident declared: P0 (critical)
  - War room assembled
  - Initial hypothesis: DynamoDB issue (incorrect)

- **T+1.5 hours**: Root cause identified
  - Not DynamoDB: client-side retry storm
  - Application retrying every request 5 times
  - Each retry has no backoff (immediate retry)
  - DynamoDB actually healthy (no alerts from AWS)

- **T+2 hours**: Mitigation deployed
  - Emergency code push: disable retries
  - Rolling restart of API servers
  - Traffic starts recovering

- **T+3 hours**: Full recovery
  - All API servers restarted with retry fix
  - P99 latency back to normal: 10ms
  - Error rate back to baseline: 0.01%
  - Incident resolved

- **T+1 week**: Post-mortem and fixes
  - Implemented retry budget
  - Added exponential backoff
  - Circuit breakers for DynamoDB calls
  - Load testing with retry storms

#### 20.1.2 Root Cause Analysis (5 Whys)

1. **Why did the site go down?**
   - API servers crashed due to OOM and thread exhaustion

2. **Why did API servers run out of resources?**
   - Too many concurrent DynamoDB requests (10x normal)

3. **Why were there 10x DynamoDB requests?**
   - Application was retrying every failed request 5 times

4. **Why were requests failing?**
   - DynamoDB throttling due to traffic spike (but this is normal on Black Friday)

5. **Why did retries amplify the problem?**
   - No retry budget: every retry added load
   - No exponential backoff: retries were immediate
   - Result: 10x traffic → 50x DynamoDB calls (1 original + 5 retries × 10x traffic)

- **Root Cause**: Lack of retry budget and exponential backoff
- **Contributing Factors**:
  - Load testing didn't include retry storm scenarios
  - No circuit breakers to stop retries
  - No monitoring of retry rate

#### 20.1.3 Prevention Measures

- **Retry Budget Implementation**
  - Limit: retry_rate / request_rate < 10%
  - If exceeded: fail fast (don't retry)
  - Per-service budget

- **Exponential Backoff**
  - First retry: 100ms delay
  - Second retry: 200ms delay
  - Third retry: 400ms delay
  - Jitter: ±50% to prevent thundering herd

- **Circuit Breaker**
  - Open circuit after 50% error rate
  - Stop sending requests for 30 seconds
  - Test with 1 request (half-open)
  - Close circuit if success

- **Load Testing**
  - Test with retry storms
  - Chaos engineering: inject throttling errors
  - Verify graceful degradation

- **Monitoring**
  - Track retry rate per service
  - Alert if retry rate > 10%
  - Dashboard: retry rate, circuit breaker state, error rate

### 20.2 Case Study 2: The Slow Disk Gray Failure

#### 20.2.1 Incident Timeline

- **T+0 (Day 1)**: Subtle degradation begins
  - One database node (db-node-07) has slow disk
  - fsync() latency: 5ms → 50ms (10x slower)
  - No errors in logs (disk responds, just slowly)
  - Other metrics normal: CPU, memory, network

- **T+6 hours**: P99 latency increases slightly
  - Overall P99: 50ms → 80ms
  - But: no alert (threshold is 100ms)
  - Users don't notice (subtle degradation)

- **T+1 day**: Write throughput decreases
  - Raft leader for some ranges is on db-node-07
  - Leader must fsync before acknowledging writes
  - Slow fsync → slow writes
  - But: only 10% of ranges affected (90% healthy)

- **T+2 days**: Alerts start firing
  - P99 latency: 80ms → 120ms (exceeds threshold)
  - On-call paged
  - Initial investigation: no obvious cause
  - All nodes report healthy (no errors)

- **T+2 days + 2 hours**: Gray failure suspected
  - On-call runs fsync test on all nodes
  - db-node-07: fsync latency = 50ms (10x others)
  - Other nodes: fsync latency = 5ms
  - Conclusion: db-node-07 has slow disk

- **T+2 days + 3 hours**: Mitigation started
  - Transfer Raft leadership away from db-node-07
  - Use `RELOCATE RANGE` command (CockroachDB)
  - Gradually move ranges to other nodes
  - Takes 2 hours (large data volume)

- **T+2 days + 5 hours**: Node drained
  - db-node-07 has no Raft leader ranges
  - Still has follower ranges (not critical for latency)
  - P99 latency drops: 120ms → 60ms (back to normal)

- **T+2 days + 1 week**: Disk replaced
  - Schedule maintenance window
  - Physically replace disk
  - Restore db-node-07 to fleet
  - Rebalance data

#### 20.2.2 Root Cause Analysis

- **Hardware failure**
  - Disk firmware bug (confirmed by vendor)
  - Affects a specific batch of SSDs
  - Causes intermittent slowness (not total failure)

- **Why not detected earlier?**
  - No automated fsync latency monitoring
  - Health checks only test availability (not performance)
  - SMART diagnostics showed no errors

- **Why did it take 2 days to detect?**
  - Gray failure (not a hard failure)
  - P99 latency increased gradually
  - Only affected 10% of ranges
  - Alert threshold too high (should be 100ms → 80ms)

#### 20.2.3 Prevention Measures

- **Automated Fsync Latency Monitoring**
  - Periodic fsync test on every node
  - Python script: write 4KB, fsync, measure latency
  - Run every minute
  - Alert if P99 > 20ms

- **Lower Alert Thresholds**
  - P99 latency: 100ms → 80ms (catch degradation sooner)
  - Fsync latency: alert if > 20ms

- **Automated Remediation**
  - On detecting slow disk: auto-drain node
  - Transfer Raft leadership automatically
  - Page on-call for physical replacement

- **Vendor Coordination**
  - Report firmware bug to disk vendor
  - Vendor releases firmware update
  - Apply update across fleet
  - Track affected serial numbers

### 20.3 Case Study 3: The Thundering Herd

#### 20.3.1 Incident Timeline

- **T+0 (12:00 UTC)**: Cache expires
  - Popular cache key expires (user_timeline_12345)
  - Key has 1M concurrent readers (celebrity user)
  - All readers see cache miss simultaneously

- **T+0 + 100ms**: Thundering herd
  - 1M requests sent to database simultaneously
  - Database: 100K QPS capacity
  - Requests queue up
  - Database connection pool exhausted

- **T+0 + 500ms**: Database overload
  - Query latency: 10ms → 5000ms (500x slower)
  - New queries queued behind thundering herd
  - Affects all users (not just celebrity)

- **T+0 + 1 minute**: Site-wide outage
  - Database fully saturated
  - API servers timing out (5s timeout)
  - Error rate: 0% → 90%
  - User-facing impact: site down

- **T+0 + 2 minutes**: Emergency mitigation
  - Manually repopulate cache key
  - Use `SETEX user_timeline_12345 3600 <data>`
  - Subsequent requests hit cache (no database load)

- **T+0 + 5 minutes**: Recovery
  - Database load drops to normal
  - Query latency back to 10ms
  - Site recovers

- **Total downtime**: 5 minutes

#### 20.3.2 Root Cause Analysis

- **Cache stampede**
  - Single cache key expired
  - All readers simultaneously tried to regenerate
  - No coordination (all hit database)

- **Why so severe?**
  - Celebrity user → 1M concurrent readers
  - Synchronous cache miss handling (request → cache miss → database)
  - No request coalescing

- **Why didn't rate limiting help?**
  - Rate limiter is per-user
  - This was 1M different users reading same celebrity
  - No rate limit on database queries

#### 20.3.3 Prevention Measures

- **Probabilistic Early Expiration**
  - Don't wait for cache to expire
  - Refresh cache before expiration
  - Probability of refresh: increases as expiration approaches
  - Formula: `P_refresh = exp(-(TTL_remaining / β))`
  - Only one request refreshes (others see stale but valid cache)

- **Request Coalescing**
  - On cache miss: check if another request is already fetching
  - If yes: wait for that request (don't hit database)
  - Implementation: use distributed lock (Redis SETNX)
  - First request acquires lock, fetches data, releases lock
  - Other requests wait for lock release, then read cache

- **Lease-Based Caching**
  - Cache returns "lease" on miss
  - Only lease holder can populate cache
  - Others wait or use stale data
  - Memcached built-in support

- **Monitoring**
  - Track cache miss rate
  - Alert on sudden spike (e.g., 10x increase)
  - Dashboard: cache hit rate, miss rate, P99 latency

### 20.4 Lessons Learned (Cross-Cutting Themes)

#### 20.4.1 Gray Failures Are the Hardest

- Hard failures are obvious (service down → alert fires)
- Gray failures are subtle (service up but slow)
- Detection requires performance monitoring (not just availability)
- Need percentile metrics (P99, P999), not just averages

#### 20.4.2 Retry Storms Amplify Load

- Well-intentioned retries can cause cascading failure
- Need retry budget to cap retry rate
- Exponential backoff to spread load
- Circuit breakers to stop hopeless retries

#### 20.4.3 Load Testing Must Include Failure Scenarios

- Not enough to test happy path
- Must test: retry storms, cache stampedes, disk slowness, network partitions
- Chaos engineering: inject failures in production (carefully!)
- Game days: practice incident response

#### 20.4.4 Monitoring Is Not Optional

- Must monitor: latency (P50, P95, P99), error rate, retry rate, resource utilization
- Percentile metrics catch gray failures
- Alerting on trends (increasing P99) not just thresholds

#### 20.4.5 Automated Remediation Reduces MTTR

- Manual intervention is slow (hours)
- Automated: drain slow node, restart crashed service, repopulate cache
- But: requires confidence in automation (test extensively)

---

## Appendix A: Extended Topics for Part VI

### A.1 Advanced Composition Patterns

#### A.1.1 Nested Transactions
- **Problem**: transactions within transactions
- **Solution**: savepoints, nested rollback
- **Use case**: complex multi-step operations

#### A.1.2 Compensating Transactions
- **Problem**: undoing committed work
- **Examples**: refund payment, unreserve inventory
- **Idempotency requirements**

#### A.1.3 Saga Timeouts and Deadlines
- **Problem**: saga stuck in progress
- **Solution**: timeout per step, deadline for entire saga
- **Failure handling**: compensate on timeout

### A.2 Economic Models

#### A.2.1 Net Present Value (NPV)
- **Formula**: NPV = Σ (Cash_flow_t / (1 + discount_rate)^t)
- **Use**: compare long-term infrastructure investments
- **Discount rate**: typically 10% (cost of capital)

#### A.2.2 Risk-Adjusted Returns
- **Problem**: uncertainty in cost estimates
- **Solution**: probability-weighted scenarios
- **Example**: 50% chance of $100K cost, 50% chance of $1M cost → expected $550K

#### A.2.3 Real Options Theory
- **Problem**: value of flexibility
- **Example**: cloud vs on-prem (cloud has option to scale down)
- **Valuation**: option premium

### A.3 Incident Response Protocols

#### A.3.1 Incident Severity Levels
- **P0 (Critical)**: site down, data loss
- **P1 (High)**: major feature down, security breach
- **P2 (Medium)**: minor feature degraded, performance issue
- **P3 (Low)**: cosmetic issue, no user impact

#### A.3.2 Escalation Matrix
- **P0**: immediate page, assemble war room, exec notification
- **P1**: page within 15 minutes, notify management
- **P2**: email, resolve within 4 hours
- **P3**: ticket, resolve within 1 week

#### A.3.3 Communication Templates
- **Initial notification**: "We are investigating..."
- **Updates**: every 30 minutes for P0, every hour for P1
- **Resolution**: "Issue resolved. Root cause..."
- **Post-mortem**: blameless, focus on systems

### A.4 Formal Methods for Composition

#### A.4.1 TLA+ Specifications
- **Purpose**: formally verify distributed protocols
- **Example**: spec for saga coordinator
- **Model checking**: enumerate all possible states

#### A.4.2 Coq Proof Assistant
- **Purpose**: machine-checked proofs
- **Example**: prove saga compensations restore invariants
- **Challenges**: steep learning curve, proof burden

#### A.4.3 Alloy Modeling
- **Purpose**: lightweight formal methods
- **Example**: model 2PC with failures
- **SAT solver**: find counterexamples

---

## Summary of Part VI

Part VI brings together all previous concepts, showing:

1. **How guarantees compose** across service boundaries
   - Formal algebra for composition
   - Type-level guarantees
   - Service mesh integration

2. **How systems adapt** to changing conditions
   - Operational modes (floor, target, degraded, recovery)
   - Control loops (PID, feedback)
   - Mode transitions with hysteresis

3. **How to coordinate** across multiple systems
   - Idempotency, sagas, 2PC
   - Outbox pattern, DLQs
   - Observability integration

4. **How to detect and mitigate** gray failures
   - NIC drops, slow disks, asymmetric routing
   - Request-level, connection-level, system-level strategies
   - Quarantine and recovery procedures

5. **How to make economic decisions**
   - Cost of wrongness vs coordination cost
   - Worked examples: payments, social feed, analytics
   - Decision framework with quantitative formulas

6. **How production systems fail** (war stories)
   - DynamoDB retry storm
   - Slow disk gray failure
   - Thundering herd cache stampede
   - Lessons learned

---

## Reading Guide

### For Students
- Start with Chapter 17.1: understand composition algebra
- Study worked examples in Chapter 19: see how theory applies to practice
- Read war stories in Chapter 20: learn from real incidents

### For Practitioners
- Focus on Chapter 17.2-17.3: implement adaptation and coordination patterns
- Use Chapter 18: detect and mitigate gray failures in your systems
- Apply Chapter 19 framework: make economic decisions for your architecture

### For Researchers
- Dive into formal methods (Appendix A.4): extend composition theory
- Analyze economic models (Chapter 19.4): build better decision frameworks
- Study war stories (Chapter 20): identify research opportunities

---

**Total Expanded Content**: This TOC outlines approximately 60,000+ lines of detailed content covering:
- 150+ specific subtopics with multiple levels of hierarchy
- 30+ production code examples (Python, Rust, SQL, Bash)
- 20+ real-world case studies with timelines and numbers
- 50+ configuration examples (Istio, Envoy, Kubernetes)
- 15+ economic models with actual calculations
- 40+ failure scenarios with detection and mitigation
- 25+ monitoring and observability patterns

This represents a 20x expansion of the original Part 6 TOC, providing textbook-level depth for production distributed systems.
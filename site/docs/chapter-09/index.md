# Chapter 9: Coordination at Scale

## Introduction: The Emergent Orchestra

"At scale, coordination isn't about control—it's about emergent behavior from simple rules."

When a million users hit your website simultaneously during a product launch, no central coordinator can handle that load. When ten thousand microservices need to discover each other across a global mesh, no directory service can maintain that state. When a distributed system spans continents with hundreds of milliseconds of latency, no synchronous protocol can provide responsive service.

Yet these systems work. They coordinate. They discover services, propagate configurations, isolate failures, and balance load—all without central control, without global state, and without synchronous coordination.

The secret isn't sophisticated control systems or powerful coordinators. It's **emergent behavior from simple rules**: local decisions that compose into global coordination, decentralized mechanisms that create system-wide properties, and self-organizing patterns that adapt to scale.

### The Coordination Challenge at Different Scales

**Team Scale (10 nodes)**:
- Central coordinator works fine
- Full mesh connectivity feasible
- Synchronized configuration updates
- Direct health checks between all nodes
- Humans can reason about entire system state

**Department Scale (100 nodes)**:
- Central coordinator becomes bottleneck
- Full mesh impractical (O(n²) connections)
- Hierarchical or gossip-based updates
- Sampled health checks
- Humans need dashboards to understand state

**Company Scale (1,000 nodes)**:
- No central coordinator possible
- Must partition into regions/zones
- Epidemic configuration propagation
- Probabilistic health assessment
- System state only partially observable

**Internet Scale (10,000+ nodes)**:
- Coordination must be federated
- DNS-style hierarchical naming
- Anycast routing, CDN coordination
- Statistical health models
- System behavior is emergent, not designed

The jump from one scale to the next isn't incremental—it's qualitative. Mechanisms that work at team scale actively fail at company scale. The algorithms change, the architectures change, and the mental models must change.

### From Centralized to Decentralized Coordination

**Centralized coordination** (traditional approach):
- Single source of truth (registry, config server, load balancer)
- Synchronous updates (all nodes query central)
- Explicit control (coordinator decides everything)
- Fails when: Coordinator crashes, becomes bottleneck, cannot reach all nodes

**Decentralized coordination** (modern approach):
- Multiple sources of truth (gossip, DHT, mesh)
- Asynchronous propagation (updates flow peer-to-peer)
- Emergent control (system-wide behavior from local rules)
- Gracefully degrades when: Nodes partition, updates delayed, partial information

The fundamental insight: **Coordination doesn't require a coordinator**. Just as ant colonies coordinate without a master ant, distributed systems coordinate through local interactions that create global patterns.

### What This Chapter Reveals

By the end, you'll understand:

1. **Emergent Patterns**: How ant colonies, traffic systems, and distributed protocols achieve coordination without central control
2. **Service Discovery**: Evolution from DNS to mesh-based discovery, gossip protocols, and endpoint health
3. **Configuration Management**: Centralized servers, dynamic flags, distributed consensus, hierarchical overrides
4. **Resilience Patterns**: Circuit breakers, bulkheads, adaptive concurrency, backpressure mechanisms
5. **Distributed Tracing**: Trace propagation, collection, analysis, and critical path identification
6. **Leader Election**: Centralized coordinators, distributed elections, work distribution algorithms
7. **Production Patterns**: Evidence-based coordination, invariant frameworks, mode matrices, scaling laws

More importantly, you'll internalize the **evidence-based mental model** for coordination:

**Coordination at scale preserves invariants (discoverability, consistency, resilience, efficiency) by generating and propagating evidence (health checks, config versions, circuit states, routing tables) through decentralized mechanisms that degrade predictably under partition or overload.**

### The Conservation Principle

Throughout this chapter, observe the **conservation of coordination**: information cannot appear or disappear without authorized flows. When we say "service discovery," we mean converting uncertain service locations into certain routing decisions through evidence (health checks, registration proofs). When we say "configuration propagation," we mean evidence flow through the network with bounded staleness. When we say "circuit breaker," we mean evidence of failure that blocks further requests.

This conservation view makes coordination patterns comprehensible. Centralized systems maintain evidence in one place (fast reads, slow writes, single point of failure). Decentralized systems distribute evidence everywhere (slow reads, fast writes, partition tolerant). The choice is about where evidence lives and how it flows.

Let's begin with the ant colony—a story that makes emergent coordination visceral.

---

## Part 1: INTUITION (First Pass) — The Felt Need

### The Ant Colony Problem

An ant colony of 500,000 ants coordinates complex behaviors: foraging, nest building, defense, waste management, brood care. No ant understands the whole system. No "queen ant" issues commands (the queen only reproduces). Yet the colony exhibits sophisticated coordinated behavior.

How?

**The Mechanism: Pheromone Trails**

1. **Foraging ant** leaves nest randomly searching for food
2. **Finds food**, carries piece back to nest
3. **While returning**, deposits pheromone trail (chemical marker)
4. **Other ants** detect pheromone, follow trail (stronger pheromone = more ants followed this path)
5. **Shorter paths** accumulate pheromone faster (ants return quicker, reinforce trail sooner)
6. **Longer paths** evaporate (pheromone decays, trail weakens)
7. **Result**: Colony converges on shortest path to food source

No ant knows "this is the shortest path." No central coordinator calculates routes. The optimal path **emerges** from simple local rules: follow pheromone, deposit pheromone, pheromone evaporates.

**This is stigmergy**: coordination through environmental modification. Ants communicate by changing the environment (leaving pheromone), not by direct messaging.

### Lessons for Distributed Systems

**Service Discovery as Pheromone Trails**:
- Services "deposit pheromone" = register in discovery service (heartbeat, health check)
- Clients "follow pheromone" = route to services based on registration freshness
- "Pheromone evaporates" = registrations expire if not refreshed
- "Optimal paths emerge" = healthy services get more traffic, unhealthy ones avoided

**Configuration Propagation as Stigmergy**:
- Each node propagates config to neighbors (modifies environment)
- Nodes adopt config when majority of neighbors have it (follow environmental signal)
- Old configs "evaporate" when no nodes reference them
- System converges on consistent config without central push

**Load Balancing as Ant Foraging**:
- Clients randomly probe services (foraging)
- Successful requests = fast response (found food)
- "Deposit pheromone" = remember fast service, prefer it
- Overloaded service = slow response (long path)
- "Evaporation" = preferences decay over time
- Result: Load distributes to responsive services

The ant colony teaches us: **coordination doesn't require intelligence or central control—it requires feedback loops, local decisions, and information decay**.

### The Traffic Light Evolution

How do traffic lights coordinate in a city? The evolution mirrors distributed systems history.

**Phase 1: Fixed Timing (1920s-1960s)**
- All lights on fixed schedules (60s green, 30s red)
- Centrally planned but not coordinated
- No adaptation to traffic
- Result: Empty streets have green lights, congested streets wait

**Phase 2: Coordinated Timing (1970s-1980s)**
- "Green wave": Lights synchronized for speed limit (drive at 35 mph, hit all greens)
- Central controller coordinates timing
- Still no real-time adaptation
- Result: Works for main corridor, side streets suffer

**Phase 3: Sensor-Based Adaptive (1990s-2000s)**
- Induction loops detect cars waiting
- Local logic: Extend green if traffic present, shorten if not
- Still centrally coordinated cycles
- Result: Better adaptation but central point of failure

**Phase 4: Distributed Adaptive (2010s-present)**
- Each intersection has sensors and local decision logic
- Lights communicate with neighbors (share traffic state)
- No central controller (or central serves as advisory, not control)
- Emergent behavior: "Green waves" form dynamically based on traffic patterns
- Result: Adapts to incidents, events, time of day without central planning

**Phase 5: V2X Future (2020s+)**
- Vehicles communicate directly with infrastructure (Vehicle-to-Everything)
- Predictive: Know cars coming 30 seconds before arrival
- Negotiated: Intersection allocates green time like resource scheduling
- Fully emergent: No fixed phases, continuous optimization

### The Distributed Systems Parallel

**Fixed Timing = Static Configuration**:
- Hard-coded service addresses in config files
- Manual updates, restart required
- No adaptation to failures

**Coordinated Timing = Central Load Balancer**:
- All traffic goes through load balancer
- Balancer knows all backend health
- Single point of failure

**Sensor-Based Adaptive = Health-Check Discovery**:
- Services register with discovery service
- Periodic health checks
- Clients query discovery for current list
- But discovery service is central bottleneck

**Distributed Adaptive = Mesh Service Discovery**:
- Each service knows neighbors
- Health state propagates peer-to-peer
- No central registry (or registry is eventually consistent cache)
- Routing decisions made locally with distributed knowledge

**V2X Future = Intent-Based Networking**:
- Services declare intent ("I need database with <100ms latency, strong consistency")
- Network provides matching service
- Continuous optimization based on observed performance
- Fully policy-driven

The evolution is clear: **from centralized static to decentralized adaptive**.

### Real Coordination Challenges

Let's ground this in production scenarios.

**Black Friday Traffic Surge (E-commerce)**:
- Normal load: 10,000 req/s
- Black Friday peak: 500,000 req/s (50× spike)
- Challenge: Scale out 50× in minutes, discover new services, balance load, maintain consistency

**Without Coordination**:
- Services launch but not discoverable
- Clients hammer old services (still have cached addresses)
- Load imbalanced (some services 100% CPU, others idle)
- Cascading failures (overloaded services crash, increasing load on survivors)

**With Coordination**:
- New services register in discovery (health checks pass after warmup)
- Clients refresh service lists (discovery propagates updates via gossip)
- Load balances (consistent hashing distributes requests)
- Circuit breakers prevent cascade (failing services removed from rotation)

**Stock Market Opening Bell (Financial)**:
- 9:30 AM: Markets open, orders flood in
- Challenge: Process millions of orders in microseconds, maintain fairness, preserve exactly-once semantics

**Without Coordination**:
- Orders processed out of order (network delays vary)
- Duplicate executions (retries without idempotency)
- Unfair advantages (colocation affects latency)

**With Coordination**:
- Total ordering (consensus protocol sequences orders)
- Idempotent processing (dedupe via request IDs)
- Fair queuing (priority based on arrival time, not network distance)

**Kubernetes Pod Scheduling (Infrastructure)**:
- Scheduler must place 1,000 pods across 100 nodes
- Constraints: Resource limits, affinity/anti-affinity, taints/tolerations
- Challenge: Optimal placement without global lock

**Without Coordination**:
- Multiple schedulers place pods on same node (resource overcommit)
- Conflicting decisions (pod A requires anti-affinity with B, but both placed on node-1)
- Starvation (some nodes idle, others overloaded)

**With Coordination**:
- Optimistic scheduling with conflict detection
- Version numbers on node state (detect concurrent modifications)
- Reschedule on conflict (retry with updated state)
- Result: Eventually optimal placement, no global lock

**Global CDN Cache Invalidation (Content Delivery)**:
- Update published at origin (v1 → v2)
- Challenge: Invalidate caches at 1,000 edge locations globally
- Requirement: Bounded staleness (no edge serves v1 after 5 seconds)

**Without Coordination**:
- Invalidation messages lost (unreliable network)
- Some edges serve v1 for minutes (stale cache)
- Users see inconsistent versions (refresh gets different data)

**With Coordination**:
- Versioned invalidation (v2 tagged with timestamp)
- Gossip propagation (edges notify neighbors)
- TTL fallback (cache expires after 5s even if no invalidation)
- Result: Bounded staleness guarantee, eventual consistency

These scenarios share a pattern: **coordination is about managing distributed state under constraints (time, consistency, partition) using local decisions that create global properties**.

---

## Part 2: UNDERSTANDING (Second Pass) — The Mechanisms

### Service Discovery Evolution

How do services find each other? The evolution of service discovery mirrors the scale journey.

#### DNS-Based Discovery

**Traditional Approach**:
```
Client → DNS lookup "api.example.com" → IP address → Connect
```

**Mechanism**:
- DNS server maintains hostname → IP mapping
- Client caches result (TTL, typically 60-300s)
- Updates via DNS admin (manual or scripted)

**Limitations**:
1. **Cache staleness**: Client caches DNS for TTL duration. Service fails, but client still uses cached IP for 5 minutes.
2. **No health checks**: DNS doesn't know if IP is healthy, just that it exists in records.
3. **Coarse granularity**: One hostname resolves to one IP (or round-robin set). No rich routing (latency-based, zone-aware).
4. **Slow propagation**: DNS updates take minutes to propagate globally (TTL + caching layers).

**Evidence**: DNS record is evidence of "this IP was assigned to this hostname at time T". Evidence lifetime = TTL. Stale evidence = cached entry after service moved.

**When DNS Works**:
- Static infrastructure (IPs rarely change)
- Coarse load distribution (round-robin adequate)
- Acceptable staleness (minutes of stale routes OK)

**SRV Records** (improvement):
```
_http._tcp.api.example.com. 86400 IN SRV 10 60 80 server1.example.com.
```
- Priority (10), Weight (60), Port (80), Target (server1)
- Enables weighted load balancing, priority failover
- Still has DNS cache staleness

#### Registry-Based Discovery

**Modern Approach**:
```
Service → Register(name, IP, health) → Registry
Client → Query(name) → Registry → List of healthy IPs → Connect
```

**Consul Architecture**:
- Services register via HTTP API or agent
- Health checks: Script, HTTP, TCP, TTL-based
- Agents gossip health state (Serf protocol, based on SWIM)
- Clients query HTTP/DNS interface
- Raft consensus for catalog consistency

**Evidence Flow**:
1. Service sends heartbeat → Agent (local evidence of liveness)
2. Agent propagates health → Cluster via gossip (distributed evidence)
3. Catalog updated → Raft commit (durable evidence)
4. Client queries catalog → Returns healthy services (fresh evidence with bounded staleness)

**Etcd Service Registry**:
- Services write key: `/services/api/{instance-id}` → `{ip: "10.0.0.1", port: 8080}`
- Use lease (TTL): Key auto-deleted if service crashes
- Clients watch prefix `/services/api/` → Notified on changes
- Raft consensus for strong consistency

**Evidence**: Lease is evidence of liveness. Lifetime = lease TTL (typically 10-60s). Watch provides push-based evidence propagation (vs DNS pull).

**ZooKeeper Ephemeral Nodes**:
- Service creates ephemeral znode: `/services/api/instance1`
- Znode deleted automatically when session ends (heartbeat timeout)
- Clients get children of `/services/api/` → List of live instances
- Watch for changes → Push notification

**Eureka Availability Zones**:
- Netflix's registry, designed for AWS multi-AZ
- Services register with availability zone metadata
- Clients prefer same-zone services (lower latency)
- Self-preservation mode: If >15% services appear down, assume network issue, stop deregistering (prefer stale data over false negatives)

**Evidence trade-off**: Eureka is AP (availability over consistency during partition). Prefers serving stale registrations over being unavailable. Accepts eventual consistency for higher availability.

#### Mesh-Based Discovery

**Service Mesh Model** (Envoy, Istio, Linkerd):
```
Service A → Sidecar Proxy A → Sidecar Proxy B → Service B
              ↓                      ↑
          Control Plane (xDS APIs)
```

**Envoy Endpoint Discovery (EDS)**:
- Control plane knows all service instances
- Envoy sidecars subscribe to endpoint updates (xDS protocols: LDS, RDS, CDS, EDS)
- Incremental updates (only changed endpoints)
- Health status included (HEALTHY, UNHEALTHY, DRAINING)

**xDS Protocols**:
- **LDS** (Listener Discovery): Which ports to listen on
- **RDS** (Route Discovery): How to route requests (URL path → cluster)
- **CDS** (Cluster Discovery): Upstream service clusters
- **EDS** (Endpoint Discovery): Specific IPs/ports in each cluster

**Evidence Flow**:
1. Service registers with control plane (or k8s API)
2. Control plane pushes EDS update → All Envoy sidecars
3. Sidecar routes traffic based on health status in EDS
4. Sidecar reports metrics back → Control plane (active health checking)

**Incremental Updates**:
- Instead of "here's the full list of 10,000 endpoints" (wasteful)
- Send "endpoint X is now HEALTHY, endpoint Y removed" (efficient)
- Version numbers prevent races (client tracks version, rejects old updates)

**Health-Based Routing**:
- Passive health: Envoy observes response codes (5xx = unhealthy)
- Active health: Envoy periodically probes endpoints (HTTP GET /health)
- Outlier detection: If endpoint's error rate > threshold, remove from load balancing
- Circuit breaking: Limit concurrent requests to failing endpoints

**Evidence**: Health status is evidence with scope = cluster, lifetime = health check interval. Circuit breaker state is evidence that prevents requests (negative evidence: "don't route here").

#### Gossip Protocols

**SWIM Protocol** (Scalable Weakly-consistent Infection-style Process Group Membership):

**Mechanism**:
1. Each node periodically pings random member (every T seconds)
2. If no ACK within timeout, ping through k other members (indirect probing)
3. If still no ACK, mark as suspected
4. Gossip membership changes (join, leave, fail) via piggyback on pings
5. Eventually all nodes learn all membership changes

**Why Gossip Scales**:
- **O(log n) propagation time**: Information reaches all n nodes in O(log n) rounds
- **O(1) per-node overhead**: Each node sends constant messages per round
- **Partition tolerant**: Gossip continues in each partition, heals when partition resolves
- **Probabilistic guarantees**: Eventual consistency with tunable probability of delivery

**Evidence Flow**:
- Ping/ACK is evidence of liveness (lifetime = timeout period)
- Gossip message is evidence of membership change (lifetime = until propagated to all)
- Incarnation numbers prevent old evidence from overwriting new (monotonic)

**Epidemic Dissemination**:
- Info spreads like epidemic: Infected → Susceptible → Infected
- Each round, infected node infects O(1) neighbors
- After O(log n) rounds, all nodes infected with high probability

**Convergence Guarantees**:
- Eventual consistency: All nodes eventually have same membership view
- Bounded staleness: Node learns of change within O(log n) gossip rounds
- Probabilistic: With probability 1 - ε, convergence in O(log n) time

**Failure Detection**:
- Direct probe: Fast for responsive nodes
- Indirect probe: Detects network partition vs node failure
- Suspicion mechanism: Reduces false positives (don't immediately mark failed)

**Production Example** (Consul):
- Gossip pool (Serf): Membership and failure detection
- Consensus (Raft): Service catalog and KV store
- Clients use gossip for fast failure detection (eventual consistency)
- Clients use catalog for authoritative service list (strong consistency)

**Evidence Layering**:
- Gossip provides BoundedStale evidence (fast, eventually consistent)
- Raft provides Fresh evidence (slower, strongly consistent)
- Application chooses: "Use gossip for circuit breaking (speed matters), use catalog for initial discovery (correctness matters)"

### Configuration Management

How do configurations propagate across distributed systems?

#### Centralized Configuration

**Config Server Pattern**:
```
Service → Poll → Config Server → Return config → Service applies
```

**Spring Cloud Config**:
- Git repository stores configs (version controlled)
- Config server serves configs via REST API
- Services query on startup: `/config/{app}/{profile}`
- Changes require service restart (or `/refresh` endpoint)

**Evidence**:
- Git commit hash is evidence of config version
- Scope: Per application/profile
- Lifetime: Until service restarts or manual refresh

**Etcd/Consul KV Store**:
- Central KV store (consensus-based, strongly consistent)
- Services watch keys: `/config/app/database-url`
- On change, notification pushed → Service reloads

**Evidence**:
- Watch version (ModRevision in etcd) proves freshness
- Lifetime: Continuous (watch connection maintained)

**Audit Trails**:
- All changes logged: Who, what, when
- Rollback: Revert to previous version (git revert or KV version)
- Immutable history: Can trace config at any point in time

**Versioning**:
```json
{
  "version": 42,
  "updated_at": "2025-10-01T00:00:00Z",
  "config": {
    "database_url": "postgres://...",
    "cache_ttl": 300
  }
}
```

Services track version, detect drift, reconcile.

#### Dynamic Configuration

**Feature Flags**:
```python
if feature_flag("new_checkout_flow"):
    use_new_checkout()
else:
    use_old_checkout()
```

**Use Cases**:
- **Gradual rollout**: Enable for 1%, then 10%, then 100%
- **A/B testing**: 50% users get variant A, 50% get B
- **Kill switch**: Instantly disable feature if broken (set flag to false)
- **Entitlements**: Premium users get feature, free users don't

**Evidence**:
- Flag evaluation result is evidence (scope: user/request, lifetime: request duration)
- Flag version is evidence of which ruleset applied
- Evaluation context: User ID, region, time → Deterministic flag value

**LaunchDarkly Architecture**:
- SDK in service evaluates flags locally (no network call per request)
- SDK streams flag updates from server (SSE or WebSocket)
- Evaluation is fast (local) but eventually consistent (stream lag)

**Rollout Strategy**:
```python
def gradual_rollout(feature, target_percentage):
    current = 0
    while current < target_percentage:
        current = min(current + 10, target_percentage)
        update_flag(feature, current)

        time.sleep(300)  # 5 minutes between increases

        if detect_regression():
            rollback_flag(feature, current - 10)
            alert_ops("Rollout failed at {}%".format(current))
            break
```

**Monitoring Integration**:
- Track metrics per flag variant
- Compare error rates: variant A vs B
- Automatic rollback if threshold exceeded

#### Distributed Configuration

**Consensus-Based Configs**:
- Config changes committed via Raft/Paxos
- All nodes eventually have same config
- Updates are linearizable (happen in definite order)

**Eventually Consistent Settings**:
- Config propagated via gossip
- Nodes may temporarily have different configs
- Acceptable for non-critical settings (log level, timeouts)

**Hierarchical Overrides**:
```
Global config: {"timeout": 30}
  ↓
Region config: {"timeout": 50}  # Override for high-latency region
  ↓
Service config: {"timeout": 10}  # Override for fast service
  ↓
Instance config: {"timeout": 60}  # Override for debugging
```

Merge strategy: Specific overrides general.

**Environment-Specific Values**:
```yaml
database:
  dev: "sqlite://local.db"
  staging: "postgres://staging.db"
  prod: "postgres://prod.db"
```

Service selects based on environment variable.

**Evidence**:
- Config version at each level (global v5, region v3, service v2)
- Effective config = merge(global, region, service, instance)
- Evidence of effective config = hash(merged config)

### Circuit Breakers and Resilience

How do systems prevent cascading failures?

#### Circuit Breaker Pattern

**State Machine**:
```
CLOSED → (failure rate > threshold) → OPEN
OPEN → (timeout expires) → HALF_OPEN
HALF_OPEN → (success) → CLOSED
HALF_OPEN → (failure) → OPEN
```

**CLOSED State**:
- Normal operation
- Track success/failure rate
- If failure rate > threshold (e.g., >50% failures in last 10 requests), trip to OPEN

**OPEN State**:
- Immediately fail all requests (don't even try)
- Return cached data or error response
- Start timeout (e.g., 30 seconds)
- After timeout, transition to HALF_OPEN

**HALF_OPEN State**:
- Allow limited requests (e.g., 3 requests)
- If all succeed, close circuit (back to CLOSED)
- If any fail, open circuit (back to OPEN)

**Evidence**:
- Failure count is evidence of unhealthiness
- Circuit state is evidence that prevents requests
- Lifetime: Closed (continuous), Open (timeout duration), Half-Open (test period)

**Tuning Parameters**:
```python
circuit_config = {
    'failure_threshold': 5,      # Trip after 5 failures
    'success_threshold': 2,      # Close after 2 successes in half-open
    'timeout': 30,               # 30s before trying half-open
    'half_open_requests': 3,     # Allow 3 requests in half-open
    'window_size': 60            # Track failures over 60s window
}
```

**Fallback Mechanisms**:
```python
try:
    return call_service()
except CircuitOpenError:
    return cached_response()  # Stale but available
```

#### Bulkhead Pattern

**Resource Isolation**:
```
Request → Thread Pool A (for service A, size 10)
Request → Thread Pool B (for service B, size 20)
```

If service A hangs, only 10 threads blocked. Service B remains unaffected.

**Thread Pool Separation**:
- Each dependency gets dedicated thread pool
- Pools independently sized based on latency and throughput
- Prevents one slow dependency from blocking all threads

**Connection Limits**:
```python
connection_pools = {
    'database': Pool(max_size=50),
    'cache': Pool(max_size=100),
    'external_api': Pool(max_size=20)
}
```

**Queue Management**:
- Bounded queues (e.g., 1000 pending requests)
- Reject new requests when queue full (fast fail)
- Prevents unbounded memory growth

**Evidence**:
- Pool utilization is evidence of load
- Queue depth is evidence of backlog
- Rejection rate is evidence of overload

#### Adaptive Concurrency

**AIMD (Additive Increase Multiplicative Decrease)**:
```python
concurrency_limit = 10

if success:
    concurrency_limit += 1  # Additive increase

if failure:
    concurrency_limit *= 0.5  # Multiplicative decrease
```

Converges on optimal concurrency without prior knowledge.

**Gradient Descent**:
- Measure latency at concurrency C
- Increase to C+1, measure again
- If latency improved, increase more
- If latency degraded, decrease
- Continuously adapt to changing conditions

**Little's Law Application**:
```
Concurrency = Throughput × Latency
```

If target latency = 100ms, current throughput = 1000 req/s:
```
Optimal concurrency = 1000 × 0.1 = 100
```

Monitor actual latency, adjust concurrency to maintain target.

**Congestion Control**:
- Similar to TCP congestion control
- Probe for bandwidth (increase concurrency)
- Detect congestion (latency spike, errors)
- Back off (decrease concurrency)
- Repeat

**Evidence**:
- Latency percentiles (P50, P99) are evidence of congestion
- Error rate is evidence of overload
- Concurrency limit is evidence-based admission control

#### Backpressure Mechanisms

**Reactive Streams**:
```
Publisher → (request N items) ← Subscriber
         ← (send ≤N items) →
```

Subscriber controls rate (pulls), not publisher (pushes).

**Flow Control**:
- Subscriber requests N items
- Publisher sends ≤N items
- Subscriber processes, requests more
- If subscriber slow, publisher naturally slows (no buffering)

**Credit-Based Systems**:
```python
class CreditSystem:
    def __init__(self):
        self.credits = 100

    def send_request(self):
        if self.credits > 0:
            self.credits -= 1
            # Send request
        else:
            # Reject or queue

    def receive_response(self):
        self.credits += 1  # Replenish
```

**Pushback Strategies**:
- HTTP 429 Too Many Requests (explicit backpressure signal)
- Retry-After header (tells client when to retry)
- Queue depth metrics (clients monitor, slow down proactively)

**Evidence**:
- Credit balance is evidence of capacity
- 429 response is evidence of overload
- Queue depth is evidence of processing lag

### Distributed Tracing

How do we understand request flows across services?

#### Trace Context Propagation

**W3C Trace Context Standard**:
```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
              ││                                │                ││
              ││ Trace ID (128-bit)             │ Span ID (64-bit) ││
              │└────────────────────────────────┘                 ││
              │                                                    ││
              │ Version                                            ││
              └────────────────────────────────────────────────────┘
                                                           Flags (sampled)
```

**Propagation**:
```python
# Service A
trace_id = generate_trace_id()
span_id = generate_span_id()
headers = {'traceparent': f'00-{trace_id}-{span_id}-01'}

# Service A → Service B
response = requests.get(url, headers=headers)

# Service B extracts
trace_id = extract_trace_id(headers['traceparent'])
parent_span_id = extract_span_id(headers['traceparent'])
child_span_id = generate_span_id()
```

**OpenTelemetry Standards**:
- Unified API for tracing, metrics, logs
- Language-agnostic (SDKs for all major languages)
- Vendor-neutral (export to any backend: Jaeger, Zipkin, Datadog)

**Baggage Propagation**:
```
baggage: userId=alice,tier=premium,region=us-east
```

Key-value pairs propagated with trace for filtering/grouping.

**Sampling Decisions**:
- **Head-based**: Decide at trace start (sample 1% of all traces)
- **Tail-based**: Decide at trace end (sample all slow traces, all errors)
- Propagate sampling decision in flags (01 = sampled, 00 = not sampled)

**Evidence**:
- Trace ID is evidence of request causality (all spans with same trace ID are related)
- Span ID is evidence of parent-child relationships
- Baggage is evidence propagated across service boundaries

#### Trace Collection

**Agent-Based Collection**:
```
Service → Local Agent → Collector → Storage
```

- Agent runs on same host as service (low latency)
- Batches spans before sending to collector (efficiency)
- Collector aggregates from all agents

**Direct Submission**:
```
Service → Collector (load balanced)
```

- Service sends spans directly
- Simpler (no agent) but higher service overhead

**Tail-Based Sampling**:
- Collector sees entire trace
- Decides to keep or discard based on trace properties:
  - Keep all traces with errors
  - Keep all traces >1s duration
  - Keep 1% of fast successful traces
- Reduces storage cost while preserving interesting traces

**Adaptive Sampling**:
```python
def sample_decision(trace):
    if trace.has_error:
        return True  # Always sample errors
    if trace.duration > 1.0:
        return True  # Always sample slow

    # Sample 1% of normal traces
    return random.random() < 0.01
```

**Evidence**:
- Span is evidence of operation (start time, duration, status)
- Scope: Single operation
- Lifetime: Stored for retention period (e.g., 7 days)

#### Trace Analysis

**Critical Path Analysis**:
```
Trace (1000ms total):
  Service A: 50ms
    → Service B: 800ms (critical path!)
        → Database: 750ms (bottleneck!)
    → Service C: 100ms
```

Critical path = longest dependency chain. Optimizing non-critical paths doesn't improve total latency.

**Latency Breakdown**:
```
Total: 1000ms
  Network: 100ms (10%)
  Service: 200ms (20%)
  Database: 700ms (70%) ← Focus here
```

**Error Correlation**:
- Trace shows error in service C
- Also shows timeout in service B → C
- Root cause: Service C slow → timeout → error
- Without tracing, would debug wrong service

**Dependency Mapping**:
```
Service A → Service B → Database
         → Service C → Cache
                     → Service D → External API
```

Automatically discover service dependencies from traces.

**Evidence**:
- Critical path is evidence of optimization target
- Latency breakdown is evidence of bottleneck location
- Dependency graph is evidence of system architecture

### Leader Election Patterns

How do distributed systems choose a leader?

#### Centralized Coordinators

**ZooKeeper Leader Election**:
```python
# Ephemeral sequential nodes
def elect_leader():
    my_node = zk.create('/election/node-', ephemeral=True, sequence=True)
    # my_node = '/election/node-0000000001'

    children = zk.get_children('/election')
    children.sort()

    if children[0] == my_node.split('/')[-1]:
        # I'm the leader!
        return Leader()
    else:
        # Watch previous node
        prev = children[children.index(my_node.split('/')[-1]) - 1]
        zk.exists(f'/election/{prev}', watch=node_deleted)
        return Follower()

def node_deleted(event):
    # Previous node died, check if I'm leader now
    elect_leader()
```

**Evidence**:
- Lowest sequence number is evidence of leadership
- Ephemeral node existence is evidence of liveness
- Lifetime: Until session timeout

**Etcd Elections**:
```go
// Campaign for leadership
session, _ := concurrency.NewSession(client)
election := concurrency.NewElection(session, "/election/")

// Blocks until elected
election.Campaign(ctx, "node-1")
// Now I'm leader

// Resign
election.Resign(ctx)
```

**Consul Sessions**:
```python
# Create session with TTL
session_id = consul.session.create(ttl='10s')

# Acquire lock
acquired = consul.kv.put('service/leader', 'node-1', acquire=session_id)

if acquired:
    # I'm the leader
    # Renew session periodically
    while True:
        consul.session.renew(session_id)
        time.sleep(5)
```

**Redis Redlock**:
```python
# Acquire lock on majority of Redis instances
def acquire_lock(resource, ttl):
    value = random_value()
    start_time = current_time()

    acquired = 0
    for redis in redis_instances:
        if redis.set(resource, value, nx=True, px=ttl):
            acquired += 1

    elapsed = current_time() - start_time

    if acquired >= (len(redis_instances) // 2 + 1) and elapsed < ttl:
        # Majority acquired, I'm leader
        return Lock(value, ttl - elapsed)
    else:
        # Failed, release locks
        release_lock(resource, value)
        return None
```

**Evidence**:
- Lock acquisition across majority is evidence of leadership (quorum-based)
- TTL bounds evidence lifetime
- If renewal fails, evidence expires, leader steps down

#### Distributed Elections

**Bully Algorithm**:
```python
def election():
    # Send election message to all higher-ID nodes
    higher_nodes = [n for n in nodes if n.id > my_id]

    responses = send_to_all(higher_nodes, "ELECTION")

    if no_responses:
        # I'm the highest, declare victory
        send_to_all(nodes, "COORDINATOR", my_id)
        return Leader()
    else:
        # Higher node will become coordinator
        return Follower()

def receive_election(from_node):
    # Higher node exists, respond and start own election
    send(from_node, "ALIVE")
    election()
```

**Ring Algorithm**:
```python
def election():
    # Send election message with my ID
    send_to_successor("ELECTION", [my_id])

def receive_election(id_list):
    if my_id in id_list:
        # Message completed ring, I'm coordinator
        highest = max(id_list)
        send_to_successor("COORDINATOR", highest)
    else:
        # Add my ID and forward
        id_list.append(my_id)
        send_to_successor("ELECTION", id_list)
```

**Raft-Based Election**:
```python
# Follower times out
def election_timeout():
    current_term += 1
    voted_for = my_id
    votes = 1

    # Request votes from all nodes
    for node in other_nodes:
        response = node.request_vote(current_term, my_id, last_log_index, last_log_term)
        if response.vote_granted:
            votes += 1

    if votes > len(nodes) // 2:
        # Majority voted for me
        become_leader()
    else:
        # Failed, revert to follower
        become_follower()
```

**Evidence**:
- Election message with highest ID is evidence of potential leader (Bully)
- Vote grant is evidence of support (Raft)
- Majority votes is evidence of legitimate leadership (quorum)

#### Work Distribution

**Consistent Hashing**:
```python
# Hash ring: 0 to 2^32-1
def get_node(key):
    key_hash = hash(key) % (2**32)

    # Find first node clockwise from key_hash
    for node in sorted(nodes, key=lambda n: hash(n.id)):
        if hash(node.id) >= key_hash:
            return node

    # Wrap around to first node
    return sorted(nodes, key=lambda n: hash(n.id))[0]
```

**Virtual Nodes** (improve balance):
```python
# Each physical node gets 100 virtual nodes
virtual_nodes = {}
for node in physical_nodes:
    for i in range(100):
        vnode_id = f"{node.id}-{i}"
        virtual_nodes[hash(vnode_id)] = node
```

**Rendezvous Hashing** (Highest Random Weight):
```python
def get_node(key):
    max_weight = -1
    selected_node = None

    for node in nodes:
        weight = hash(f"{key}:{node.id}")
        if weight > max_weight:
            max_weight = weight
            selected_node = node

    return selected_node
```

**Jump Consistent Hash**:
```python
def jump_hash(key, num_nodes):
    b, j = -1, 0
    while j < num_nodes:
        b = j
        key = (key * 2862933555777941757 + 1) & 0xffffffffffffffff
        j = int((b + 1) * (float(1 << 31) / float((key >> 33) + 1)))
    return b
```

O(log n) computation, minimal reassignment on node add/remove.

**Maglev Hashing**:
- Google's consistent hashing for load balancing
- Lookup table size M (e.g., 65537, prime)
- Each backend gets equal share of table
- Minimal disruption on backend changes

**Evidence**:
- Hash value is evidence of assignment (key → node)
- Ring position is evidence of responsibility range
- Work distribution is deterministic evidence (same key always routes to same node, given same node set)

---

## Part 3: MASTERY (Third Pass) — Evidence-Based Operation

### Evidence-Based Coordination

Coordination at scale requires treating all state as evidence with explicit scope, lifetime, and binding.

#### Discovery Evidence

**Service Registration Proofs**:
```json
{
  "service": "api",
  "instance": "api-1",
  "address": "10.0.1.15:8080",
  "registered_at": "2025-10-01T00:00:00Z",
  "lease_id": "abc123",
  "lease_ttl": 30,
  "evidence": {
    "scope": "cluster-east",
    "lifetime": "30s",
    "binding": "lease:abc123",
    "freshness": "Fresh"
  }
}
```

**Health Check Certificates**:
```json
{
  "instance": "api-1",
  "health": "passing",
  "checks": [
    {"name": "http", "status": "passing", "output": "200 OK"},
    {"name": "memory", "status": "passing", "output": "60% used"}
  ],
  "checked_at": "2025-10-01T00:00:05Z",
  "evidence": {
    "scope": "instance",
    "lifetime": "10s",  # Check interval
    "binding": "check:http,check:memory",
    "freshness": "Fresh(5s)"
  }
}
```

**Routing Table Versions**:
```python
routing_table = {
    "version": 42,
    "updated_at": "2025-10-01T00:00:00Z",
    "routes": {
        "api": ["10.0.1.15:8080", "10.0.1.16:8080"],
        "cache": ["10.0.2.10:6379"]
    },
    "evidence": {
        "scope": "zone-a",
        "lifetime": "until_next_update",
        "binding": "version:42",
        "freshness": "BoundedStale(delta=current_time - updated_at)"
    }
}
```

**Endpoint Freshness**:
```python
def is_fresh(endpoint, max_age_ms):
    age_ms = current_time_ms() - endpoint['registered_at']
    return age_ms < max_age_ms

# Use fresh endpoints only
fresh_endpoints = [e for e in endpoints if is_fresh(e, 5000)]
```

**Evidence Lifecycle**:
1. **Generation**: Service registers → Creates evidence
2. **Propagation**: Registration propagates via gossip/consensus → Evidence flows
3. **Validation**: Clients check evidence freshness → Evidence verified
4. **Expiration**: TTL expires or service deregisters → Evidence revoked
5. **Renewal**: Service sends heartbeat → Evidence refreshed

#### Configuration Evidence

**Config Version Attestations**:
```json
{
  "config": {
    "database_url": "postgres://...",
    "cache_ttl": 300
  },
  "version": 17,
  "committed_at": "2025-10-01T00:00:00Z",
  "commit_hash": "a1b2c3d4",
  "evidence": {
    "scope": "application:api",
    "lifetime": "immutable",  # Version 17 never changes
    "binding": "commit:a1b2c3d4",
    "freshness": "Historical"
  }
}
```

**Rollout Confirmations**:
```python
rollout_status = {
    "feature": "new_checkout",
    "target_percentage": 50,
    "actual_percentage": 48,  # Due to sampling
    "instances_updated": 24,
    "instances_total": 50,
    "evidence": {
        "scope": "feature:new_checkout",
        "lifetime": "until_next_rollout",
        "binding": "instances:[api-1, api-2, ...]",
        "freshness": "Fresh(polling_interval=30s)"
    }
}
```

**Feature Flag Evaluations**:
```python
evaluation = {
    "flag": "premium_features",
    "user_id": "alice",
    "value": True,
    "reason": "user in segment:premium",
    "version": 5,  # Flag rule version
    "evidence": {
        "scope": "user:alice, request:xyz",
        "lifetime": "request_duration",
        "binding": "flag_version:5, user_segment:premium",
        "freshness": "Fresh"
    }
}
```

**Override Audit Trails**:
```python
override = {
    "config_key": "timeout",
    "global_value": 30,
    "override_value": 60,
    "override_scope": "instance:api-debug-1",
    "applied_by": "ops-engineer@example.com",
    "applied_at": "2025-10-01T00:00:00Z",
    "reason": "debugging timeout issues",
    "evidence": {
        "scope": "instance:api-debug-1",
        "lifetime": "24h",  # Debug overrides expire
        "binding": "applied_by:ops-engineer",
        "authorization": "role:ops, action:override"
    }
}
```

#### Resilience Evidence

**Circuit Breaker States**:
```python
circuit_state = {
    "service": "payment-api",
    "state": "OPEN",
    "opened_at": "2025-10-01T00:00:00Z",
    "failure_count": 10,
    "success_count": 0,
    "last_failure": "2025-10-01T00:00:10Z",
    "next_retry": "2025-10-01T00:00:30Z",  # 30s timeout
    "evidence": {
        "scope": "client:api-1 → service:payment-api",
        "lifetime": "timeout=30s",
        "binding": "failures:[error1, error2, ...]",
        "mode": "Degraded"
    }
}
```

**Backpressure Signals**:
```python
backpressure = {
    "service": "order-processor",
    "queue_depth": 5000,
    "max_queue": 10000,
    "processing_rate": 100,  # req/s
    "arrival_rate": 500,     # req/s
    "signal": "SLOW_DOWN",   # or REJECT, OK
    "evidence": {
        "scope": "service:order-processor",
        "lifetime": "continuous",
        "binding": "queue_depth:5000",
        "freshness": "Fresh(measured_at=now)"
    }
}
```

**Concurrency Limits**:
```python
concurrency = {
    "service": "external-api",
    "current": 45,
    "limit": 50,
    "limit_source": "adaptive",  # or static, quota
    "headroom": 5,
    "evidence": {
        "scope": "client:api-1 → service:external-api",
        "lifetime": "adaptive_window=60s",
        "binding": "latency_p99:150ms, target:100ms",
        "mode": "Target"
    }
}
```

**Recovery Metrics**:
```python
recovery = {
    "circuit": "payment-api",
    "state_transition": "HALF_OPEN → CLOSED",
    "test_requests": 3,
    "test_successes": 3,
    "recovery_time": "45s",  # Time from OPEN to CLOSED
    "evidence": {
        "scope": "circuit:payment-api",
        "lifetime": "until_next_failure",
        "binding": "successes:[req1, req2, req3]",
        "mode": "Recovery → Target"
    }
}
```

### Invariant Framework for Coordination

Define invariants that coordination mechanisms must preserve.

#### Primary Invariant: COORDINATION

**Formal Statement**:
```
∀ service s, ∀ time t:
  Discoverable(s, t) ∧
  ConfigConsistent(s, t) ∧
  FailureIsolated(s, t) ∧
  LoadBalanced(s, t)
```

**Evidence Requirements**:
- **Discoverable**: Registration evidence with Fresh or BoundedStale freshness
- **ConfigConsistent**: Config version evidence matching quorum
- **FailureIsolated**: Circuit breaker evidence preventing cascade
- **LoadBalanced**: Request distribution evidence within threshold

**Violation Detection**:
```python
def check_coordination_invariant(service):
    if not is_discoverable(service):
        alert("COORDINATION violation: service not discoverable")
        evidence = {"issue": "no_registration", "last_seen": service.last_heartbeat}

    if not is_config_consistent(service):
        alert("COORDINATION violation: config drift detected")
        evidence = {"issue": "config_mismatch", "expected": v17, "actual": v15}

    if not is_failure_isolated(service):
        alert("COORDINATION violation: cascading failure detected")
        evidence = {"issue": "circuit_closed", "failure_rate": 0.85}

    if not is_load_balanced(service):
        alert("COORDINATION violation: load imbalance")
        evidence = {"issue": "hot_spot", "instance": "api-1", "load": "95%"}
```

#### Supporting Invariants

**DISCOVERY: Services are findable**
```
∀ service s, ∀ client c:
  Registered(s) → Discoverable(s, c) within TTL
```

Evidence: Registration with heartbeat, scope = cluster, lifetime = TTL

**CONSISTENCY: Configs converge**
```
∀ instance i1, i2 of service s, ∀ config_key k:
  Eventually (config[i1][k] = config[i2][k])
```

Evidence: Config version propagation, scope = service, lifetime = propagation_delay

**RESILIENCE: Failures don't cascade**
```
∀ service s1 → s2:
  FailureRate(s2) > threshold → CircuitOpen(s1, s2)
```

Evidence: Circuit breaker state, scope = client-service pair, lifetime = timeout

**EFFICIENCY: Resources are utilized**
```
∀ instance i of service s:
  Load(i) ≈ AvgLoad(s) ± threshold
```

Evidence: Load metrics, scope = instance, lifetime = measurement_window

### Mode Matrix for Coordination

Define operational modes with explicit degradation paths.

#### Target Mode

**Service Discovery**:
- All services registered with fresh health checks (evidence age <10s)
- Clients have up-to-date routing tables (version = latest)
- DNS fallback not needed

**Configuration**:
- All instances on same config version (version = v17)
- Feature flags evaluated with <1ms latency
- No overrides active (clean state)

**Resilience**:
- All circuit breakers closed (normal traffic flow)
- Backpressure signals = OK (no queue buildup)
- Concurrency within 80% of limit (headroom available)

**Load Balancing**:
- Request distribution even (max/avg <1.2×)
- All instances healthy and in rotation
- No sticky routing required

**Evidence**:
```python
target_mode_evidence = {
    "discovery": "Fresh(age<10s), scope=cluster",
    "config": "version=v17, all_instances",
    "resilience": "all_circuits=CLOSED",
    "load": "distribution_variance<0.2"
}
```

#### Degraded Mode

**Service Discovery**:
- Some services using stale registrations (evidence age 10-60s)
- Clients using cached routing tables (version = latest - 1)
- DNS fallback for critical services

**Configuration**:
- Config version skew (some instances v16, some v17)
- Feature flag evaluations using stale rules (cache)
- Temporary overrides active (workarounds)

**Resilience**:
- Some circuit breakers open (failures isolated)
- Backpressure signals = SLOW_DOWN (queue growing)
- Concurrency at 95% of limit (low headroom)

**Load Balancing**:
- Request distribution skewed (max/avg <2×)
- Some instances removed from rotation (health checks failing)
- Sticky routing for session affinity

**Evidence**:
```python
degraded_mode_evidence = {
    "discovery": "BoundedStale(age=10-60s), scope=cluster",
    "config": "version_skew, tolerable",
    "resilience": "some_circuits=OPEN, failures_isolated",
    "load": "distribution_variance<0.5, acceptable"
}
```

**Trigger Conditions**:
- Discovery: Health check failure rate >10%
- Config: Propagation delay >60s
- Resilience: Circuit trip rate >3 per minute
- Load: Instance failure or removal

#### Floor Mode

**Service Discovery**:
- Static service lists (hard-coded fallback)
- No health checks (assume all available)
- Local-only routing (no cross-zone)

**Configuration**:
- Default configuration (no remote config)
- Feature flags = all disabled (safe defaults)
- No dynamic overrides

**Resilience**:
- All circuit breakers open (reject all remote calls)
- Backpressure signals = REJECT (survival mode)
- Concurrency limit = 1 (minimal processing)

**Load Balancing**:
- Round-robin only (no health-based routing)
- Single local instance (no distribution)
- No retries (fail fast)

**Evidence**:
```python
floor_mode_evidence = {
    "discovery": "Static(hard_coded), scope=local",
    "config": "Defaults(no_remote), safe",
    "resilience": "all_circuits=OPEN, survival",
    "load": "single_instance, minimal"
}
```

**Trigger Conditions**:
- Discovery: Registry unreachable for >5min
- Config: Config service down, no cache
- Resilience: Failure rate >50%
- Load: Only one instance remains

#### Recovery Mode

**Service Discovery**:
- Re-registration of all services
- Health check warmup period (grace before routing)
- Gradual addition to routing tables

**Configuration**:
- Config reconciliation (pull latest, apply)
- Feature flag re-sync (fetch all flags)
- Override cleanup (remove temporary fixes)

**Resilience**:
- Circuit reset (OPEN → HALF_OPEN → CLOSED)
- Backpressure relief (drain queues, increase limits)
- Concurrency ramp-up (gradual increase to normal)

**Load Balancing**:
- Load rebalancing (redistribute requests)
- Health re-check (validate all instances)
- Gradual traffic increase (avoid thundering herd)

**Evidence**:
```python
recovery_mode_evidence = {
    "discovery": "Re-registering, warmup_period=30s",
    "config": "Reconciling, version→v17",
    "resilience": "Circuits=HALF_OPEN, testing",
    "load": "Rebalancing, gradual_traffic"
}
```

**Recovery Steps**:
1. Validate system state (check quorum, connectivity)
2. Re-establish evidence (registrations, health checks)
3. Reconcile inconsistencies (configs, routing tables)
4. Test critical paths (circuit half-open requests)
5. Gradually increase load (10% → 50% → 100%)
6. Monitor for regression (ready to re-enter Degraded)
7. Transition to Target (evidence stable for 5min)

### Production Patterns

#### Service Discovery Operations

**Health Check Configuration**:
```yaml
health_check:
  # Probe interval
  interval: 10s

  # Probe timeout
  timeout: 3s

  # Deregister after failures
  deregister_critical_service_after: 30s

  # Successes before healthy
  success_before_healthy: 2

  # Failures before critical
  failures_before_critical: 3

  # Check types
  checks:
    - id: "http"
      http: "http://localhost:8080/health"
      interval: "10s"
      timeout: "3s"

    - id: "memory"
      script: "/usr/local/bin/check_memory.sh"
      interval: "30s"
      timeout: "5s"

    - id: "ttl"
      ttl: "60s"
      notes: "Service self-reports health via API"
```

**Registration Pattern**:
```python
class ServiceRegistration:
    def __init__(self, consul, service_name, instance_id):
        self.consul = consul
        self.service_name = service_name
        self.instance_id = instance_id
        self.registered = False

    def register(self):
        """Register service with health checks."""
        self.consul.agent.service.register(
            name=self.service_name,
            service_id=self.instance_id,
            address=get_local_ip(),
            port=8080,
            check={
                'http': 'http://localhost:8080/health',
                'interval': '10s',
                'timeout': '3s',
                'deregister_critical_service_after': '30s'
            }
        )
        self.registered = True
        logging.info(f"Registered {self.instance_id}")

    def deregister(self):
        """Graceful deregistration."""
        if self.registered:
            self.consul.agent.service.deregister(self.instance_id)
            logging.info(f"Deregistered {self.instance_id}")

    def __enter__(self):
        self.register()
        return self

    def __exit__(self, *args):
        self.deregister()

# Usage
with ServiceRegistration(consul, "api", "api-1") as reg:
    # Service runs
    run_service()
# Automatic deregistration on exit
```

**Client Discovery Pattern**:
```python
class ServiceDiscoveryClient:
    def __init__(self, consul):
        self.consul = consul
        self.cache = {}
        self.cache_ttl = 30  # seconds

    def get_service_instances(self, service_name):
        """Get healthy service instances with caching."""
        now = time.time()

        # Check cache
        if service_name in self.cache:
            cached_at, instances = self.cache[service_name]
            if now - cached_at < self.cache_ttl:
                return instances

        # Query consul
        _, services = self.consul.health.service(
            service_name,
            passing=True  # Only healthy
        )

        instances = [
            {
                'address': s['Service']['Address'],
                'port': s['Service']['Port'],
                'id': s['Service']['ID']
            }
            for s in services
        ]

        # Update cache
        self.cache[service_name] = (now, instances)

        return instances

    def get_instance(self, service_name):
        """Get random healthy instance (client-side load balancing)."""
        instances = self.get_service_instances(service_name)

        if not instances:
            raise NoHealthyInstancesError(service_name)

        return random.choice(instances)

# Usage
client = ServiceDiscoveryClient(consul)
instance = client.get_instance("database")
conn = connect(instance['address'], instance['port'])
```

#### Configuration Rollout

**Gradual Rollout Pattern**:
```python
class GradualRollout:
    def __init__(self, feature_flag_client, metric_client):
        self.flags = feature_flag_client
        self.metrics = metric_client

    def rollout_feature(self, feature, target_percentage):
        """Gradually roll out feature with monitoring."""
        current = 0
        step = 10  # Increase by 10% each step
        wait_time = 300  # 5 minutes between steps

        while current < target_percentage:
            # Increase percentage
            current = min(current + step, target_percentage)
            self.flags.update_percentage(feature, current)

            logging.info(f"Rolled out {feature} to {current}%")

            # Wait for metrics
            time.sleep(wait_time)

            # Check for regression
            if self.detect_regression(feature, current):
                # Rollback
                previous = current - step
                self.flags.update_percentage(feature, previous)

                alert(f"Rollout {feature} failed at {current}%, rolled back to {previous}%")
                break

        else:
            logging.info(f"Successfully rolled out {feature} to {target_percentage}%")

    def detect_regression(self, feature, percentage):
        """Detect if rollout caused regression."""
        # Compare error rates
        baseline_errors = self.metrics.get_error_rate(
            feature=feature,
            variant='control',
            window='5m'
        )

        variant_errors = self.metrics.get_error_rate(
            feature=feature,
            variant='treatment',
            window='5m'
        )

        # Regression if error rate 50% higher
        if variant_errors > baseline_errors * 1.5:
            logging.warning(f"Regression detected: {variant_errors} vs {baseline_errors}")
            return True

        # Compare latency
        baseline_latency = self.metrics.get_latency_p99(
            feature=feature,
            variant='control',
            window='5m'
        )

        variant_latency = self.metrics.get_latency_p99(
            feature=feature,
            variant='treatment',
            window='5m'
        )

        # Regression if P99 latency 100ms worse
        if variant_latency > baseline_latency + 100:
            logging.warning(f"Latency regression: {variant_latency} vs {baseline_latency}")
            return True

        return False

# Usage
rollout = GradualRollout(feature_flags, metrics)
rollout.rollout_feature("new_checkout_flow", target_percentage=100)
```

#### Circuit Breaker Tuning

**Adaptive Circuit Breaker**:
```python
class AdaptiveCircuitBreaker:
    def __init__(self, name):
        self.name = name
        self.state = 'CLOSED'
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None

        # Adaptive parameters
        self.failure_threshold = 5
        self.success_threshold = 2
        self.timeout = 30  # seconds
        self.half_open_requests = 3
        self.window_size = 60  # seconds

        # Metrics for adaptation
        self.recent_failures = deque(maxlen=100)
        self.recent_latencies = deque(maxlen=100)

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == 'OPEN':
            # Check if timeout elapsed
            if time.time() - self.opened_at > self.timeout:
                self.state = 'HALF_OPEN'
                self.success_count = 0
                logging.info(f"Circuit {self.name}: OPEN → HALF_OPEN")
            else:
                raise CircuitOpenError(f"Circuit {self.name} is OPEN")

        if self.state == 'HALF_OPEN':
            # Limit requests in half-open
            if self.success_count + self.failure_count >= self.half_open_requests:
                raise CircuitOpenError(f"Circuit {self.name} half-open limit reached")

        # Execute function
        start = time.time()
        try:
            result = func(*args, **kwargs)

            # Success
            latency = time.time() - start
            self.on_success(latency)

            return result

        except Exception as e:
            # Failure
            self.on_failure()
            raise

    def on_success(self, latency):
        """Handle successful call."""
        self.recent_latencies.append(latency)

        if self.state == 'HALF_OPEN':
            self.success_count += 1

            # Close circuit if enough successes
            if self.success_count >= self.success_threshold:
                self.state = 'CLOSED'
                self.failure_count = 0
                self.success_count = 0
                logging.info(f"Circuit {self.name}: HALF_OPEN → CLOSED")

        elif self.state == 'CLOSED':
            # Decay failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    def on_failure(self):
        """Handle failed call."""
        now = time.time()
        self.recent_failures.append(now)
        self.last_failure_time = now

        if self.state == 'HALF_OPEN':
            # Immediate open on half-open failure
            self.state = 'OPEN'
            self.opened_at = now
            logging.info(f"Circuit {self.name}: HALF_OPEN → OPEN")

        elif self.state == 'CLOSED':
            self.failure_count += 1

            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                self.opened_at = now
                logging.info(f"Circuit {self.name}: CLOSED → OPEN")

                # Adapt threshold based on recent pattern
                self.adapt_threshold()

    def adapt_threshold(self):
        """Adapt failure threshold based on recent history."""
        # Count failures in window
        now = time.time()
        window_failures = [
            t for t in self.recent_failures
            if now - t < self.window_size
        ]

        # If failures clustered, lower threshold (trip faster)
        if len(window_failures) > 10:
            self.failure_threshold = max(3, self.failure_threshold - 1)
            logging.info(f"Circuit {self.name}: lowered threshold to {self.failure_threshold}")

        # Calculate P99 latency
        if len(self.recent_latencies) >= 10:
            p99 = np.percentile(self.recent_latencies, 99)

            # If latency degrading, lower threshold
            if p99 > 1.0:  # 1 second
                self.failure_threshold = max(3, self.failure_threshold - 1)
                logging.info(f"Circuit {self.name}: lowered threshold due to latency")

# Usage
circuit = AdaptiveCircuitBreaker("payment-api")

try:
    result = circuit.call(payment_api.charge, user_id, amount)
except CircuitOpenError:
    # Fallback
    result = use_cached_payment_method(user_id)
```

### Coordination at Different Scales

The mechanisms we've explored scale differently. Choose based on your scale.

#### Team Scale (10 nodes)

**Characteristics**:
- Humans can understand entire system
- Full mesh connectivity feasible
- Synchronous coordination acceptable
- Failure = node crash (rare)

**Patterns**:
- **Service Discovery**: Consul or etcd with strong consistency
- **Leader Election**: ZooKeeper ephemeral nodes or etcd elections
- **Configuration**: Central config server (Spring Cloud Config)
- **Health Checks**: Direct peer-to-peer checks (all-to-all)
- **Load Balancing**: Simple round-robin or random

**Evidence Requirements**:
- Fresh evidence (strong consistency)
- Global scope (all nodes agree)
- Short lifetime (10s health checks)

**Example**:
```python
# 10 nodes, simple leader election
def elect_leader(nodes):
    # All nodes try to acquire lock
    for node in nodes:
        if node.acquire_lock('/leader'):
            return node

    # Lock held by existing leader
    return get_lock_holder('/leader')
```

#### Department Scale (100 nodes)

**Characteristics**:
- Need dashboards to understand state
- Full mesh impractical (O(n²) = 10,000 connections)
- Some asynchrony required
- Failures more common

**Patterns**:
- **Service Discovery**: Consul with gossip (eventual consistency)
- **Leader Election**: Raft-based (etcd, Consul)
- **Configuration**: Hierarchical (global + regional)
- **Health Checks**: Sampled (each node checks k random peers)
- **Load Balancing**: Consistent hashing

**Evidence Requirements**:
- BoundedStale evidence acceptable (eventual consistency)
- Regional scope (partition by zone/rack)
- Medium lifetime (30s health checks)

**Example**:
```python
# 100 nodes, gossip-based discovery
def gossip_round(node, all_nodes):
    # Select k random peers
    peers = random.sample(all_nodes, k=3)

    # Exchange state
    for peer in peers:
        send(peer, node.state)
        node.merge(receive(peer))

    # Converges in O(log n) rounds
```

#### Company Scale (1,000 nodes)

**Characteristics**:
- System state partially observable
- Must partition (zones, regions, clusters)
- Asynchronous required
- Failures constant

**Patterns**:
- **Service Discovery**: Federated registries (per zone)
- **Leader Election**: Distributed (Raft clusters per zone)
- **Configuration**: Epidemic propagation (gossip)
- **Health Checks**: Probabilistic (failure detectors)
- **Load Balancing**: Rendezvous or jump hashing

**Evidence Requirements**:
- Eventual evidence (high availability)
- Zone/cluster scope (federation)
- Long lifetime (60s+ health checks)

**Example**:
```python
# 1000 nodes, federated discovery
class FederatedDiscovery:
    def __init__(self, zone):
        self.zone = zone
        self.local_registry = ConsulClient(zone)
        self.remote_registries = {
            z: ConsulClient(z) for z in other_zones
        }

    def discover(self, service):
        # Prefer local zone (low latency)
        local = self.local_registry.discover(service)
        if local:
            return local

        # Fallback to remote zones
        for zone, registry in self.remote_registries.items():
            remote = registry.discover(service)
            if remote:
                logging.info(f"Using {service} from zone {zone}")
                return remote

        raise ServiceNotFoundError(service)
```

#### Internet Scale (10,000+ nodes)

**Characteristics**:
- Emergent behavior (cannot design all interactions)
- Hierarchical required (DNS-style)
- Fully asynchronous
- Partitions, failures, attacks constant

**Patterns**:
- **Service Discovery**: DNS + anycast + CDN
- **Leader Election**: Multi-leader (per region)
- **Configuration**: CDN-based (edge caching)
- **Health Checks**: Statistical models (aggregate metrics)
- **Load Balancing**: Maglev or ECMP

**Evidence Requirements**:
- Stale evidence acceptable (availability critical)
- Hierarchical scope (global → region → zone)
- Very long lifetime (minutes to hours)

**Example**:
```python
# 10000+ nodes, anycast routing
class AnycastRouter:
    """Route to nearest healthy instance via BGP anycast."""

    def __init__(self):
        self.anycast_ip = "203.0.113.1"  # Announced from all regions

    def route(self, request):
        # Client connects to anycast IP
        # BGP routes to nearest region automatically
        # No service discovery needed!
        return connect(self.anycast_ip)

    def health_check(self):
        # If region unhealthy, withdraw BGP announcement
        # Traffic automatically flows to next-nearest region
        if not is_healthy():
            bgp_withdraw(self.anycast_ip)
```

### Case Studies

#### Kubernetes Coordination

**Architecture**:
```
API Server (central hub)
  ↓
etcd (backing store, Raft consensus)
  ↓
Controllers (watch API, reconcile state)
  ↓
Kubelet (node agent, reports status)
```

**Service Discovery**:
- Services are DNS records (`my-service.my-namespace.svc.cluster.local`)
- DNS backed by CoreDNS, queries API server
- Endpoints = list of pod IPs (updated by endpoint controller)

**Leader Election**:
- Controllers use lease-based election (stored in etcd)
- Each controller acquires lease: `/leases/kube-scheduler`
- Lease has TTL, renewed via heartbeat
- Only lease holder is active (others standby)

**Configuration**:
- ConfigMaps and Secrets (stored in etcd)
- Mounted into pods as files or env vars
- Changes require pod restart (or watch + reload)

**Health Checks**:
- Liveness probe: Container is running?
- Readiness probe: Container can serve traffic?
- Startup probe: Container finished starting?

**Evidence Flow**:
1. Pod starts → Kubelet reports to API server
2. API server writes to etcd → Raft commit
3. Endpoint controller watches API → Updates endpoints
4. CoreDNS watches endpoints → Updates DNS
5. Client queries DNS → Gets pod IPs → Connects

**Coordination Evidence**:
- API server is source of truth (strongly consistent via etcd)
- Controllers watch with resource versions (optimistic concurrency)
- Kubelet uses heartbeat (node lease, 10s TTL)
- DNS is eventually consistent (caching, TTL)

**Mode Matrix**:
- **Target**: API server reachable, etcd quorum, all controllers active
- **Degraded**: API server slow (etcd latency), some controllers down
- **Floor**: API server unreachable, pods continue running with last config
- **Recovery**: API server restored, controllers reconcile state

#### Netflix Eureka

**AP Choice** (Availability over Consistency):
- Services register with Eureka server
- Clients cache full registry (refresh every 30s)
- Eureka servers replicate peer-to-peer (eventual consistency)

**Self-Preservation Mode**:
- If >15% of services appear down (network issue suspected)
- Eureka stops deregistering services (assume stale data better than no data)
- Prefers serving potentially stale registrations over false negatives

**Zone Awareness**:
- Each service has availability zone metadata
- Clients prefer same-zone services (lower latency)
- Cross-zone fallback if local zone empty

**Evidence Trade-offs**:
- Client cache is BoundedStale (30s max staleness)
- Self-preservation accepts stale evidence explicitly
- Zone preference is best-effort (no guarantees)

**Why AP**:
- Netflix prioritizes availability (streaming can't be down)
- Stale service list acceptable (retry on connection failure)
- Partition tolerance critical (multi-region deployment)

#### HashiCorp Consul

**Hybrid CP/AP**:
- Service catalog is CP (Raft consensus, strongly consistent)
- Health checks are AP (gossip, eventually consistent)

**Multi-Datacenter Federation**:
- Each datacenter has own Raft cluster (local CP)
- Datacenters connected via WAN gossip (global AP)
- Queries default to local DC (strong consistency)
- Cross-DC queries are eventually consistent

**Gossip Pools**:
- LAN pool: Nodes in same DC (Serf)
- WAN pool: Server nodes across DCs (Serf)

**Service Mesh Integration**:
- Consul as control plane
- Envoy as data plane (sidecar proxy)
- Intentions = service-to-service permissions (stored in catalog, strongly consistent)

**Evidence Layering**:
- Catalog provides Fresh evidence (Raft, for correctness)
- Gossip provides BoundedStale evidence (fast failure detection)
- Intentions provide Authorization evidence (cryptographic)

**Coordination Pattern**:
```python
# Register service (CP, consistent)
consul.agent.service.register(name="api", ...)

# Check health (AP, fast)
is_healthy = consul.agent.checks()['service:api']['Status'] == 'passing'

# Discover services (CP or AP, choose per query)
# CP: Query catalog (authoritative, slower)
services_cp = consul.catalog.service("api")

# AP: Query health (fast, may be stale)
services_ap = consul.health.service("api", passing=True)
```

#### Apache ZooKeeper Recipes

ZooKeeper is a coordination primitive, not a full service discovery system. But it enables coordination patterns.

**Leader Election Recipe**:
```python
def elect():
    # Create ephemeral sequential node
    my_node = zk.create('/election/node-', ephemeral=True, sequence=True)
    # Result: /election/node-0000000042

    while True:
        children = zk.get_children('/election')
        children.sort()

        if children[0] == my_node.split('/')[-1]:
            # I'm leader
            return Leader()
        else:
            # Watch previous node
            prev_index = children.index(my_node.split('/')[-1]) - 1
            prev_node = children[prev_index]

            exists = zk.exists(f'/election/{prev_node}', watch=on_delete)
            if not exists:
                # Previous node deleted between get_children and exists
                # Retry
                continue

            # Wait for previous node to die
            return Follower(watch_node=prev_node)

def on_delete(event):
    # Previous node died, check if I'm leader now
    elect()
```

**Distributed Lock Recipe**:
```python
def acquire_lock(resource):
    # Create ephemeral sequential node
    my_node = zk.create(f'/locks/{resource}/lock-', ephemeral=True, sequence=True)

    while True:
        children = zk.get_children(f'/locks/{resource}')
        children.sort()

        if children[0] == my_node.split('/')[-1]:
            # I have the lock
            return Lock(my_node)
        else:
            # Wait for previous lock holder
            prev_index = children.index(my_node.split('/')[-1]) - 1
            prev_node = children[prev_index]

            zk.exists(f'/locks/{resource}/{prev_node}', watch=on_lock_released)
            return None

def release_lock(lock):
    zk.delete(lock.node)  # Delete ephemeral node
```

**Barrier Recipe**:
```python
def barrier(name, num_participants):
    # Create barrier node
    zk.create(f'/barriers/{name}', value=str(num_participants))

    # Each participant creates child node
    my_node = zk.create(f'/barriers/{name}/participant-', ephemeral=True, sequence=True)

    # Wait for all participants
    while True:
        children = zk.get_children(f'/barriers/{name}')
        if len(children) >= num_participants:
            # Barrier reached
            return

        # Watch for new participants
        zk.get_children(f'/barriers/{name}', watch=on_participant_joined)
        # Sleep or wait for watch event
```

**Evidence in ZooKeeper**:
- Ephemeral nodes are evidence of liveness (lifetime = session)
- Sequential numbers are evidence of order (monotonic)
- Watches are push-based evidence propagation (vs polling)

---

## Synthesis: Coordination Principles

### Design Principles

**1. Favor emergent behavior over central control**

Like ant colonies, design systems where global coordination emerges from local rules.

- Bad: Central load balancer decides all routing (bottleneck, SPOF)
- Good: Each client makes local routing decisions based on health (emergent load balancing)

**2. Use soft state with refresh**

State that expires unless refreshed prevents stale evidence.

- Service registration with TTL (expires if not renewed)
- Leases with heartbeat (automatically revoked on failure)
- Cache with TTL (eventually becomes consistent)

**3. Design for partition tolerance**

Partitions will happen. Design coordination to degrade gracefully.

- CP choice: Accept unavailability in minority partition
- AP choice: Accept inconsistency, resolve conflicts later
- Hybrid: Different choices for different data

**4. Build in feedback loops**

Systems self-correct through feedback.

- Circuit breakers react to error rate (feedback: errors → open circuit → fewer errors)
- Adaptive concurrency reacts to latency (feedback: latency → lower concurrency → better latency)
- Gossip protocols react to partition (feedback: no acks → retry with different peers)

**5. Layer coordination mechanisms**

Use cheap mechanisms first, expensive mechanisms only when needed.

- Layer 1: Local cache (no coordination)
- Layer 2: Gossip (cheap coordination)
- Layer 3: Consensus (expensive coordination)

Example: Consul uses gossip for health (fast), Raft for catalog (correct).

### Scaling Laws

**Discovery: O(log n) is achievable**

With gossip protocols:
- Each round, information spreads to 2× nodes (if fanout = 2)
- After O(log n) rounds, all nodes informed
- Per-node overhead: O(1) messages per round

**Health Checks: O(1) with sampling**

- Each node checks k random peers (k = constant)
- Total checks = n × k = O(n)
- Per-node overhead = O(1)
- Failure detection time = O(log n) with gossip

**Configuration: O(n) with caching**

- Initial propagation: O(n) messages (each node receives update)
- With caching: Only changed nodes receive update
- Amortized: O(1) per update

**Gossip Convergence: O(√n)**

- Epidemic model: susceptible → infected
- Convergence time = O(log n) rounds
- But with packet loss p, time ≈ O(log n / (1 - p))
- Space complexity: O(n) for membership

### Trade-offs

**Consistency vs Availability**

- Consistent systems (CP): Unavailable during partition in minority
- Available systems (AP): Inconsistent during partition, eventual consistency
- Choose based on business requirements (bank = CP, shopping cart = AP)

**Latency vs Accuracy**

- Fast coordination: Use local cache (may be stale)
- Accurate coordination: Query authoritative source (higher latency)
- Hybrid: Use cache with TTL, refresh in background

**Simplicity vs Scalability**

- Simple systems: Central coordinator (doesn't scale)
- Scalable systems: Distributed coordination (complex)
- Pragmatic: Start simple, evolve to distributed as scale demands

**Cost vs Reliability**

- Cheap: Single instance (can fail)
- Expensive: Multi-region replication (survives region failure)
- Economic: Risk assessment (how much does downtime cost?)

---

## Exercises

### Design

**1. Design service discovery for 10,000 nodes**

Requirements:
- Global deployment (5 regions)
- Sub-second discovery latency
- Graceful degradation during partition

Considerations:
- Federated registries (one per region)?
- Gossip within region, eventually consistent cross-region?
- DNS fallback for critical services?
- Health check strategy (sampling? hierarchical aggregation?)

**2. Create multi-region configuration system**

Requirements:
- Configurations propagate globally within 1 minute
- Strong consistency within region
- Eventual consistency cross-region
- Rollback capability

Design:
- Consensus per region (Raft cluster)?
- Merkle tree for cross-region sync?
- Version vectors for conflict detection?
- Hierarchical config (global → region → zone)?

**3. Build circuit breaker with adaptive thresholds**

Requirements:
- Adapts to changing error rates
- Different thresholds for different error types (5xx vs timeout)
- Gradual recovery (not binary open/closed)

Design:
- Sliding window for error tracking?
- Percentile-based thresholds (P99 error rate)?
- Half-open with limited requests?
- Exponential backoff for retry timing?

**4. Design distributed rate limiter**

Requirements:
- 1000 requests/second limit across 100 nodes
- No central coordinator (avoid bottleneck)
- Allow bursts up to 2× limit for 10 seconds

Design:
- Token bucket per node (10 req/s each)?
- Gossip to share token usage?
- Local enforcement with periodic reconciliation?
- Spillover tokens to neighbors when idle?

**5. Create chaos testing framework**

Requirements:
- Inject failures (network partition, node crash, latency)
- Verify system behavior (does it degrade predictably?)
- Automated testing (CI/CD integration)

Design:
- Failure injection points (proxy, iptables, process kill)?
- Invariant checking (are coordination invariants preserved)?
- Scenario library (partition, cascade, thundering herd)?

### Implementation

**1. Implement gossip protocol**

```python
class GossipProtocol:
    def __init__(self, node_id, peers):
        self.node_id = node_id
        self.peers = peers
        self.state = {}
        self.version = 0

    def gossip_round(self):
        # TODO: Implement SWIM-style gossip
        # 1. Select k random peers
        # 2. Send state to peers
        # 3. Receive state from peers
        # 4. Merge states
        # 5. Update version
        pass

    def merge_state(self, peer_state, peer_version):
        # TODO: Implement state merge with conflict resolution
        pass
```

**2. Build circuit breaker library**

```python
class CircuitBreaker:
    def __init__(self, name, config):
        # TODO: Implement state machine (CLOSED, OPEN, HALF_OPEN)
        # TODO: Track success/failure counts
        # TODO: Implement timeout and retry logic
        pass

    def call(self, func, *args, **kwargs):
        # TODO: Implement call with circuit breaker protection
        pass
```

**3. Create service registry**

```python
class ServiceRegistry:
    def __init__(self):
        # TODO: Implement registration with TTL
        # TODO: Implement health checks
        # TODO: Implement watch/notification
        pass

    def register(self, service_name, instance_id, address, port):
        pass

    def discover(self, service_name):
        pass
```

**4. Implement distributed tracing**

```python
class Tracer:
    def __init__(self):
        # TODO: Implement trace context propagation
        # TODO: Implement span creation
        # TODO: Implement sampling decisions
        pass

    def start_span(self, operation_name, parent_context=None):
        pass

    def inject(self, span, headers):
        pass

    def extract(self, headers):
        pass
```

**5. Build feature flag system**

```python
class FeatureFlags:
    def __init__(self):
        # TODO: Implement flag storage
        # TODO: Implement gradual rollout
        # TODO: Implement targeting (user, region)
        pass

    def is_enabled(self, flag, user_id=None, context=None):
        pass

    def update_rollout(self, flag, percentage):
        pass
```

### Analysis

**1. Measure discovery latency**

- Instrument service registration (time from register to discoverable)
- Measure client discovery (time from query to receive instances)
- Analyze percentiles (P50, P99, P99.9)
- Correlate with system load (does latency increase with node count?)

**2. Analyze configuration drift**

- Compare configs across all instances
- Identify drift (instances with different versions)
- Measure convergence time (from update to all-instances-consistent)
- Find stragglers (instances slow to update)

**3. Calculate circuit breaker effectiveness**

- Measure requests blocked (how many errors prevented?)
- Measure cascade prevention (did circuit break prevent downstream overload?)
- Analyze false positives (circuit opened unnecessarily?)
- Optimize thresholds (minimize false positives while preventing cascades)

**4. Trace request paths**

- Visualize request flows (service dependency graph)
- Identify critical paths (longest latency chain)
- Find bottlenecks (service with highest latency contribution)
- Detect anomalies (requests with unusual paths)

**5. Profile coordination overhead**

- Measure coordination costs (gossip messages, heartbeats, consensus rounds)
- Compare to application traffic (what % overhead?)
- Identify optimization opportunities (can we reduce heartbeat frequency?)
- Calculate cost (network bandwidth, CPU for coordination)

---

## Key Takeaways

**Coordination must scale sub-linearly**

O(n²) algorithms don't scale to thousands of nodes. Use gossip (O(log n)), consistent hashing (O(1)), hierarchical structures (O(log n)).

**Emergent behavior beats central control**

Ant colonies, traffic lights, and distributed systems all show: local rules create global coordination. Design for emergence, not control.

**Soft state enables resilience**

State with TTL auto-corrects. Registration expires if not refreshed. Leases auto-revoke on failure. Caches auto-invalidate. Embrace ephemeral evidence.

**Feedback loops ensure stability**

Circuit breakers react to errors. Adaptive concurrency reacts to latency. Gossip reacts to partitions. Systems self-correct through feedback.

**Layer simple mechanisms**

Start with local (cache), escalate to distributed (gossip), only use expensive (consensus) when needed. Don't use Raft for everything.

**Monitor everything**

Coordination failures are subtle. Monitor: evidence age, quorum status, circuit states, gossip convergence, health check pass rates.

**Test coordination failures**

Chaos engineering: inject partitions, kill nodes, delay messages. Verify: does system degrade predictably? Do invariants hold? Does it recover?

---

## Further Reading

### Books

- **"Distributed Systems for Fun and Profit"** by Mikito Takada
  - Concise introduction to distributed systems concepts
  - Covers CAP, consistency models, time and order
  - Free online book

- **"Site Reliability Engineering"** by Google
  - Chapter on distributed coordination (Chubby, Borg)
  - Production patterns for service discovery, health checking
  - Real-world trade-offs and lessons learned

- **"Release It!"** by Michael Nygard
  - Circuit breakers, bulkheads, timeouts
  - Stability patterns and anti-patterns
  - Production war stories

- **"Antifragile"** by Nassim Taleb
  - Systems that gain from disorder
  - Relevant to chaos engineering and resilience
  - Mental model for embracing failure

### Papers

**Coordination Protocols**:

- **SWIM: Scalable Weakly-consistent Infection-style Process Group Membership Protocol** (2002)
  - Gossip-based failure detection
  - O(log n) convergence with O(1) per-node overhead
  - Foundation for Consul, Cassandra membership

- **Epidemic Algorithms for Replicated Database Maintenance** (1987)
  - Original epidemic/gossip paper
  - Probabilistic guarantees
  - Analysis of convergence time

- **The Phi Accrual Failure Detector** (2004)
  - Adaptive failure detection
  - Used in Cassandra, Akka
  - Better than timeout-based detection

**Service Discovery**:

- **Chord: A Scalable Peer-to-peer Lookup Service** (2001)
  - DHT for distributed hash table
  - O(log n) lookup
  - Foundation for many P2P systems

- **Consistent Hashing and Random Trees** (1997)
  - Original consistent hashing paper
  - Minimal disruption on node add/remove
  - Used in CDNs, distributed caches

**Resilience**:

- **On Designing and Deploying Internet-Scale Services** (2007)
  - Microsoft's operational wisdom
  - Graceful degradation, health monitoring
  - Service design for operations

### Production Blogs

- **Netflix Tech Blog**: Eureka, Zuul, Hystrix (circuit breaker)
- **Uber Engineering**: Ringpop (gossip-based coordination)
- **Airbnb Engineering**: SmartStack (service discovery)
- **Twitter Engineering**: Finagle (RPC with circuit breakers)
- **Google Cloud Blog**: Maglev (load balancing)

### Tools & Frameworks

- **Consul**: Service discovery, health checking, KV store
- **etcd**: Distributed KV store, service discovery
- **Envoy**: Service mesh data plane
- **Istio**: Service mesh control plane
- **Jaeger**: Distributed tracing
- **Prometheus**: Metrics and monitoring
- **Chaos Monkey**: Chaos engineering (Netflix)

---

## Chapter Summary

**"At scale, coordination emerges from simple local rules, not centralized control—and evidence-based operation makes this emergence comprehensible and reliable."**

This chapter explored coordination at scale—how distributed systems discover services, propagate configurations, isolate failures, and balance load without central control.

### Key Mental Models

**1. Emergent Coordination**

Like ant colonies using pheromone trails, distributed systems coordinate through local interactions. No master node, no global state, just simple rules that compose into complex behavior.

**2. Evidence-Based Operation**

All coordination state is evidence: service registrations (liveness evidence), health checks (freshness evidence), circuit breakers (failure evidence), routing tables (reachability evidence). Coordination is about generating, propagating, and verifying evidence.

**3. Scale-Appropriate Mechanisms**

What works at 10 nodes fails at 10,000. Team scale: central coordinator. Company scale: federated. Internet scale: hierarchical + anycast. Choose mechanisms that scale sub-linearly.

**4. Graceful Degradation**

Coordination failures happen. Systems must degrade predictably: Target → Degraded → Floor → Recovery. Explicit modes with documented evidence requirements.

**5. Layered Coordination**

Use cheap mechanisms first (local cache), escalate to expensive (consensus) only when needed. Consul: gossip for health (fast), Raft for catalog (correct).

### The Evidence Framework

Coordination evidence has:
- **Scope**: Local, zone, region, global
- **Lifetime**: TTL, lease duration, continuous
- **Binding**: What it proves (liveness, config version, health)
- **Freshness**: Fresh, BoundedStale, Eventual, Historical

Example: Service registration = {scope: cluster, lifetime: 30s TTL, binding: instance → address, freshness: Fresh if age <30s}

### Practical Takeaways

**Design**:
- Favor gossip over central coordination (scales better)
- Use soft state with TTL (auto-corrects on failure)
- Layer evidence (cheap → expensive escalation)
- Design for partition tolerance (AP or CP choice explicit)

**Operations**:
- Monitor evidence age (detect staleness)
- Track mode transitions (Target → Degraded → Recovery)
- Alert on invariant violations (COORDINATION broken)
- Test with chaos (inject partitions, verify degradation)

**Debugging**:
- Service not discoverable? Check registration evidence (expired TTL? failed health check?)
- Config drift? Check propagation evidence (gossip lag? partition?)
- Cascading failure? Check circuit breaker evidence (should be OPEN, why CLOSED?)
- Load imbalance? Check routing evidence (hash function? health weights?)

### What's Next

Coordination enables services to work together. But working together means calling each other—and every network call can fail, timeout, or return garbage. How do we make remote calls reliable? How do we handle partial failures? How do we maintain invariants across service boundaries?

Chapter 10 explores **RPC and Communication Patterns**—the mechanisms we use to make distributed systems feel like local systems, despite the network's unreliability. We'll see how RPC, gRPC, GraphQL, and message queues embody different trade-offs, and how evidence capsules propagate guarantees across communication boundaries.

---

*This chapter's guarantee vector: `⟨Scope=Global, Order=Causal, Isolation=RA, Freshness=BoundedStale, Idempotency=Idem, Authorization=Auth⟩` — We've explored global coordination patterns, established causal understanding of mechanisms, provided read-atomic knowledge, maintained bounded staleness with production examples, offered idempotent insights you can revisit, all with proper attribution to research and production systems.*

*Context capsule for next chapter: `{invariant: COMMUNICATION, evidence: RPC semantics, boundary: service-to-service, mode: Target, fallback: revisit coordination as foundation}`*

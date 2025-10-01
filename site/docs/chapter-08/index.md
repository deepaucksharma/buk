# Chapter 8: The Modern Distributed System

## Introduction: Composing at Scale

Modern distributed systems aren't built—they're composed.

From services that communicate through meshes, to events that flow through streams, to data products that serve analytics at scale, today's architectures are fundamentally about **composition**. Not the careful assembly of monolithic components, but the dynamic orchestration of hundreds or thousands of independent services, each with its own lifecycle, guarantees, and failure modes.

When Netflix deploys a change, it ripples through 1000+ microservices. When Uber processes a ride request, it traverses 50+ services across multiple regions. When LinkedIn publishes a post, it flows through Kafka clusters handling millions of events per second. These aren't edge cases—this is modern distributed systems at scale.

But composition amplifies every challenge we've explored: impossibility results compound across service boundaries, time and causality become harder to track across meshes, consensus must scale to thousands of participants, and failures cascade in unexpected ways. The question isn't whether to compose—scale demands it—but **how to compose safely**, preserving invariants while degrading predictably when components fail.

### The Compositional Shift

**2000s: The Monolith Era**
Applications were single deployments. All logic in one codebase. Horizontal scaling meant load balancing identical copies. State lived in a single database cluster. Coordination was local. Failures were total.

**Problem**: Teams couldn't scale independently. Deployments required full system restarts. One bug brought down everything. Innovation was serialized through monolithic release cycles.

**2010s: The Microservices Explosion**
"Break the monolith into services." Each service owns its data, deploys independently, scales horizontally. Amazon mandated service-oriented architecture in 2002. Netflix pioneered chaos engineering. The industry followed.

**Problem**: Distributed monoliths emerged—fine-grained services that were tightly coupled through synchronous calls. Debugging became impossible (where did this request fail?). Network partitions caused cascading failures. The complexity moved from code to infrastructure.

**2015-2020: The Infrastructure Layer**
"We need infrastructure to manage service communication." Service meshes (Istio, Linkerd) handled traffic management, security, and observability. API gateways (Kong, Envoy) managed external access. Event streaming platforms (Kafka, Pulsar) enabled asynchronous integration. Container orchestration (Kubernetes) automated deployment and scaling.

**Problem**: Too many moving parts. Operational complexity exploded. Observability became critical but hard. Every company was rebuilding the same infrastructure patterns.

**2020-Present: The Compositional Architecture**
"Services + Meshes + Events + Data Products." Modern systems compose multiple architectural patterns:
- **Service mesh** for synchronous service-to-service communication
- **Event streaming** for asynchronous integration and data pipelines
- **Data mesh** for federated data ownership and self-serve analytics
- **API gateway** for external API management
- **Serverless** for event-driven compute

The architecture is **deliberately compositional**: each pattern solves specific problems, and they compose through well-defined boundaries with explicit evidence propagation.

### Why Modern Architecture Emerged

Four forces drove the shift:

**1. Scale Requirements Changed**
- 2000s: Thousands of requests/second, millions of users
- 2020s: Millions of requests/second, billions of users
- Vertical scaling hit physical limits
- Horizontal scaling required distribution

**2. Teams Grew Differently**
- Monolithic teams: 10-50 engineers, single codebase
- Microservices teams: 1000+ engineers, 100+ services
- Conway's Law: System architecture mirrors organization structure
- Independent teams need independent deployments

**3. Deployment Velocity Needs**
- Monoliths: Weekly or monthly releases
- Microservices: Multiple deployments per day per service
- Business competition demands rapid iteration
- Failure isolation enables independent deployment

**4. Failure Isolation Demands**
- Monolith failure: Everything down
- Service failure: Degraded experience, not total outage
- Resilience through bulkheads
- Graceful degradation over total failure

### What This Chapter Reveals

By the end, you'll understand:

1. **Service Mesh Architecture**: How sidecars, control planes, and data planes provide infrastructure for service communication
2. **Event-Driven Architecture**: How event streaming, event sourcing, CQRS, and sagas enable loose coupling
3. **Data Mesh Principles**: How domain-oriented data ownership and data products scale analytics
4. **Modern Composition Patterns**: How these patterns compose, where they fail, and how to operate them
5. **Production Reality**: Real case studies from Netflix, Uber, Spotify, Airbnb, LinkedIn

More crucially, you'll learn the **compositional mental model**:

**Modern systems preserve invariants across compositional boundaries by propagating evidence through context capsules, with explicit guarantee vectors that weaken predictably at each composition point, and mode matrices that coordinate degradation across layers.**

### The Compositional Invariant

The fundamental invariant of modern distributed systems is **COMPOSABILITY**:

**Services compose safely**: Two services can communicate without violating each other's invariants
**Events flow correctly**: Event ordering and delivery guarantees are preserved end-to-end
**Data products integrate**: Analytics pipelines can consume data without breaking producers
**Policies enforce uniformly**: Security, rate limiting, and compliance apply consistently

This invariant is maintained through **evidence at boundaries**:
- Service mesh: mTLS certificates prove identity, trace contexts prove causality
- Event streams: Sequence numbers prove order, consumer offsets prove delivery
- Data mesh: Schema versions prove compatibility, lineage graphs prove provenance
- API gateway: Auth tokens prove authorization, rate limit counters prove compliance

When evidence cannot be maintained (network partitions, service failures, data quality issues), the system **degrades explicitly** through documented mode transitions, weakening guarantees in known ways rather than failing silently.

Let's begin with the story that made service mesh inevitable: Netflix's journey from DVD shipping to 1000+ microservices.

---

## Part 1: INTUITION (First Pass) — The Felt Need

### The Netflix Story: From Monolith to Service Mesh

**2000-2008: The Monolithic Era**

Netflix started as a DVD-by-mail service with a classic monolithic architecture:
- Single Java application
- Oracle database
- Vertical scaling (bigger machines)
- Deployments: monthly, required scheduled downtime

This worked fine for DVD shipping. But in 2007, Netflix launched streaming video. Traffic exploded. The monolith couldn't keep up.

**2008-2012: The Microservices Migration**

Netflix bet the company on cloud and microservices:
- Migrated from datacenter to AWS
- Broke monolith into hundreds of services
- Each service owned its database (polyglot persistence)
- Independent deployment and scaling

**The problem emerged quickly**: Service-to-service communication was chaos.

**Example: Playing a video required**:
1. Authentication service (verify user)
2. Subscription service (check payment status)
3. Recommendation service (track viewing for recommendations)
4. License service (verify content rights for user's region)
5. CDN routing service (select optimal video server)
6. Playback service (start streaming)

Each call added latency. Each service could fail independently. Failures cascaded: if the recommendation service was down, should video playback fail? Network issues between services caused mysterious timeouts. Security was ad-hoc—how does service A know request came from legitimate service B?

**2012-2015: Building Infrastructure**

Netflix built custom solutions:
- **Eureka**: Service discovery (which instances are alive?)
- **Ribbon**: Client-side load balancing (which instance should I call?)
- **Hystrix**: Circuit breaker (stop calling failing services)
- **Zuul**: API gateway (external traffic routing)
- **Chaos Monkey**: Randomly kill instances to test resilience

This worked but required every service team to integrate these libraries. Library upgrades were painful. Polyglot services (Python, Node.js) couldn't use Java libraries.

**2016-Present: The Service Mesh Era**

The industry realized: "Service communication infrastructure shouldn't be in application libraries—it should be in the infrastructure layer."

**Service mesh emerged**: Deploy a sidecar proxy (Envoy) next to every service. The proxy handles:
- Service discovery
- Load balancing
- Circuit breaking
- Retries and timeouts
- mTLS encryption
- Distributed tracing
- Metrics collection

The service communicates with its local sidecar. The sidecar handles all network complexity. Services written in any language get the same infrastructure for free.

**Evidence at work**:
- **Service identity**: mTLS certificates prove "I am service A" (Auth evidence)
- **Health checks**: Sidecar proves "my service is alive" (Liveness evidence)
- **Trace context**: Distributed tracing proves causality across services (Causal evidence)
- **Traffic policies**: Control plane proves "route 10% of traffic to v2" (Routing evidence)

**Mode matrix**:
- **Target**: All services healthy, mesh routing optimally
- **Degraded**: Service unhealthy, circuit breaker activated, traffic routed to healthy instances
- **Floor**: Too many services failing, load shedding activated, only critical paths served
- **Recovery**: Services restarting, gradual traffic ramp-up (canary deployment)

### The Uber Evolution: Finding the Right Granularity

**2012-2014: Escaping the Monolith**

Uber started with a monolithic Python application. As they scaled globally:
- Codebase became unmaintainable (500k+ lines)
- Teams blocked each other (shared database)
- Deployments were risky (all-or-nothing)

**The solution**: Microservices. Aggressively.

**2015-2017: The Microservices Explosion**

Uber decomposed the monolith into 2200+ microservices:
- Trip service
- Driver location service
- Payment service
- Pricing service
- Matching service (match riders to drivers)
- Fraud detection service
- ...and 2000 more

**The problems**:
1. **Too granular**: A single ride request touched 50+ services
2. **Network overhead**: Inter-service latency dominated total latency
3. **Debugging nightmare**: Trace a request through 50 services? Good luck.
4. **Operational complexity**: 2200 services meant 2200 deployment pipelines, 2200 on-call rotations

**Example**: The pricing calculation was split across 12 microservices:
- Base fare service
- Surge pricing service
- Promotions service
- Tax calculation service
- Currency conversion service
- Rounding service
- ...

Each service call added 5-20ms latency. Total pricing calculation: 120-240ms. For something that should be a local function call.

**2018-Present: The Reversal to "Macroservices"**

Uber realized: "We went too far. Not every function needs to be a service."

**New principle: Domain-oriented services**
- Group related functionality into larger services
- Use service boundaries that align with business domains (not technical layers)
- Accept some internal coupling to reduce network calls

**Result**:
- Consolidated 2200 services to ~800 "macroservices"
- Pricing service: One service handling all pricing logic internally
- Latency: 120ms → 15ms
- Operational complexity: Dramatically reduced

**The lesson**: Service granularity is a design trade-off:
- **Too coarse** (monolith): Deployment coupling, scaling rigidity
- **Too fine**: Network overhead, operational complexity
- **Just right**: Domain boundaries aligned with team ownership

**Evidence boundary principle**: Draw service boundaries where evidence changes meaning. Pricing is all about "total cost" evidence—keep it in one service. Payment is about "transaction commit" evidence—separate service with strong consistency.

### Why Modern Architecture Emerged: The Felt Pain

These stories reveal the forces that created modern distributed systems:

**1. Synchronous Service Meshes Aren't Enough**

Netflix's mesh handles synchronous request/response well. But what about:
- Analytics pipelines processing billions of events?
- Machine learning models training on petabytes of data?
- Real-time features like "who's viewing this video right now?"

Service mesh is optimized for request/response, not data pipelines. **Event streaming** emerged to handle asynchronous, high-throughput data flows.

**2. Every Service Owning Data Creates Data Silos**

Uber's 800 services each own their data:
- Driver service: driver profiles, locations, availability
- Trip service: ride requests, matches, completions
- Payment service: payment methods, transactions

Analytics question: "What's the average trip distance for drivers who joined in the last 6 months?"

This requires joining data across services. Options:
- **Service-to-service calls**: Too slow for analytics, couples services
- **Shared database**: Violates service autonomy, creates coupling
- **ETL pipeline**: Extract data nightly, centralize in warehouse (stale, brittle)

**Data mesh** emerged: Treat data as products owned by domain teams, exposed through well-defined interfaces, enabling self-serve analytics without centralizing ownership.

**3. Security and Policy Enforcement Is Infrastructure, Not Application Code**

Every service needs:
- Authentication and authorization
- Rate limiting
- Request logging
- Compliance (GDPR, PCI)

Building this in each service is redundant and error-prone. **API gateways** emerged to centralize cross-cutting concerns at system boundaries.

**4. Event-Driven Features Need Event-Driven Infrastructure**

Modern applications are increasingly event-driven:
- Real-time dashboards
- Notification systems
- Recommendation engines
- Fraud detection

These need **event streaming platforms** (Kafka, Pulsar) that provide:
- Durable event logs (replay history)
- Ordering guarantees (process in sequence)
- Scale (millions of events/second)
- Integration patterns (event sourcing, CQRS, sagas)

The modern distributed system composes these patterns: service mesh for synchronous communication, event streaming for asynchronous integration, data mesh for analytics, API gateway for external access, all operating on infrastructure (Kubernetes) that abstracts deployment and scaling.

---

## Part 2: UNDERSTANDING (Second Pass) — The Patterns

### Service Mesh Architecture

A service mesh provides infrastructure for service-to-service communication. It consists of two planes:

**Data Plane**: Sidecar proxies deployed next to every service instance
**Control Plane**: Centralized management for configuring proxies

#### The Sidecar Pattern

**Architecture**:
```
┌─────────────┐
│  Service A  │←─────┐
└─────────────┘      │ localhost
       ↓             │
┌─────────────┐      │
│   Envoy     │←─────┘
│  (Sidecar)  │
└─────────────┘
       ↓ network
┌─────────────┐
│   Envoy     │
│  (Sidecar)  │
└─────────────┘
       ↑
┌─────────────┐
│  Service B  │
└─────────────┘
```

**How it works**:
1. Service A wants to call Service B
2. Service A sends request to localhost (its sidecar)
3. Sidecar intercepts, applies policies (auth, rate limiting, tracing)
4. Sidecar routes to Service B's sidecar (service discovery, load balancing)
5. Service B's sidecar receives, applies policies, forwards to Service B

**Envoy as the universal data plane**:
- C++ proxy designed for service mesh use
- HTTP/1.1, HTTP/2, gRPC support
- Dynamic configuration (no restarts)
- Rich observability (metrics, tracing, logging)
- Used by Istio, Consul Connect, AWS App Mesh

**Evidence generated**:
- **Service identity**: X.509 certificates (SPIFFE standard)
- **Trace context**: W3C Trace Context headers (traceparent, tracestate)
- **Health status**: HTTP health check responses
- **Traffic metrics**: Request count, latency, error rates

**Guarantee vector**: `⟨Route, Causal, RA, Fresh(cert), Idem, Auth(mTLS)⟩`
- Route scope (cluster-local)
- Causal ordering (trace context)
- Read-atomic consistency (routing decisions)
- Fresh certificates (short TTL, auto-rotation)
- Idempotent routing (retries safe)
- Authenticated (mTLS)

#### Control Plane Patterns

**Istio Architecture**:
```
Control Plane:
  ├─ Istiod (unified control plane)
  │   ├─ Pilot: Service discovery, traffic management
  │   ├─ Citadel: Certificate management (CA)
  │   └─ Galley: Configuration validation
  └─ API Server: Kubernetes integration

Data Plane:
  └─ Envoy sidecars (one per pod)
```

**Configuration**:
- **VirtualService**: Routing rules (canary, A/B testing)
- **DestinationRule**: Load balancing, circuit breakers
- **Gateway**: Ingress/egress configuration
- **ServiceEntry**: External service integration

**Linkerd Simplicity**:
- Written in Rust (lightweight, memory-safe)
- Simpler than Istio (fewer moving parts)
- Default mTLS (zero config)
- Automatic retries and timeouts

**Trade-off**: Less flexibility, easier operation.

**Consul Connect**:
- Built into Consul (service discovery + mesh)
- Multi-datacenter support (WAN federation)
- Centralized configuration
- Intent-based security (which services can talk)

**AWS App Mesh**:
- Managed service mesh (no control plane to run)
- Integrates with AWS services (ALB, Cloud Map)
- X-Ray tracing integration
- VPC-level networking

**Control plane evidence**:
- **Configuration version**: Which rules are active?
- **Certificate validity**: mTLS certs expire in minutes, auto-rotated
- **Service registry**: Which instances are healthy?
- **Policy audit log**: Who changed routing rules?

#### Traffic Management

**Load Balancing Strategies**:

**Round robin**: Distribute evenly across instances
```
Request 1 → Instance A
Request 2 → Instance B
Request 3 → Instance C
Request 4 → Instance A (cycle)
```

**Least connections**: Route to instance with fewest active connections
- Better for long-lived connections
- Requires connection tracking

**Weighted**: Distribute based on instance capacity
```
Instance A (8 CPU): 40% traffic
Instance B (4 CPU): 20% traffic
Instance C (8 CPU): 40% traffic
```

**Consistent hashing**: Route based on request attribute (user ID, session)
- Sticky sessions (same user → same instance)
- Better cache hit rates
- Useful for stateful services

**Circuit Breakers**:

Prevent cascading failures by stopping calls to failing services.

**States**:
- **Closed**: Normal operation, requests flow
- **Open**: Too many failures, reject requests immediately (fail fast)
- **Half-open**: Try one request to check if service recovered

**Configuration**:
```yaml
circuitBreaker:
  consecutiveErrors: 5      # Open after 5 errors
  interval: 30s             # Check every 30s
  baseEjectionTime: 30s     # Stay open for 30s minimum
  maxEjectionPercent: 50    # Don't eject >50% of instances
```

**Evidence**: Error rate, latency percentiles → trigger state transition.

**Mode transitions**:
- Target → Degraded: Circuit opens (too many errors)
- Degraded → Recovery: Half-open (testing recovery)
- Recovery → Target: Circuit closes (service healthy)

**Retries with Backoff**:

**Exponential backoff**:
```
Attempt 1: immediate
Attempt 2: wait 100ms
Attempt 3: wait 200ms
Attempt 4: wait 400ms
Attempt 5: wait 800ms
```

**Jitter**: Add randomness to prevent thundering herd
```
wait = base_delay * (2 ^ attempt) * random(0.5, 1.5)
```

**Retry budget**: Limit total retries (e.g., no more than 20% extra load)

**Idempotency requirement**: Only retry if operation is idempotent (GET, PUT with idempotency key).

**Canary Deployments**:

Gradually roll out new version:
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        user-agent:
          regex: ".*Chrome.*"
    route:
    - destination:
        host: reviews
        subset: v2       # Chrome users get v2
      weight: 100
  - route:
    - destination:
        host: reviews
        subset: v1       # Everyone else gets v1
      weight: 90
    - destination:
        host: reviews
        subset: v2       # 10% to v2
      weight: 10
```

**Progressive rollout**:
- 5% traffic → v2 (monitor metrics)
- 25% traffic → v2 (if healthy)
- 50% traffic → v2
- 100% traffic → v2
- Remove v1

**Automated canary analysis**: Monitor error rates, latency. Automatic rollback if degradation detected.

**Blue-Green Deployments**:

Run two environments (blue=current, green=new):
1. Deploy v2 to green environment (zero traffic)
2. Test green environment
3. Switch 100% traffic to green (atomic cutover)
4. Keep blue running (instant rollback if issues)
5. After validation, decommission blue

**Faster than canary** (single switch vs gradual rollout) but **riskier** (100% traffic at once).

**Traffic Shadowing** (mirroring):

Send production traffic to new version without using responses:
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 100
    mirror:
      host: reviews
      subset: v2      # Shadow traffic to v2
    mirrorPercentage:
      value: 10.0     # Mirror 10% of requests
```

**Use case**: Test new version with production traffic patterns without affecting users. Observe error rates, latency, resource usage.

#### Security in the Mesh

**Zero-Trust Networking**:

Traditional security: "Trust anything inside the network perimeter."

**Problem**: Once attacker gets inside, they can access everything.

**Zero-trust**: "Trust nothing. Verify everything."
- Every service must authenticate
- Every request must be authorized
- Encrypt all traffic (even internal)

**Service Identity (SPIFFE)**:

**SPIFFE** (Secure Production Identity Framework For Everyone):
- Standard for service identity
- Format: `spiffe://trust-domain/path` (e.g., `spiffe://cluster.local/ns/default/sa/reviews`)
- Encoded in X.509 certificates

**SPIRE** (SPIFFE Runtime Environment):
- Issues certificates to services
- Automatic rotation (short-lived certs, e.g., 1-hour TTL)
- Workload API for fetching certs

**mTLS (Mutual TLS)**:

Both client and server authenticate:
1. Client connects to server
2. Server presents certificate (signed by CA)
3. Client verifies server certificate
4. Client presents certificate
5. Server verifies client certificate
6. Encrypted channel established

**Evidence**: Both parties have proof of each other's identity. Can't be spoofed.

**Certificate Rotation**:

Certificates expire quickly (1 hour to 1 day). Automatic rotation:
1. Service requests new cert from Citadel/SPIRE
2. Presents short-lived proof (e.g., Kubernetes service account token)
3. Receives new X.509 cert
4. Starts using new cert
5. Old cert expires

**No downtime**: Services use new cert before old expires.

**Policy Enforcement**:

**Authorization policies**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: reviews-policy
spec:
  selector:
    matchLabels:
      app: reviews
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/productpage"]
    to:
    - operation:
        methods: ["GET"]
```

Only `productpage` service can GET from `reviews` service. Everything else denied.

**Guarantee vector for mesh security**: `⟨Cluster, Causal, RA, Fresh(1h), Idem, Auth(mTLS+policy)⟩`

### Event-Driven Architecture

Service meshes handle synchronous request/response. Event-driven architecture handles asynchronous, loosely coupled integration.

#### Event Streaming Platforms

**Apache Kafka Architecture**:

```
Producers → Broker Cluster (Topics/Partitions) → Consumers
                ↓
            ZooKeeper (Metadata, coordination)
```

**Core concepts**:
- **Topic**: Logical channel (e.g., "user-events")
- **Partition**: Shard of topic for parallelism (e.g., topic has 10 partitions)
- **Producer**: Writes events to topic
- **Consumer**: Reads events from topic
- **Consumer group**: Multiple consumers coordinate to share partitions

**Guarantees**:
- **Ordering**: Within a partition, events are strictly ordered
- **Durability**: Events persisted to disk, replicated across brokers
- **At-least-once delivery**: Consumer may see duplicate events
- **Exactly-once semantics** (with transactions): No duplicates

**Partitioning**:
```
Topic: user-events (3 partitions)

Event (user_id=123) → hash(123) % 3 = partition 1
Event (user_id=456) → hash(456) % 3 = partition 0
Event (user_id=789) → hash(789) % 3 = partition 2
```

All events for user 123 go to partition 1 → **ordered per user**.

**Consumer groups**:
```
Consumer Group: analytics
  ├─ Consumer A: reads partition 0, 1
  ├─ Consumer B: reads partition 2

Consumer Group: recommendations
  ├─ Consumer C: reads partition 0
  ├─ Consumer D: reads partition 1
  ├─ Consumer E: reads partition 2
```

Each group processes all events independently. Within a group, each partition consumed by exactly one consumer.

**Evidence**:
- **Offset**: Position in partition (e.g., offset 12,345)
- **Commit**: Consumer stores last processed offset
- **Sequence number**: Per-partition monotonic counter
- **Timestamp**: Event creation time

**Guarantee vector**: `⟨Partition, PartialOrder, RA, EO, Idem(offset), Auth⟩`
- Partition scope (per-partition ordering)
- Partial order (total order within partition, no order across partitions)
- Read-atomic (consumer reads committed events)
- Eventual order (cross-partition ordering eventually consistent)
- Idempotent with offset tracking (replay safe)

**Apache Pulsar Architecture**:

**Key difference from Kafka**: Decoupled storage and serving.

```
Producers → Brokers (serving) → BookKeeper (storage)
                ↓
            ZooKeeper (metadata)
```

**Segment-based storage**:
- Events written to segments (immutable chunks)
- Segments distributed across BookKeeper nodes
- Brokers are stateless (can be added/removed freely)

**Advantages**:
- Faster rebalancing (no data movement)
- Infinite retention (cheap object storage)
- Multi-tenancy (namespace isolation)

**Geo-replication**:
- Built-in cross-datacenter replication
- Conflict resolution (last-write-wins)

**Amazon Kinesis**:

AWS-managed streaming:
- Shards (similar to Kafka partitions)
- Auto-scaling (add/remove shards)
- Integration with AWS services (Lambda, S3, Redshift)

**Trade-off**: Less control, easier operation.

**Azure Event Hubs**:

Azure-managed streaming:
- Partitions (like Kafka)
- Capture feature (auto-archive to Blob Storage)
- Kafka protocol support (can use Kafka clients)

#### Event Sourcing

**Principle**: Events are the source of truth, not current state.

**Traditional approach**:
```
Current state:
Account balance: $1000

Events:
Deposited $500 (lost)
Withdrew $200 (lost)
Transferred $300 (lost)
```

**Event sourcing**:
```
Event log (immutable):
1. Account opened ($0)
2. Deposited $500 → $500
3. Withdrew $200 → $300
4. Transferred $300 → $600
5. Deposited $400 → $1000

Current state: Computed from events
```

**Rebuilding state from events**:
```python
def rebuild_account(account_id):
    events = event_store.get_events(account_id)
    state = Account(balance=0)
    for event in events:
        state = state.apply(event)
    return state
```

**Temporal queries**: "What was the balance on January 15?"
```python
def balance_at(account_id, timestamp):
    events = event_store.get_events_until(account_id, timestamp)
    state = Account(balance=0)
    for event in events:
        state = state.apply(event)
    return state.balance
```

**Event store design**:
- Append-only log (events never deleted)
- Indexed by aggregate ID (e.g., account_id)
- Snapshots for performance (store state every N events)

**Evidence**:
- **Event sequence**: Monotonic version number per aggregate
- **Causality**: Events reference previous events
- **Immutability**: Events are cryptographically signed (tamper-proof)

**Guarantee vector**: `⟨Aggregate, TotalOrder, RA, Fresh, Idem(seq), Auth(sign)⟩`

#### CQRS Pattern

**Command Query Responsibility Segregation**: Separate write model from read model.

**Problem with traditional CRUD**:
- Same data model for writes (transactional) and reads (analytics)
- Complex queries slow down transactional system
- Hard to scale reads independently from writes

**CQRS solution**:
```
Commands (writes) → Write Model (normalized, consistent)
                         ↓ events
Read Model ← Events (denormalized, optimized for queries)
       ↑
    Queries (reads)
```

**Example: E-commerce order system**

**Write model**:
```
Tables:
- orders (id, customer_id, status, created_at)
- order_items (order_id, product_id, quantity, price)
- inventory (product_id, quantity)

Command: PlaceOrder
  1. Validate inventory
  2. Create order
  3. Decrement inventory
  4. Publish OrderPlaced event
```

**Read model** (updated asynchronously from events):
```
Materialized views:
- customer_orders (customer_id, order_count, total_spent)
- product_sales (product_id, units_sold, revenue)
- daily_revenue (date, total_revenue)

Event: OrderPlaced
  1. Update customer_orders (increment count, add total)
  2. Update product_sales (add units, revenue)
  3. Update daily_revenue (add to total)
```

**Eventual consistency boundaries**:
- Write model: Strongly consistent (ACID transactions)
- Read model: Eventually consistent (updated from event stream)
- Staleness: Bounded by event processing latency (typically <1s)

**Synchronization strategies**:
- **Polling**: Read model polls event log periodically
- **Push**: Event store pushes to read model subscribers
- **Change data capture** (CDC): Database replication log

**Mode matrix**:
- **Target**: Write model accepts commands, events flow to read model
- **Degraded**: Event processing backlog, read model stale
- **Floor**: Read model unavailable, serve cached data or reject queries
- **Recovery**: Rebuild read model from event log

**Guarantee vector comparison**:
- Write model: `⟨Global, SS, SER, Fresh, Idem, Auth⟩`
- Read model: `⟨Global, Causal, RA, BS(δ), Idem, Auth⟩` where δ = event processing lag

#### Saga Orchestration

**Problem**: Distributed transactions across services without 2PC (two-phase commit).

**Why not 2PC?**
- Coordinator is single point of failure
- Blocking protocol (one service failing blocks all)
- Long locks reduce availability
- Violates service autonomy

**Saga solution**: Long-lived transaction as sequence of local transactions with compensating actions.

**Example: E-commerce order**

**Happy path**:
1. Order service: Create order → Success
2. Payment service: Charge customer → Success
3. Inventory service: Reserve items → Success
4. Shipping service: Schedule shipment → Success
5. Order service: Mark order completed

**Failure scenario** (inventory unavailable):
1. Order service: Create order → Success
2. Payment service: Charge customer → Success
3. Inventory service: Reserve items → **Failure**
4. **Compensate**: Payment service: Refund customer
5. **Compensate**: Order service: Cancel order

**Choreography vs Orchestration**:

**Choreography** (event-driven, no coordinator):
```
Order service:
  OrderCreated event → payment service
Payment service:
  PaymentCompleted event → inventory service
Inventory service:
  InventoryReserved event → shipping service
  InventoryFailed event → payment service (refund)
```

**Pro**: Loose coupling, no single point of failure
**Con**: Hard to track saga state, complex error handling

**Orchestration** (coordinator manages saga):
```
Saga coordinator:
  1. Call order service (create order)
  2. Call payment service (charge)
  3. Call inventory service (reserve)
  4. If failure: call compensation actions in reverse
```

**Pro**: Clear saga state, easier debugging
**Con**: Coordinator is coupling point

**Compensation logic**:
```python
class OrderSaga:
    def execute(self):
        try:
            order = self.order_service.create_order()
            payment = self.payment_service.charge(order)
            inventory = self.inventory_service.reserve(order)
            shipping = self.shipping_service.schedule(order)
            return success(order)
        except Exception as e:
            self.compensate(order, payment, inventory)
            return failure(e)

    def compensate(self, order, payment, inventory):
        if inventory:
            self.inventory_service.release(inventory)
        if payment:
            self.payment_service.refund(payment)
        if order:
            self.order_service.cancel(order)
```

**Idempotency requirement**: Compensating actions must be idempotent (safe to retry).

**Evidence**:
- **Saga ID**: Unique identifier for saga instance
- **State**: Which steps completed, which failed
- **Compensation log**: Which compensations executed

**Guarantee vector**: `⟨Saga, Causal, RA, EO, Idem(saga-id), Auth⟩`
- Saga scope (eventual consistency across services)
- Causal ordering (compensation after failure)
- Eventually ordered (saga eventually completes or compensates)

### Data Mesh Principles

**Problem**: Centralized data lakes/warehouses don't scale with organization growth.

**Traditional approach**:
- Domain teams produce data
- Central data team owns data lake/warehouse
- Analytics teams request data from central team
- Bottleneck: Central team can't scale with demand

**Data mesh approach**: Federated data ownership, domain-oriented data products.

#### Domain-Oriented Data Ownership

**Principle**: Domain teams that produce data also own data products for that domain.

**Example: E-commerce company**

**Domains**:
- **Product catalog**: Product info, categories, inventory
- **Orders**: Order history, status, fulfillment
- **Customers**: Profiles, preferences, behavior
- **Marketing**: Campaigns, promotions, conversions

**Traditional** (centralized):
```
Product team → Operational DB
Orders team → Operational DB
Customer team → Operational DB
         ↓ ETL (owned by central data team)
    Data Warehouse
         ↓
  Analytics teams
```

**Data mesh** (federated):
```
Product team:
  Operational DB + Product Data Product (API, events, snapshots)

Orders team:
  Operational DB + Orders Data Product

Customer team:
  Operational DB + Customer Data Product

Analytics teams:
  Self-serve access to data products
```

**Data as a product**:
- **Discoverable**: Catalog of available data products
- **Addressable**: Standard API/protocol for access
- **Trustworthy**: Quality guarantees (SLA, schema, freshness)
- **Self-describing**: Documentation, lineage, examples

#### Data Product Thinking

**Input/output contracts**:

**Contract**: Schema + guarantees
```yaml
data_product: customer_behavior
owner: customer_team
output_contract:
  schema:
    user_id: UUID
    event_type: enum[page_view, click, purchase]
    timestamp: ISO8601
    properties: JSON
  guarantees:
    freshness: <5 minutes (P95)
    completeness: >99.9% of events captured
    partitioning: by date
    retention: 2 years
  access:
    protocol: Kafka topic
    topic: customer.behavior.v1
    auth: OAuth2
```

**Quality guarantees**:
- **Freshness**: How stale can data be?
- **Completeness**: What % of events captured?
- **Accuracy**: What error rate is acceptable?
- **Schema stability**: Breaking changes allowed?

**Discovery mechanisms**:

**Data catalog**:
```
Product: customer_behavior
Description: User behavior events (page views, clicks, purchases)
Owner: customer-team@company.com
SLA: 99.9% availability, <5min freshness
Schema: /schemas/customer_behavior/v1
Access: kafka://cluster.prod/customer.behavior.v1
Lineage: Upstream from web_events, mobile_events
         Downstream to recommendation_model, marketing_analytics
Examples: /examples/customer_behavior_queries.sql
Last updated: 2023-09-15
Quality score: 98/100
```

**Lifecycle management**:
- **Version**: Major/minor versioning (v1, v2)
- **Deprecation**: Announce 6 months before removal
- **Migration**: Provide migration tools/guides
- **Breaking changes**: New major version (v1 → v2)

#### Computational Governance

**Policy as code**: Governance rules encoded and enforced automatically.

**Example policies**:

**Privacy** (GDPR, CCPA):
```python
@policy
def check_pii_masking(data_product):
    """Ensure PII fields are masked in non-production"""
    if env != "production":
        assert data_product.fields.email.masked
        assert data_product.fields.phone.masked
        assert data_product.fields.ssn.masked
```

**Data quality**:
```python
@policy
def check_freshness(data_product):
    """Ensure data meets freshness SLA"""
    last_update = data_product.last_updated_at
    max_age = data_product.contract.freshness
    assert now() - last_update < max_age
```

**Schema evolution**:
```python
@policy
def check_backward_compatibility(schema_new, schema_old):
    """Ensure new schema is backward compatible"""
    for field in schema_old.required_fields:
        assert field in schema_new.fields
```

**Automated compliance**:
- **Pre-publish**: Check policies before data product published
- **Continuous**: Monitor compliance in production
- **Alerting**: Notify owner if policy violated

**Privacy by design**:
- **Minimize**: Collect only necessary data
- **Anonymize**: Remove PII where possible
- **Encrypt**: Encrypt sensitive data at rest
- **Audit**: Log all access to sensitive data

**Lineage tracking**:

**Data lineage graph**:
```
web_server_logs → events_raw → events_cleaned → customer_behavior
                                                       ↓
                                          recommendation_model
                                                       ↓
                                            personalized_homepage
```

**Use cases**:
- **Impact analysis**: If I change events_cleaned, what's affected?
- **Root cause**: Recommendation model has bad data, trace upstream
- **Compliance**: Delete user data across all derived datasets

**Evidence**:
- **Lineage**: Directed acyclic graph (DAG) of data flow
- **Schema version**: Which schema version in use?
- **Quality score**: Automated quality checks
- **Access log**: Who accessed data, when?

**Guarantee vector**: `⟨Domain, Causal, RA, BS(SLA), Idem, Auth⟩`

### API Gateway Patterns

**API gateway**: Entry point for external clients accessing microservices.

#### Gateway Responsibilities

**Authentication/Authorization**:
```
Client request (with API key) → Gateway
  ↓
Verify API key against auth service
  ↓
Valid? → Forward to service (with user context)
Invalid? → 401 Unauthorized
```

**Rate Limiting**:
```python
def rate_limit(client_id, limit=100, window=60):
    """Allow 100 requests per 60 seconds per client"""
    key = f"rate:{client_id}:{window_start()}"
    count = redis.incr(key)
    redis.expire(key, window)
    if count > limit:
        return 429  # Too Many Requests
    return None  # Allow
```

**Evidence**: Rate limit counter in Redis, TTL expires counter.

**Request Routing**:
```yaml
routes:
  - path: /users/*
    service: user-service
    timeout: 5s
  - path: /orders/*
    service: order-service
    timeout: 10s
  - path: /products/*
    service: product-service
    cache: 60s
```

**Protocol Translation**:
- External: HTTP/REST
- Internal: gRPC (more efficient)
- Gateway translates between protocols

**Response Caching**:
```
Client → Gateway → Check cache (Redis)
                      ↓ hit
                  Return cached response
                      ↓ miss
                  Call service → Cache response → Return
```

**Cache invalidation**: TTL-based or event-driven (service publishes invalidation event).

#### Modern Gateway Evolution

**Kong**:
- **Plugin architecture**: Authentication, rate limiting, logging, transformations
- **Declarative config**: YAML-based configuration
- **Database-backed**: PostgreSQL for config storage (or DB-less mode)

**Example plugin**:
```yaml
plugins:
  - name: rate-limiting
    config:
      minute: 100
      policy: redis
  - name: jwt
    config:
      claims_to_verify: [exp, nbf]
  - name: request-transformer
    config:
      add:
        headers:
          - "X-User-ID: $(jwt.user_id)"
```

**Zuul → Spring Cloud Gateway**:

Netflix built Zuul (Java, blocking I/O). Replaced with Spring Cloud Gateway (reactive, non-blocking).

**Why?**
- Better scalability (reactive I/O)
- Lower latency (less thread overhead)
- Spring ecosystem integration

**Envoy Gateway**:

Envoy (service mesh data plane) can be API gateway:
- Same binary for mesh and gateway (consistency)
- Advanced traffic management
- Rich observability

**GraphQL Gateways**:

**Problem**: REST APIs are rigid (fixed endpoints, over/under-fetching).

**GraphQL solution**: Client specifies exactly what data needed.

**Request**:
```graphql
query {
  user(id: 123) {
    name
    orders {
      id
      total
      items {
        product {
          name
        }
      }
    }
  }
}
```

**Gateway**:
1. Parse GraphQL query
2. Call user-service (get user)
3. Call order-service (get orders for user)
4. Call product-service (get products for items)
5. Assemble response

**Evidence**: Query execution plan (which services called, in what order).

**Guarantee vector**: `⟨Client, Causal, RA, BS(cache-TTL), Idem, Auth(token)⟩`

### Serverless Integration

**Serverless**: Functions that run on-demand, auto-scale, pay-per-use.

#### Function Composition

**AWS Step Functions**:

State machine for orchestrating Lambda functions:
```json
{
  "StartAt": "ProcessOrder",
  "States": {
    "ProcessOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123:function:process-order",
      "Next": "ChargePayment"
    },
    "ChargePayment": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123:function:charge-payment",
      "Next": "ReserveInventory",
      "Catch": [{
        "ErrorEquals": ["PaymentFailed"],
        "Next": "CancelOrder"
      }]
    },
    "ReserveInventory": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123:function:reserve-inventory",
      "Next": "ShipOrder",
      "Catch": [{
        "ErrorEquals": ["InventoryFailed"],
        "Next": "RefundPayment"
      }]
    },
    "ShipOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123:function:ship-order",
      "End": true
    },
    "RefundPayment": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123:function:refund-payment",
      "Next": "CancelOrder"
    },
    "CancelOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123:function:cancel-order",
      "End": true
    }
  }
}
```

**Visual workflow**, **error handling**, **retries** built-in.

**Azure Logic Apps**:

Similar to Step Functions, visual designer, integrations with Azure services.

**Temporal Workflows**:

Code-based workflow engine (not FaaS, but similar pattern):
```python
@workflow.defn
class OrderWorkflow:
    @workflow.run
    async def run(self, order_id: str):
        # Durable execution (survives crashes)
        order = await workflow.execute_activity(
            process_order, order_id, start_to_close_timeout=60)

        try:
            payment = await workflow.execute_activity(
                charge_payment, order, start_to_close_timeout=30)

            inventory = await workflow.execute_activity(
                reserve_inventory, order, start_to_close_timeout=30)

            shipping = await workflow.execute_activity(
                ship_order, order, start_to_close_timeout=300)

            return success(order)
        except PaymentFailed:
            await workflow.execute_activity(cancel_order, order)
            return failure("payment")
        except InventoryFailed:
            await workflow.execute_activity(refund_payment, payment)
            await workflow.execute_activity(cancel_order, order)
            return failure("inventory")
```

**Durable execution**: Workflow state persisted, can resume after crash.

**Event-Driven Functions**:

**Lambda triggered by events**:
```yaml
functions:
  processOrder:
    handler: handler.processOrder
    events:
      - http:
          path: /orders
          method: post
      - sqs:
          arn: arn:aws:sqs:us-east-1:123:order-queue
      - s3:
          bucket: orders-bucket
          event: s3:ObjectCreated:*
```

**Use cases**:
- HTTP API (API Gateway → Lambda)
- Queue processing (SQS → Lambda)
- File processing (S3 upload → Lambda)
- Scheduled tasks (CloudWatch Events → Lambda)

#### Edge Computing

**Cloudflare Workers**:

JavaScript functions running on Cloudflare edge (200+ locations):
```javascript
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // Runs at edge, close to user
  const response = await fetch(request)
  // Transform response
  return new Response(response.body, {
    headers: { ...response.headers, 'X-Edge': 'Cloudflare' }
  })
}
```

**Latency**: <10ms (vs 50-200ms for regional Lambda).

**Lambda@Edge**:

AWS Lambda at CloudFront edge locations:
```javascript
exports.handler = (event, context, callback) => {
  const request = event.Records[0].cf.request;

  // Modify request before origin
  request.headers['x-custom'] = [{
    key: 'X-Custom',
    value: 'Edge'
  }];

  callback(null, request);
};
```

**Deno Deploy**:

JavaScript/TypeScript at edge:
```typescript
import { serve } from "https://deno.land/std/http/server.ts";

serve((req) => {
  return new Response("Hello from edge!");
});
```

**Regional Processing**:

For data locality (GDPR: EU data must stay in EU):
```
User in Germany → EU edge function → EU database
User in US → US edge function → US database
```

**Evidence**: Geolocation header, region tag in logs.

**Guarantee vector**: `⟨Region, Causal, RA, Fresh, Idem, Auth⟩`

---

## Part 3: MASTERY (Third Pass) — Composition and Operation

### Evidence-Based Modern Architecture

Modern distributed systems preserve invariants through evidence at compositional boundaries.

#### Service Mesh Evidence

**Service identity certificates**:
```
Certificate:
  Subject: spiffe://cluster.local/ns/default/sa/reviews
  Issuer: cluster.local CA
  Valid: 2023-09-15 10:00:00 to 2023-09-15 11:00:00 (1 hour)
  Serial: 0x1234567890abcdef
  Signature: (RSA-SHA256)
```

**Evidence properties**:
- **Scope**: Cluster-local
- **Lifetime**: 1 hour (short-lived, auto-rotated)
- **Binding**: Service account (Kubernetes identity)
- **Verification**: mTLS handshake
- **Revocation**: Implicit (expiration), explicit (CRL if needed)

**Traffic policy attestations**:
```
VirtualService: reviews-v1-to-v2-canary
Version: 47
Applied: 2023-09-15 10:15:00
Policy:
  - 90% traffic → reviews-v1
  - 10% traffic → reviews-v2
Checksum: sha256:abcd...
Signed by: platform-team
```

**Evidence**: Configuration version proves "these routing rules are active."

**Health check proofs**:
```
HTTP GET /healthz → 200 OK
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "cache": "ok"
  },
  "timestamp": "2023-09-15T10:20:00Z"
}
```

**Evidence**: Health response proves service is alive and ready.

**Trace context propagation**:
```
HTTP headers:
  traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
  tracestate: vendor1=value1,vendor2=value2
```

**Evidence**: Trace ID proves causal relationship across services.

**Guarantee vector**: `⟨Cluster, Causal, RA, Fresh(1h), Idem, Auth(mTLS)⟩`

#### Event Stream Evidence

**Event ordering guarantees**:
```
Partition 0:
  Offset 1000: { user_id: 123, action: "login", timestamp: T1 }
  Offset 1001: { user_id: 123, action: "view", timestamp: T2 }
  Offset 1002: { user_id: 123, action: "purchase", timestamp: T3 }

Guarantee: T1 < T2 < T3 (total order within partition)
```

**Evidence**: Offset proves position in total order.

**Delivery confirmations**:
```
Consumer commits offset 1002
Evidence: "I processed all events up to 1002"

If consumer crashes and restarts:
  Read from last committed offset (1002)
  Resume processing from 1003
```

**At-least-once guarantee**: May reprocess 1002 if crash before commit, but never skip events.

**Replay positions**:
```
Consumer group: analytics
  Partition 0: offset 1002
  Partition 1: offset 2345
  Partition 2: offset 891

Reset to offset 0 → replay entire history
```

**Evidence**: Offset enables time-travel (replay from any point).

**Consumer group coordination**:
```
Consumer group: fraud-detection
  Member A: owns partitions [0, 1]
  Member B: owns partitions [2, 3]

Member B crashes:
  Rebalance triggered
  Member A: takes ownership of [0, 1, 2, 3]

Member B rejoins:
  Rebalance triggered
  Member A: [0, 1]
  Member B: [2, 3]
```

**Evidence**: Consumer group state in ZooKeeper/Kafka coordinator proves partition ownership.

**Guarantee vector**: `⟨Partition, TotalOrder, RA, EO, Idem(offset), Auth⟩`

#### Data Mesh Evidence

**Data quality scores**:
```
Data Product: customer_behavior
Quality Score: 94/100
  Freshness: 98/100 (avg delay: 2.3 min, SLA: <5 min)
  Completeness: 95/100 (99.5% events captured, SLA: >99%)
  Accuracy: 90/100 (schema violations: 0.3%, SLA: <1%)
  Timeliness: 93/100 (P95 delay: 4.1 min, SLA: <5 min)
```

**Evidence**: Automated quality checks generate score.

**Lineage graphs**:
```
customer_behavior ← web_events (via ETL job: web_events_pipeline)
                  ← mobile_events (via Kafka stream: mobile_processor)

customer_behavior → recommendation_model (consumer: ml_team)
                  → marketing_analytics (consumer: marketing_team)
```

**Evidence**: Lineage proves data provenance and impact.

**Schema evolution tracking**:
```
Schema versions:
  v1 (2022-01-01): fields [user_id, event_type, timestamp]
  v2 (2022-06-15): added [session_id, device_type]
  v3 (2023-01-10): deprecated [device_type], added [platform]

Current: v3
Consumers:
  recommendation_model: using v3
  marketing_analytics: using v2 (compatibility mode)
```

**Evidence**: Schema registry proves compatibility.

**Access audit trails**:
```
Access log:
  2023-09-15 10:00:00: user=analyst@company.com, query=SELECT COUNT(*), purpose=analytics
  2023-09-15 10:05:00: user=ml-service, query=EXPORT data, purpose=model-training
  2023-09-15 10:10:00: user=external-partner, query=SELECT *, purpose=integration [DENIED: insufficient permissions]
```

**Evidence**: Audit log proves compliance (who accessed what, when, why).

**Guarantee vector**: `⟨Domain, Causal, RA, BS(SLA), Idem, Auth⟩`

### Invariant Framework for Modern Systems

Modern distributed systems preserve a primary invariant: **COMPOSABILITY**.

#### Primary Invariant: COMPOSABILITY

**Definition**: Services, events, and data products compose safely without violating local invariants.

**Sub-invariants**:

**1. Service composition preserves guarantees**:
```
Service A (provides: Fresh(φ)) → Service B (requires: BS(δ))
Composition valid if φ ⊆ δ (fresh evidence satisfies bounded staleness)

Service A (provides: BS(10s)) → Service B (requires: Fresh(φ))
Composition invalid (stale evidence insufficient)
```

**2. Event flows preserve order**:
```
Producer → Partition → Consumer
Total order preserved within partition
Partial order across partitions (must use correlation IDs)
```

**3. Data products maintain contracts**:
```
Data product changes schema (v1 → v2)
Contract: v2 is backward compatible with v1
Verification: Automated schema compatibility check
```

**4. Policies apply uniformly**:
```
Service mesh policy: All traffic requires mTLS
Applied to: Every service in mesh
Enforcement: Sidecar rejects non-mTLS connections
Verification: Policy audit logs
```

#### Supporting Invariants

**ISOLATION**: Failure boundaries prevent cascades

**Implementation**:
- Circuit breakers isolate failing services
- Bulkheads limit resource usage per tenant
- Timeouts prevent infinite waits
- Rate limits prevent overload

**Evidence**:
- Circuit breaker state (open/closed/half-open)
- Resource usage metrics (CPU, memory, connections)
- Timeout counters (how many requests timed out)
- Rate limit counters (how many requests rejected)

**OBSERVABILITY**: Full visibility into system state

**Implementation**:
- Distributed tracing (Jaeger, Zipkin)
- Centralized logging (ELK, Splunk)
- Metrics aggregation (Prometheus, Datadog)
- Service dependency mapping (Kiali, Service Graph)

**Evidence**:
- Trace spans (causality across services)
- Log correlation IDs (group related logs)
- Metric time series (performance over time)
- Dependency graph (which services call which)

**ADAPTABILITY**: Dynamic configuration without restarts

**Implementation**:
- Feature flags (LaunchDarkly, Unleash)
- Dynamic routing (service mesh VirtualService)
- Auto-scaling (Kubernetes HPA, cluster autoscaler)
- A/B testing (traffic splitting)

**Evidence**:
- Feature flag evaluation logs
- Routing rule versions
- Scaling decisions (why did we scale up/down?)
- Experiment assignments (user → variant mapping)

**SECURITY**: Zero-trust verification

**Implementation**:
- mTLS for service-to-service
- JWT/OAuth2 for user authentication
- Authorization policies (RBAC, ABAC)
- Secrets management (Vault, AWS Secrets Manager)

**Evidence**:
- X.509 certificates (service identity)
- JWT claims (user identity, permissions)
- Policy evaluation logs (allowed/denied)
- Secret access audit logs

### Mode Matrix for Modern Systems

Modern systems operate in multiple modes, degrading predictably.

#### Target Mode (Optimal State)

**All services healthy**:
- Service mesh: All sidecars reporting healthy
- Circuit breakers: All closed (normal traffic flow)
- Latency: Within SLA (e.g., P99 < 100ms)
- Error rate: <0.1%

**Events flowing smoothly**:
- Kafka lag: <1000 messages per partition
- Event processing: Within freshness SLA
- Consumer groups: All members active
- Replication: All brokers in-sync

**Data products fresh**:
- Quality scores: >95/100
- Freshness: Within SLA (e.g., <5 minutes)
- Schema compatibility: All consumers compatible
- Lineage: Up-to-date

**Policies enforcing**:
- mTLS: 100% of traffic encrypted
- Rate limits: Enforced, <1% of requests throttled
- Authorization: Policies evaluated, audit logged
- Compliance: All policies passing

**Guarantee vector**: `⟨Global, Causal, RA, Fresh(SLA), Idem, Auth⟩`

#### Degraded Mode (Partial Failures)

**Circuit breakers activated**:
```
Service B failing (error rate 60%)
Service A → Circuit breaker to B opens
Service A → Returns cached/default response
Mode: Degraded (reduced functionality)
```

**Event backlogs growing**:
```
Kafka lag increasing:
  Normal: 100 messages/partition
  Degraded: 10,000 messages/partition
  Cause: Consumer processing slower than producers
  Action: Alert on-call, scale consumers
```

**Stale data products**:
```
Data product: customer_behavior
  Normal freshness: 2 minutes
  Current freshness: 15 minutes
  Cause: ETL job failing
  Mode: Degraded (serve stale data with warning)
```

**Partial policy enforcement**:
```
Rate limiting:
  Redis (rate limit store) down
  Fallback: In-memory rate limiting (not distributed)
  Mode: Degraded (per-instance limits, less accurate)
```

**Guarantee vector weakens**: `⟨Range, Causal, RA, BS(degraded), Idem, Auth⟩`
- Scope reduced (range instead of global)
- Staleness increased (BS instead of Fresh)

#### Floor Mode (Survival)

**Core services only**:
```
Too many failures detected
Load shedding activated:
  Critical paths: Allowed (authentication, core transactions)
  Non-critical: Rejected (analytics, recommendations)
Mode: Floor (minimum viable functionality)
```

**Event streaming paused**:
```
Kafka cluster unhealthy (majority brokers down)
Producers: Buffer events locally
Consumers: Pause processing
Mode: Floor (durability over availability)
```

**Cached data only**:
```
Database unreachable
API gateway: Serve cached responses only
Freshness: Unknown (cache populated hours ago)
Mode: Floor (availability over freshness)
```

**Emergency policies**:
```
Normal policies: Fine-grained (per-user, per-API)
Floor mode: Coarse-grained (all anonymous users blocked)
Mode: Floor (safety over functionality)
```

**Guarantee vector minimal**: `⟨Local, None, None, Stale, None, None⟩`
- Only local guarantees (no distributed coordination)
- No ordering or freshness
- Safety preserved, availability reduced

#### Recovery Mode

**Services restarting**:
```
Service B recovering:
  Circuit breaker: Half-open (testing)
  Traffic: 1% to B (canary)
  If success rate >99%:
    Gradually increase traffic (5%, 25%, 50%, 100%)
    Close circuit breaker
    Mode: Recovery → Target
```

**Events replaying**:
```
Consumer group: fraud-detection
  Crashed during processing
  Recovery: Resume from last committed offset
  Replay: Process backlog (10,000 events)
  Gradually catch up (lag decreasing)
  Mode: Recovery → Target
```

**Data recomputing**:
```
Data product: customer_behavior
  ETL job failed for 2 hours
  Recovery: Backfill missing data
  Recompute aggregates
  Validate quality
  Mode: Recovery → Target
```

**Policies revalidating**:
```
Policy engine restarted
  Reload policies from config
  Validate against schema
  Apply to all services
  Audit first 1000 requests
  Mode: Recovery → Target
```

**Guarantee vector recovering**: `⟨Range→Global, Causal, RA, BS→Fresh, Idem, Auth⟩`

### Production Patterns

#### Service Mesh Operations

**Gradual rollouts**:

**Traffic shift pattern**:
```yaml
# Week 1: Deploy v2, 5% traffic
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 95
    - destination:
        host: reviews
        subset: v2
      weight: 5
```

**Monitoring**: Error rate, latency P50/P95/P99, resource usage.

**Week 2**: If healthy, increase to 25%.
**Week 3**: 50%.
**Week 4**: 100%, remove v1.

**Canary analysis**:

**Automated metrics comparison**:
```
v1 metrics (baseline):
  Error rate: 0.05%
  Latency P99: 80ms
  CPU: 30%

v2 metrics (canary):
  Error rate: 0.06% (within threshold: <0.1%)
  Latency P99: 85ms (within threshold: <100ms)
  CPU: 28% (better)

Decision: PASS → increase traffic
```

**Flagger** (automated canary tool):
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: reviews
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  progressDeadlineSeconds: 60
  service:
    port: 9080
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 5
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m
```

**Service dependency mapping**:

**Kiali** (Istio service graph):
```
productpage → reviews → ratings
           → details

Metrics:
  productpage → reviews: 100 req/s, 0.1% error, 50ms P99
  reviews → ratings: 80 req/s, 0.05% error, 20ms P99
```

**Use cases**:
- Understand traffic flow
- Identify bottlenecks
- Detect failures
- Security (which services communicate?)

**Performance profiling**:

**Latency breakdown**:
```
Total request latency: 120ms
  productpage processing: 10ms
  productpage → reviews (network): 5ms
  reviews processing: 30ms
  reviews → ratings (network): 3ms
  ratings processing: 15ms
  ratings → reviews (network): 2ms
  reviews → productpage (network): 5ms
  productpage response: 50ms

Bottleneck: productpage response rendering (50ms)
```

#### Event Stream Management

**Partition rebalancing**:

**Scenario**: Add new consumer to group

**Before**:
```
Consumer A: partitions [0, 1, 2]
Consumer B: partitions [3, 4, 5]
```

**Add Consumer C**:
```
Rebalance triggered
New assignment:
  Consumer A: partitions [0, 1]
  Consumer B: partitions [2, 3]
  Consumer C: partitions [4, 5]
```

**Rebalance overhead**: All consumers stop processing, wait for assignment, resume. Can take seconds.

**Strategies to minimize**:
- Static membership (consumers keep same partitions across restarts)
- Incremental cooperative rebalancing (only affected partitions rebalance)

**Consumer lag monitoring**:

**Metrics**:
```
Consumer group: fraud-detection
  Partition 0:
    Latest offset: 10,000
    Committed offset: 9,500
    Lag: 500 messages (5 seconds behind at current rate)
  Partition 1:
    Latest offset: 12,000
    Committed offset: 2,000
    Lag: 10,000 messages (100 seconds behind) ⚠ ALERT
```

**Alerts**:
- Lag increasing (consumer slower than producer)
- Lag above threshold (SLA violation)
- Consumer stopped (no offset commits)

**Dead letter queues**:

**Pattern**: Failed messages sent to DLQ for later investigation.

```python
try:
    process(message)
    commit_offset(message.offset)
except Exception as e:
    log_error(e, message)
    send_to_dlq(message, e)
    commit_offset(message.offset)  # Don't reprocess
```

**DLQ consumer**:
```python
for message in dlq:
    analyze_failure(message)
    if can_retry:
        send_to_original_topic(message)
    else:
        alert_humans(message)
```

**Schema registry**:

**Confluent Schema Registry**:
- Store Avro/Protobuf/JSON schemas
- Enforce compatibility (backward, forward, full)
- Schema evolution management

**Example**:
```python
# Producer
schema = """
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "int"},
    {"name": "name", "type": "string"}
  ]
}
"""
schema_registry.register("user-events-value", schema)

# Evolve schema (backward compatible)
schema_v2 = """
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "int"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": ["null", "string"], "default": null}
  ]
}
"""
schema_registry.register("user-events-value", schema_v2)

# Old consumers can still read (ignore new email field)
# New consumers can read old records (email=null)
```

#### Data Mesh Governance

**Data product catalog**:

**Metadata**:
```yaml
data_product:
  name: customer_behavior
  version: v3
  owner: customer-team@company.com
  description: User behavior events (page views, clicks, purchases)

  schema:
    format: Avro
    registry: schema-registry.company.com
    version: 3

  access:
    protocol: Kafka
    topic: customer.behavior.v3
    cluster: prod-kafka-01.company.com
    auth: OAuth2 (scope: data.customer.behavior.read)

  sla:
    availability: 99.9%
    freshness_p95: 5 minutes
    completeness: 99.9%

  lineage:
    upstream:
      - web-events (source: web-server-logs)
      - mobile-events (source: mobile-app)
    downstream:
      - recommendation-model (consumer: ml-team)
      - marketing-analytics (consumer: marketing-team)

  documentation:
    readme: /docs/customer_behavior.md
    examples: /examples/customer_behavior_queries.sql
    changelog: /changelog/customer_behavior.md
```

**Quality monitoring**:

**Automated checks**:
```python
@quality_check(schedule="*/5 * * * *")  # Every 5 minutes
def check_freshness():
    last_event = get_latest_event_timestamp("customer.behavior.v3")
    age = now() - last_event
    assert age < timedelta(minutes=5), f"Data stale: {age}"

@quality_check(schedule="0 * * * *")  # Hourly
def check_completeness():
    web_events = count_events("web-events", last_hour)
    customer_events = count_events("customer.behavior.v3", last_hour)
    ratio = customer_events / web_events
    assert ratio > 0.99, f"Completeness: {ratio:.2%}"

@quality_check(schedule="*/15 * * * *")  # Every 15 minutes
def check_schema_violations():
    violations = count_schema_violations("customer.behavior.v3", last_15_min)
    total = count_events("customer.behavior.v3", last_15_min)
    error_rate = violations / total
    assert error_rate < 0.01, f"Schema violations: {error_rate:.2%}"
```

**Access control**:

**Example**: GDPR compliance (EU data restricted to EU teams)

```yaml
data_product: customer_behavior_eu
access_policy:
  - principal: group:eu-analytics-team
    actions: [read]
    conditions:
      - ip_range: 10.0.0.0/8  # EU VPC
  - principal: group:ml-team
    actions: [read]
    conditions:
      - purpose: model-training
      - data_residency: EU
  - principal: user:external-partner
    actions: [deny]
    reason: Third-party access forbidden
```

**Cost allocation**:

**Chargeback model**: Domain teams pay for data products they consume.

```
Team: marketing-analytics
Data products consumed:
  - customer_behavior: 500 GB/month, $50
  - product_catalog: 10 GB/month, $1
  - order_history: 1 TB/month, $100
Total: $151/month
```

**Encourages**:
- Data minimization (only consume what you need)
- Quality focus (don't produce unused data products)
- Ownership accountability (teams own costs)

### Modern System Composition

#### Layered Architecture

**Infrastructure layer**:
- Compute: Kubernetes, VMs, serverless
- Network: VPC, service mesh, load balancers
- Storage: Databases, object storage, caches

**Platform layer**:
- Service mesh: Istio, Linkerd
- Event streaming: Kafka, Pulsar
- API gateway: Kong, Envoy Gateway
- Observability: Prometheus, Jaeger, ELK

**Service layer**:
- Domain services: User, Order, Payment, Inventory
- Support services: Auth, Notification, Search
- Data services: Analytics, ML models

**Experience layer**:
- Web app: React, Angular
- Mobile app: iOS, Android
- API: GraphQL, REST
- Third-party integrations

**Evidence flows upward**:
- Infrastructure: Health checks, resource metrics
- Platform: Traffic policies, event offsets, auth tokens
- Service: Business events, transaction commits
- Experience: User actions, API calls

#### Cross-Cutting Concerns

**Distributed tracing**:

**OpenTelemetry** (unified observability):
```python
from opentelemetry import trace
from opentelemetry.propagate import inject

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("process_order")
def process_order(order_id):
    span = trace.get_current_span()
    span.set_attribute("order.id", order_id)

    # Propagate trace context to downstream service
    headers = {}
    inject(headers)
    response = requests.post(
        "http://payment-service/charge",
        headers=headers,
        json={"order_id": order_id}
    )

    span.set_attribute("payment.status", response.status_code)
    return response
```

**Trace visualization**:
```
process_order (120ms)
  ├─ validate_order (10ms)
  ├─ charge_payment (50ms) → payment-service
  │   ├─ check_fraud (20ms) → fraud-service
  │   └─ process_transaction (30ms)
  ├─ reserve_inventory (30ms) → inventory-service
  └─ send_confirmation (30ms) → notification-service
```

**Centralized logging**:

**Structured logging**:
```python
import structlog

log = structlog.get_logger()

log.info(
    "order_processed",
    order_id=order_id,
    user_id=user_id,
    total=100.50,
    duration_ms=120,
    trace_id=trace_context.trace_id
)
```

**Log aggregation** (ELK stack):
```
Elasticsearch: Store and index logs
Logstash: Parse and transform logs
Kibana: Visualize and query logs
```

**Query**:
```
trace_id:"4bf92f3577b34da6a3ce929d0e0e4736"
```

**Returns all logs** for that distributed trace across all services.

**Metrics aggregation**:

**Prometheus** (pull-based):
```yaml
# Service exposes metrics endpoint
GET /metrics
Response:
  # HELP http_requests_total Total HTTP requests
  # TYPE http_requests_total counter
  http_requests_total{method="GET",status="200"} 1234
  http_requests_total{method="POST",status="201"} 567

  # HELP http_request_duration_seconds HTTP request latency
  # TYPE http_request_duration_seconds histogram
  http_request_duration_seconds_bucket{le="0.1"} 800
  http_request_duration_seconds_bucket{le="0.5"} 1100
  http_request_duration_seconds_bucket{le="1.0"} 1200
```

**Prometheus scrapes** metrics every 15 seconds.

**Alerting**:
```yaml
groups:
- name: example
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    annotations:
      summary: High error rate detected
```

**Security scanning**:

**Container scanning** (Trivy, Snyk):
```bash
trivy image myapp:v1.2.3
```

**Finds vulnerabilities** in dependencies, OS packages.

**SAST** (Static Application Security Testing):
```bash
semgrep --config=auto .
```

**Finds code vulnerabilities** (SQL injection, XSS, etc.).

**DAST** (Dynamic Application Security Testing):
- Run application in test environment
- Automated attack simulation
- Detect runtime vulnerabilities

**Policy enforcement** (OPA - Open Policy Agent):
```rego
package kubernetes.admission

deny[msg] {
  input.request.kind.kind == "Pod"
  image := input.request.object.spec.containers[_].image
  not startswith(image, "myregistry.com/")
  msg := sprintf("Image %v not from trusted registry", [image])
}
```

#### Technology Choices

**Language diversity**:

**Polyglot architecture**:
- User service: Java (mature, performant)
- Recommendation service: Python (ML libraries)
- API gateway: Go (low latency, concurrency)
- Frontend: TypeScript (type safety)

**Trade-offs**:
- **Pro**: Right tool for each job
- **Con**: Operational complexity (multiple runtimes, build systems)

**Standardization**:
- Service mesh abstracts communication (language-agnostic)
- Observability via OpenTelemetry (language-agnostic)
- Deployment via containers (language-agnostic)

**Database per service**:

**Principle**: Each service owns its data, chooses its database.

**Example**:
- User service: PostgreSQL (relational, ACID)
- Session service: Redis (in-memory, fast)
- Product catalog: Elasticsearch (search, full-text)
- Event log: Kafka (append-only, durable)
- Analytics: Snowflake (data warehouse, OLAP)

**Trade-offs**:
- **Pro**: Service autonomy, optimal database per use case
- **Con**: No cross-service joins, eventual consistency

**Message broker selection**:

**Kafka**:
- **Use case**: High-throughput event streaming, replay, retention
- **Guarantees**: Ordering, durability, exactly-once semantics
- **Complexity**: Medium (ZooKeeper, partition management)

**RabbitMQ**:
- **Use case**: Task queues, routing, request/reply
- **Guarantees**: At-least-once, priority queues
- **Complexity**: Low (single broker, clustering)

**AWS SQS**:
- **Use case**: Decoupled task queues, serverless integration
- **Guarantees**: At-least-once, FIFO queues optional
- **Complexity**: Very low (managed service)

**Redis Streams**:
- **Use case**: Lightweight streaming, low latency
- **Guarantees**: Consumer groups, persistence optional
- **Complexity**: Low (single Redis instance or cluster)

**Orchestration platforms**:

**Kubernetes**:
- Container orchestration
- Service discovery (DNS, environment variables)
- Auto-scaling (HPA, VPA, cluster autoscaler)
- Rolling updates, rollbacks
- Configuration (ConfigMaps, Secrets)

**Nomad** (HashiCorp):
- Simpler than Kubernetes
- Supports containers, VMs, binaries
- Integrated with Consul (service mesh), Vault (secrets)

**AWS ECS**:
- AWS-native container orchestration
- Integrates with ALB, CloudWatch, IAM
- Fargate (serverless containers)

**Choice criteria**:
- Kubernetes: Full control, cloud-agnostic, complex
- Nomad: Simplicity, multi-workload
- ECS: AWS integration, managed, less flexible

### Case Studies

#### Spotify's Backend Architecture

**Scale**:
- 500M+ users
- 100M+ tracks
- 4B+ playlists
- 1000+ microservices

**Architecture evolution**:

**2010-2014: Monolith → Microservices**:
- Broke monolith into domain services
- Squad model: Small autonomous teams (6-12 people)
- Each squad owns services end-to-end

**Domain services**:
- **User service**: Profiles, preferences, subscriptions
- **Playlist service**: Create, edit, share playlists
- **Player service**: Streaming, playback, offline
- **Social service**: Following, feeds, sharing
- **Recommendation service**: Discover Weekly, Daily Mix

**Event-driven features**:

**Real-time collaborative playlists**:
```
User A adds song → Event published to Kafka
                  → User B's client notified (WebSocket)
                  → Playlist updated in real-time
```

**Discover Weekly**:
```
User listening events → Kafka → ML pipeline
                              → Train recommendation model
                              → Generate personalized playlists
```

**Data platform**:

**Scio** (Scala API for Apache Beam):
- Batch and streaming data processing
- Powers analytics, recommendations, reporting

**Example pipeline**:
```scala
sc.kafkaTopic("listening-events")
  .withTimestamps
  .windowBy(Hours(1))
  .groupBy(_.userId)
  .mapValues(events => TopSongs(events))
  .saveAsKafka("top-songs-hourly")
```

**Technology choices**:
- **Services**: Java, Python, Go (polyglot)
- **Data processing**: Scala (Scio), Python (ML)
- **Storage**: Cassandra (user data), PostgreSQL (metadata), GCS (audio)
- **Messaging**: Kafka (events), gRPC (service-to-service)

**Lessons**:
- Squad model scales teams (ownership, autonomy)
- Event-driven enables real-time features
- Data platform is core infrastructure

#### Airbnb's Service Architecture

**Scale**:
- 150M+ users
- 7M+ listings
- 1B+ guest arrivals (total)

**Architecture evolution**:

**2008-2014: Monolithic Rails app**:
- Fast initial development
- Technical debt accumulated
- Scaling challenges (database, deployments)

**2015-Present: Service-oriented architecture**:

**Core services**:
- **Homes service**: Listing CRUD, search, availability
- **Reservations service**: Booking, cancellation, modifications
- **Payments service**: Transactions, payouts, refunds
- **User service**: Profiles, verification, reviews
- **Messaging service**: Host-guest communication

**API gateway strategy**:

**Unified gateway**:
- Single entry point for mobile/web clients
- GraphQL API (flexible, efficient)
- Backend for Frontend (BFF) pattern

**GraphQL query**:
```graphql
query {
  listing(id: "12345") {
    title
    photos { url }
    host { name, verified }
    reviews(limit: 5) { rating, comment }
    availability(start: "2023-10-01", end: "2023-10-07")
  }
}
```

**Gateway orchestrates**:
- Homes service: Listing details, photos
- User service: Host info
- Reviews service: Review data
- Availability service: Calendar check

**Client gets exactly what it needs** in one request.

**Event pipeline**:

**Kafka-based event streaming**:
```
Booking created → Event published
                → Analytics pipeline (Spark)
                → Data warehouse (Hive)
                → Business intelligence dashboards
```

**Real-time pricing** (dynamic pricing based on demand):
```
Events: Searches, bookings, cancellations
      → Kafka → Flink streaming job
             → Update pricing model
             → Publish new prices to pricing service
```

**Data quality**:

**Schema enforcement** (Avro schemas in Schema Registry):
- Producers must register schema
- Consumers validate schema compatibility
- Prevents breaking changes

**Lessons**:
- GraphQL reduces API complexity
- Event streaming powers analytics and ML
- Data quality is non-negotiable

#### Netflix's Full Stack

**Scale**:
- 230M+ subscribers
- 125M+ hours watched daily
- 1000+ microservices
- Multiple AWS regions

**Architecture layers**:

**Edge services** (Zuul → Envoy):
- API gateway for client requests
- Routing, authentication, rate limiting
- Deployed globally (AWS edge locations)

**Mid-tier services**:
- **User service**: Profiles, preferences, viewing history
- **Recommendation service**: Personalized recommendations
- **Playback service**: Start streaming, track progress
- **Metadata service**: Show info, images, trailers
- **Subscription service**: Billing, plan management

**Data layer**:
- **EVCache** (Memcached): In-memory cache (hot data)
- **Cassandra**: User data, viewing history (multi-region)
- **Elasticsearch**: Search, metadata indexing
- **S3**: Media storage (video files)

**Chaos engineering**:

**Simian Army** (failure injection):
- **Chaos Monkey**: Randomly terminates instances
- **Chaos Kong**: Fails entire AWS region
- **Latency Monkey**: Injects artificial latency

**Why?**
- Test resilience before production failures
- Ensure graceful degradation
- Build confidence in fault tolerance

**Example**:
```
Chaos Monkey terminates instance of recommendation service
Expected behavior:
  - Load balancer detects failure (health check)
  - Routes traffic to healthy instances
  - Auto-scaler launches replacement instance
  - Users experience no disruption
```

**Observability**:

**Distributed tracing** (built in-house, similar to Jaeger):
```
Client request:
  ├─ Edge service (Zuul): 5ms
  ├─ User service: 20ms
  ├─ Recommendation service: 100ms ⚠ SLOW
  │   ├─ ML model inference: 80ms ⚠ BOTTLENECK
  │   └─ Metadata service: 15ms
  └─ Response: 5ms
Total: 130ms
```

**Actionable insight**: Optimize ML model (batch predictions, caching).

**Lessons**:
- Chaos engineering builds resilience
- Observability is critical at scale
- Caching is essential for performance

#### LinkedIn's Kafka Ecosystem

**Scale**:
- 900M+ members
- 7+ trillion events/day (Kafka)
- Largest Kafka deployment

**Kafka as central nervous system**:

**Use cases**:
1. **Activity tracking**: User actions (profile views, messages, posts)
2. **Metrics**: Service performance, errors, latency
3. **Logging**: Centralized log aggregation
4. **Stream processing**: Real-time analytics, ML features
5. **Data integration**: CDC (change data capture), ETL

**Brooklin** (data streaming platform):
- Multi-cluster Kafka replication
- Cross-datacenter mirroring
- Disaster recovery (async replication)

**Example**:
```
Primary datacenter (US-West):
  Kafka cluster A
      ↓ Brooklin replication
Secondary datacenter (US-East):
  Kafka cluster B (replica)
```

**If primary fails**: Failover to secondary.

**Samza** (stream processing):

**LinkedIn's stream processing framework**:
```java
class PageViewCounter extends StreamTask {
  public void process(
      IncomingMessageEnvelope envelope,
      MessageCollector collector,
      TaskCoordinator coordinator) {

    PageView pageView = (PageView) envelope.getMessage();

    // Count by page
    int count = state.get(pageView.page, 0);
    state.put(pageView.page, count + 1);

    // Emit updated count
    collector.send(new OutgoingMessageEnvelope(
      OUTPUT_STREAM,
      pageView.page,
      new PageViewCount(pageView.page, count + 1)
    ));
  }
}
```

**Venice** (derived data serving):

**Problem**: Kafka is great for streaming, but bad for random access.

**Solution**: Venice reads Kafka, builds indexes, serves queries.

```
Kafka topic: user-profiles (changelog)
            ↓
Venice: Ingests changes, builds key-value store
            ↓
Clients: Query Venice for low-latency reads (GET /user/123)
```

**Guarantees**:
- Eventual consistency (Venice lags behind Kafka by seconds)
- High throughput (millions of QPS)
- Low latency (P99 < 10ms)

**Architecture**:
```
Producers → Kafka (source of truth)
               ↓
          Venice storage nodes (key-value store)
               ↓
          Venice router (stateless query layer)
               ↓
          Clients
```

**Lessons**:
- Kafka enables event-driven architecture
- Stream processing powers real-time features
- Derived data stores optimize serving

---

## Synthesis: Patterns and Anti-Patterns

### Successful Patterns

**1. Start with the monolith**:

**Anti-pattern**: Greenfield project → immediately build microservices
**Problem**: Don't understand domain boundaries yet

**Pattern**: Build monolith → understand domain → extract services
**Why**: Service boundaries should align with domain boundaries (DDD)

**Example**:
```
Monolith:
  ├─ User module
  ├─ Order module
  ├─ Inventory module
  └─ Payment module

Understand coupling:
  User ←→ Order (high coupling, many calls)
  Order ←→ Inventory (medium coupling)
  Order → Payment (low coupling, one-way)

Extract services:
  Service 1: User + Order (keep coupled modules together)
  Service 2: Inventory
  Service 3: Payment
```

**2. Service per team**:

**Conway's Law**: "System architecture mirrors organization structure."

**Pattern**: Align services with team ownership
- Each team owns 1-5 services
- Team has end-to-end responsibility (dev, deploy, operate)
- Clear ownership enables accountability

**Anti-pattern**: Shared ownership (many teams touch one service)
**Problem**: Coordination overhead, unclear responsibility

**3. Events for integration**:

**Pattern**: Services integrate asynchronously via events
**Why**: Loose coupling, scalability, resilience

**Example**:
```
Order service: Order created → Publish OrderCreated event
                             ↓
Inventory service: Subscribe to OrderCreated → Reserve items
Email service: Subscribe to OrderCreated → Send confirmation
Analytics service: Subscribe to OrderCreated → Update metrics
```

**Services don't know about each other**, only events.

**Anti-pattern**: Synchronous service chains
```
Order service → Inventory service → Email service → Analytics service
```
**Problem**: Tight coupling, cascading failures, latency accumulation.

**4. Data products for analytics**:

**Pattern**: Domain teams expose data products for analytics
**Why**: Self-serve, federated ownership, scalability

**Example**:
```
Order team: Exposes "orders" data product (Kafka topic, S3 snapshots)
Analytics team: Subscribes to "orders" → Builds reports
ML team: Subscribes to "orders" → Trains models
```

**Anti-pattern**: Centralized data warehouse
**Problem**: Bottleneck (single team owns all data), doesn't scale

### Common Anti-Patterns

**1. Distributed monolith**:

**Symptoms**:
- Fine-grained services (100+ services)
- Tight coupling (service A always calls B, C, D)
- Synchronous chains (deep call stacks)
- Shared database (multiple services access same tables)

**Example**:
```
Frontend → Service A → Service B → Service C → Service D → Service E → Database

All services share database:
  Service A: Reads users, orders
  Service B: Reads orders, inventory
  Service C: Reads inventory, products
```

**Problem**: Microservices complexity, monolith coupling.

**Solution**:
- Consolidate tightly coupled services
- Database per service
- Asynchronous integration

**2. Chatty services**:

**Anti-pattern**: Service makes many small synchronous calls

**Example**:
```
GET /product/123

Product service:
  - Call inventory service (check stock)
  - Call pricing service (get price)
  - Call review service (get rating)
  - Call image service (get photos)
  - Call recommendation service (get related products)

Total: 5 service calls → 100ms latency
```

**Solution**:
- **Batch requests**: Call services in parallel
- **Data denormalization**: Product service caches data
- **BFF pattern**: Backend for Frontend aggregates calls

**3. Shared databases**:

**Anti-pattern**: Multiple services access same database tables

**Example**:
```
Order service: Writes to orders table
Inventory service: Reads from orders table (to know what to reserve)
Analytics service: Reads from orders table (for reports)
```

**Hidden coupling**:
- Schema changes break multiple services
- Performance issues (table locks, slow queries) affect all services
- Cannot change database technology per service

**Solution**:
- Database per service
- Services integrate via APIs or events
- Duplicate data where necessary (trade storage for independence)

**4. Missing observability**:

**Anti-pattern**: Deploy services without tracing, logging, metrics

**Symptoms**:
- "Where did this request fail?" (no tracing)
- "Why is latency high?" (no profiling)
- "What happened at 2am?" (no logging)

**Solution**:
- **Distributed tracing**: OpenTelemetry, Jaeger
- **Centralized logging**: ELK, Splunk, Datadog
- **Metrics**: Prometheus, Grafana
- **Dashboards**: Service health, traffic, errors, latency (RED metrics)

### Decision Framework

**When to use service mesh**:

**Use when**:
- 10+ services
- Need mTLS, observability, traffic management
- Polyglot architecture (many languages)

**Don't use when**:
- <10 services (overhead not worth it)
- Simple architecture (don't need features)
- Running on simple infrastructure (not Kubernetes)

**When to go event-driven**:

**Use when**:
- Asynchronous workflows (order processing, notifications)
- Event sourcing (audit log, temporal queries)
- High-throughput data pipelines (analytics, ML)
- Decoupling producers and consumers

**Don't use when**:
- Need immediate consistency (use synchronous calls)
- Simple CRUD (RESTful APIs sufficient)
- Low message volume (<100/sec)

**When to adopt data mesh**:

**Use when**:
- Large organization (100+ engineers)
- Many domains producing data
- Centralized data team is bottleneck
- Need federated ownership

**Don't use when**:
- Small team (<20 engineers)
- Single domain
- Centralized team works fine

**When to stay simple**:

**Don't over-engineer**:
- Start with monolith if domain unknown
- Add services when boundaries clear
- Add event streaming when async workflows emerge
- Add service mesh when security/observability needed

**Complexity is a tax**:
- More services = more deployment, monitoring, coordination
- More infrastructure = more operational overhead
- Only pay the tax when benefits exceed costs

### Future Directions

**eBPF and kernel-level observability**:

**eBPF** (extended Berkeley Packet Filter):
- Run custom code in Linux kernel
- Zero-overhead observability (no sidecars)
- Network, security, performance monitoring

**Use case**: Service mesh without sidecars
- Kernel intercepts network traffic
- Applies policies (routing, security)
- Collects metrics
- **Cilium** (eBPF-based service mesh)

**WebAssembly for edge compute**:

**Wasm**: Portable, sandboxed code execution
- Language-agnostic (compile Rust, C++, Go to Wasm)
- Near-native performance
- Secure sandbox

**Use case**: Edge functions
- Deploy Wasm to CDN edges
- Run custom logic close to users
- Cloudflare Workers, Fastly Compute@Edge

**AI-driven operations**:

**AIOps**: ML for IT operations
- Anomaly detection (unusual traffic, errors)
- Root cause analysis (what caused this outage?)
- Auto-remediation (restart failing services)
- Capacity planning (predict future load)

**Example**:
```
Anomaly detected: Latency P99 spiked from 100ms → 500ms
AI analysis:
  - Correlated with deployment of service-v2
  - Service-v2 making 3× more database queries
  - Recommendation: Rollback service-v2
  - Automatically executed rollback
```

**Quantum networking impact**:

**Quantum key distribution (QKD)**:
- Unbreakable encryption (quantum physics guarantees)
- Detect eavesdropping (observation changes quantum state)

**Implication for distributed systems**:
- Post-quantum cryptography needed (current encryption breakable by quantum computers)
- New security primitives
- Future (10-20 years)

---

## Exercises

### Design Exercises

**1. Design service mesh for e-commerce**:

**Requirements**:
- 15 microservices (user, product, cart, order, payment, inventory, etc.)
- Need mTLS between services
- Canary deployments for high-risk services (payment)
- Observability (tracing, metrics)

**Tasks**:
- Choose service mesh (Istio, Linkerd, or Consul)
- Design mTLS certificate rotation
- Define canary rollout strategy
- Design observability stack

**2. Create event-driven order processing**:

**Requirements**:
- Order flow: Submit → Validate → Charge → Reserve inventory → Ship
- Handle failures (payment declined, inventory unavailable)
- Idempotency (duplicate events must be safe)

**Tasks**:
- Design event schema (Avro)
- Define Kafka topics and partitioning
- Implement saga pattern (choreography or orchestration)
- Design compensation logic

**3. Plan data mesh for analytics**:

**Requirements**:
- 5 domains: Users, Products, Orders, Marketing, Support
- Each domain exposes data products
- Analytics team needs self-serve access

**Tasks**:
- Define data products per domain (schema, SLA)
- Design data catalog (metadata, discovery)
- Define governance policies (quality, privacy)
- Plan lineage tracking

**4. Build API gateway strategy**:

**Requirements**:
- External API for mobile/web clients
- Internal APIs for services
- Authentication (OAuth2), rate limiting, caching

**Tasks**:
- Choose gateway (Kong, Envoy, AWS API Gateway)
- Design authentication flow
- Define rate limiting strategy (per user, per API key)
- Design caching policy (which endpoints, TTL)

**5. Design serverless integration**:

**Requirements**:
- Process uploaded files (S3 upload triggers processing)
- Image processing (resize, thumbnail, metadata extraction)
- Async workflow (upload → resize → thumbnail → store)

**Tasks**:
- Design Lambda functions (trigger, processing, storage)
- Define workflow (Step Functions or Temporal)
- Handle errors (retries, dead letter queue)
- Monitor execution (CloudWatch, X-Ray)

### Implementation Projects

**1. Deploy Istio service mesh**:

**Steps**:
1. Set up Kubernetes cluster (Minikube, kind, or cloud)
2. Install Istio (`istioctl install`)
3. Deploy sample app (Bookinfo)
4. Enable sidecar injection
5. Configure mTLS (strict mode)
6. Create VirtualService (canary: 90% v1, 10% v2)
7. Monitor with Kiali (service graph)
8. Test traffic shifting

**2. Build event sourcing system**:

**Steps**:
1. Set up Kafka (Docker or cloud)
2. Define event schema (Avro: AccountOpened, MoneyDeposited, MoneyWithdrawn)
3. Implement event store (append events to Kafka topic)
4. Implement read model (rebuild state from events)
5. Test temporal queries (balance at time T)
6. Implement snapshot for performance

**3. Implement CQRS pattern**:

**Steps**:
1. Design write model (PostgreSQL: orders, order_items)
2. Design read model (MongoDB: customer_orders, product_sales)
3. Publish events on writes (OrderPlaced event to Kafka)
4. Implement event consumer (update read model)
5. Test eventual consistency (write → delay → read)
6. Measure staleness (event timestamp vs read model update)

**4. Create data product**:

**Steps**:
1. Choose domain (e.g., customer behavior)
2. Define schema (Avro: user_id, event_type, timestamp, properties)
3. Publish events to Kafka topic
4. Register schema in Schema Registry
5. Write documentation (README, examples)
6. Expose via data catalog
7. Implement quality checks (freshness, completeness)

**5. Build custom API gateway**:

**Steps**:
1. Set up Kong (Docker)
2. Configure service (backend service URL)
3. Add route (path → service mapping)
4. Enable plugins:
   - JWT authentication
   - Rate limiting (100 req/min)
   - Request logging
5. Test authentication (valid token → 200, invalid → 401)
6. Test rate limiting (exceed limit → 429)

### Analysis Tasks

**1. Analyze service dependencies**:

**Task**: Map service call graph for your system

**Steps**:
1. Collect distributed traces (Jaeger, Zipkin)
2. Extract service-to-service calls
3. Build dependency graph (nodes=services, edges=calls)
4. Identify:
   - Critical services (most depended on)
   - Chatty services (many calls)
   - Isolated services (no dependencies)
5. Visualize with Kiali or custom tool

**2. Measure event latencies**:

**Task**: Measure end-to-end event processing latency

**Steps**:
1. Instrument event producer (timestamp: event_produced_at)
2. Instrument event consumer (timestamp: event_consumed_at)
3. Calculate latency: consumed_at - produced_at
4. Collect metrics (P50, P95, P99)
5. Identify bottlenecks:
   - Producer publishing delay
   - Kafka broker lag
   - Consumer processing delay
6. Optimize slowest component

**3. Audit data quality**:

**Task**: Measure data product quality

**Steps**:
1. Define quality metrics:
   - Freshness (event timestamp vs now)
   - Completeness (expected events vs actual)
   - Accuracy (schema violations)
2. Implement quality checks (automated scripts)
3. Run checks periodically (cron, Airflow)
4. Generate quality score (weighted average)
5. Alert on quality degradation

**4. Profile service mesh overhead**:

**Task**: Measure latency added by service mesh

**Steps**:
1. Baseline: Measure service latency without mesh
2. Enable mesh: Deploy Istio sidecars
3. Measure latency with mesh
4. Calculate overhead: latency_mesh - latency_baseline
5. Break down overhead:
   - mTLS handshake
   - Policy evaluation
   - Sidecar routing
6. Optimize if overhead exceeds threshold (e.g., >10%)

**5. Calculate composition costs**:

**Task**: Measure cost of microservices vs monolith

**Steps**:
1. Infrastructure costs:
   - Compute (VMs, containers per service)
   - Network (inter-service traffic)
   - Storage (databases per service)
2. Operational costs:
   - Deployment (CI/CD per service)
   - Monitoring (metrics, logs per service)
   - On-call (more services = more alerts)
3. Compare to monolith costs
4. Calculate break-even point (when microservices cost < monolith value)

---

## Key Takeaways

**Modern systems are compositional**:
- Services compose via mesh
- Events compose via streaming
- Data composes via products
- Composition boundaries require explicit evidence propagation

**Service mesh provides infrastructure**:
- mTLS (zero-trust security)
- Traffic management (canary, circuit breaking)
- Observability (tracing, metrics)
- Language-agnostic (sidecar pattern)

**Events enable loose coupling**:
- Asynchronous integration
- Scalability (decouple producers/consumers)
- Resilience (buffer failures)
- Audit log (event sourcing)

**Data mesh scales analytics**:
- Federated ownership (domain teams own data products)
- Self-serve (analytics teams consume directly)
- Governance (policy as code)
- Quality (SLA, monitoring)

**Observability is non-negotiable**:
- Distributed tracing (causality across services)
- Centralized logging (correlation)
- Metrics aggregation (performance)
- Service dependency mapping (understanding)

**Security must be built-in**:
- Zero-trust (verify everything)
- mTLS (service identity)
- Policy enforcement (authorization)
- Secrets management (no hardcoded credentials)

**Complexity requires discipline**:
- Start simple (monolith → services)
- Align with teams (Conway's Law)
- Measure costs (infrastructure, operational)
- Avoid anti-patterns (distributed monolith, chatty services)

---

## Further Reading

### Books

**Architecture Patterns**:
- Newman, Sam. "Building Microservices" (2021, 2nd ed.) — Comprehensive microservices guide
- Kleppmann, Martin. "Designing Data-Intensive Applications" (2017) — Foundational distributed systems
- Stopford, Ben. "Designing Event-Driven Systems" (2018) — Event streaming patterns
- Dehghani, Zhamak. "Data Mesh" (2022) — Data mesh principles and implementation

**Service Mesh**:
- Calcote, Lee & Butcher, Nic. "Istio: Up and Running" (2019) — Istio practical guide
- Morgan, Liam. "Service Mesh Patterns" (2020) — Common patterns and anti-patterns

**Event Streaming**:
- Narkhede, Neha et al. "Kafka: The Definitive Guide" (2021, 2nd ed.) — Kafka deep dive
- Boner, Jonas. "Reactive Design Patterns" (2017) — Event-driven architecture patterns

**Cloud Native**:
- Burns, Brendan et al. "Kubernetes: Up and Running" (2022, 3rd ed.) — Kubernetes fundamentals
- Indrasiri, Kasun & Suhothayan, Sriskandarajah. "Kubernetes Patterns" (2023) — Cloud-native patterns

### Papers and Articles

**Service Mesh**:
- "The Service Mesh: What Every Software Engineer Needs to Know About the World's Most Over-Hyped Technology" (Buoyant blog)
- "Envoy Proxy: Architecture Overview" (Envoy documentation)

**Event Streaming**:
- "Apache Kafka: A Distributed Streaming Platform" (Confluent)
- "Streaming 101: The World Beyond Batch" (Tyler Akidau, 2015)
- "Event Sourcing" (Martin Fowler, 2005)

**Data Mesh**:
- "How to Move Beyond a Monolithic Data Lake to a Distributed Data Mesh" (Zhamak Dehghani, 2019)
- "Data Mesh Principles and Logical Architecture" (Zhamak Dehghani, 2020)

**Production Experience**:
- Netflix Tech Blog (netflixtechblog.com) — Microservices, chaos engineering
- Uber Engineering Blog (eng.uber.com) — Service architecture evolution
- Spotify Engineering (engineering.atspotify.com) — Event-driven architecture
- LinkedIn Engineering (engineering.linkedin.com) — Kafka ecosystem

### Open Source Projects

**Service Mesh**:
- Istio (istio.io) — Feature-rich service mesh
- Linkerd (linkerd.io) — Lightweight, Rust-based
- Consul Connect (consul.io) — HashiCorp's service mesh

**Event Streaming**:
- Apache Kafka (kafka.apache.org) — Distributed streaming platform
- Apache Pulsar (pulsar.apache.org) — Cloud-native streaming
- NATS (nats.io) — Lightweight messaging

**Observability**:
- OpenTelemetry (opentelemetry.io) — Observability standard
- Jaeger (jaegertracing.io) — Distributed tracing
- Prometheus (prometheus.io) — Metrics and alerting
- Grafana (grafana.com) — Visualization

**API Gateway**:
- Kong (konghq.com) — Open-source API gateway
- Envoy Gateway (gateway.envoyproxy.io) — Envoy-based gateway

---

## Chapter Summary

### The Compositional Revolution

**"Modern distributed systems aren't built from scratch—they're composed from services, events, and data products, each with explicit guarantees that weaken predictably at compositional boundaries."**

This chapter explored how modern distributed systems embrace composition as a first-class design principle. Not the monolithic composition of the past, but dynamic orchestration of hundreds or thousands of independent components, each preserving local invariants while participating in global workflows.

### Key Mental Models

**1. Composition Over Construction**

Modern systems aren't monolithic artifacts but compositions of:
- **Services** communicating through meshes
- **Events** flowing through streams
- **Data** exposed as products
- **Functions** executing at edges

Each component has well-defined boundaries, explicit contracts, and independent lifecycle.

**2. Evidence at Boundaries**

Composition preserves invariants through evidence propagation:
- **Service mesh**: mTLS certificates prove identity, trace contexts prove causality
- **Event streams**: Offsets prove ordering, commits prove delivery
- **Data mesh**: Schemas prove compatibility, lineage proves provenance
- **API gateway**: Tokens prove authorization, counters prove rate compliance

Evidence flows across boundaries in **context capsules**, weakening predictably at each composition point.

**3. Mode Coordination**

Modern systems degrade through coordinated mode transitions:
- **Target mode**: All components healthy, full guarantees
- **Degraded mode**: Partial failures, weakened guarantees, explicit
- **Floor mode**: Survival, minimal guarantees, safety preserved
- **Recovery mode**: Gradual restoration, progressive guarantee strengthening

Each component signals its mode; composition respects weakest mode.

**4. Patterns Compose**

Architectural patterns are compositional:
- Service mesh + Event streaming (sync + async)
- API gateway + Service mesh (external + internal)
- Data mesh + Event streaming (products + pipelines)
- Serverless + Edge computing (functions + regions)

Patterns compose through shared evidence (trace context, correlation IDs, lineage).

**5. Operational Complexity Is Real**

Composition has costs:
- **Infrastructure**: More components, more overhead
- **Deployment**: More pipelines, more coordination
- **Observability**: More traces, more logs, more metrics
- **Failure modes**: More cascades, more degradation paths

Only adopt when benefits (scalability, resilience, velocity) exceed costs.

### The Evidence-Based View

Reframe modern architecture through evidence:

- **Service mesh**: Infrastructure for generating and verifying service identity evidence, with explicit traffic policy evidence and health check evidence
- **Event streaming**: Infrastructure for generating order evidence (offsets) and delivery evidence (commits), enabling replay from any evidence point
- **Data mesh**: Infrastructure for exposing data with quality evidence (SLA compliance), compatibility evidence (schema registry), and provenance evidence (lineage)
- **Composition**: Propagating evidence across boundaries via context capsules, weakening guarantees explicitly at each composition point

### Practical Takeaways

**Design Principles**:
- Start simple (monolith), compose when boundaries clear
- Align services with teams (Conway's Law)
- Events for async integration (loose coupling)
- Data products for analytics (federated ownership)
- Observability from day one (tracing, logging, metrics)

**Technology Choices**:
- Service mesh when >10 services, need mTLS/observability
- Event streaming for async workflows, high throughput
- Data mesh for large orgs, federated data ownership
- API gateway for external APIs, cross-cutting concerns
- Stay simple when benefits don't justify costs

**Operational Guidelines**:
- Monitor mode state across components
- Alert on evidence expiration/degradation
- Test partition scenarios (chaos engineering)
- Document mode transitions and triggers
- Measure composition costs (infrastructure, operational)

**Debugging Approaches**:
- Distributed tracing for causality
- Centralized logging for correlation
- Metrics for performance
- Service graphs for dependencies
- Mode state for degradation understanding

### What's Next

This chapter showed how modern systems compose services, events, and data products. But composition introduces new challenges: How do we observe complex interactions? How do we debug failures that span 50+ services? How do we ensure security when every service is a potential attack vector?

The next chapter would explore **Observability and Debugging at Scale**—the tools, techniques, and mental models for understanding and operating compositional distributed systems. We'd explore distributed tracing (following requests across services), log aggregation (correlating events), metrics collection (understanding performance), and chaos engineering (testing resilience).

But for now, we've established the compositional foundation: modern distributed systems preserve invariants through evidence propagation across compositional boundaries, degrading explicitly through coordinated mode transitions when evidence cannot be maintained.

---

## Sidebar: Cross-Chapter Connections

**To Chapter 1 (Impossibility Results)**:
- Service mesh handles CAP choice (circuit breakers for partitions)
- Event streaming handles FLP (timeouts for consensus in consumer groups)
- PACELC manifests in sync (mesh) vs async (events) choice

**To Chapter 2 (Time, Order, Causality)**:
- Distributed tracing uses happens-before (causality across services)
- Event streams use Lamport timestamps (partition offsets)
- Data mesh uses vector clocks (schema versions, lineage)

**To Chapter 3 (Consensus)**:
- Service mesh uses leader election (Istio control plane)
- Event streaming uses Paxos (Kafka controller election)
- Distributed transactions use sagas (consensus-free coordination)

**To Chapter 4 (Replication)**:
- Service mesh routes to replicas (load balancing)
- Event streaming replicates partitions (Kafka ISR)
- Data mesh replicates data products (multi-region)

**To Chapter 5 (Transactions)**:
- ACID in services (local transactions)
- Sagas across services (distributed transactions without 2PC)
- Event sourcing as transaction log (append-only, immutable)

**To Chapter 6 (Storage)**:
- Database per service (polyglot persistence)
- Event store (Kafka as durable log)
- Data lake/warehouse (data mesh analytics layer)

**To Chapter 7 (Cloud-Native)** (if exists):
- Kubernetes as orchestration platform
- Service mesh on Kubernetes
- Serverless functions (Lambda, Cloudflare Workers)

---

**This chapter's guarantee vector**: `⟨Global, Causal, RA, BS(production-examples), Idem, Auth(case-studies)⟩` — We've explored global compositional patterns, established causal understanding through real architectures, provided read-atomic knowledge of modern systems, bounded staleness through production examples (Netflix, Uber, Spotify, Airbnb, LinkedIn), offered idempotent insights you can revisit, all authenticated by production case studies and open-source implementations.

**Context capsule for next chapter**: `{invariant: OBSERVABILITY, evidence: traces+logs+metrics, boundary: compositional systems, mode: Target, fallback: manual debugging}`

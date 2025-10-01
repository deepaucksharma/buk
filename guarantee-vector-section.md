### Guarantee Vectors: Typing End-to-End Properties

We've seen what's impossible. Now we need a precise way to describe what guarantees *are* possible, how they compose, and how they degrade when impossibilities manifest.

Traditional approaches label systems with single adjectives: "strongly consistent," "eventually consistent," "highly available." These labels are too coarse. Consider: a globally replicated system might be strongly consistent for writes (via Paxos) but eventually consistent for reads (via local replicas), with bounded staleness of 100ms, and idempotent retry semantics for failures. How do we capture this?

**Guarantee vectors** provide a typed, compositional framework for precisely specifying distributed system guarantees. Instead of one label, we use a 6-tuple that captures orthogonal dimensions of system behavior:

```
G = ⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩
```

Each component types a specific aspect of the guarantee. The vector notation makes composition explicit: when services chain, guarantees compose via well-defined operators. Most importantly, the **weakest component determines the end-to-end guarantee**—a principle that makes system analysis tractable.

#### Why Vectors? The Composition Problem

Consider a read request in a distributed database:

```
Client → Load Balancer → API Gateway → Database Leader → Storage Engine → Disk
```

Each hop provides guarantees:
- Load balancer: Eventually routes to healthy node (eventual order)
- API Gateway: Session consistency (causal order)
- Database Leader: Linearizable writes (strict serializability)
- Storage Engine: Snapshot isolation (serializable visibility)
- Disk: Durable writes (persistent)

What guarantee does the client get? **The meet (∧) of all components**: eventual order ∧ causal ∧ linearizable ∧ snapshot = **eventual consistency** (the weakest). A single eventually consistent component weakens the entire chain.

Traditional labels hide this. Guarantee vectors make it explicit.

#### The 6-Tuple Definition

Let's define each component with precision:

**1. Scope: Over What Space Does the Guarantee Hold?**

```
Scope ∈ {Object, Range, Transaction, Global}
```

- **Object**: Guarantee applies to a single object/key
  - Example: Per-key linearizability (each key independently consistent)
- **Range**: Guarantee applies to a contiguous keyspace range
  - Example: Range locks, shard-local transactions
- **Transaction**: Guarantee applies to all objects in a transaction
  - Example: Snapshot isolation across transaction scope
- **Global**: Guarantee applies to the entire system
  - Example: Strict serializability across all keys

**Why it matters**: Scope determines coordination cost. Object-scope is cheap (local). Global scope is expensive (all nodes must coordinate). Impossibility results constrain achievable scope—FLP limits global scope, CAP forces scope reduction during partitions.

**2. Order: How Are Operations Sequenced?**

```
Order ∈ {None, Causal, Lx, SS}
```

- **None**: No ordering guarantee (operations may appear in any order)
  - Example: Shopping cart with concurrent adds (resolve later)
- **Causal**: Operations preserve causality (if A happened-before B, all observers see A before B)
  - Example: Social media feed (replies appear after posts)
- **Lx (Linearizable per-object)**: Each object has a total order respecting real-time
  - Example: Redis INCR (atomic increments per key)
- **SS (Strict Serializable)**: Global total order respecting real-time across all objects
  - Example: Spanner transactions, SERIALIZABLE in PostgreSQL

**Why it matters**: Order determines whether you can reason about "happened before." FLP impossibility constrains achievable order without synchrony assumptions. PACELC says stronger order costs latency.

**3. Visibility: What Do Concurrent Transactions See?**

```
Visibility ∈ {Fractured, RA, SI, SER}
```

- **Fractured**: No consistency across reads (each read may see different version)
  - Example: Stale cache hits during partition
- **RA (Read Atomic)**: All reads in an operation see the same consistent snapshot
  - Example: Eventual consistency with read-your-writes
- **SI (Snapshot Isolation)**: Transactions read from a consistent snapshot, no write skew within transaction
  - Example: MVCC databases at default isolation level
- **SER (Serializable)**: Equivalent to some serial execution; prevents all anomalies
  - Example: PostgreSQL SERIALIZABLE, Spanner

**Why it matters**: Visibility determines what anomalies are possible (phantom reads, write skew, lost updates). CAP theorem directly constrains visibility during partitions—partition means fractured visibility unless you sacrifice availability.

**4. Recency: How Fresh Is the Data?**

```
Recency ∈ {EO, BS(δ), Fresh(φ)}
```

- **EO (Eventual Order)**: Writes propagate eventually, no time bound
  - Example: DNS propagation (minutes to hours)
- **BS(δ) (Bounded Staleness)**: Reads are at most δ time units stale
  - Example: Azure Cosmos DB with 5-second staleness bound
- **Fresh(φ) (Fresh with proof φ)**: Reads are guaranteed fresh, with verifiable evidence φ
  - Example: Linearizable read with quorum certificate or leader lease

**Why it matters**: Recency captures the time dimension of consistency. PACELC's latency-consistency trade-off is explicitly in the recency component. Fresh(φ) requires evidence (quorum, lease), which FLP says needs failure detection.

**5. Idempotence: Can Operations Be Safely Retried?**

```
Idempotence ∈ {None, Idem(K)}
```

- **None**: Operations are not idempotent; retries may cause duplicates
  - Example: POST without idempotency key (double-charge risk)
- **Idem(K)**: Operations idempotent with keying discipline K
  - Example: PUT with conditional writes, POST with idempotency token

**Why it matters**: Networks lose messages. Retries are inevitable. Without idempotence, you risk duplicate operations (double-charges, duplicate orders). Idem(K) makes retries safe, which is essential for circumventing FLP (retry until success) and CAP (retry after partition heals).

**6. Auth: Who Can Generate Evidence?**

```
Auth ∈ {Unauth, Auth(π)}
```

- **Unauth**: No authentication; trust all claims
  - Example: Internal service mesh (trusted network)
- **Auth(π)**: Evidence requires authentication via mechanism π
  - Example: JWT tokens, mTLS certificates, signatures

**Why it matters**: Byzantine failures and security require authenticated evidence. Auth(π) enables verification without trust. In Byzantine consensus, Auth(π) reduces message complexity from O(n³) to O(n²) (lower bound).

#### Composition Operators: How Guarantees Transform

Guarantees don't exist in isolation—they compose through system boundaries. We define four composition operators:

**1. Meet (∧): Sequential or Parallel Composition**

When service A calls service B, or when merging results from parallel calls:

```
G_result = meet(G_A, G_B)
```

**Meet rule**: Component-wise minimum (weakest wins)

Example:
```
G_A = ⟨Global, SS, SER, Fresh(φ), Idem(K), Auth⟩
G_B = ⟨Range, Causal, RA, BS(100ms), Idem(K), Auth⟩

G_result = ⟨Range, Causal, RA, BS(100ms), Idem(K), Auth⟩
```

Interpretation: B's weaker guarantees propagate to the result. The chain is only as strong as its weakest link.

**Why**: Evidence cannot strengthen spontaneously. If B provides only range-scoped evidence, the result cannot be global. If B provides bounded-stale data, the result cannot be fresh.

**2. Upgrade (↑): Inject Evidence to Strengthen**

To strengthen guarantees, inject evidence-generating mechanism:

```
G_weak ↑ Evidence(φ) → G_strong
```

Example: Add consensus to eventual consistency
```
G_weak = ⟨Range, Causal, RA, EO, Idem(K), Auth⟩
      ↑ PaxosConsensus(quorum_cert)
→ G_strong = ⟨Global, Lx, SER, Fresh(quorum_cert), Idem(K), Auth⟩
```

**Upgrade is not free**: It requires coordination, which adds latency. This is PACELC's EL trade-off made explicit.

Examples:
- EO ↑ Fresh: Add leader lease + fencing tokens
- Causal ↑ SS: Add consensus protocol (Paxos, Raft)
- Unauth ↑ Auth: Add signature verification

**3. Downgrade (⤓): Explicit Weakening**

When evidence expires or is unavailable, explicitly weaken guarantees:

```
G_strong ⤓ reason → G_weak
```

Example: Partition detection
```
G_CP = ⟨Global, SS, SER, Fresh(φ), Idem(K), Auth⟩
     ⤓ partition_minority
→ G_degraded = ⟨Local, None, Fractured, EO, Idem(K), Auth⟩
```

**Downgrade must be explicit**: System must detect the condition (partition, timeout, lease expiry) and communicate the weakened guarantee to clients.

Examples:
- Fresh ⤓ BS: Lease expired, serve cached data with staleness bound
- SS ⤓ Causal: Partition detected, majority unavailable
- Auth ⤓ Unauth: Certificate expired, continue in degraded mode

**4. Context Capsule: Carrying Guarantees Across Boundaries**

When calling another service, send a **context capsule** that declares the guarantee:

```
ContextCapsule {
  current_G: GuaranteeVector,
  required_G: GuaranteeVector,
  evidence: Evidence,
  mode: Mode(Target | Degraded | Floor | Recovery),
  epoch: Epoch,
  staleness_bound: Option<Duration>
}
```

The callee:
1. Checks if it can meet `required_G`
2. If yes: provides `required_G` (or stronger)
3. If no: returns error or degraded result with actual `G`

**Example**: API gateway calls database
```
Capsule sent:
  required_G = ⟨Transaction, SS, SER, Fresh(φ), Idem(K), Auth⟩

Database response:
  actual_G = ⟨Transaction, SS, SER, BS(50ms), Idem(K), Auth⟩
  reason = "Leader lease expired 50ms ago"
  mode = Degraded
```

Gateway now knows it received stale data and can decide: accept it, retry, or return error to client.

#### Worked Examples: Impossibilities Through Vectors

Let's see how impossibility results manifest as constraints on achievable guarantee vectors.

**Example 1: FLP Impossibility Transformation**

**Start**: Pure asynchronous system (no failure detection)
```
G_async = ⟨Global, Causal, RA, EO, Idem(K), Auth⟩
```
- No termination guarantee (FLP)
- Cannot upgrade to linearizable order

**Add**: Eventually Perfect Failure Detector (◊P)
```
G_async ↑ ◊P(heartbeat, timeout) → G_FLP_circumvent
G_FLP_circumvent = ⟨Global, Lx, SER, Fresh(lease), Idem(K), Auth⟩
```
- Now achieves linearizable order
- Termination guaranteed after GST (Global Stabilization Time)

**Evidence chain**:
1. Heartbeat receipt → liveness evidence
2. Timeout expiry → failure suspicion evidence
3. Quorum of non-failed processes → majority evidence
4. Leader lease based on majority → freshness evidence (φ = lease)

**Key insight**: FLP says you can't get Fresh(φ) without detectable time bounds. Adding ◊P provides those bounds (eventual accuracy), enabling the upgrade.

**Example 2: CAP Decision Tree with Vectors**

**Initial state** (no partition):
```
G_initial = ⟨Global, SS, SER, Fresh(φ), Idem(K), Auth⟩
```
- Both consistency and availability achieved

**Partition detected**: Network split into majority and minority

**CP Choice** (prioritize consistency):

Majority partition:
```
G_CP_majority = ⟨Global, SS, SER, Fresh(φ), Idem(K), Auth⟩
```
- Maintains all strong guarantees
- Availability: Yes (has quorum)

Minority partition:
```
G_CP_minority = ⟨Local, None, Fractured, EO, Idem(K), Auth⟩
```
- Scope reduced to Local (no quorum)
- Order reduced to None (cannot commit)
- Visibility fractured (no consistent reads)
- Availability: No (fail closed)

**AP Choice** (prioritize availability):

Both partitions:
```
G_AP_both = ⟨Range, Causal, RA, BS(δ), Idem(K), Auth⟩
```
- Scope reduced to Range (per-partition)
- Order weakened to Causal (vector clocks)
- Recency weakened to Bounded Staleness
- Visibility read-atomic (consistent within partition)
- Availability: Yes (both partitions serve requests)

**Evidence changes**:
- CP: Requires Fresh(φ) = quorum certificate; minority lacks it → blocks
- AP: Accepts BS(δ) = last-known version; both partitions have local evidence → continue

**Key insight**: CAP is about which evidence you require. CP requires fresh quorum evidence (unavailable in minority). AP accepts bounded-stale local evidence (available in both).

**Example 3: PACELC Latency-Consistency Trade-off**

**Scenario**: Cross-region replication (3 datacenters: US-East, US-West, EU)

**Choice 1: PC/EC** (Consistency always, even during normal operation)
```
G_PC_EC = ⟨Global, SS, SER, Fresh(φ_quorum), Idem(K), Auth⟩
```
- Every write: Synchronous replication to 2/3 replicas (quorum)
- Latency: 150ms (cross-region RTT)
- Partition: Minority unavailable (PC)
- Evidence: Quorum certificate for every operation

**Choice 2: PA/EL** (Low latency normally, availability during partition)
```
G_PA_EL = ⟨Range, Causal, RA, BS(200ms), Idem(K), Auth⟩
```
- Every write: Asynchronous replication
- Latency: 5ms (local write)
- Partition: All partitions continue (PA)
- Evidence: Local version vector, replicate best-effort

**Composition cost**:
```
PC/EC: Latency = 150ms, Availability = 99.9%
PA/EL: Latency = 5ms, Availability = 99.99%

For 3-hop service chain (A → B → C):
PC/EC chain: 450ms total latency
PA/EL chain: 15ms total latency
```

**Key insight**: PACELC's EL trade-off is explicit in the Recency component. Fresh(φ) requires coordination (latency cost). BS(δ) or EO avoid coordination (low latency).

**Example 4: DynamoDB Request Path Composition**

Let's trace a single GetItem request through DynamoDB's architecture with guarantee vector composition:

**1. Client SDK → Load Balancer**
```
G_client = ⟨Object, Lx, SER, Fresh(φ), Idem(K), Auth(IAM)⟩
```
(Client desires strong consistency)

**2. Load Balancer → Storage Node**
```
G_lb = ⟨Range, Causal, RA, BS(100ms), Idem(K), Auth(IAM)⟩
```
(Load balancer may route to stale replica)

**Composition (meet)**:
```
G_result = meet(G_client, G_lb) = ⟨Object, Causal, RA, BS(100ms), Idem(K), Auth(IAM)⟩
```

**3. Strongly Consistent Read Request** (client specifies):
```
Request: GetItem(ConsistentRead=true)
```

This injects an upgrade operator:
```
G_lb ↑ QuorumRead(evidence=partition_lease) → G_strong
G_strong = ⟨Object, Lx, SER, Fresh(partition_lease), Idem(K), Auth(IAM)⟩
```

**Evidence chain**:
- Partition lease: Proves which node owns this key range
- Quorum read: Reads from quorum of replicas (latest version)
- Version number: Provides ordering evidence

**Cost**: +10ms latency (quorum read vs. local read)

**4. Partition Scenario**: During partition, quorum unreachable

Storage node downgrades:
```
G_strong ⤓ partition_quorum_lost → G_degraded
G_degraded = ⟨Object, None, Fractured, EO, Idem(K), Auth(IAM)⟩
```

Response to client:
```
Error: ServiceUnavailable
Message: "Cannot satisfy ConsistentRead=true during partition"
```

Client can retry with ConsistentRead=false:
```
G_eventual = ⟨Object, Causal, RA, BS(δ_unknown), Idem(K), Auth(IAM)⟩
```
- Returns potentially stale data
- But remains available (AP choice)

**Vector transformation summary**:
```
Desired:     ⟨Object, Lx, SER, Fresh(φ), Idem(K), Auth⟩
Available:   ⟨Range, Causal, RA, BS(100ms), Idem(K), Auth⟩
Upgrade:     ↑ QuorumRead(lease)
Achieved:    ⟨Object, Lx, SER, Fresh(lease), Idem(K), Auth⟩
Degraded:    ⤓ partition_quorum_lost
Final:       ⟨Object, None, Fractured, EO, Idem(K), Auth⟩
```

#### Visual Model: The Guarantee Lattice

Guarantees form a lattice ordered by strength. Here's the partial order for the Order component:

```
         SS (Strict Serializable)
          |
         Lx (Linearizable per-object)
          |
       Causal
          |
        None

Composition: meet(SS, Causal) = Causal (weaker)
Upgrade:     Causal ↑ consensus → SS (requires evidence)
Downgrade:   SS ⤓ partition → Causal (lose global order)
```

The same lattice structure applies to each component:

**Scope lattice**: Global > Transaction > Range > Object
**Visibility lattice**: SER > SI > RA > Fractured
**Recency lattice**: Fresh(φ) > BS(δ) > EO

**Composition rule**: Move down the lattice (to weaker guarantees) unless evidence moves you up.

#### Key Insights: Why This Framework Matters

**1. Weakest Component Determines End-to-End Guarantee**

A system is only as strong as its weakest link. If any component in a chain provides Fractured visibility, the end-to-end guarantee is Fractured, no matter how strong other components are.

**Implication**: Audit every boundary. One eventually consistent cache ruins linearizability.

**2. Evidence Costs Are Explicit**

Every upgrade requires evidence. Evidence requires coordination. Coordination has latency cost:
- EO → BS(δ): Add version tracking, asynchronous replication
- BS(δ) → Fresh(φ): Add quorum reads/writes, consensus protocol
- None → Causal: Add vector clocks, causality tracking
- Causal → SS: Add global consensus (Paxos, Raft)

PACELC's trade-off is visible: stronger guarantees (higher in lattice) cost more latency.

**3. Impossibilities Constrain Achievable Vectors**

FLP: Cannot achieve `⟨Global, SS, SER, Fresh(φ), _, _⟩` in pure asynchronous system (no evidence generation without time bounds)

CAP (during partition):
- CP: Cannot achieve availability in minority
- AP: Cannot achieve Fresh(φ) globally (evidence cannot propagate)

PACELC: Fresh(φ) costs latency proportional to replication distance and coordination rounds

**4. Composition Is Predictable**

Given:
```
G_A = ⟨Scope_A, Order_A, Vis_A, Rec_A, Idem_A, Auth_A⟩
G_B = ⟨Scope_B, Order_B, Vis_B, Rec_B, Idem_B, Auth_B⟩
```

Sequential composition (A → B):
```
G_result = ⟨min(Scope_A, Scope_B),
            min(Order_A, Order_B),
            min(Vis_A, Vis_B),
            min(Rec_A, Rec_B),
            min(Idem_A, Idem_B),
            min(Auth_A, Auth_B)⟩
```

This makes reasoning tractable. You don't need to simulate execution—just compute the meet.

**5. Degradation Is Explicit and Controlled**

When impossibilities manifest (partition, timeout, lease expiry), systems must downgrade:

```
if partition_detected() && is_minority():
    current_G ⤓ partition_minority
    capsule.mode = Degraded
    capsule.actual_G = ⟨Local, None, Fractured, EO, Idem, Auth⟩
    return ServiceUnavailable(capsule)
```

Clients see the degraded guarantee explicitly and can decide how to proceed.

#### Connection to Impossibility Results: The Complete Picture

Let's tie this back to what we've learned:

**FLP Impossibility**:
```
Asynchronous system:  ⟨_, _, _, EO, _, _⟩  (no time bounds)
       ↑ ◊P (failure detector)
Eventually synchronous: ⟨_, _, _, Fresh(φ), _, _⟩  (after GST)
```

FLP says: You cannot upgrade from EO to Fresh(φ) without assumptions. Failure detectors provide those assumptions.

**CAP Theorem**:
```
No partition:  ⟨Global, SS, SER, Fresh(φ), _, _⟩
Partition + CP: Majority: ⟨Global, SS, SER, Fresh(φ), _, _⟩
                Minority: ⟨Local, None, Fractured, EO, _, _⟩
Partition + AP: Both:     ⟨Range, Causal, RA, BS(δ), _, _⟩
```

CAP says: Cannot maintain Fresh(φ) globally during partition without sacrificing availability. Pick which component to weaken: Recency (AP) or Availability (CP).

**PACELC**:
```
Fresh(φ):   Latency = high  (quorum coordination)
BS(δ):      Latency = medium (async replication)
EO:         Latency = low     (local-only)
```

PACELC says: Recency component directly trades against latency. Explicit in the vector.

**Consensus Lower Bounds**:
```
SS requires:  f+1 rounds minimum
Fresh(φ):     Quorum reads/writes (majority round-trips)
Global:       O(n) messages minimum
```

Lower bounds determine the minimum cost of generating evidence for each component. The vector makes the cost structure explicit.

---

### Summary: Guarantees as Types

Guarantee vectors transform distributed systems reasoning from art to science:

**Before**: "This system is eventually consistent... mostly... except when it's strongly consistent... I think?"

**After**: "This system provides `⟨Range, Causal, RA, BS(100ms), Idem(K), Auth⟩` in Target mode, degrading to `⟨Object, None, Fractured, EO, Idem(K), Auth⟩` during partitions, with explicit downgrade notification."

The vector framework gives us:
1. **Precision**: Each component is well-defined
2. **Composability**: Meet operator for chaining services
3. **Predictability**: Weakest component determines end-to-end guarantee
4. **Observability**: Vectors can be exposed in APIs and monitoring
5. **Operationality**: Explicit upgrade/downgrade operators

Most importantly, guarantee vectors make **impossibility results operational**. They're not abstract theorems—they're constraints on achievable vectors. When you see a system's guarantee vector, you see exactly which impossibilities it respects and how it circumvents them.

In the next section, we explore the formal evidence calculus that underlies these vectors—the precise rules for evidence generation, propagation, expiration, and verification that make guarantees verifiable rather than aspirational.

---

!!! key-takeaway "The Conservation Principle for Guarantees"
    **Guarantees cannot strengthen without evidence.** When service A calls service B:

    - If B provides weaker guarantees than A, the result is weak (evidence dilutes)
    - If B provides stronger guarantees than A needs, the result matches A's request (evidence is sufficient)
    - To strengthen guarantees mid-chain requires injecting evidence-generating mechanism (upgrade operator)

    **Corollary**: Single-page systems are easier to reason about than distributed systems because there's no composition—one evidence domain, one guarantee vector. Distribution forces composition, and composition applies the meet operator, weakening guarantees at every boundary unless explicitly managed.

---

!!! example "Exercise: Analyze Your System's Guarantee Vector"
    Pick a critical request path in your system (e.g., "user login" or "place order"):

    1. **List all hops**: Client → Gateway → Auth Service → Database → ...
    2. **Assign vectors**: What guarantee does each hop provide?
    3. **Compute meet**: What's the end-to-end vector?
    4. **Identify weakest link**: Which hop determines the overall guarantee?
    5. **Spot upgrade opportunities**: Where could you inject evidence to strengthen?
    6. **Design degradation**: What should each hop's vector become during partition/timeout?

    If you can't answer these questions, your system's guarantees are implicit and fragile. Making them explicit via vectors is the first step to operationalizing impossibility results.

# The Invariant Hierarchy and Evidence Model: Understanding Impossibility Results

## Introduction: Impossibility as Invariant Protection

The foundational impossibility results in distributed systems—FLP, CAP, and their descendants—are not arbitrary mathematical curiosities. They are fundamental statements about what can and cannot be preserved across space and time when information is distributed. At their core, these impossibility results are theorems about **invariant protection**: they define the boundaries of what properties can be maintained simultaneously when uncertainty is irreducible.

This chapter develops a rigorous framework for understanding impossibility results through the lens of invariants and evidence. We will see that:

1. Every impossibility result protects a fundamental invariant by proving that certain combinations of properties cannot coexist
2. The "impossibility" is actually the absence of sufficient evidence to make decisions while preserving all desired invariants
3. Practical systems circumvent these impossibilities by introducing new forms of evidence (failure detectors, bounded synchrony assumptions, randomization)
4. Understanding the invariant hierarchy helps us design systems that degrade predictably when evidence becomes unavailable

**The Central Insight**: A distributed system is a machine for preserving invariants across space and time by converting uncertainty into evidence. Impossibility results tell us where this conversion fails fundamentally.

---

## Part 1: PRIMARY INVARIANT - CONSERVATION

### 1.1 What is Conservation in Distributed Systems?

**Conservation** is the fundamental invariant that states: **Nothing is created or destroyed except through authorized, observable flows.**

In distributed systems, conservation manifests in several critical forms:

#### 1.1.1 Decision Conservation (Consensus)
Once a decision is made, it cannot be unmade or changed. If process P decides value v, then:
- No process can later decide a different value v' ≠ v
- The decision must persist across failures and restarts
- All future observations must be consistent with this decision

**Threat**: Network partitions can create scenarios where different subsets of processes make conflicting decisions, violating conservation.

**Evidence Required**: Quorum certificates that prove a majority witnessed the decision, ensuring no conflicting decision could have been made.

#### 1.1.2 State Conservation (ACID Properties)
The total "quantity" of state in the system remains constant:
- Account balances: If A transfers $100 to B, A decreases by exactly $100 and B increases by exactly $100
- Inventory: If an item is reserved, it's removed from available inventory
- Ownership: If ownership transfers, exactly one entity loses it and one gains it

**Threat**: Concurrent updates from different replicas can create or destroy state (e.g., double-spending in distributed ledgers).

**Evidence Required**: Serialization proofs (commit certificates, linearizability evidence) showing the total order of state modifications.

#### 1.1.3 Message Conservation (Exactly-Once Semantics)
Each message produces exactly one effect:
- Not zero effects (message must eventually be processed)
- Not multiple effects (idempotency required or explicit deduplication)
- The effect is attributed to the correct sender

**Threat**: Network duplicates, retries, and partial failures can cause messages to be processed multiple times or attributed incorrectly.

**Evidence Required**: Idempotency tokens, sequence numbers, or deduplication tables that track message processing.

### 1.2 Why Impossibility Results Protect Conservation

Impossibility results are fundamentally about showing that certain guarantees would violate conservation when information is incomplete.

#### 1.2.1 FLP and Decision Conservation

The FLP impossibility result proves that in an asynchronous system with even one crash failure, there is no deterministic protocol that guarantees both:
- **Agreement** (conservation of decision): All non-faulty processes decide the same value
- **Termination** (liveness): All non-faulty processes eventually decide

The proof constructs an execution where the system remains forever in a "bivalent" state—where both outcomes (decide 0 or decide 1) are still possible. This is precisely a state where decision conservation cannot yet be enforced because insufficient evidence exists about which processes are alive and which have failed.

**The Conservation Insight**: To preserve decision conservation, you need evidence that a majority agrees. But in an asynchronous system, you cannot distinguish "process crashed" from "process slow," so you cannot gather sufficient evidence without potentially waiting forever.

**Evidence Gap**:
- **Missing Evidence**: Definitive failure detection
- **Cannot Know**: Which processes are alive vs. slow
- **Conservation at Risk**: Making a decision without sufficient evidence risks split-brain (violating agreement)
- **Impossibility Statement**: "No protocol can generate sufficient evidence for decision conservation while guaranteeing termination in all executions"

#### 1.2.2 CAP and State Conservation

The CAP theorem proves that during a network partition, you cannot simultaneously guarantee:
- **Consistency** (state conservation across replicas): All nodes see the same state
- **Availability** (liveness): Every request receives a response
- **Partition Tolerance** (reality): The system continues operating despite network splits

**The Conservation Insight**: During a partition, you have two isolated subsets of nodes. If you allow both sides to accept writes (availability), you risk creating divergent state that violates conservation (e.g., double-spending). If you reject writes on one side (consistency), you sacrifice availability.

**Evidence Gap**:
- **Missing Evidence**: Quorum reachability proof
- **Cannot Know**: Whether the other side of the partition is processing requests
- **Conservation at Risk**: Accepting writes without quorum evidence risks state divergence
- **Impossibility Statement**: "No protocol can generate sufficient evidence for state conservation across partitions while remaining available on both sides"

The choice is:
1. **CP Systems** (e.g., Spanner, etcd): Preserve conservation by becoming unavailable when evidence is missing
2. **AP Systems** (e.g., Cassandra, DynamoDB): Accept temporary conservation violations, relying on eventual reconciliation

#### 1.2.3 PACELC and Conservation Economics

PACELC extends CAP by recognizing that even without partitions, conservation has costs:
- **During Partition**: Choose Consistency or Availability (same as CAP)
- **Else (normal operation)**: Choose Latency or Consistency

**The Conservation Insight**: Generating evidence for state conservation requires coordination. Coordination requires communication. Communication takes time. Therefore, strong conservation guarantees increase latency even in the failure-free case.

**Evidence Costs**:
- **Fresh Evidence**: Requires synchronous replication (2PC, Raft log commitment)
  - Latency: 2-10ms local, 50-200ms cross-region
  - Throughput: Limited by slowest replica in quorum
- **Bounded Staleness**: Allows lagging replicas with maximum age δ
  - Latency: Read from local replica if within bound
  - Evidence: Closed timestamp or lease expiry
- **Eventual Consistency**: Accepts temporary divergence
  - Latency: Local read/write
  - Evidence: Version vectors for reconciliation later

### 1.3 Conservation Across Scopes

Conservation applies at different granularities, with different costs:

| Scope | Conservation Property | Evidence Type | Cost |
|-------|----------------------|---------------|------|
| **Single Object** | Per-key linearizability | Version number, CAS token | O(1) per operation |
| **Range** | Range consistency (e.g., secondary index) | Range lock, timestamp range | O(log n) for range size |
| **Transaction** | ACID across multiple objects | Commit certificate, 2PC decision | O(participants) messages |
| **Global** | Serializability across all transactions | Global timestamp oracle, distributed log | O(n) for n participants |
| **Multi-Region** | Global consistency across datacenters | Consensus across regions | O(regions × RTT) latency |

**Design Principle**: Enforce conservation at the narrowest scope necessary. Every scope increase multiplies evidence generation costs.

---

## Part 2: SUPPORTING INVARIANTS FROM THE CATALOG

### 2.1 UNIQUENESS - "At Most One of X"

**Definition**: In the system, there exists at most one instance of X at any given time.

Uniqueness is crucial for:
- **Leader Election**: At most one leader per term/epoch
- **Resource Allocation**: At most one process holds a lock
- **Primary Replica**: At most one replica accepts writes
- **Transaction Coordinator**: At most one coordinator for a transaction ID

#### 2.1.1 Uniqueness in Consensus (Mapping to FLP)

Consensus requires uniqueness of decision. The FLP impossibility shows that ensuring unique decision in asynchronous systems is impossible with guaranteed termination.

**Threat Model**:
- **Simultaneous Leaders**: Two processes both believe they're the leader
- **Split Brain**: Network partition causes each side to elect a leader
- **Epoch Confusion**: New leader elected while old leader still operating

**Protection Mechanism**: Leader leases with epochs
- **Evidence Generated**: `{lease_epoch: N, holder: P, expiry: T, witnesses: [Q1, Q2, Q3]}`
- **Scope**: Per shard/range
- **Lifetime**: Configurable (typically 3-10 seconds)
- **Binding**: Specific process ID + epoch number
- **Revocation**: Explicit epoch increment or lease expiry

**Why This Works** (Circumventing FLP):
- Introduces partial synchrony assumption: leases expire in bounded time
- Old leader's actions become invalid after expiry (evidence lifetime)
- New leader waits for old lease to expire before starting
- Evidence provides the missing information FLP says we can't have deterministically

**Production Example - Raft Leader Election**:
```
Initial State: No leader, epoch 0
Step 1: Candidate A requests votes for epoch 1
Step 2: Majority (A, B, C) grant votes → A has evidence of uniqueness
Step 3: A announces leadership with evidence: {epoch: 1, voted_by: [A,B,C]}
Step 4: B and C see this evidence, recognize A as unique leader
Step 5: If network partition splits A from others:
  - A's lease expires (no heartbeat responses)
  - A steps down (no longer has valid evidence)
  - Others can elect new leader in epoch 2 after election timeout
```

**Evidence Lifecycle**:
```
Generated: Majority votes collected → quorum certificate created
Validated: Each recipient verifies majority signature
Active: Leader uses evidence to authorize writes (term/epoch checked)
Expiring: Heartbeat deadline approaching, renewal attempted
Expired: Heartbeat missed → followers reject further commands
Renewed: New heartbeat extends lease, same epoch
Revoked: Network partition → timeout triggers new election in higher epoch
```

#### 2.1.2 Uniqueness in CAP - Primary Replica Selection

In CP systems (like Spanner), uniqueness of the write-accepting replica ensures consistency:

**Evidence**: Paxos group leadership + TrueTime bounds
```
{
  group_id: "shard-47",
  leader: "replica-3",
  epoch: 142,
  lease_expiry: TrueTime.now() + 10s,
  quorum_witnesses: ["replica-1", "replica-2", "replica-3"]
}
```

**Conservation Guarantee**: By ensuring at most one replica accepts writes, state conservation is preserved—no conflicting concurrent updates.

**CAP Trade-off Manifestation**:
- During partition: Minority side cannot establish uniqueness (no quorum)
- Minority becomes unavailable (chooses C over A)
- Majority side maintains unique primary, continues serving requests
- After partition heals: No conflicting state because minority was inactive

### 2.2 ORDER - "A Precedes B"

**Definition**: Events have a definable ordering relationship that all observers agree upon.

Order is essential for:
- **Causality**: If A causes B, all observers must see A before B
- **Consistency Models**: Linearizability requires real-time order
- **Replicated Logs**: All replicas must apply operations in the same order
- **Transactions**: Read must see writes in commit order

#### 2.2.1 Order in FLP - Why Agreement Requires Order

The FLP proof fundamentally relies on the ordering of process steps and message deliveries. The impossibility arises because:

1. **Asynchrony Breaks Observable Order**: Without timing bounds, messages can be arbitrarily reordered
2. **Order Evidence Requires Communication**: To agree on order, processes must exchange messages
3. **Communication Can Stall**: In asynchronous systems, messages can be delayed indefinitely
4. **Circular Dependency**: Need order to make decision, need decision to establish order

**The Bivalent State Construction**:
```
Configuration C is bivalent if:
  - Some execution from C leads to decision 0
  - Some execution from C leads to decision 1
  - The deciding factor is message delivery order

The FLP proof shows you can always construct an execution where:
  - Adversary controls message delivery order
  - System remains bivalent forever
  - Different orders lead to different decisions
  - No process can distinguish this from normal operation
```

**Evidence Gap**: In an asynchronous system, you cannot generate evidence about "true" ordering without timing assumptions.

#### 2.2.2 Order in CAP - Linearizability Definition

Linearizability, the "C" in CAP's formalization, is fundamentally about preserving real-time order:

**Formal Definition**:
For operations op1 and op2, if op1 completes before op2 begins (in real time), then in the linearization order, op1 must appear before op2.

**Evidence Required**: Timestamps or sequence numbers that respect real-time order
- **Total Order Broadcast**: All replicas apply operations in same order
- **Commit Index**: Position in replicated log
- **Real-Time Bounds**: TrueTime in Spanner provides uncertainty intervals

**Why Partition Breaks This**:
```
Client A                 Partition             Client B
   |                         ||                    |
write(x=1) → [Leader A]     ||                    |
   ← success                 ||                    |
                             ||    [Leader B] ← write(x=2)
                             ||                    ← success
```

Without partition tolerance, you might have:
- Both sides accepting writes
- Different orders on each side: [x=1] vs [x=2]
- After healing: which order is "correct"?
- Conservation violated: linearizability broken

**CP Solution**: Reject one side (unavailability)
**AP Solution**: Accept both, reconcile later (breaks linearizability during partition)

#### 2.2.3 Order and PACELC - Coordination Cost

Maintaining strong order (linearizability, serializability) requires coordination:

**Cost Model**:
```
Operation Latency = Local Processing + Coordination Cost

For Linearizable Write:
  Coordination = 2 × (Network RTT to Quorum)
  Local DC: 2 × 1ms = 2ms overhead
  Cross-region: 2 × 100ms = 200ms overhead

For Serializable Transaction:
  Coordination = 2PC latency + Conflict detection
  Multi-region: 200-500ms typical
```

**Evidence Binding to Order**:

Different order guarantees require different evidence:

| Order Guarantee | Evidence Type | Generation Cost | Verification Cost |
|----------------|---------------|-----------------|-------------------|
| **No Order** | None | O(1) local | O(1) |
| **Per-Object Order** | Per-key version | O(1) local | O(1) version check |
| **Causal Order** | Vector clock | O(n) for n processes | O(n) comparison |
| **Linearizability** | Commit certificate | O(quorum) messages | O(1) cert check |
| **Serializability** | Transaction ordering | O(conflicts × quorum) | O(serialization graph) |

**PACELC Design Choices**:
- **PC/EC** (Spanner): Always pay coordination cost for strong order
- **PA/EL** (Cassandra): Accept weak order, use LWW or version vectors
- **PC/EL** (MongoDB): Strong order during partition, best-effort normally

### 2.3 AUTHENTICITY - "Only Valid Participants"

**Definition**: Only authorized processes can perform actions, and their actions cannot be forged or corrupted.

Authenticity protects:
- **Byzantine Fault Tolerance**: Distinguishing correct from malicious processes
- **Access Control**: Only authorized users can modify data
- **Message Integrity**: Messages haven't been tampered with in transit
- **Identity**: Processes are who they claim to be

#### 2.3.1 Authenticity in Byzantine Consensus

FLP assumes crash failures—processes stop or continue correctly. Byzantine failures are more severe: processes can behave arbitrarily, lie, forge messages.

**Threat Model Extensions**:
- **Malicious Processes**: Send conflicting messages to different recipients
- **Message Forgery**: Impersonate another process
- **State Corruption**: Report false state to cause incorrect decisions
- **Replay Attacks**: Re-send old messages to cause confusion

**Evidence Required - Digital Signatures**:
```
Message := {
  content: "vote for proposal P in epoch E",
  sender: process_id,
  signature: Sign(content, private_key[sender]),
  timestamp: T,
  nonce: random_value
}

Recipient verification:
1. Verify(signature, public_key[sender], content) = VALID
2. Check timestamp within acceptable window
3. Check nonce not seen before (replay protection)
4. Check sender authorized for this message type
```

**Byzantine Agreement Impossibility** (with authenticity):
- With digital signatures: Requires n ≥ 3f + 1 processes to tolerate f Byzantine faults
- Without signatures: Requires n ≥ 5f + 1 (much worse)
- Why: Need 2f + 1 honest processes to form majority, plus f to tolerate being offline

**Conservation Through Authenticity**:
- Decision conservation: Can't be violated by forged votes
- State conservation: Can't be violated by unauthorized writes
- Message conservation: Signatures prevent double-spends via replay

#### 2.3.2 Authenticity in CAP - Identity During Partition

During network partition, authenticity becomes critical:

**The Split-Brain Problem**:
```
Before Partition:
  Nodes: [A, B, C, D, E]
  Leader: A (epoch 5)

After Partition:
  Group 1: [A, B] (minority)
  Group 2: [C, D, E] (majority)

Without Authenticity:
  - A continues claiming to be leader
  - C, D, E elect new leader C (epoch 6)
  - Client could be confused about who is leader

With Epoch-Based Authenticity:
  - Every message includes epoch number and leader signature
  - B sees C's epoch 6 > A's epoch 5, recognizes A is outdated
  - Clients reject A's messages (old epoch)
  - Conservation preserved: only epoch 6 leader (C) is valid
```

**Evidence Binding**:
```
Leadership Evidence := {
  leader_id: process_id,
  epoch: monotonic_counter,
  lease_start: timestamp,
  lease_expiry: timestamp,
  election_certificate: {
    voters: [list of process_ids],
    signatures: [list of signatures],
    vote_payload: "I vote for {leader_id} in epoch {epoch}"
  }
}

Validation:
1. Verify all signatures in election_certificate
2. Check voters form a valid quorum
3. Check epoch > last_known_epoch
4. Check current_time within [lease_start, lease_expiry]
```

**CAP with Authenticity**:
- **CP Systems**: Use epoch-based evidence to ensure old primaries cannot accept writes
- **AP Systems**: Use version vectors with process IDs to track causality during partition
- **Reconciliation**: After partition heals, use timestamps and process IDs to resolve conflicts

#### 2.3.3 Authenticity Under PACELC - Trust vs. Performance

Strong authenticity (cryptographic verification) has performance costs:

**Cost Analysis**:
```
Operation Type             | No Auth | Symmetric Auth | Asymmetric Auth
---------------------------|---------|----------------|----------------
Message signing            | 0µs     | 2-5µs (HMAC)   | 50-200µs (RSA)
Signature verification     | 0µs     | 2-5µs          | 50-200µs
Threshold signature (BFT)  | N/A     | N/A            | 5-20ms (n processes)
Per-request overhead       | +0ms    | +0.01ms        | +0.2ms
```

**PACELC Trade-offs**:
- **High Trust Environment** (single organization, trusted network):
  - E → L: Choose latency, minimal authenticity
  - Use process IDs and internal certificates
  - Example: Internal Google services, HMAC-based auth

- **Low Trust Environment** (multi-org, public networks):
  - E → C: Choose consistency with strong authenticity
  - Use digital signatures, threshold cryptography
  - Example: Blockchain, inter-bank settlement

- **Hybrid** (trusted core, untrusted edge):
  - Core: Fast with symmetric auth
  - Edge: Slow with asymmetric auth
  - Evidence rebinding at trust boundary

---

## Part 3: THE INVARIANT HIERARCHY

The invariants we've discussed form a hierarchy, where higher-level invariants are built from lower-level ones. Understanding this hierarchy is crucial for designing systems that degrade gracefully—when evidence for high-level invariants is unavailable, the system can fall back to preserving lower-level ones.

### 3.1 Fundamental Level - What Cannot Be Violated

These are the sacred invariants that must never be violated, even under catastrophic failures:

#### 3.1.1 Conservation (The Foundation)
- **Definition**: Nothing created or destroyed except via authorized flows
- **Examples**:
  - Bank account balance changes sum to zero across transfers
  - Inventory: items reserved + items available = total inventory
  - Distributed counters: increments match final value
- **Protection**: Multi-version concurrency control (MVCC), transaction logs, state machine replication
- **Evidence**: Commit certificates, audit logs, Merkle proofs of state transitions
- **Failure Mode**: If violated, requires manual intervention and reconciliation (data loss/corruption)

#### 3.1.2 Uniqueness (The Serialization Point)
- **Definition**: At most one holder of exclusive resource at any time
- **Examples**:
  - Leader in consensus protocol
  - Lock holder for critical section
  - Primary replica for writes
- **Protection**: Epoch-based leases, quorum intersection, mutual exclusion algorithms
- **Evidence**: Lease certificates, lock tokens, epoch numbers
- **Failure Mode**: If violated → split brain, data corruption, lost updates
- **Recovery**: Fencing tokens force old holders to step down

#### 3.1.3 Authenticity/Integrity (The Trust Foundation)
- **Definition**: Only authorized entities perform actions; data hasn't been tampered
- **Examples**:
  - Authenticated RPC calls
  - Signed transactions in blockchain
  - Verified software updates
- **Protection**: Digital signatures, MACs, access control lists, capability systems
- **Evidence**: Signatures, certificates, authentication tokens
- **Failure Mode**: If violated → unauthorized access, data corruption, security breach
- **Recovery**: Revoke compromised credentials, restore from verified backup

### 3.2 Derived Level - What Emerges From Fundamentals

These invariants are built on the fundamental ones and can be temporarily relaxed if necessary:

#### 3.2.1 Order (Derived from Uniqueness + Conservation)
**Construction**:
- Uniqueness provides a serialization point (e.g., single writer, leader, lock holder)
- Conservation requires that state changes are not lost
- Order emerges: changes are applied through the unique serialization point in sequence

**Hierarchy**:
```
No Order
   ↓
Per-Object Order (CAS, version numbers)
   ↓
Causal Order (vector clocks, causality tracking)
   ↓
Linearizability (real-time order, single logical timeline)
   ↓
Serializability (transaction order, equivalent to serial execution)
```

**Degradation Path**:
- Target: Serializability (strongest)
- Degraded: Snapshot Isolation (per-transaction order)
- Floor: Causal Consistency (causality preserved)
- Emergency: Eventual Consistency (order not guaranteed)

**Evidence Requirements**:
| Order Level | Evidence | Cost | Lifetime |
|------------|----------|------|----------|
| None | Version tags | O(1) | Per-update |
| Causal | Vector clocks | O(n processes) | Per-causality chain |
| Linearizable | Commit cert | O(quorum msgs) | Per-operation |
| Serializable | Global order + conflict graph | O(conflicts × participants) | Per-transaction |

#### 3.2.2 Exclusivity (Temporary Uniqueness)
**Construction**:
- Uniqueness with explicit lifetime bounds
- Renewable evidence with expiry

**Examples**:
- **Leases**: Temporary exclusive access that expires
  - Evidence: `{holder: P, epoch: E, expiry: T, grantor_quorum: Q}`
  - Lifetime: Fixed (3-10 seconds typical)
  - Renewal: Holder must refresh before expiry
  - Failure: On expiry, resource becomes available to others

- **Optimistic Locks**: Read version, write if unchanged
  - Evidence: `{object_id: O, version: V, timestamp: T}`
  - Lifetime: Until next write attempt
  - Validation: Check current version = V
  - Failure: Retry if version changed

- **Distributed Locks** (Chubby, etcd):
  - Evidence: `{lock_path: "/resource/X", session_id: S, sequence: N}`
  - Lifetime: Tied to session heartbeat
  - Renewal: Automatic while session alive
  - Failure: Session timeout → lock auto-released

**Degradation**: Exclusivity → Shared Access with Coordination → Uncoordinated Access

#### 3.2.3 Monotonicity (Order Constraint)
**Construction**:
- Order where values only increase (or only decrease)
- Derived from conservation of "progress"

**Examples**:
- **Logical Clocks** (Lamport, HLC):
  - Evidence: Timestamp that never decreases
  - Ensures causal order

- **Closed Timestamps** (CockroachDB):
  - Evidence: "All writes < T have been applied"
  - Monotonically advancing
  - Enables consistent reads at T

- **Epochs/Terms** (Raft, Paxos):
  - Evidence: Monotonic term/epoch numbers
  - Old leaders cannot override new ones

- **Watermarks** (streaming systems):
  - Evidence: "All data before T has been processed"
  - Enables windowing and garbage collection

**Protection Mechanism**:
```
Update Rule:
  new_value = max(old_value, proposed_value)

Validation:
  if proposed_value ≤ current_value:
    reject OR accept as no-op (idempotent)
  else:
    current_value := proposed_value
```

**Why Important**: Monotonicity provides **irreversibility**—once a value is reached, the system cannot go backward. This is crucial for:
- Garbage collection (safe to delete data before watermark)
- Consistent snapshots (read at closed timestamp)
- Epoch-based recovery (old leaders cannot resurface)

### 3.3 Composite Level - What Users Experience

These are the high-level guarantees that applications depend on, built from combinations of derived invariants:

#### 3.3.1 Freshness (Order + Recency Bound)
**Construction**: Order + Time Bound on Evidence Age

**Definition**: Data returned is no older than δ from the true current value.

**Evidence Formula**:
```
Freshness Guarantee := {
  order: linearizable | snapshot | causal,
  recency_bound: δ,
  proof: φ
}

where:
  φ ∈ {
    read_index + lease,        // follower reads in Raft
    closed_timestamp,          // CockroachDB
    TrueTime_interval,         // Spanner
    bounded_staleness_promise  // Azure Cosmos DB
  }
```

**Degradation Hierarchy**:
1. **Fresh(φ)**: Verifiable proof of freshness
   - Latency: High (coordination required)
   - Evidence: Explicit proof from leader/quorum

2. **BoundedStaleness(δ)**: Guaranteed maximum age
   - Latency: Medium (local read if within bound)
   - Evidence: Lease expiry or closed timestamp

3. **BestEffort**: No guarantee, but usually recent
   - Latency: Low (immediate local read)
   - Evidence: None (assume probably recent)

4. **Eventual**: Will converge eventually, no bound
   - Latency: Lowest (always local)
   - Evidence: Version vectors for reconciliation

**Example - Follower Reads in Raft**:
```
Client requests read from Follower F:

Target Mode (Fresh):
1. F sends ReadIndex request to Leader L
2. L confirms it's still leader (heartbeat to quorum)
3. L returns current commit_index = N
4. F waits until local_commit_index ≥ N
5. F serves read with evidence: {commit_index: N, confirmed_at: T}
6. Latency: 1 RTT to leader + waiting for log replication

Degraded Mode (BoundedStaleness):
1. F has lease from L: valid until T_expiry
2. Current time T_now < T_expiry
3. F serves read immediately
4. Evidence: {lease_expiry: T_expiry, staleness_bound: T_expiry - T_now}
5. Latency: 0 (local)

Floor Mode (Eventual):
1. F serves whatever it has locally
2. Evidence: None (or just local commit_index)
3. Latency: 0 (local)
4. Risk: Stale if F is partitioned
```

#### 3.3.2 Visibility/Coherent Cut (Order + Atomicity)
**Construction**: Order + Atomic View Across Multiple Objects

**Definition**: A read observes a consistent snapshot—if A and B are related by causality or transaction, a read sees either both or neither.

**Threat**: Partially visible state (read sees A's update but not B's correlated update).

**Examples**:
- **Read-Your-Writes**: After writing X, subsequent reads see X
- **Monotonic Reads**: After reading version V, subsequent reads see ≥ V
- **Snapshot Isolation**: Transaction reads consistent snapshot at start time
- **Serializable Snapshot Isolation**: Snapshot + write conflict detection

**Evidence Types**:
| Visibility Level | Evidence | Example |
|-----------------|----------|---------|
| Per-Object | Version number | DynamoDB eventual consistency |
| Session | Session token | MongoDB causal consistency |
| Snapshot | Snapshot timestamp | PostgreSQL MVCC |
| Serializable | Commit timestamp + conflict detection | CockroachDB SSI |

**Mode Matrix**:
```
Target: Serializable Snapshot Isolation
  - Evidence: Transaction start timestamp T_start
  - Read: Snapshot at T_start
  - Write: Detect conflicts with [T_start, T_commit)
  - Protection: Abort on conflict

Degraded: Snapshot Isolation
  - Evidence: Snapshot timestamp T_snap
  - Read: Snapshot at T_snap
  - Write: No conflict detection
  - Risk: Write skew anomalies possible

Floor: Read Committed
  - Evidence: Per-statement timestamp
  - Read: Latest committed version
  - Write: Immediate visibility
  - Risk: Unrepeatable reads
```

#### 3.3.3 Convergence (Order + Commutativity)
**Construction**: Weak Order + Merge Function

**Definition**: Replicas that receive the same set of updates (in any order) converge to the same state.

**CRDTs** (Conflict-Free Replicated Data Types):
- **State-based**: Merge function is associative, commutative, idempotent
- **Operation-based**: Operations are commutative

**Evidence**:
```
CRDT_State := {
  value: current_state,
  version_vector: {P1: N1, P2: N2, ...},
  merge_history: [operations_applied]
}

Convergence Proof:
  For replicas R1, R2:
    If delivered(R1) = delivered(R2) (same set of ops)
    Then state(R1) = state(R2)

  Evidence: Version vectors prove delivery
```

**Examples**:
- **G-Counter** (grow-only counter):
  - State: Map from process_id → local_count
  - Merge: element-wise max
  - Query: sum of all local counts

- **OR-Set** (observed-remove set):
  - State: {(element, unique_tag)} pairs
  - Add: include (e, new_tag)
  - Remove: delete all (e, *) where tag observed
  - Merge: union of all (e, tag) pairs

- **LWW-Register** (last-write-wins):
  - State: (value, timestamp)
  - Merge: keep entry with max timestamp
  - Evidence: Timestamp provides total order

**Degradation Path**:
```
Target: CRDT with version vectors
  - Evidence: Full version vector per update
  - Guarantee: Convergence with causality
  - Cost: O(n processes) per update

Degraded: LWW with timestamps
  - Evidence: Timestamp per update
  - Guarantee: Convergence (arbitrary order)
  - Cost: O(1) per update
  - Risk: Lost updates if timestamps tie

Floor: Last-seen wins
  - Evidence: None (local view)
  - Guarantee: Eventually consistent
  - Risk: Undefined resolution
```

#### 3.3.4 Idempotence (Order + Deduplication)
**Construction**: Order + Message Identity

**Definition**: Applying the same operation multiple times produces the same result as applying it once.

**Why Critical**: Network retries, at-least-once delivery, and failure recovery all cause duplicate messages.

**Evidence Types**:

1. **Natural Idempotence** (no evidence needed):
   - Set x = v (overwrite)
   - max(x, v)
   - Add to set

2. **Application-Level Tokens**:
   ```
   Request := {
     idempotency_key: "uuid-12345",
     operation: "transfer $100 from A to B",
     timestamp: T
   }

   Server maintains:
     dedup_table[idempotency_key] = {
       status: completed | in_progress,
       result: operation_result,
       expiry: T + retention_period
     }
   ```

3. **Sequence Numbers** (per-session):
   ```
   Session := {
     session_id: "session-67890",
     next_sequence: N
   }

   Request := {
     session_id: "session-67890",
     sequence: N
   }

   Server tracks: last_processed[session_id] = M
   Accept only if sequence = M + 1
   ```

**Mode Matrix**:
```
Target: Exactly-Once with Tokens
  - Evidence: Idempotency key + dedup table
  - Guarantee: Operation applied once
  - Lifetime: Token valid until expiry (hours/days)
  - Cost: O(1) dedup lookup per request

Degraded: At-Least-Once with Natural Idempotence
  - Evidence: None (operation itself is idempotent)
  - Guarantee: Safe to retry
  - Limitation: Only works for naturally idempotent ops

Floor: At-Most-Once with Timeouts
  - Evidence: Timeout on failure
  - Guarantee: Won't retry (may lose operation)
  - Risk: Data loss if original failed
```

#### 3.3.5 Bounded Staleness (Time + Evidence Lifetime)
**Construction**: Evidence Age Bound

**Definition**: Data is at most δ time units behind the true current state.

**Evidence**:
```
BoundedStaleness_Certificate := {
  snapshot_time: T_snapshot,
  evidence_generated_at: T_evidence,
  staleness_bound: δ,
  proof: {
    type: lease | closed_timestamp | version_with_timestamp,
    valid_until: T_expiry
  }
}

Guarantee:
  If read at T_read, and T_read - T_snapshot ≤ δ:
    Data is at most δ stale
  else:
    Evidence expired, must refresh or degrade
```

**Implementation Patterns**:

1. **Time-Based Leases** (DynamoDB):
   - Leader holds lease for L seconds
   - Replicas safe to read if within L of last heartbeat
   - Evidence: `{last_heartbeat: T, lease_duration: L, current_time: T'}`
   - Staleness bound: `δ = T' - T` (must be < L)

2. **Closed Timestamps** (CockroachDB):
   - Leader announces: "All transactions < T are committed"
   - Replicas safe to read at T
   - Evidence: `{closed_timestamp: T, announced_at: T_a}`
   - Staleness bound: `δ = now() - T`

3. **Hybrid Logical Clocks** (HLC):
   - Combines physical time + logical counter
   - Provides causality + approximate real-time
   - Evidence: `{hlc: (pt, l), clock_skew_bound: ε}`
   - Staleness bound: `δ = ε` (clock synchronization error)

**Azure Cosmos DB Example**:
```
Consistency Levels with Bounded Staleness:

Strong:
  - δ = 0 (no staleness)
  - Evidence: Synchronous replication
  - Latency: High (wait for quorum)

Bounded Staleness (configurable):
  - δ = K versions OR T seconds (whichever first)
  - Evidence: Version counter or timestamp
  - Latency: Medium (can read from nearby replica)
  - Example: "At most 100 versions behind" or "At most 5 seconds behind"

Eventual:
  - δ = unbounded
  - Evidence: None
  - Latency: Low (local read always)
```

---

## Part 4: THREAT MODELS FOR EACH INVARIANT

Understanding how each invariant can be violated is crucial for designing protection mechanisms.

### 4.1 Threats to Conservation

#### 4.1.1 Network Partitions
**Attack Vector**: Network splits system into isolated groups

**Scenario**:
```
Initial State:
  Replicas: [A, B, C, D, E]
  Account balance: $1000 (replicated)

Partition:
  Group 1: [A, B] (minority)
  Group 2: [C, D, E] (majority)

Attack:
  Client X → A: withdraw $800 (succeeds on minority)
  Client Y → C: withdraw $800 (succeeds on majority)

Result: $1600 withdrawn from $1000 account
  → Conservation violated (money created)
```

**Defense**:
1. **Quorum Intersection** (CP approach):
   - Require write quorum = ⌊n/2⌋ + 1
   - Group 1 (2 nodes) < quorum → reject write
   - Group 2 (3 nodes) = quorum → accept write
   - Evidence: Quorum certificate from majority

2. **Compensation** (AP approach):
   - Accept both writes with version vectors
   - Detect conflict after partition heals
   - Evidence: `{A: v1, timestamp: T1}` vs `{C: v2, timestamp: T2}`
   - Compensating action: Reverse one transaction, notify affected parties

#### 4.1.2 Asynchrony
**Attack Vector**: Unbounded message delays cause timeout-based decisions

**Scenario**:
```
Leader L has lock on resource R
Lease duration: 10 seconds

Timeline:
T=0:  L acquires lease, sends heartbeats
T=5:  Network slowdown, heartbeats delayed
T=10: Followers timeout, assume L crashed
T=10: Followers elect new leader M
T=11: L's heartbeat finally arrives
T=12: Both L and M believe they hold the lock

Result: Two leaders, conservation of uniqueness violated
```

**Defense - Fencing Tokens**:
```
Epoch-Based Fencing:
1. Every lease has increasing epoch number
2. Resource R tracks: current_epoch = N
3. Leader L has: {epoch: N, resource: R}
4. Leader M elected with: {epoch: N+1, resource: R}

When accessing R:
  L sends: (operation, epoch: N)
  M sends: (operation, epoch: N+1)

R accepts only if: request.epoch ≥ current_epoch
  - L's request (epoch N) rejected if M already wrote (epoch N+1)
  - Conservation preserved: only latest epoch holder can act

Evidence: Epoch number provides total order on lease holders
```

#### 4.1.3 Byzantine Actors
**Attack Vector**: Malicious processes send conflicting information

**Scenario**:
```
Byzantine Process B in 3-node system [A, B, C]:

B → A: "I vote for proposal X"
B → C: "I vote for proposal Y"

If A and C don't communicate:
  A thinks majority voted X: [A, B]
  C thinks majority voted Y: [C, B]

Result: Split decision, conservation violated
```

**Defense - Byzantine Quorum with Signatures**:
```
Requirement: n ≥ 3f + 1 for f Byzantine faults

With n=4, f=1:
  Quorum size = ⌊(n+f)/2⌋ + 1 = 3

Vote Collection:
  Each vote is signed: Sign(vote, private_key[voter])
  Proposer collects ≥3 signed votes
  Quorum certificate = {votes: [...], signatures: [...]}

Verification:
  Every process verifies all 3 signatures
  Byzantine B cannot forge others' signatures
  B's conflicting votes detected by sharing certificates

Evidence: Cryptographic signatures provide authenticity
         Quorum size ensures 2f+1 honest nodes in any quorum
```

#### 4.1.4 Gray Failures
**Attack Vector**: Partial failures where component appears working but behaves incorrectly

**Examples**:
- Disk returning corrupted data (silent corruption)
- Network dropping 1% of packets (not detected by TCP)
- CPU occasionally computing wrong results (bit flips)
- Clock skew beyond acceptable bounds

**Scenario**:
```
Replica R has corrupted storage:
  Reads return slightly wrong values
  Writes appear to succeed but data corrupted

Client reads value X=100
Client writes X=101
Later read returns X=99 (corrupted)

Result: Conservation violated (update lost)
```

**Defense - End-to-End Checksums**:
```
Data Storage:
  stored_value = {
    data: X,
    checksum: Hash(X),
    version: V,
    timestamp: T
  }

On Read:
  1. Read stored_value
  2. Verify Hash(stored_value.data) == stored_value.checksum
  3. If mismatch: Read from another replica OR Repair from quorum

Evidence: Checksum provides integrity proof
         Merkle trees enable efficient verification of large datasets
```

### 4.2 Threats to Uniqueness

#### 4.2.1 Split Brain via Partition
**Scenario**: Network partition with symmetric quorums

```
System: [A, B, C, D, E]
Partition: [A, B, C] | [D, E] + old leader L

If L was leader before partition:
  - L (in minority) still thinks it's leader
  - Majority [A, B, C] elects new leader A
  - Both L and A accept writes

Result: Two leaders (uniqueness violated)
```

**Defense - Epoch-Based Invalidation**:
```
Every leadership comes with epoch number:
  Old leader L: {epoch: N, lease_expiry: T}
  New leader A: {epoch: N+1, lease_granted: T'}

Key insight: T' > T (new election after old lease expired)

Followers track: current_epoch = max(seen_epochs)
  - Reject writes from epoch N after seeing epoch N+1
  - L's writes rejected: "stale epoch"

Evidence: Monotonic epoch numbers provide ordering
         Lease expiry provides time-based invalidation
```

#### 4.2.2 Clock Skew
**Scenario**: Leader lease expires at different times on different nodes due to clock skew

```
Leader L holds lease:
  L's clock: Lease valid until 10:00:10
  Follower F's clock: 10:00:15 (5 seconds ahead)

At L's time 10:00:05:
  - L thinks lease valid (5 seconds left)
  - F thinks lease expired (5 seconds ago)
  - F starts new election
  - F elects new leader M at F's time 10:00:20 (L's time 10:00:15)

Overlap period:
  L's time [10:00:05, 10:00:10]: L thinks it's leader
  F's time [10:00:15, 10:00:20]: F thinks M is leader

Result: Ambiguous leadership (uniqueness threatened)
```

**Defense - Clock Uncertainty Intervals**:
```
TrueTime (Spanner) approach:
  Instead of timestamp T, use interval [T_earliest, T_latest]
  Uncertainty: ε = clock_synchronization_error

Lease Protocol:
  Leader L acquires lease at [T_start - ε, T_start + ε]
  Lease expires at [T_end - ε, T_end + ε]

Conservative wait:
  L waits until T_end + ε (latest possible expiry) before stepping down
  Followers wait until T_end - ε (earliest possible expiry) before electing new

Gap: 2ε between old leader stepping down and new election
  - Ensures no overlap (uniqueness preserved)
  - Cost: 2ε unavailability window

Evidence: Uncertainty interval provides safety margin
         GPS + atomic clocks reduce ε to ~7ms in Spanner
```

### 4.3 Threats to Order

#### 4.3.1 Concurrent Updates
**Scenario**: Two clients update same object concurrently

```
Object X = "v0"
Client A reads X → v0
Client B reads X → v0
Client A writes X = "v1"
Client B writes X = "v2"

Question: What is final value of X?
  - If B overwrites A: Lost update (A's change lost)
  - If A overwrites B: Lost update (B's change lost)
  - If both preserved somehow: Conflict (order ambiguous)
```

**Defense - Versioning with Conflict Detection**:

1. **Optimistic Concurrency Control**:
```
Read:
  return {value: X, version: V}

Write(new_value, expected_version):
  if current_version == expected_version:
    current_version += 1
    store(new_value, current_version)
    return success
  else:
    return conflict (retry required)

Evidence: Version number provides order
```

2. **Multi-Version Concurrency Control (MVCC)**:
```
Store all versions: {(v0, t0), (v1, t1), (v2, t2), ...}

Transaction T starts at time T_start:
  Read: Return latest version where timestamp ≤ T_start
  Write: Create new version at T_commit

Conflict detection:
  T1 writes X at t1
  T2 (started before t1) tries to write X at t2
  → Conflict: T2's read of X is stale
  → Abort T2, retry with fresh snapshot

Evidence: Timestamps provide total order
         Snapshot isolation provides consistent view
```

#### 4.3.2 Message Reordering
**Scenario**: Network reorders messages

```
Process P sends:
  M1: "X = 1" at t=1
  M2: "X = 2" at t=2
  M3: "Y = X" at t=3 (expects Y = 2)

Network delivers: M1, M3, M2
Receiver sees:
  X = 1 (from M1)
  Y = 1 (from M3, reading X=1)
  X = 2 (from M2, arrives late)

Result: Y=1 instead of expected Y=2 (order violated)
```

**Defense - Sequence Numbers**:
```
Each message tagged with sequence number:
  M1: {op: "X=1", seq: 1}
  M2: {op: "X=2", seq: 2}
  M3: {op: "Y=X", seq: 3}

Receiver maintains: expected_seq = N

On receive:
    if msg.seq == expected_seq:
      apply(msg)
      expected_seq += 1
      check_buffer_for_next()
    elif msg.seq > expected_seq:
      buffer(msg)  // hold for later
    else:
      discard(msg)  // duplicate or old

Evidence: Sequence numbers provide total order
         Buffer handles out-of-order delivery
```

#### 4.3.3 Causal Anomalies
**Scenario**: Effect observed before cause

```
Alice posts: "Check out this photo!" (message M1)
Alice uploads photo P (message M2)

Due to different network paths:
  Bob receives M2 (sees photo) before M1
  Bob sees photo before the message announcing it

Result: Confusing user experience (causality violated)
```

**Defense - Vector Clocks**:
```
Each process P maintains vector: VC[P] = {P1: n1, P2: n2, ...}

Alice's actions:
  M1: "Check out this photo!"
      VC_M1 = {Alice: 1, Bob: 0}
  M2: Photo upload (caused by M1)
      VC_M2 = {Alice: 2, Bob: 0}

Bob receives M2 first:
  Bob's current VC = {Alice: 0, Bob: 5}
  Check: VC_M2[Alice]=2 > Bob's_VC[Alice]=0
  → Bob hasn't seen Alice's message 1 yet
  → Buffer M2 until M1 arrives

After receiving M1:
  Bob's VC = {Alice: 1, Bob: 5}
  → Now can deliver M2

Evidence: Vector clocks capture causal dependencies
         Happens-before relationship: M1 → M2
```

### 4.4 Threats to Authenticity

#### 4.4.1 Sybil Attacks
**Scenario**: Attacker creates many fake identities to gain control

```
Byzantine consensus requires n ≥ 3f + 1
  f = number of Byzantine faults tolerated

Attacker strategy:
  Join system with many fake identities
  If attacker controls > f identities, can break consensus

Example: 10 nodes, can tolerate f=3 Byzantine
  Attacker creates 4 fake nodes
  Attacker now controls 4/10 = 40% (> f)
  Can prevent consensus or force wrong decisions
```

**Defense - Identity Verification**:

1. **Proof of Work** (Bitcoin):
```
Identity = computational power
Each vote costs mining work
Attacker must have > 50% hash rate to attack

Evidence: Block header with sufficient hash difficulty
         Chain with most accumulated work wins
```

2. **Proof of Stake** (Ethereum):
```
Identity = staked capital
Each vote weighted by stake amount
Attacker must own > 50% of total stake

Evidence: Signed messages with stake amount
         Economic disincentive: attacking devalues own stake
```

3. **Permissioned Systems** (Hyperledger):
```
Identity = certificate from CA (Certificate Authority)
Only known, verified entities can join
Limit: n known participants, f Byzantine tolerated

Evidence: X.509 certificates
         CA vouches for identity
```

#### 4.4.2 Message Forgery
**Scenario**: Attacker impersonates another process

```
Process A (honest)
Process B (Byzantine)
Process C (honest)

B sends to C:
  Forged message: "I am A, vote for proposal X"

If C cannot verify it's really from A:
  C might attribute vote to A
  Attacker B controls A's vote
```

**Defense - Digital Signatures**:
```
Setup: Each process has (public_key, private_key) pair

Process A sends message:
  msg = {content: "vote for X", sender: A}
  signature = Sign(msg, private_key[A])
  send: (msg, signature)

Process C receives:
  Verify(signature, public_key[A], msg)
  If valid: Accept message as from A
  If invalid: Reject (forged or corrupted)

Evidence: Signature proves authenticity
         Only holder of private_key[A] could produce valid signature
         Public key cryptography provides non-repudiation
```

#### 4.4.3 Replay Attacks
**Scenario**: Attacker resends old valid messages

```
Time T1: Alice sends Bob $100
  Message: {from: Alice, to: Bob, amount: 100, signature: S}

Time T2: Attacker intercepts and stores message
Time T3: Attacker replays message
  Bob receives same message again
  Signature is valid (original signature from Alice)
  If not protected: Bob receives $100 again (double-credit)
```

**Defense - Nonces and Timestamps**:
```
Message structure:
  {
    from: Alice,
    to: Bob,
    amount: 100,
    nonce: "unique-id-12345",  // Or sequence number
    timestamp: T1,
    signature: Sign(all_above, private_key[Alice])
  }

Receiver Bob maintains:
  seen_nonces: Set of processed nonces
  time_window: Accept only if |now - timestamp| < δ

On receive:
  1. Verify signature
  2. Check nonce ∉ seen_nonces
  3. Check timestamp within window
  4. If all valid: Process message, add nonce to seen_nonces
  5. Else: Reject as replay

Evidence: Nonce provides uniqueness
         Timestamp provides freshness
         Combined: Message is authentic AND recent
```

---

## Part 5: PROTECTION BOUNDARIES

Where you enforce invariants dramatically affects system design, performance, and failure modes.

### 5.1 Scope Levels and Their Costs

| Boundary | Invariants Protected | Evidence Required | Cost | Example |
|----------|---------------------|-------------------|------|---------|
| **Single Key** | Per-object consistency | Version number | O(1) local | DynamoDB per-item |
| **Range/Shard** | Range consistency | Range lock/lease | O(log range_size) | CockroachDB range lease |
| **Service** | Service-level invariants | Service-wide consensus | O(replicas) | Single Raft group |
| **Region** | Regional consistency | Cross-AZ consensus | O(AZs × RTT) | Multi-AZ Spanner |
| **Global** | Global consistency | Cross-region consensus | O(regions × WAN_RTT) | Global Spanner |
| **Federation** | Cross-org invariants | Blockchain consensus | O(orgs × verification) | Multi-party computation |

### 5.2 Design Principle: Narrow Scope by Default

**Insight**: Every boundary crossing weakens guarantees or increases cost. Design to minimize scope.

#### 5.2.1 Single-Key Atomicity (Narrowest Scope)

**Example**: Atomic increment counter

```
Invariant: Counter value is accurate (conservation)
Scope: Single key
Protection: Atomic read-modify-write

Implementation (Redis):
  INCR counter → Atomic operation, single server
  Cost: O(1), ~1µs
  Evidence: None required (single-threaded execution provides atomicity)

Failure Mode: If server crashes, counter lost
  Recovery: Restore from AOF log or RDB snapshot
```

**Why It Works**: Single-threaded event loop provides natural mutual exclusion. No distributed coordination needed.

#### 5.2.2 Range Consistency (Shard-Level Scope)

**Example**: Secondary index maintenance

```
Invariant: Index entry exists IFF corresponding row exists
Scope: All rows in shard + index entries for those rows
Protection: Shard-level transaction

Implementation (CockroachDB):
  Range: [key_start, key_end)
  Lease holder: Replica 1
  Transaction:
    1. Write to row in range
    2. Update index entry
    3. Both protected by same range lease

Evidence: {range: [start, end), lease_holder: R1, epoch: E}
Cost: O(1) if both row and index in same range
      O(ranges) if spans multiple ranges (distributed transaction)
```

**Trade-off**: Larger ranges → fewer leases (cheaper) but more cross-range transactions (expensive).

#### 5.2.3 Service-Level Invariants

**Example**: Leader election in Raft

```
Invariant: At most one leader per term (uniqueness)
Scope: All replicas in Raft group
Protection: Quorum-based election

Implementation:
  Replicas: [A, B, C, D, E]
  Election in term T:
    Candidate A requests votes
    Majority [A, B, C] grant votes
    A becomes leader with evidence:
      {term: T, voted_by: [A,B,C], quorum_size: 3/5}

Cost: O(replicas) messages per election
      1-2 RTTs to complete election

Evidence: Quorum certificate proves uniqueness
         No other candidate in term T could get majority
```

#### 5.2.4 Cross-Region Consistency

**Example**: Global transaction in Spanner

```
Invariant: Serializable transaction across multiple regions
Scope: Global (all participating regions)
Protection: 2PC + Paxos in each region

Implementation:
  Transaction touches data in [US, EU, ASIA]

  Phase 1 (Prepare):
    Coordinator → US: prepare
    Coordinator → EU: prepare
    Coordinator → ASIA: prepare
    Wait for all ACKs

  Phase 2 (Commit):
    Coordinator → All: commit
    Each region runs Paxos to durably log commit decision

Evidence:
  - Per-region: Paxos commit certificate
  - Global: 2PC coordinator log entry

Cost: 2 × WAN_RTT + 2 × Paxos_latency
      Typical: 2 × 150ms + 2 × 10ms = 320ms
```

**Why So Expensive**: Must wait for slowest region (tail latency amplified). Evidence from all regions required for global invariant.

### 5.3 Boundary Crossing and Guarantee Degradation

**Key Insight**: Crossing a boundary without carrying evidence causes guarantee downgrade.

#### 5.3.1 The Context Capsule Pattern

When crossing boundaries, explicitly package evidence:

```
Context_Capsule := {
  invariant: Which property is preserved,
  evidence: Proof(s) validating it,
  boundary: Valid scope/domain and epoch,
  mode: Current mode (floor/target/degraded/recovery),
  fallback: Authorized downgrade if verification fails
}
```

**Example - Microservice Call**:

```
Service A (strongly consistent) calls Service B (eventually consistent):

A's guarantee: Linearizable reads (Fresh evidence)
B's guarantee: Eventual consistency (no evidence)

Without capsule:
  A → B: request(data)
  B processes with no freshness guarantee
  Result: Downgrade to eventual (weakest link)

With capsule:
  A → B: request(data, capsule: {
    evidence: {snapshot_ts: T, lease: L},
    requires: Fresh(T),
    fallback: reject_if_stale
  })

  B options:
    1. Upgrade: B fetches fresh data to match A's requirement
    2. Reject: B returns error "cannot provide Fresh guarantee"
    3. Degrade: A's fallback accepts eventual, labeled as such
```

#### 5.3.2 Boundary Types and Evidence Handling

| Boundary Type | Evidence Action | Example |
|--------------|----------------|---------|
| **Trust Boundary** | Re-authenticate | User request → internal service |
| **Consistency Boundary** | Re-prove freshness | Strong service → weak service |
| **Isolation Boundary** | Re-scope | Cross-tenant access |
| **Epoch Boundary** | Re-validate | Leader change, config change |
| **Time Boundary** | Renew expiring evidence | Lease renewal |

### 5.4 Case Study: Multi-Tier Storage System

Consider a system with:
- **Hot tier**: In-memory, linearizable
- **Warm tier**: SSD, snapshot isolation
- **Cold tier**: S3, eventual consistency

**Invariant**: Read-your-writes within session

#### Strategy 1: Narrow Scope (Weak Global Guarantee)

```
Protection per tier:
  Hot: Linearizable within tier
  Warm: Snapshot isolation within tier
  Cold: Eventual within tier

Cross-tier: No coordination

Result:
  Write to Hot (X=1)
  Read from Warm: might not see X=1 (stale)
  → Read-your-writes violated across tiers

Cost: Low (no cross-tier coordination)
Guarantee: Weak (per-tier only)
```

#### Strategy 2: Wide Scope (Strong Global Guarantee)

```
Protection: Session token carries evidence

Write(X=1):
  1. Write to Hot tier
  2. Generate evidence: {key: X, version: V, tier: hot, ts: T}
  3. Attach to session: session.evidence[X] = {V, hot, T}

Read(X):
  1. Check session.evidence[X]
  2. If exists: {V, hot, T}
  3. Query tier: "Give me X version ≥ V OR fresher"
  4. If tier cannot satisfy: Proxy to Hot tier

Result:
  Write to Hot (X=1, V=1)
  Read from Warm: Check V ≥ 1
  If Warm has V=0 (stale): Redirect to Hot
  → Read-your-writes guaranteed

Cost: Higher (cross-tier checks, possible redirects)
Guarantee: Strong (session-level consistency)
```

#### Strategy 3: Hybrid (Explicit Degradation)

```
Protection: Mode-based with user control

Write(X=1):
  Mode: Target (try strong)
  1. Write to Hot, generate evidence
  2. Attach to session

Read(X):
  Mode: Target (try strong)
  1. Check session evidence
  2. If Warm has stale version:
     - Mode: Target → Try Hot tier (may timeout)
     - Mode: Degraded → Return stale with label: {stale: true, age: δ}
     - Mode: Floor → Return whatever available

User experience:
  Normal: Read-your-writes (Target mode)
  High load: May get stale with explicit label (Degraded mode)
  Outage: Best-effort (Floor mode)

Cost: Medium (tries strong, falls back gracefully)
Guarantee: Labeled (user knows what they got)
```

**Lesson**: Boundary placement determines where invariants are enforced and at what cost. Explicit modes let you trade off guarantee strength based on system state.

---

## Part 6: EVIDENCE LIFECYCLE FOR IMPOSSIBILITY PROOFS

Impossibility proofs are statements about **missing evidence**: what you cannot know, and why that prevents certain guarantees.

### 6.1 What Evidence Proves Something is Impossible

#### 6.1.1 FLP: Impossibility of Deterministic Termination

**What FLP Proves**: There exists an execution where no deterministic protocol can decide.

**Evidence Type**: Constructive proof (adversarial execution)

**The Proof Strategy**:
1. Start from a bivalent configuration (both outcomes possible)
2. Show adversary can always force another bivalent configuration
3. Construct infinite execution that never decides
4. Evidence: The execution trace itself proves impossibility

**Key Insight**: FLP doesn't say "you cannot build consensus." It says "you cannot build consensus without additional assumptions."

**Missing Evidence in FLP Model**:
- No timing information (asynchronous)
- No failure detection (cannot distinguish slow from dead)
- No randomness (deterministic)

**What This Means**: To circumvent FLP, you must introduce one of these missing evidence types.

#### 6.1.2 CAP: Impossibility of CA During P

**What CAP Proves**: During partition, you cannot have both consistency (C) and availability (A).

**Evidence Type**: Proof by contradiction

**The Proof**:
```
Assume: System is CA during partition P

Setup:
  Nodes: [A, B] partitioned from [C, D]
  Initial value: X = v0

Execution:
  Client 1 → A: Write X = v1
    - If A accepts (availability): A has X=v1
  Client 2 → C: Read X
    - If C returns v0 (hasn't seen v1): Consistency violated
    - If C waits for A (to get v1): Availability violated
    - If C rejects: Availability violated

Contradiction: Cannot be both consistent and available
```

**Missing Evidence During Partition**:
- Cannot get quorum (not enough nodes reachable)
- Cannot verify if other side accepted writes
- Cannot get current state from other side

#### 6.1.3 Lower Bounds: Minimal Communication Complexity

**What It Proves**: Consensus requires Ω(n) messages in failure-free case

**Evidence Type**: Information-theoretic argument

**The Proof**:
```
Claim: Can do consensus with o(n) messages (less than linear)

Contradiction:
  If process P doesn't receive any message:
    - P cannot know others' inputs
    - P must decide based only on its own input
    - But decision must be same for all processes
    - Yet inputs can differ → P's decision might be wrong

Conclusion: Every process must receive at least one message
            → Total messages ≥ n (actually n-1 for tree topology)
```

**Missing Evidence**: Without receiving messages from all (or most) others, cannot ensure agreement.

### 6.2 How Failure Detectors Generate Evidence

Failure detectors are the primary mechanism for circumventing FLP by generating evidence about process liveness.

#### 6.2.1 The Failure Detector Hierarchy

| Detector | Property | Evidence Generated | Cost |
|----------|----------|-------------------|------|
| **Perfect (P)** | Never suspects correct process | Definitive liveness proof | Impossible in async |
| **Eventually Perfect (◇P)** | Eventually stops suspecting correct | Time-bounded liveness proof | Requires partial synchrony |
| **Strong (S)** | Some correct process never suspected | Designated leader evidence | Requires stable leader |
| **Eventually Strong (◇S)** | Eventually some correct never suspected | Eventual leader evidence | Sufficient for consensus |
| **Weak (W)** | Some correct suspects some faulty | Coarse failure evidence | Insufficient alone |

#### 6.2.2 Implementing ◇P: Eventually Perfect Detector

**Strategy**: Heartbeats with adaptive timeouts

```
Each process P maintains:
  suspected: Set[process_id]
  timeout[Q]: Duration = initial_timeout
  last_heartbeat[Q]: Timestamp

Sending heartbeats:
  Every T milliseconds:
    broadcast("heartbeat from P")

Receiving heartbeat from Q:
  last_heartbeat[Q] = now()
  if Q ∈ suspected:
    remove Q from suspected
    timeout[Q] *= 1.5  // Increase timeout (adapt to slower network)

Checking timeouts:
  Every T milliseconds:
    for Q in all_processes:
      if now() - last_heartbeat[Q] > timeout[Q]:
        if Q ∉ suspected:
          add Q to suspected
          timeout[Q] *= 2  // Double timeout before next try
```

**Evidence Generated**:
```
Suspicion_Evidence := {
  suspected_process: Q,
  reason: "no heartbeat for timeout[Q]",
  timeout_duration: timeout[Q],
  last_seen: last_heartbeat[Q],
  confidence: timeout[Q] / expected_RTT
}
```

**Properties**:
- **Completeness**: Eventually suspects crashed process (as timeout → ∞)
- **Eventual Accuracy**: Eventually stops suspecting correct process (after GST, network stabilizes)

**Why This Works** (Circumvents FLP):
- Partial synchrony assumption: After GST, message delays bounded
- Adaptive timeouts: Eventually large enough to accommodate actual delays
- Evidence: Suspicion provides liveness oracle that FLP says we cannot have in pure asynchronous

#### 6.2.3 Evidence Lifetime in Failure Detection

**Key Insight**: Failure detection evidence has limited lifetime and must be refreshed.

```
Evidence_Lifecycle:

1. Generated:
   - Heartbeat timeout expires
   - Process Q added to suspected set
   - Evidence: {suspected: Q, at: T, timeout: δ}

2. Active:
   - Q remains in suspected set
   - Consensus can proceed without Q
   - Q's votes ignored

3. Expiring:
   - Heartbeat received from Q
   - Grace period before removing from suspected
   - Evidence being reconsidered

4. Expired:
   - Q removed from suspected set
   - Q's votes accepted again
   - Old suspicion evidence invalid

5. Renewed:
   - If Q misses another heartbeat
   - Re-add to suspected with new evidence
   - Timeout increased (adaptive)
```

**Lifetime Characteristics**:
- **Initial**: Short timeout (e.g., 500ms)
- **Adaptive**: Increases with each false suspicion (up to 10s+)
- **Bound**: Must not exceed liveness requirement (if timeout too long, system hangs)

### 6.3 Circumventing Impossibilities Through Evidence

#### 6.3.1 Adding Synchrony Assumptions (Partial Synchrony)

**DLS Model** (Dwork, Lynch, Stockmeyer):
- Unknown bound Δ on message delay
- Bound holds eventually after unknown GST (Global Stabilization Time)
- Before GST: Can make no progress (asynchronous)
- After GST: Can complete consensus (synchronous)

**Evidence Generated**:
```
Synchrony_Evidence := {
  assumption: "partial_synchrony",
  bound: Δ,
  gst: "unknown but assumed passed",
  timeout: T > Δ (conservative estimate)
}

Mode Transitions:
  Before GST (suspected):
    - Timeouts trigger frequently (messages delayed > T)
    - False suspicions common
    - Consensus stalls or slow
    - Mode: Degraded

  After GST (actual):
    - Messages arrive within Δ < T
    - No false suspicions
    - Consensus completes in bounded time
    - Mode: Target
```

**Production Example - Raft Election**:
```
Initial election timeout: 150-300ms (randomized)

Execution:
  T=0: Leader L starts, sends heartbeats every 50ms
  T=200: Network congestion, heartbeat delayed 180ms
  T=230: Some followers timeout, start election
  T=250: Split vote (no leader elected)
  T=400: Election timeout, retry with higher timeout 300-600ms
  T=450: Network stabilizes, election succeeds

Evidence evolution:
  T=230: {suspected: L, timeout: 200ms, confidence: low}
  T=250: {no_leader, election_failed, votes_split}
  T=400: {election_retry, timeout: 500ms, confidence: medium}
  T=450: {leader: M, term: 2, timeout: 500ms, confidence: high}

Lesson: System adapts timeout until evidence of stability achieved
```

#### 6.3.2 Adding Randomization (Probabilistic Termination)

**Ben-Or Algorithm**: Uses randomness to break symmetry

```
Consensus with Randomness:

Phase 1: Propose
  - Each process proposes value
  - Collect proposals from others

Phase 2: Vote
  - If majority proposes v: Vote for v
  - Else: Vote for random value (coin flip)

Phase 3: Decide
  - If majority voted v: Decide v
  - Else: Retry phase 1 with new coin flip

Termination:
  - Probability 1 of eventually terminating (not deterministic)
  - Expected O(1) rounds with n processes, f < n/2 faults
```

**Evidence Generated**:
```
Randomness_Evidence := {
  coin_flip: random_bit,
  commitment: Hash(coin_flip || nonce),  // Commit before reveal
  reveal: coin_flip,                      // Reveal after others commit
  verification: "Hash(reveal) == commitment"
}

Properties:
  - Cannot predict before commitment phase
  - Cannot forge after seeing others' commitments
  - Breaks symmetry with high probability
```

**Why This Works**:
- FLP assumes deterministic protocol
- Randomization makes adversary's job harder
- With probability 1, eventually lucky coin flips lead to decision
- Evidence: Random bits provide the "extra information" FLP proof shows is missing

#### 6.3.3 Adding Stronger Assumptions (Synchrony)

**Synchronous Model**:
- Known bound Δ on message delay
- All messages delivered within Δ
- Processes can use timeouts reliably

**Evidence Generated**:
```
Timing_Evidence := {
  message_delay_bound: Δ,
  send_time: T_send,
  receive_deadline: T_send + Δ,
  actual_receive_time: T_receive
}

Guaranteed:
  T_receive ≤ T_send + Δ

Consequence:
  - Timeout after Δ: Definitive evidence of crash
  - No false suspicions
  - FLP circumvented: Can distinguish slow from crashed
```

**Consensus in Synchronous Model** (Simple Algorithm):
```
For f faults, need f+1 rounds:

Round 1:
  - Everyone broadcasts their value
  - Wait Δ time
  - If didn't receive from process P: Mark P as crashed

Round 2:
  - Broadcast "I suspect P"
  - Wait Δ time
  - Collect suspicions from others

...

Round f+1:
  - By now, all processes agree on same suspected set
  - All honest processes have same view
  - Decide: min(values_from_non_suspected)

Evidence:
  Each round provides definitive evidence of who is alive
  After f+1 rounds, impossible for disagreement
```

**Cost of Stronger Assumption**:
- Must provision for worst-case Δ (expensive in WAN)
- False timeouts if Δ underestimated → Safety violated
- Over-provisioning if Δ overestimated → Performance suffers

### 6.4 Evidence Expiry and Renewal Patterns

#### 6.4.1 Lease-Based Evidence

**Pattern**: Evidence with explicit expiry time

```
Lease := {
  resource: "shard-42",
  holder: process_id,
  epoch: N,
  granted_at: T_start,
  expires_at: T_end,
  grantor_quorum: [P1, P2, P3]
}

Lifecycle:
  Generated (T_start):
    - Holder acquires lease from quorum
    - Evidence valid for [T_start, T_end]

  Active (T_start < now < T_end - renewal_window):
    - Holder can use resource
    - Others must honor holder's actions

  Expiring (T_end - renewal_window < now < T_end):
    - Holder attempts renewal
    - Sends heartbeat to grantor_quorum
    - On success: New lease generated, extends T_end
    - On failure: Wait for expiry, then re-acquire

  Expired (now ≥ T_end):
    - Evidence no longer valid
    - Holder must stop using resource
    - Others can acquire new lease (with epoch N+1)

  Revoked (explicit):
    - Quorum decides to revoke (e.g., node misbehaving)
    - Broadcast: {revoke_lease: resource, epoch: N}
    - Holder must stop immediately
    - New lease granted with epoch N+1
```

**Renewal Strategies**:

1. **Proactive Renewal** (common):
```
Renew at: T_end - (T_end - T_start)/2  // Halfway through lease

Example:
  Lease: [0s, 10s]
  Renew at: 5s
  If successful: New lease [5s, 15s]
  If failed: Retry at 7s, 8s, 9s
  If all fail: Stop at 10s
```

2. **Reactive Renewal** (on-demand):
```
Renew only when operation needs it

Example:
  Check before each operation:
    if now() > T_end - safety_margin:
      renew_lease()

  Risk: Latency spike during renewal
  Benefit: Fewer renewals if infrequent operations
```

3. **Adaptive Renewal** (based on load):
```
Adjust renewal timing based on system state

High load (many operations):
  - Renew proactively (avoid latency spikes)
  - Longer lease duration

Low load (few operations):
  - Renew reactively (save bandwidth)
  - Shorter lease duration (faster failover)
```

#### 6.4.2 Quorum Certificate Evidence

**Pattern**: Evidence that requires re-verification at boundaries

```
Quorum_Certificate := {
  decision: value,
  epoch: N,
  voters: [P1, P2, P3],
  signatures: [Sig1, Sig2, Sig3],
  timestamp: T
}

Lifecycle:
  Generated:
    - Proposer collects ≥ quorum votes
    - Creates certificate bundling signatures
    - Evidence: Majority witnessed decision

  Validated:
    - Recipient verifies all signatures
    - Checks voters form valid quorum
    - Checks epoch is current
    - If valid: Accept decision

  Propagated:
    - Certificate sent to other processes
    - Each must independently verify
    - No transitive trust (non-transitive evidence)

  Expired:
    - Epoch advances (configuration change)
    - Old certificate no longer valid
    - Must obtain new certificate in new epoch
```

**Non-Transitivity Example**:
```
Process A collects quorum certificate:
  A has evidence: Decision D is safe

A tells B: "D is safe, here's the certificate"
  B verifies certificate: OK, B trusts D

B tells C: "D is safe"
  C asks: "Where's the certificate?"
  B must send certificate (cannot just claim "A told me")

Evidence does NOT transit through claims:
  A's evidence → B requires verification
  B's claim → C requires re-verification of original evidence
```

#### 6.4.3 Time-Based Evidence (Timestamps, HLC)

**Pattern**: Evidence that degrades with time

```
Timestamp_Evidence := {
  value: X,
  timestamp: T,
  clock_uncertainty: ε,
  max_staleness: δ
}

Lifecycle:
  Generated (at T):
    - Write produces new version with timestamp T
    - Evidence: "Value X valid at time T"

  Fresh (now < T + δ):
    - Read at time T' where T' - T < δ
    - Evidence: "X is at most δ stale"
    - Mode: Target (freshness guarantee)

  Stale (now ≥ T + δ):
    - Read at time T' where T' - T ≥ δ
    - Evidence: "X is more than δ stale"
    - Mode: Degraded (staleness exceeded bound)
    - Options:
      a) Reject read (fail closed)
      b) Return with staleness label
      c) Fetch fresh version (latency spike)

  Expired (now ≥ T + retention_period):
    - Data garbage collected
    - Evidence no longer exists
    - Cannot serve reads at time T anymore
```

**Closed Timestamp Pattern** (CockroachDB):
```
Leader maintains:
  closed_timestamp: T_closed (monotonically increasing)

Invariant:
  "All transactions with commit_ts < T_closed have been applied"

Evidence:
  Leader broadcasts: {closed_ts: T_closed, epoch: E}

Follower reads:
  Read at snapshot time T_snap where T_snap < T_closed:
    - Follower can serve locally (no leader involvement)
    - Guarantee: Read sees all commits < T_snap
    - Evidence: closed_ts broadcast from leader

  Read at T_snap ≥ T_closed:
    - Must wait for T_closed to advance
    - Or proxy to leader

Lifecycle:
  T_closed advances as time progresses:
    - Every few seconds, leader increments T_closed
    - Broadcast to followers
    - Old T_closed values discarded (superseded)
```

#### 6.4.4 Evidence Renewal Under Failure

**Challenge**: What if evidence cannot be renewed due to failures?

**Strategies**:

1. **Fail Closed** (CP approach):
```
On renewal failure:
  - Stop accepting operations
  - Return error: "Lease expired, cannot proceed"
  - Wait for recovery (new lease acquired)

Example: Raft follower cannot reach leader
  - After election timeout: No longer serves reads
  - Waits for new leader election
  - Once new leader elected: Resume operations

Mode: Floor (preserve safety, sacrifice liveness)
```

2. **Fail Open** (AP approach):
```
On renewal failure:
  - Continue with degraded guarantees
  - Return data with staleness label
  - Accept writes with conflict risk

Example: Cassandra replica cannot reach others
  - Continue serving reads (possibly stale)
  - Accept writes (create version, resolve later)
  - Mark data with timestamps for later reconciliation

Mode: Degraded (preserve liveness, weaken consistency)
```

3. **Fallback Evidence** (Hybrid):
```
Primary evidence: Lease from leader (strong guarantee)
Fallback evidence: Last-known-good timestamp (weak guarantee)

On renewal failure:
  - Check fallback: Is last-known-good recent enough?
  - If yes: Use with degraded guarantee (bounded staleness)
  - If no: Fail closed (too stale, unsafe)

Example: CockroachDB follower reads
  Primary: Read from leader (fresh)
  Fallback: Read from follower with closed_timestamp
    - If closed_timestamp recent (< δ): Allow read
    - If closed_timestamp stale (≥ δ): Proxy to leader or fail

Mode: Conditional (degrade gracefully based on evidence age)
```

---

## Part 7: SYNTHESIS - IMPOSSIBILITY AS EVIDENCE BOUNDARIES

### 7.1 The Unified View

Impossibility results define the **boundaries of evidence**:

| Impossibility | What's Missing | Evidence Needed | How to Obtain |
|--------------|----------------|----------------|---------------|
| **FLP** | Failure detection | Liveness proof | Partial synchrony, randomization, or synchrony |
| **CAP** | Quorum during partition | Reachability proof | Choose availability OR consistency (cannot have both) |
| **PACELC** | Free coordination | Staleness bound | Accept latency OR accept staleness |
| **Lower Bounds** | Information without communication | Global knowledge | O(n) messages, O(quorum) for majority |

**Central Insight**: Every impossibility result says "you lack evidence to make this decision while preserving these invariants."

### 7.2 Designing Around Impossibilities

**Process**:

1. **Identify Invariants**: What must never be violated?
   - Conservation, uniqueness, authenticity, order

2. **Analyze Threats**: What could violate them?
   - Partitions, asynchrony, Byzantine actors, gray failures

3. **Define Evidence**: What proves invariants hold?
   - Quorum certificates, leases, signatures, timestamps

4. **Determine Costs**: What does evidence generation cost?
   - Latency, bandwidth, CPU, coordination

5. **Choose Trade-offs**: Which impossibility to accept?
   - CA (unavailable during partition) vs. AP (inconsistent during partition)
   - Low latency + weak consistency vs. high latency + strong consistency

6. **Design Modes**: How to degrade when evidence unavailable?
   - Floor: Minimum viable correctness
   - Target: Normal operation
   - Degraded: Reduced guarantees
   - Recovery: Restoring evidence

### 7.3 Example: Building a Distributed Counter

**Requirement**: Implement a distributed counter with increment operation.

**Invariant**: Counter value = sum of all increments (conservation)

#### Option 1: Strong Consistency (CP)

```
Design:
  - Single leader holds lease
  - All increments go to leader
  - Leader maintains authoritative count

Evidence:
  - Leader lease: {holder: L, epoch: E, expiry: T}
  - Counter value: {count: N, version: V, last_increment: T'}

Guarantees:
  - Linearizable increments
  - Accurate count at all times

Costs:
  - Latency: 1-2 RTTs to leader
  - Availability: Unavailable during leader election (2-10 seconds)
  - Throughput: Limited by single leader (10K-100K ops/sec)

Modes:
  Target: Leader available, lease valid
    - Accept increments
    - Return current count

  Degraded: Leader election in progress
    - Reject increments (unavailable)
    - Cannot return accurate count

  Recovery: New leader elected
    - Read committed log
    - Reconstruct count
    - Resume operations
```

#### Option 2: Weak Consistency (AP)

```
Design:
  - Multiple replicas accept increments
  - Replicas exchange updates asynchronously
  - Eventual consistency via CRDT (PN-Counter)

Evidence:
  - Per-replica: {replica_id: R, local_count: N}
  - Global: {replica_counts: {R1: N1, R2: N2, ...}}

Guarantees:
  - Eventually consistent
  - Monotonic reads (count only increases)

Costs:
  - Latency: O(1) local (no coordination)
  - Availability: Always available (no leader needed)
  - Throughput: Sum of all replicas (100K-1M+ ops/sec)
  - Storage: O(replicas) per counter

Modes:
  Target: All replicas reachable
    - Accept local increments
    - Merge updates from others
    - Return sum of all replica counts

  Degraded: Partition (some replicas unreachable)
    - Accept local increments (partition-available)
    - Return partial count (may be stale)
    - Label: "Count based on N/M replicas"

  Recovery: Partition heals
    - Exchange missed updates
    - Merge replica counts
    - Converge to true sum
```

#### Option 3: Bounded Staleness (Hybrid)

```
Design:
  - Leader holds lease and authoritative count
  - Followers can serve reads with bounded staleness
  - Increments go to leader (strong) or followers (eventual)

Evidence:
  - Leader lease: {holder: L, epoch: E, expiry: T}
  - Closed timestamp: {closed_ts: T_c, epoch: E}
  - Replica version: {replica: R, count: N, as_of: T_r}

Guarantees:
  - Reads: At most δ stale (configurable)
  - Writes: Linearizable (if to leader) or eventual (if to follower)

Costs:
  - Read latency: O(1) local if within δ, else 1 RTT to leader
  - Write latency: 1-2 RTTs to leader (strong) or O(1) local (eventual)
  - Availability: Read-available always, write-available if leader reachable

Modes:
  Target: Leader reachable, closed_ts recent
    - Reads: Serve from local replica (count at closed_ts)
    - Writes: Forward to leader
    - Staleness: ≤ δ

  Degraded: Leader unreachable OR closed_ts stale
    - Reads: Serve local with stale label (staleness > δ)
    - Writes: Accept locally, gossip to others (eventual)
    - Mode label: "Degraded to eventual consistency"

  Recovery: Leader re-elected or reachable
    - Followers sync with leader
    - Update closed_ts
    - Resume target mode
```

**Choosing Among Options**:

| Use Case | Choice | Rationale |
|----------|--------|-----------|
| Bank account balance | Option 1 (CP) | Accuracy critical, can tolerate brief unavailability |
| Website visitor counter | Option 2 (AP) | Approximate ok, must never be unavailable |
| Metrics dashboard | Option 3 (Hybrid) | Recent data preferred, stale ok if fresh unavailable |

### 7.4 The Evidence Budget Concept

**Idea**: Every operation has an "evidence budget"—how much cost you're willing to pay for guarantees.

```
Evidence_Budget := {
  latency_budget: 10ms,
  bandwidth_budget: 1KB,
  availability_requirement: 99.9%,
  staleness_tolerance: 1 second
}

Operation Planning:
  Required evidence: Quorum certificate (3/5 nodes)
  Cost estimate: 2 RTTs (4ms) + 500 bytes

  Check:
    4ms ≤ 10ms ✓ (within latency budget)
    500B ≤ 1KB ✓ (within bandwidth budget)
    Availability: Can tolerate 2/5 nodes down ✓
    Staleness: Synchronous (0 staleness) ✓

  Decision: Proceed with strong consistency (budget allows)

Alternative Scenario:
  Network degraded: RTT = 50ms
  Cost estimate: 2 RTTs (100ms) + 500 bytes

  Check:
    100ms > 10ms ✗ (exceeds latency budget)

  Decision: Downgrade to local read with bounded staleness
    Local read: 1ms latency (within budget)
    Staleness: ≤ 1s (within tolerance)
    Mode: Degraded (labeled)
```

**Operational Pattern**:
- Set evidence budgets based on SLA requirements
- Monitor actual evidence costs in production
- Automatically degrade when costs exceed budget
- Alert operators when degradation occurs
- Return to target mode when evidence costs drop

### 7.5 The Impossibility Landscape - A Mental Map

```
                      SYNCHRONY
                         ↑
                         |
    [Fully Synchronous]  |  Known bounds, reliable timeouts
         ↑               |  Cost: Over-provision for worst-case
         |               |  Benefit: Simple protocols, fast consensus
         |               |
    [Partial Sync]       |  Unknown bounds, eventual stability
         ↑               |  Cost: Adaptive timeouts, slower initially
         |               |  Benefit: Practical model, matches reality
         |               |
    [Asynchronous] ------+  No bounds, cannot timeout reliably
                         |  Cost: Cannot solve consensus deterministically
                         |  Benefit: Weak assumptions, broad applicability
                         |
                         ↓
                    NO SYNCHRONY

                    RANDOMIZATION →

    [Deterministic] ←→ [Probabilistic]

    Deterministic:
      - FLP says consensus impossible
      - Need synchrony to proceed

    Probabilistic:
      - Expected finite termination
      - Probability 1 of eventual decision
      - Breaks symmetry with randomness

                    FAILURE MODEL →

    [Crash]  →  [Omission]  →  [Byzantine]

    Crash: Process stops
      - Quorum = n/2 + 1
      - Simple detection (heartbeats)

    Omission: Process drops messages
      - Similar to crash, harder to detect
      - Quorum = n/2 + 1

    Byzantine: Arbitrary behavior
      - Quorum = 2f/3 + 1 (with signatures)
      - Complex detection (cross-verify)

                 CONSISTENCY SPECTRUM →

    [Strong]  →  [Bounded]  →  [Eventual]

    Strong (Linearizable):
      - Real-time order preserved
      - High coordination cost
      - CAP: Choose C (unavailable during P)

    Bounded (Bounded Staleness):
      - Staleness ≤ δ
      - Moderate coordination cost
      - CAP: Tunable (C ↔ A based on δ)

    Eventual:
      - Converges eventually
      - No coordination cost
      - CAP: Choose A (inconsistent during P)
```

**Navigating the Landscape**:
1. Start with requirements (what invariants must hold?)
2. Identify position on each axis
3. Understand costs and benefits of that position
4. Design evidence mechanisms to match
5. Prepare degradation paths when assumptions violated

---

## Conclusion: Impossibility Results as Design Principles

Impossibility results are not obstacles—they are **design principles** that clarify trade-offs.

**Key Takeaways**:

1. **Invariants are Sacred**: Identify what must never be violated (conservation, uniqueness, authenticity)

2. **Evidence is the Currency**: You cannot enforce invariants without evidence. Evidence has cost (latency, bandwidth, coordination).

3. **Impossibilities Define Boundaries**: FLP, CAP, and lower bounds tell you where evidence is unavailable or too expensive.

4. **Circumvention Requires Assumptions**: Partial synchrony, randomization, or stronger models provide the missing evidence.

5. **Scope Determines Cost**: Enforce invariants at the narrowest scope possible. Every boundary crossing has cost.

6. **Evidence Has Lifetime**: Leases, certificates, timestamps all expire. Design renewal patterns.

7. **Degrade Gracefully**: When evidence unavailable, explicitly degrade guarantees (floor/target/degraded/recovery modes).

8. **Make Trade-offs Visible**: Use typed guarantees and context capsules to carry evidence across boundaries.

**The Unified Mental Model**:

> A distributed system is a machine for preserving invariants across space and time by converting uncertainty into evidence. Impossibility results tell us where this conversion fails fundamentally. To build practical systems, we either:
> - Add assumptions that provide missing evidence (partial synchrony, randomization)
> - Weaken invariants to match available evidence (eventual consistency)
> - Explicitly degrade when evidence is unavailable (mode-based operation)
>
> Every design choice is a decision about which invariants to protect, which evidence to generate, and how to degrade when evidence is insufficient.

In the next sections of this chapter, we'll apply this invariant and evidence framework to understand specific impossibility results (FLP, CAP, PACELC) and real production systems (Raft, Spanner, Cassandra). We'll see that every protocol is fundamentally a strategy for generating and managing evidence to protect invariants within the boundaries defined by impossibility results.

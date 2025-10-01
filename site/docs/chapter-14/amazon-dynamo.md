# Amazon Dynamo: The Shopping Cart That Scaled

## Introduction: When Availability Trumps Consistency

On Black Friday 2004, Amazon's shopping cart service went down for 45 minutes. In those 45 minutes, Amazon lost millions of dollars in revenue. Worse, customers couldn't add items to their carts—the core experience of shopping online was broken.

The root cause? A distributed database that chose consistency over availability. When a network partition occurred, the database refused to accept writes until consistency could be guaranteed. This was the "right" choice according to traditional database theory, but it was catastrophically wrong for Amazon's business.

**The realization**: For a shopping cart, it's better to show slightly stale data than to show an error. If two customers add the same item simultaneously from different datacenters and we can't immediately reconcile, we should accept both writes and merge them later. A duplicate item in a cart is a minor annoyance. A non-functional cart is a lost customer.

This incident led to Dynamo, Amazon's revolutionary distributed key-value store that flipped the conventional wisdom: **Availability is more important than consistency. Always accept writes. Resolve conflicts later.**

### The Architectural Revolution

Before Dynamo (pre-2007):
- Databases chose CP (consistency + partition tolerance)
- During partitions, minority side rejected writes
- Applications dealt with "database unavailable" errors

After Dynamo (2007-present):
- Dynamo chose AP (availability + partition tolerance)
- During partitions, both sides accept writes
- Database handles conflict resolution, presents conflicts to application

**The numbers**:
- Availability: 99.9995% (1.5 minutes downtime per year)
- Latency: 99.9th percentile < 300ms for reads and writes
- Scale: Millions of requests per second
- Storage: Petabytes across 1000s of nodes

The architecture has been cloned by Cassandra, Riak, Voldemort, and influenced virtually every modern NoSQL database.

### The Core Insight: Conflicts Are Inevitable, Accept Them

Traditional databases avoid conflicts through coordination:
- Locks prevent concurrent writes to same data
- Primary-backup replication serializes updates
- 2PC ensures all nodes agree before committing

Dynamo accepts conflicts as inevitable:
- Network partitions will happen
- Nodes will fail
- Clock skew will reorder events

**Instead of preventing conflicts, Dynamo:**
1. **Detects conflicts** using vector clocks
2. **Preserves all conflicting versions** (siblings)
3. **Delegates resolution** to application or uses last-write-wins

This is **optimistic concurrency** taken to its logical extreme: Always accept operations, never block, reconcile conflicts after the fact.

### Why This Matters

Dynamo introduced techniques now standard in distributed systems:

1. **Consistent hashing**: Distributed data placement with minimal movement on node changes
2. **Vector clocks**: Causality tracking without coordination
3. **Quorum systems**: Tunable consistency/availability trade-offs
4. **Hinted handoff**: Availability during temporary failures
5. **Merkle trees**: Efficient replica synchronization
6. **Gossip protocol**: Decentralized membership and failure detection

These aren't theoretical algorithms—they're battle-tested solutions running the world's largest e-commerce platform.

**The evidence lens**: Dynamo generates **causality evidence** (vector clocks) and **availability evidence** (quorum responses), uses them to order events and detect conflicts, and degrades gracefully by preserving divergent versions rather than blocking.

Let's dive into how it works.

---

## Part 1: INTUITION (First Pass)—The Shopping Cart Problem

### The Setup: Shopping Cart Requirements

Amazon's shopping cart must:

1. **Always writeable**: Customer must always be able to add items
2. **Low latency**: Add-to-cart should be <100ms globally
3. **Durable**: Don't lose cart contents (customer's intent to buy)
4. **Eventually consistent**: OK if different views converge later
5. **Conflict resolution**: Handle duplicate adds, concurrent removes

**Anti-requirements** (What we DON'T need):
- Immediate consistency: It's OK if two datacenters show different cart contents briefly
- Strong ordering: It's OK if "add item A" and "add item B" get reordered

### The Naive Approach (Why It Fails)

**Attempt 1: Single master database**
```python
# All writes go to one master DB
def add_to_cart(user_id, item_id):
    master_db.execute(
        "INSERT INTO cart (user_id, item_id) VALUES (?, ?)",
        user_id, item_id
    )
```

**Failure mode**: Master becomes single point of failure. If master goes down, no one can add items to cart. Black Friday 2004 repeated.

**Attempt 2: Master-replica with synchronous replication**
```python
def add_to_cart(user_id, item_id):
    # Write to master, wait for replicas to acknowledge
    master_db.execute("INSERT ...", user_id, item_id)
    wait_for_replicas(min_replicas=2)
```

**Failure mode**: During network partition, master can't reach replicas. Write blocks waiting for acknowledgment. Cart appears frozen to customer.

**Attempt 3: Asynchronous replication**
```python
def add_to_cart(user_id, item_id):
    # Write to master, return immediately
    master_db.execute("INSERT ...", user_id, item_id)
    async_replicate_to_replicas()
```

**Failure mode**: If master fails before replication completes, recent cart additions are lost. Customer sees items disappear from cart. Trust destroyed.

**The Realization**: You can't build a highly available system with a single master. Need to accept writes at multiple nodes simultaneously. But then you get conflicts.

### The First Conflict: Concurrent Adds

Two customers add different items to the same cart simultaneously:

```
Datacenter A (US-East):
  Customer adds "iPhone" to cart at t=1

Datacenter B (US-West):
  Customer adds "iPad" to cart at t=1

Network is partitioned, A and B can't communicate.

How do we handle this when partition heals?
```

**Bad solution 1: Last-write-wins (based on timestamp)**
```python
if item_a.timestamp > item_b.timestamp:
    cart = [item_a]  # Discard item_b
else:
    cart = [item_b]  # Discard item_a
```

**Problem**: Timestamps are unreliable (clock skew). Might discard the "iPhone" because US-West's clock was slow. Customer loses their selection.

**Bad solution 2: Reject one write**
```python
# Only accept write if you're the master
if not is_master():
    return ERROR("Write not accepted, try master")
```

**Problem**: During partition, one datacenter becomes unavailable for writes. Back to Black Friday 2004.

**Good solution: Accept both, merge later**
```python
# Both datacenters accept writes
version_a = {"cart": ["iPhone"], "vector_clock": {A: 1}}
version_b = {"cart": ["iPad"], "vector_clock": {B: 1}}

# When partition heals, detect conflict (vector clocks are concurrent)
# Present both versions to application
merged_cart = merge([version_a, version_b])
# → ["iPhone", "iPad"]
```

**The insight**: For shopping carts, merging is semantically correct. The customer wanted both items. This is an application-specific resolution strategy, but it works perfectly.

### Vector Clocks: Tracking Causality Without Coordination

Vector clocks solve the problem: "Did event A happen before event B, or are they concurrent?"

**The concept**:

Each node maintains a counter of events it has seen:
```python
vector_clock = {
    'node_a': 0,  # Events seen from node A
    'node_b': 0,  # Events seen from node B
    'node_c': 0   # Events seen from node C
}
```

When node A processes an event:
```python
vector_clock['node_a'] += 1
```

When node A receives data from node B:
```python
vector_clock = merge(local_vector_clock, received_vector_clock)
vector_clock['node_a'] += 1  # Local event
```

**Comparison rules**:

```python
def happens_before(vc1, vc2):
    # vc1 < vc2 if: vc1[n] <= vc2[n] for all n, and vc1 != vc2
    return all(vc1[n] <= vc2[n] for n in nodes) and vc1 != vc2

def concurrent(vc1, vc2):
    # Concurrent if neither happened before the other
    return not happens_before(vc1, vc2) and not happens_before(vc2, vc1)
```

**Example**:

```
Event 1: Node A writes "add iPhone"
  vector_clock = {A: 1, B: 0, C: 0}

Event 2: Node A writes "add AirPods" (causally after Event 1)
  vector_clock = {A: 2, B: 0, C: 0}

Event 3: Node B writes "add iPad" (concurrent with Events 1&2)
  vector_clock = {A: 0, B: 1, C: 0}

Comparison:
  Event 1 < Event 2 (A:1 < A:2)  → Event 2 supersedes Event 1
  Event 2 || Event 3 (A:2 > A:0, but B:0 < B:1)  → Concurrent, conflict!
```

When a read encounters concurrent versions (siblings), it returns **both** to the application. The application must merge them.

### The Shopping Cart with Vector Clocks

```python
class DynamoShoppingCart:
    def __init__(self):
        self.node_id = get_node_id()

    def add_item(self, user_id, item_id):
        # Read current cart
        versions = self.read(user_id)

        # Pick the latest version(s) as context
        # If multiple concurrent versions, merge them
        cart_items = self.merge_versions(versions)

        # Add new item
        cart_items.append(item_id)

        # Increment vector clock
        vector_clock = self.merge_vector_clocks(versions)
        vector_clock[self.node_id] += 1

        # Write back
        self.write(user_id, cart_items, vector_clock)

    def merge_versions(self, versions):
        # Application-specific merge logic
        all_items = []
        for v in versions:
            all_items.extend(v.cart_items)
        return list(set(all_items))  # Deduplicate

    def merge_vector_clocks(self, versions):
        # Take pairwise max of all vector clocks
        merged = {}
        for v in versions:
            for node, count in v.vector_clock.items():
                merged[node] = max(merged.get(node, 0), count)
        return merged
```

**The flow**:

```
1. Customer adds iPhone:
   Read: []
   Write: ["iPhone"] with VC={A:1}

2. Customer adds iPad (from different datacenter):
   Read: ["iPhone"] with VC={A:1}
   Write: ["iPhone", "iPad"] with VC={A:1, B:1}

3. Network partition: Customer adds AirPods from A, MacBook from B
   At A: Read ["iPhone", "iPad"] with VC={A:1, B:1}
         Write ["iPhone", "iPad", "AirPods"] with VC={A:2, B:1}

   At B: Read ["iPhone", "iPad"] with VC={A:1, B:1}
         Write ["iPhone", "iPad", "MacBook"] with VC={A:1, B:2}

4. Partition heals, next read sees both versions:
   Version 1: ["iPhone", "iPad", "AirPods"] with VC={A:2, B:1}
   Version 2: ["iPhone", "iPad", "MacBook"] with VC={A:1, B:2}

   Neither happened before the other (A:2>A:1 but B:1<B:2) → Concurrent

5. Application merges:
   ["iPhone", "iPad", "AirPods", "MacBook"] with VC={A:2, B:2}
```

**The beauty**: No coordination required. Each datacenter accepts writes independently. Conflicts are detected and resolved after the fact. Cart is always available.

---

## Part 2: UNDERSTANDING (Second Pass)—Architecture Deep Dive

### Consistent Hashing: Data Placement Without Central Coordinator

Dynamo distributes data across nodes using **consistent hashing**.

**The problem with naive hashing**:

```python
# Naive approach: Hash key to determine node
node_id = hash(key) % num_nodes
```

**Issue**: When you add or remove a node, `num_nodes` changes, so almost every key rehashes to a different node. Massive data movement.

**Consistent hashing solution**:

Hash both keys and nodes to the same space (e.g., 0 to 2^128):

```
Ring: 0 ──────────────────────────────────── 2^128

Nodes:      N1        N2            N3
            ↓         ↓             ↓
            |         |             |
            23        104           201

Keys:   K1      K2         K3   K4
        ↓       ↓          ↓    ↓
        15      67         178  250
```

**Placement rule**: Key is stored on the first node clockwise from its hash position.

```
K1 (hash=15)  → N1 (first node ≥ 15)
K2 (hash=67)  → N2 (first node ≥ 67)
K3 (hash=178) → N3 (first node ≥ 178)
K4 (hash=250) → N1 (wraps around)
```

**Adding a node**:

```
Add N4 at position 150:

Keys:   K1      K2    K3        K4
        ↓       ↓     ↓         ↓
        15      67    178       250

Nodes:  N1      N2    N4  N3
        ↓       ↓     ↓   ↓
        23      104   150 201

K3 now maps to N4 instead of N3.
Only keys in range (104, 150] move.
```

**Impact**: Only `1/N` of keys move when adding a node to an N-node cluster. Minimal disruption.

### Virtual Nodes: Load Balancing and Heterogeneity

**Problem**: With physical nodes on the ring, distribution is uneven. Some nodes get more keys than others.

**Solution**: Each physical node is assigned multiple **virtual nodes** (vnodes) at random positions on the ring.

```
Physical nodes: 3 (N1, N2, N3)
Virtual nodes per physical node: 4

Ring:
  V1a(→N1)  V2a(→N2)  V3a(→N3)  V1b(→N1)  V2b(→N2)  ...
     ↓         ↓         ↓         ↓         ↓
    10        35        60        90        115       ...
```

**Benefits**:

1. **Even distribution**: More vnodes → smoother load distribution
2. **Heterogeneity**: Powerful nodes get more vnodes than weak nodes
3. **Faster rebalancing**: When a node fails, its vnodes are distributed across many other nodes

**Typical configuration**: 128-256 vnodes per physical node.

### Replication and Quorum

Each key is replicated to **N** nodes (typically N=3):

```
Key K hashes to position 100 on ring.

Coordinator: First node clockwise (V1b → N1)
Replica 1: Second node clockwise (V2b → N2)
Replica 2: Third node clockwise (V3a → N3)

Preference list for K: [N1, N2, N3]
```

**Quorum parameters** (R, W, N):
- **N**: Number of replicas
- **W**: Write quorum (must wait for W replicas to acknowledge)
- **R**: Read quorum (must wait for R replicas to respond)

**Consistency guarantee**: If R + W > N, reads see latest write.

**Proof**:
```
N = 3, W = 2, R = 2

Write succeeds → At least 2 replicas have latest version
Read queries 2 replicas → At least 1 of them has latest version
```

**Tunable trade-offs**:

| R | W | Consistency | Latency | Availability |
|---|---|-------------|---------|--------------|
| 1 | 1 | Weak | Low | High |
| 2 | 2 | Strong (if R+W>N) | Medium | Medium |
| 3 | 1 | Weak | Medium | High |
| 1 | 3 | Strong for writes | High for writes | Lower |

Amazon typically uses (N=3, R=2, W=2) for critical data like shopping carts.

### Write Path: Sloppy Quorum and Hinted Handoff

**Normal write flow**:

```
Client → Coordinator (first node in preference list)
Coordinator → Replicates to N nodes in preference list
Coordinator ← Wait for W acknowledgments
Coordinator → Return success to client
```

**When nodes fail: Sloppy Quorum**

If a node in the preference list is down:

```
Preference list: [N1, N2, N3]
N2 is down.

Coordinator (N1) writes to:
- N1 (self)
- N3 (second available)
- N4 (next node on ring, temporary substitute)
```

This is a **sloppy quorum**: We wrote to W nodes, but not necessarily the "right" nodes. N4 is a temporary stand-in for N2.

**Hinted handoff**: N4 stores the write with a hint: "This belongs to N2, deliver when N2 recovers."

```
N4's storage:
  Key=K, Value=V, Hint="intended for N2"

When N2 recovers:
  N4 → N2: "Here's data that was written while you were down"
  N2 applies the data
  N4 deletes the hint
```

**The benefit**: High availability. Even if nodes fail, writes succeed as long as W nodes in the cluster are reachable.

**The cost**: Temporary inconsistency. Reads might miss data stored on hinted nodes.

### Read Path: Read Repair and Merkle Trees

**Normal read flow**:

```
Client → Coordinator
Coordinator → Query R replicas in preference list
Coordinator ← Receive R responses
Coordinator → Return latest version(s) to client
```

**Detecting staleness**:

Coordinator compares vector clocks from R replicas:

```
Replica 1: Version A with VC={N1:5, N2:3, N3:2}
Replica 2: Version A with VC={N1:5, N2:3, N3:2}  (same)
Replica 3: Version B with VC={N1:4, N2:3, N3:2}  (older)
```

Version A happened after Version B (N1:5 > N1:4, others equal).

**Read repair**:

Coordinator immediately updates Replica 3 with Version A:

```
Coordinator → Replica 3: "Your version is stale, here's the latest"
```

This is **synchronous read repair**: Happens during the read request.

**Merkle trees for background repair**:

Replicas periodically compare their data using **Merkle trees** (hash trees):

```
                    Root Hash
                   /         \
            Hash(A,B)         Hash(C,D)
             /    \            /     \
        Hash(A) Hash(B)   Hash(C) Hash(D)
          /       |         |        \
        Data A  Data B    Data C    Data D
```

To compare two replicas:

```
1. Exchange root hashes
   - If same → Data is identical, done
   - If different → Descend into children

2. Exchange child hashes
   - Identify which subtree differs

3. Continue recursively until leaf level
4. Transfer only the differing keys
```

**Efficiency**: For 1 million keys, Merkle tree has ~20 levels. Can identify differences with ~20 hash comparisons instead of 1 million.

**Anti-entropy**: Replicas use Merkle trees to synchronize in the background, ensuring eventual consistency even if read repair misses some stale data.

---

## Part 3: PRODUCTION NUMBERS AND REAL-WORLD USE

### Dynamo at Amazon Scale

**Deployment (circa 2007 paper)**:

- Nodes: Commodity hardware (cheap, failure-prone)
- Scale: 100s of nodes per Dynamo ring
- Data: Terabytes per ring
- Request rate: 10,000s of requests per second
- Services: 100+ internal Amazon services use Dynamo

**Services using Dynamo**:

1. **Shopping cart**: Original use case, highest availability requirement
2. **Session management**: Store user sessions, must be always available
3. **Product catalog**: Read-heavy, can tolerate staleness
4. **Customer preferences**: User settings, infrequently updated
5. **Sales rank**: Computed rankings, eventually consistent

**Latency numbers (99.9th percentile)**:

| Operation | Target | Actual (median node) | Actual (99.9th node) |
|-----------|--------|---------------------|---------------------|
| Read | <300ms | 12ms | 198ms |
| Write | <300ms | 15ms | 217ms |

**Why 99.9th percentile matters**:

Amazon's philosophy: Optimize for the slowest 0.1% of requests, because:
- High-value customers often generate more requests
- Slow requests compound (user retries, timeout cascades)
- 99.9th is what user experiences during peak load

### Availability: 99.9995% Over Peak Holiday Season

**2006 holiday season (before Dynamo)**:

- Multiple outages due to database unavailability
- Lost revenue during Black Friday weekend
- Customer complaints about cart freezing

**2007 holiday season (after Dynamo)**:

- Availability: 99.9995% (1.5 minutes downtime per year)
- Zero customer-visible cart failures
- Handled 2x traffic growth with same infrastructure

**Key availability wins**:

1. **No single point of failure**: Every node can handle any key
2. **Graceful degradation**: Lost nodes reduce capacity, not availability
3. **Hinted handoff**: Temporary failures don't block writes
4. **Background repair**: System self-heals automatically

### Conflict Resolution: Application-Specific Strategies

**Shopping cart: Union merge**

```python
def merge_shopping_carts(cart1, cart2):
    # Merge is simple: Union of items
    merged = cart1.items | cart2.items  # Set union
    return merged
```

**Session state: Last-write-wins (with caution)**

```python
def merge_sessions(session1, session2):
    # For session, last-write-wins is acceptable
    # Use timestamp from vector clock's wall time
    if session1.wall_time > session2.wall_time:
        return session1
    else:
        return session2
```

**Counter: Addition**

```python
def merge_counters(counter1, counter2):
    # For counters, sum the values
    # (More sophisticated: Use PN-Counter CRDT)
    return counter1.value + counter2.value
```

**Best practices**:

1. **Design for idempotency**: Operations should be safe to apply multiple times
2. **Use CRDTs**: Conflict-free Replicated Data Types have built-in merge semantics
3. **Last-write-wins only when safe**: Risk losing data if clocks are skewed
4. **Let application decide**: Dynamo provides siblings, application knows semantics

### Failure Detection: Gossip Protocol

Dynamo uses a **gossip protocol** for membership and failure detection:

**How gossip works**:

```python
class GossipProtocol:
    def __init__(self):
        self.membership = {}  # node_id → (status, heartbeat, timestamp)

    def gossip_round(self):
        # Every second, pick random node and exchange membership info
        peer = random.choice(self.known_nodes)
        my_view = self.membership.copy()
        peer_view = peer.get_membership()

        # Merge views (take higher heartbeat for each node)
        for node, (status, heartbeat, timestamp) in peer_view.items():
            if node not in my_view:
                my_view[node] = (status, heartbeat, timestamp)
            elif heartbeat > my_view[node][1]:
                my_view[node] = (status, heartbeat, timestamp)

        self.membership = my_view

    def detect_failures(self):
        current_time = time.time()
        for node, (status, heartbeat, timestamp) in self.membership.items():
            if current_time - timestamp > 10:  # No update in 10 seconds
                self.membership[node] = ('suspected', heartbeat, timestamp)
```

**Properties**:

- **Eventually consistent**: All nodes converge to same membership view
- **Decentralized**: No single coordinator
- **Scales**: O(log N) rounds to propagate information to N nodes
- **Resilient**: Tolerates arbitrary node failures

**False positives**: Network delays can cause temporary suspicion. Gossip corrects when node responds again.

---

## Part 4: MASTERY (Third Pass)—Deep Technical Insights

### Vector Clock Size Problem

**Issue**: Vector clocks grow with number of nodes that touched the data.

```
Version 1: {N1:1}
Version 2: {N1:1, N2:1}  (updated by N2)
Version 3: {N1:1, N2:1, N3:1}  (updated by N3)
...
Version 100: {N1:1, N2:1, N3:1, ..., N100:1}  (touched by 100 nodes)
```

For a large cluster (1000s of nodes), vector clocks can become huge.

**Dynamo's solution: Timestamp pruning**

Each entry in vector clock has a timestamp:

```python
vector_clock = {
    'N1': (counter=1, timestamp=1633027200),
    'N2': (counter=1, timestamp=1633027205),
    'N3': (counter=1, timestamp=1633027210)
}
```

If vector clock exceeds threshold (e.g., 10 entries), prune the oldest:

```python
if len(vector_clock) > 10:
    oldest_node = min(vector_clock.items(), key=lambda x: x[1].timestamp)
    del vector_clock[oldest_node]
```

**Trade-off**: May lose causality information, leading to false conflicts. But in practice, most keys are touched by few nodes. For heavily-accessed keys, false conflicts are rare and merging is cheap.

**Alternative: Dotted Version Vectors (DVV)**

More recent approach used by Riak:

```python
# Instead of per-node counters, track per-operation dots
dvv = {
    'N1': [(1, value_a), (5, value_c)],  # Operations 1 and 5 by N1
    'N2': [(2, value_b)]  # Operation 2 by N2
}
```

DVVs are more space-efficient and provide better causality tracking.

### CAP Theorem in Practice: Dynamo's Position

Dynamo demonstrates the **AP choice** in CAP:

**During network partition**:

```
Cluster split into two groups:
Group A: [N1, N2]
Group B: [N3, N4, N5]

Client writes key K (preference list: N1, N2, N3):
- Write succeeds in Group A (N1, N2 ← sloppy quorum)
- Write succeeds in Group B (N3, N4 with hint ← sloppy quorum)

Result: Both groups accepted the write with different values.
When partition heals, vector clocks show conflict.
```

**Consistency is sacrificed**: Different clients reading from different groups see different values.

**Availability is preserved**: All clients can read and write regardless of partition.

**Eventual consistency**: When partition heals, Merkle trees and read repair converge all replicas.

**The trade-off is explicit**: Dynamo chose availability because for shopping carts, being down is worse than being briefly inconsistent.

### PACELC Framework: Dynamo's Full Profile

PACELC extends CAP to consider latency:

- **During Partition**: Choose Availability (A) over Consistency (C)
- **Else (normal operation)**: Choose Latency (L) over Consistency (C)

Dynamo is **PA/EL**: Availability during partitions, Low latency during normal operation.

**Evidence**:

1. **Sloppy quorum**: Prioritizes availability (writes succeed even if "correct" nodes are down)
2. **Async replication**: After W replicas ack, remaining replicas updated asynchronously (low latency, eventual consistency)
3. **Read from any replica**: R < N means some replicas might be stale (low latency, risk of stale reads)

### Implementing Dynamo: Open Source Variants

**Cassandra** (Facebook → Apache):
- Dynamo's architecture + BigTable's data model
- Adds CQL (SQL-like query language)
- More emphasis on read optimization (bloom filters, compaction)

**Riak** (Basho):
- Closest to original Dynamo design
- Uses Dotted Version Vectors (DVV)
- Strong focus on operational simplicity

**Voldemort** (LinkedIn):
- Key-value store with pluggable storage
- Used for read-heavy workloads (caching, product catalog)

**Comparison**:

| Feature | Dynamo | Cassandra | Riak |
|---------|--------|-----------|------|
| Data model | Key-value | Wide column | Key-value |
| Vector clocks | Yes (pruned) | Version numbers | DVV |
| Conflict resolution | Application | Last-write-wins | Application/CRDTs |
| Query language | None | CQL (SQL-like) | None |
| Secondary indexes | No | Yes | Yes |

### When NOT to Use Dynamo-Style Databases

**Poor fit scenarios**:

1. **Need strong consistency**: Financial transactions, inventory management
   - Dynamo can have conflicts, requires application resolution
   - Better: Spanner, CockroachDB, or traditional RDBMS

2. **Complex queries**: Joins, aggregations, filtering
   - Dynamo only supports key-value lookups
   - Better: PostgreSQL, MySQL, or analytical databases

3. **Small scale**: < 10 nodes
   - Dynamo's complexity not justified
   - Better: Managed PostgreSQL/MySQL with replication

4. **Can't handle conflicts**: Legacy applications expecting ACID
   - Rewriting for eventual consistency is expensive
   - Better: Stick with traditional database

**Good fit scenarios**:

1. **High availability critical**: Every second of downtime = lost money
2. **Simple access patterns**: Get/put by key, list keys
3. **Can tolerate staleness**: Shopping carts, sessions, caches
4. **Global distribution**: Need low latency worldwide
5. **Write-heavy**: Traditional DBs bottleneck on write contention

---

## Key Takeaways

### The Core Innovations

1. **Consistent hashing**: Decentralized data placement, minimal rebalancing
2. **Vector clocks**: Causality tracking without coordination
3. **Quorum with sloppy quorum**: Tunable consistency, high availability
4. **Hinted handoff**: Graceful degradation during failures
5. **Merkle trees**: Efficient background synchronization
6. **Application-driven conflict resolution**: Database detects, application resolves

### The Trade-Offs

**What you gain**:
- 99.99%+ availability
- Low latency (<10ms typical, <300ms 99.9th)
- Horizontal scalability (add nodes, get more capacity)
- Graceful degradation (no single point of failure)

**What you sacrifice**:
- Strong consistency (eventual consistency only)
- Complex queries (key-value only)
- Guaranteed uniqueness (application must handle conflicts)
- Transaction support (single-key only)

### The Evidence Lens on Dynamo

Dynamo demonstrates **optimistic evidence generation**:

- **Causality evidence**: Vector clocks prove ordering between versions
- **Availability evidence**: Sloppy quorum proves W nodes accepted write
- **Durability evidence**: Hinted handoff preserves writes during failures
- **Consistency evidence**: Merkle trees prove replicas converged

When evidence conflicts (concurrent versions), Dynamo **preserves all evidence** (siblings) and delegates resolution to the application. This is the opposite of Spanner's approach (wait until evidence is unambiguous).

**The pattern**: In AP systems, generate evidence optimistically, accept conflicts, repair divergence in background.

---

## Next Steps

We've seen how Amazon chose availability over consistency and built a system that never goes down. Next, we'll explore **Netflix's Chaos Engineering**, where the philosophy is: "Don't just handle failures—actively cause them to ensure resilience."

**Continue to**: [Netflix: Chaos Engineering Pioneer](./netflix-chaos.md)

**Related chapters**:
- [Chapter 2: Time and Order](../chapter-02/index.md) - Vector clocks and causality
- [Chapter 4: Replication](../chapter-06/index.md) - Quorum systems and consistency
- [Chapter 5: Consistency Models](../chapter-05/index.md) - Eventual consistency

---

**References**:
- DeCandia et al., "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007)
- Vogels, "Eventually Consistent" (ACM Queue 2008)
- Lakshman & Malik, "Cassandra: A Decentralized Structured Storage System" (2010)

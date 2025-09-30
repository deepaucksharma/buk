# Chapter 4: Replication - The Path to Availability

## Introduction: How Systems Cheat Death

Replication is how distributed systems cheat death—by refusing to have a single point of failure.

When a hard drive fails, when a datacenter loses power, when a network cable is cut, when cosmic rays flip bits in memory—systems survive because data exists in multiple places. But replication isn't free. Every copy introduces a question: **how do we keep them synchronized?**

This question has haunted distributed systems for decades. The answer reveals a fundamental trade-off that shapes every design decision: **consistency versus availability versus performance**. You cannot have perfect consistency, perfect availability, and perfect performance simultaneously. Physics and mathematics force you to choose.

### The Replication Dilemma

Consider a bank account with $1,000, replicated across three servers:

**Write operation**: Transfer $500 to another account.

**Synchronous replication** (strong consistency):
- Write to all three servers before confirming
- If one server is slow or down, the entire write is blocked
- Latency: P99 = 200ms (waiting for slowest server)
- Availability: 99.9% × 99.9% × 99.9% = 99.7% (all must respond)
- Consistency: Perfect (all replicas always agree)

**Asynchronous replication** (eventual consistency):
- Write to primary server, confirm immediately
- Replicate to others in the background
- Latency: P99 = 10ms (single-server write)
- Availability: 99.9% (only primary must respond)
- Consistency: Eventually consistent (replicas lag behind, temporary disagreement)

**The trade-off is inescapable.** Fast, available, consistent—pick two.

This isn't a theoretical exercise. Every database, every cache, every distributed system makes this trade-off thousands of times per second. Understanding replication means understanding where to pay the cost and how to degrade gracefully when you can't afford it.

### Why Replication Matters

Replication serves three fundamental purposes:

**1. Durability**: Data survives failures
- Single disk fails: MTBF (Mean Time Between Failures) ≈ 4-5 years
- Three replicas fail simultaneously: MTBF ≈ several thousand years
- Replication converts unreliable components into reliable systems

**2. Availability**: System survives node failures
- Single server: 99.9% availability = 8.76 hours downtime/year
- Three replicas with failover: 99.99% availability = 52.6 minutes downtime/year
- Each additional nine costs exponentially more but enables always-on systems

**3. Performance**: Scale reads, reduce latency
- Reads can be served from multiple replicas (horizontal scaling)
- Geo-replication places data near users (Tokyo users read from Tokyo replica, 10ms vs 200ms from US)
- Write performance is harder (more replicas = more coordination)

**The tension**: More replicas increase durability and availability but make consistency harder and writes slower.

### Real-World Consequences

**AWS DynamoDB outage (2015)**:
- Network partition split cluster into multiple groups
- Nodes in each group thought they were the majority
- Multiple "leaders" accepted writes (split-brain)
- Conflicting writes to the same keys
- Recovery took hours of manual reconciliation
- Cost: Millions in lost transactions
- **Root cause**: Eventual consistency without proper conflict resolution

**Facebook's Memcache inconsistency (2012)**:
- Write to database, invalidate cache entry
- Race condition: Read from cache before invalidation propagates
- Stale data served to millions of users
- Users saw old posts, incorrect friend counts
- **Solution**: Leases and versioning (Chapter 2 techniques applied to caching)

**GitHub outage (2018)**:
- Network partition separated US East from US West datacenters
- Both sides continued serving writes (AP choice)
- 40 minutes of divergent state
- Manual reconciliation required
- Some data loss (conflicting writes, last-write-wins)
- **Lesson**: AP systems must plan for partition recovery

### What This Chapter Covers

**Part 1: Intuition (First Pass)**
- The Library Book Problem: Why replication is hard
- Single copy vs multiple copies: The coordination challenge
- Real-world replication patterns you see daily

**Part 2: Understanding (Second Pass)**
- **Primary-Backup**: Single leader, followers (MySQL, PostgreSQL, MongoDB)
- **Multi-Master**: Multiple concurrent writers (Cassandra, DynamoDB, Riak)
- **Quorum-Based**: Configurable consistency (Cassandra, DynamoDB with tunable consistency)
- **State Machine Replication**: Log-based replication (Kafka, Raft, Paxos)
- **Geo-Replication**: Cross-region challenges (Spanner, Aurora, Cosmos DB)

**Part 3: Mastery (Third Pass)**
- **Evidence framework**: Replication as evidence generation and validation
- **Invariant preservation**: AVAILABILITY, DURABILITY, CONSISTENCY, MONOTONICITY
- **Mode matrix**: Target, Degraded, Floor, Recovery modes
- **Production patterns**: Monitoring, conflict resolution, case studies

### The Evidence-Based View

Reframe replication through evidence:

**Replication is the process of generating, propagating, and validating evidence across multiple nodes to preserve data despite failures.**

- **Write acknowledgment**: Evidence that replica received the write
- **Replication offset/position**: Evidence of how current the replica is
- **Version vectors**: Evidence of causality and conflict detection
- **Quorum certificates**: Evidence that sufficient replicas agree

**Evidence lifecycle in replication**:
```
Generate (write) →
Propagate (replicate) →
Validate (version check) →
Active (serve reads) →
Expire (detect staleness) →
Refresh (anti-entropy/repair)
```

**Evidence freshness determines guarantees**:
- **Fresh(φ)**: All replicas synchronized (strong consistency)
- **BS(δ)**: Replicas within δ milliseconds (bounded staleness)
- **EO (Eventually)**: Replicas converge eventually (eventual consistency)

### The Conservation Principle

Throughout this chapter, observe the **conservation of certainty**: You cannot create consistency from nothing—synchronization requires communication, which requires time.

**The replication certainty equation**:
```
Consistency + Availability + Latency = Constant

If you increase consistency (synchronous replication):
  → Latency increases (wait for acknowledgments)
  → Availability decreases (more nodes must respond)

If you increase availability (asynchronous replication):
  → Consistency decreases (replicas diverge)
  → Latency decreases (don't wait)
```

### Chapter Structure

**First pass (Intuition)**: Experience the problem through stories
- The library with photocopied books
- Bank accounts that exist in multiple places
- Shopping carts that merge mysteriously

**Second pass (Understanding)**: Build mental models of replication strategies
- Primary-backup (leader-follower, master-slave)
- Multi-master (peer-to-peer, conflict resolution)
- Quorum replication (tunable consistency)
- Chain replication (strong consistency with performance)
- CRDTs (conflict-free replicated data types)

**Third pass (Mastery)**: Compose and operate replication systems
- Evidence-based replication framework
- Guarantee vectors for different strategies
- Mode transitions during failures
- Production case studies and patterns

Let's begin with the Library Book Problem—a story that makes replication's challenges visceral.

---

## Part 1: INTUITION (First Pass) — The Felt Need

### The Library Book Problem

A university library has one copy of a popular textbook. Hundreds of students need it. The library's solution: make photocopies.

**Single Copy System**:
- One authoritative book
- Students must come to library to read it
- Only one student can read at a time
- If the book is damaged, all knowledge is lost
- **High consistency** (everyone sees the same version)
- **Low availability** (only one reader at a time)
- **Poor performance** (contention, travel time)

**Multiple Copy System**:
- Library makes 10 photocopies
- Students can take copies home
- Multiple students read simultaneously
- If one copy is damaged, others survive
- **High availability** (many readers simultaneously)
- **High performance** (no contention, no travel)
- **But now there's a problem...**

**The Update Problem**:

The author publishes an erratum: Page 47 has a critical error, equation should be E=mc² not E=mc³.

How do you update all 10 copies?

**Synchronous update** (bring all copies back):
- Recall all copies to the library
- Update each copy with the erratum
- Re-distribute corrected copies
- **Consistency**: All copies corrected before students read them
- **Availability**: Students cannot read during update (downtime)
- **Performance**: Expensive coordination overhead

**Asynchronous update** (mail erratum to students):
- Mail correction notice to all students
- Students apply the correction when they receive it
- **Availability**: Students keep reading (no downtime)
- **Performance**: No coordination overhead
- **Consistency**: Students read different versions (some have correction, others don't)

**What if a student never receives the erratum?**
- They have permanently stale data
- They might fail the exam due to incorrect equation
- **This is the replication problem in miniature**

### Real-World Replication: Bank Account Balance

Your bank account balance: $1,000. Three replicas across three datacenters (for disaster recovery).

**Write operation**: You buy coffee for $5.

**Scenario 1: Synchronous replication**
```
T=0:    Coffee shop charges your card ($5)
T=0:    Bank's primary database: $1,000 → $995
T=0:    Replicate to Datacenter 2... (waiting)
T=50ms: Datacenter 2 acknowledges
T=0:    Replicate to Datacenter 3... (waiting)
T=120ms: Datacenter 3 acknowledges (slow network)
T=120ms: Confirm transaction to coffee shop
```
**Latency**: 120ms (P99 could be 500ms+ if one replica is slow)
**Consistency**: All replicas show $995 before confirmation
**Availability**: If Datacenter 3 is down, transaction fails (cannot confirm)

**Scenario 2: Asynchronous replication**
```
T=0:    Coffee shop charges your card ($5)
T=0:    Bank's primary database: $1,000 → $995
T=0:    Confirm transaction to coffee shop (immediately)
T=0:    Start replication to Datacenters 2 and 3 (background)
T=50ms: Datacenter 2 updated ($995)
T=120ms: Datacenter 3 updated ($995)
```
**Latency**: <1ms (single database write)
**Availability**: Datacenter 3 down? No problem, still confirm
**Consistency**: Between T=0 and T=120ms, replicas show different balances

**The race condition**:
```
T=0:   You buy coffee, primary: $1,000 → $995
T=0:   Confirm immediately
T=1ms: Your friend checks your balance from Datacenter 2 (still $1,000)
       They think: "You have $1,000, you can lend me $100"
T=50ms: Datacenter 2 updated to $995
```
**Your friend saw stale data.** This is eventual consistency in action.

**Real incident**: A bank deployed asynchronous replication for ATM balance checks (to improve response time). A customer withdrew $500 from ATM A (connected to Datacenter 1). Before replication to Datacenter 2, the customer withdrew $500 from ATM B (connected to Datacenter 2). Both withdrawals succeeded (each saw $1,000 balance). The account went negative. The bank had to implement compensating transactions and stricter consistency for balance checks.

### The Shopping Cart Mystery

You're shopping on an e-commerce site. You add three items to your cart:
1. Book A ($20)
2. Book B ($30)
3. Laptop ($1,000)

Your cart is replicated across multiple datacenters (for low latency—you read from the nearest datacenter).

**Network partition**: The datacenter serving you gets disconnected from others.

**You remove the laptop** (decide it's too expensive):
- Your datacenter (US-West) updates cart: [Book A, Book B]
- Cannot replicate to US-East (partitioned)

**Meanwhile, you open another browser tab** (routed to US-East):
- US-East still has old cart: [Book A, Book B, Laptop]
- You see the laptop still in your cart

**You remove Book B** (realize you already own it):
- US-East updates cart: [Book A, Laptop]
- Cannot replicate to US-West (partitioned)

**Network partition heals**:
- US-West has: [Book A, Book B] (removed Laptop)
- US-East has: [Book A, Laptop] (removed Book B)
- **Conflict**: Two divergent carts

**How do you merge them?**

**Naive approach: Last-write-wins**:
- US-East update was 5 seconds after US-West
- Use US-East's version: [Book A, Laptop]
- **Problem**: You actually removed the Laptop, but it's back
- Checkout with Laptop, get a surprise charge

**Better approach: Union (add everything)**:
- Merge: [Book A, Book B, Laptop]
- **Problem**: Items you removed are back
- But at least you can remove them again (better than surprise charges)

**Best approach: CRDT (Conflict-free Replicated Data Type)**:
- Track both additions and removals explicitly
- Added: {Book A, Book B, Laptop}
- Removed: {Laptop, Book B}
- Final: {Book A} (additions minus removals)
- **Correct result**: Only Book A remains

**This is Amazon's approach**: Shopping carts use a specialized CRDT. You might occasionally see removed items reappear (eventual consistency), but explicit removals eventually win.

### Social Media Post Replication

You post on social media: "I love distributed systems!"

Your post is replicated to 10 datacenters worldwide (so users everywhere see low latency).

**Replication pattern**:
```
T=0:    You post (write to US-West)
T=0:    Acknowledge immediately (eventual consistency)
T=10ms: Replicate to US-East
T=50ms: Replicate to Europe
T=100ms: Replicate to Asia
T=150ms: Replicate to Australia
```

**Your friend in Australia**:
```
T=50ms: Checks feed, doesn't see your post yet (replica hasn't received it)
T=60ms: Refreshes, still doesn't see it
T=160ms: Refreshes, sees your post
```
**They wonder: "Why did the post appear late? Server lag?"**

No—it's replication lag. The post existed (you saw it immediately), but evidence hadn't propagated to Australia yet.

**The reply problem**:
```
T=0:    You post: "I love distributed systems!"
T=50ms: Friend in Europe sees post, replies: "Me too!"
T=100ms: Friend in Asia sees reply before seeing original post
```
**Asia user sees**:
```
> Me too!
  (No context—what are they replying to?)
```

**Causality violation**. Replies should never appear before original posts. But with asynchronous replication and insufficient causal tracking, it happens.

**Facebook's solution**: Use version vectors and causality tracking (Chapter 2). If a reply references a post version that a user hasn't seen yet, either:
- Wait to display reply until original post arrives (consistency, but slower)
- Display reply with placeholder "Loading referenced post..." (availability, but awkward)

### Why Replication Is Hard

These stories reveal the core challenges:

**1. Coordination has latency cost**
- Synchronous replication waits for all replicas (slow)
- Asynchronous replication proceeds without waiting (fast but inconsistent)
- The speed of light imposes minimum latency (80ms+ cross-continent)

**2. Network partitions happen**
- Replicas become temporarily disconnected
- Must choose: stop serving (CP) or diverge (AP)
- Divergence requires reconciliation later (conflict resolution)

**3. Conflicting updates are inevitable**
- Multiple clients write to different replicas simultaneously
- Without coordination, replicas accept incompatible writes
- Need conflict detection (versions) and resolution (merge strategy)

**4. Causality must be preserved**
- Some operations depend on others (reply depends on original post)
- Timestamps alone are insufficient (clock skew, replication lag)
- Need causal tracking (vector clocks, happened-before relationships)

**5. Failure modes multiply**
- Single replica: One failure mode (node crashes)
- Three replicas: Multiple failure modes (one crashes, two crash, network partition, slow replica, byzantine replica)
- Each failure mode needs explicit handling

**The replication problem is inescapable**: You cannot have multiple copies of data that are always synchronized, always available, and always consistent. Pick your trade-offs.

---

## Part 2: UNDERSTANDING (Second Pass) — Building Mental Models

### Primary-Backup Replication

The most common pattern: one primary (leader, master) accepts writes, replicates to backups (followers, replicas, secondaries).

#### Synchronous Replication

**Protocol**:
1. Client sends write to primary
2. Primary writes locally
3. Primary sends write to all backups
4. Backups write locally, acknowledge
5. Primary waits for all acknowledgments
6. Primary acknowledges client

**Properties**:
- **Strong consistency**: All replicas have identical data at all times
- **Durability**: Write survives F failures (with F+1 replicas)
- **High latency**: Wait for slowest replica (P99 latency = P99 of slowest replica)
- **Low availability**: If any replica is down, writes block (unless degraded mode)

**Evidence**:
- Write acknowledgment from each replica is evidence of durability
- All acknowledgments required before client acknowledgment
- **Guarantee vector**: `⟨Global, SS, SER, Fresh(φ), Idem, Auth⟩`

**When to use**:
- Financial transactions (cannot tolerate data loss)
- Inventory management (overselling is unacceptable)
- Regulatory compliance (audit logs must be durable)

**Example: PostgreSQL synchronous replication**:
```sql
-- Configure synchronous replication to 2 replicas
synchronous_commit = on
synchronous_standby_names = 'replica1,replica2'
```
- Write to primary
- Primary waits for both replicas to acknowledge
- If replica1 or replica2 is down, writes block (unless you change config)

**Mode transitions**:
- **Target mode**: All replicas healthy, writes succeed within SLA
- **Degraded mode**: One replica slow/down, increase timeout or reduce replicas
- **Floor mode**: Only primary available, disable synchronous (switch to async)
- **Recovery mode**: Backup recovering from primary, catching up

#### Asynchronous Replication

**Protocol**:
1. Client sends write to primary
2. Primary writes locally
3. Primary acknowledges client immediately
4. Primary sends write to backups (background)
5. Backups apply write when they receive it

**Properties**:
- **Eventual consistency**: Replicas lag behind primary by replication lag δ
- **Low latency**: Client doesn't wait for replicas (P50 latency < 10ms)
- **High availability**: Primary can serve writes even if all replicas are down
- **Potential data loss**: If primary fails before replication, recent writes lost

**Evidence**:
- Write acknowledgment from primary only
- Replica acknowledgments are background evidence (not required for confirmation)
- **Guarantee vector**: `⟨Global, EC, RA, BS(δ), Idem, Auth⟩`
- Replication lag δ is the staleness bound

**When to use**:
- Social media (occasional stale reads acceptable)
- Caching (cache misses are tolerable)
- Analytics (approximate results acceptable)
- High-throughput writes (cannot afford synchronous overhead)

**Example: MySQL asynchronous replication**:
```sql
-- Enable replication (default is async)
CHANGE MASTER TO MASTER_HOST='primary.db', ...;
START SLAVE;
```
- Primary commits immediately
- Replicas pull binlog and apply changes
- Replication lag: typically 10-100ms, can spike to seconds during load

**The data loss window**:
```
T=0:    Client writes X=10 to primary
T=0:    Primary acknowledges (X=10 persisted locally)
T=5ms:  Primary starts sending binlog to replica
T=10ms: Primary crashes (hardware failure)
T=10ms: Replica is promoted to new primary (X=9, doesn't have X=10 yet)
```
**Result**: Write X=10 is lost. Client thinks it succeeded (got acknowledgment), but data is gone.

**Real incident**: GitHub (2012) lost some commit comments during a primary failure. Asynchronous replication lag was 3 seconds. When primary crashed, the newly promoted replica was missing those 3 seconds of writes. Data loss was permanent. GitHub now uses semi-synchronous replication.

#### Semi-Synchronous Replication

**Compromise**: Wait for at least one backup to acknowledge (not all).

**Protocol**:
1. Client sends write to primary
2. Primary writes locally
3. Primary sends write to all backups
4. Primary waits for at least one backup to acknowledge
5. Primary acknowledges client
6. Other backups acknowledge asynchronously

**Properties**:
- **Bounded staleness**: At least one replica is synchronous (durable across failures)
- **Medium latency**: Wait for fastest replica (not slowest)
- **Medium availability**: If primary + one replica are up, writes succeed
- **Reduced data loss**: Write survives primary failure (one replica is up-to-date)

**Evidence**:
- Acknowledgment from primary + at least one replica
- **Guarantee vector**: `⟨Global, Causal, SI, Fresh(φ) for one replica, Idem, Auth⟩`

**When to use**:
- Balance between performance and durability
- Cannot afford full synchronous latency, cannot tolerate data loss
- Most production databases default to this

**Example: MySQL semi-synchronous replication**:
```sql
-- Enable semi-sync on primary
INSTALL PLUGIN rpl_semi_sync_master SONAME 'semisync_master.so';
SET GLOBAL rpl_semi_sync_master_enabled = 1;
SET GLOBAL rpl_semi_sync_master_timeout = 10000; -- 10 second timeout

-- Enable semi-sync on replica
INSTALL PLUGIN rpl_semi_sync_slave SONAME 'semisync_slave.so';
SET GLOBAL rpl_semi_sync_slave_enabled = 1;
```
- Primary waits up to 10 seconds for at least one replica
- If timeout, degrades to asynchronous (availability over durability)

**Mode transitions**:
- **Target**: Primary + at least one replica sync
- **Degraded**: Timeout exceeded, switch to async (explicit mode change logged)
- **Recovery**: Replicas catch up, return to semi-sync

#### Chain Replication

**Different topology**: Linear chain instead of star.

**Structure**:
```
Client → Head → Node 2 → Node 3 → Tail → Client
         (writes)                  (reads)
```

**Protocol**:
1. Client sends write to **Head**
2. Head writes locally, forwards to Node 2
3. Node 2 writes locally, forwards to Node 3
4. Node 3 writes locally, forwards to Tail
5. Tail writes locally, **acknowledges to client**
6. Client reads always from **Tail**

**Properties**:
- **Strong consistency**: Tail has all committed writes (linearizable)
- **High throughput**: Writes pipelined through chain
- **Fault tolerance**: If middle node fails, reconnect chain
- **Simple recovery**: New node can join at tail, catch up

**Why it works**:
- Writes propagate sequentially through chain
- Only Tail acknowledges (proof that all nodes have the write)
- Reads from Tail always see all committed writes (no read-your-writes issues)

**Evidence**:
- Acknowledgment from Tail is proof that entire chain has the write
- **Guarantee vector**: `⟨Global, SS, SER, Fresh(φ), Idem, Auth⟩` (strong consistency)

**When to use**:
- Storage systems (CRAQ, Amazon's backup system)
- Strong consistency with good throughput
- Fewer nodes in chain (3-5 nodes typical)

**Advantages over primary-backup**:
- Load distribution: Writes propagate through chain, not all from primary
- Tail serves reads, Head serves writes (separation of concerns)
- Simpler quorum logic (Tail acknowledgment is sufficient)

**Disadvantages**:
- Latency: Sequential propagation (latency = nodes × per-hop latency)
- Head of line blocking: Slow node blocks entire chain
- Limited topology: Only works for linear chains

### Multi-Master Replication

Multiple nodes accept writes concurrently. No single leader.

#### The Conflict Problem

**Setup**: Two replicas (A and B), both accept writes.

**Concurrent writes**:
```
T=0: Client 1 writes X=5 to Replica A
T=0: Client 2 writes X=7 to Replica B
T=10ms: Replicas exchange updates
```

**Result**: Conflict. Both replicas now have two conflicting values for X.

**Replica A's perspective**:
- Local write: X=5 (T=0)
- Received from B: X=7 (T=10ms)
- **Which value to keep?**

**Replica B's perspective**:
- Local write: X=7 (T=0)
- Received from A: X=5 (T=10ms)
- **Which value to keep?**

**If they choose differently, replicas diverge permanently.** Need deterministic conflict resolution.

#### Last-Write-Wins (LWW)

**Strategy**: Use timestamps to determine winner. Highest timestamp wins.

**Protocol**:
```
Each write has timestamp: (value, timestamp, node_id)
When receiving conflicting write:
  if remote.timestamp > local.timestamp:
    keep remote.value
  elif remote.timestamp == local.timestamp:
    keep remote.value if remote.node_id > local.node_id (tie-breaker)
  else:
    keep local.value
```

**Example**:
```
Replica A: X=(5, T=1000, node=A)
Replica B: X=(7, T=1005, node=B)

Both replicas converge to: X=(7, T=1005, node=B)
```

**Properties**:
- **Convergence**: All replicas eventually agree (eventual consistency)
- **Simple**: Easy to implement and reason about
- **Data loss**: Earlier write is discarded (X=5 is lost forever)
- **Clock dependent**: Requires synchronized clocks (or logical clocks)

**Clock skew problems**:
```
Replica A clock: Actual time T=1000, clock shows T=1100 (100ms fast)
Replica B clock: Actual time T=1000, clock shows T=1000

Client 1 writes X=5 to A (timestamp T=1100)
Client 2 writes X=7 to B (timestamp T=1000) [this actually happened first]

LWW resolves to X=5 (T=1100 > T=1000)
But X=7 actually happened later!
```

**Clock skew causes incorrect conflict resolution.** Last-write-wins becomes "fastest-clock-wins."

**When to use**:
- Lost writes are acceptable (cached data, session state)
- Clocks are well-synchronized (NTP with <10ms accuracy)
- Conflicts are rare (different clients write different keys)

**Examples**:
- Cassandra (default conflict resolution)
- Riak (lww bucket property)
- DynamoDB (timestamp-based or client-provided version)

#### Vector Clocks and Version Vectors

**Problem with timestamps**: Cannot capture causality.

**Vector clocks**: Track causality by maintaining a vector of logical clocks (one per node).

**Structure**:
```
Vector clock: {A: 3, B: 5, C: 2}
Means:
  - Node A has seen 3 events from A
  - Node A has seen 5 events from B
  - Node A has seen 2 events from C
```

**Protocol**:
```
When node A performs write:
  VC_A[A] += 1
  attach VC_A to write

When node A receives write with VC_B:
  VC_A = merge(VC_A, VC_B)  // element-wise max
  VC_A[A] += 1
```

**Conflict detection**:
```
VC1 = {A: 3, B: 5, C: 2}
VC2 = {A: 4, B: 4, C: 3}

Is VC1 < VC2? (VC1 happened-before VC2)
  VC1 ≤ VC2 if VC1[i] ≤ VC2[i] for all i
  No: VC1[B]=5 > VC2[B]=4

Is VC2 < VC1?
  No: VC2[A]=4 > VC1[A]=3

Conclusion: VC1 and VC2 are concurrent (neither happened-before the other)
→ CONFLICT
```

**Example**:
```
Initial: X = 0, VC = {A:0, B:0}

T=0: Client writes X=5 to Replica A
     VC_A = {A:1, B:0}, value = 5

T=0: Client writes X=7 to Replica B (concurrent)
     VC_B = {A:0, B:1}, value = 7

T=10ms: Replicas exchange:
     A receives (X=7, VC={A:0, B:1})
     A detects conflict: VC_A={A:1,B:0} not < {A:0,B:1} and vice versa
     A keeps both values as siblings: [5, 7]

     B receives (X=5, VC={A:1, B:0})
     B detects conflict: same reasoning
     B keeps both values as siblings: [5, 7]
```

**Sibling management**:
- Both values kept (siblings)
- Application must resolve (merge, choose, or ask user)
- Or use CRDT (automatic merge)

**Evidence**:
- Vector clock is evidence of causality
- **Guarantee vector**: `⟨Object, Causal, RA, EO, Idem(K), Auth⟩`

**When to use**:
- Need causal consistency (replies after posts, not before)
- Cannot tolerate data loss (keep all conflicting writes)
- Application can resolve conflicts (merge strategies available)

**Examples**:
- Dynamo-style databases (Riak, Voldemort)
- Distributed caches with causal consistency
- CRDTs (use version vectors internally)

**Downsides**:
- Vector size grows with number of nodes (each node has an entry)
- Pruning is complex (need to track which nodes are dead)
- Siblings can accumulate (need aggressive merge or GC)

#### CRDTs (Conflict-Free Replicated Data Types)

**Big idea**: Design data structures where merging is commutative, associative, and idempotent. Conflicts resolve automatically.

**Mathematical foundation**:
- **Commutativity**: merge(A, B) = merge(B, A) (order doesn't matter)
- **Associativity**: merge(merge(A, B), C) = merge(A, merge(B, C))
- **Idempotency**: merge(A, A) = A (duplicate messages don't break convergence)

**Result**: All replicas converge to the same state, regardless of message order or duplication.

#### CRDT Types

**G-Counter (Grow-only Counter)**:
```
Structure: {A: 5, B: 3, C: 2}  // Each node's contribution
Value: sum = 5 + 3 + 2 = 10

Increment on node A:
  counter[A] += 1
  → {A: 6, B: 3, C: 2}

Merge:
  merge({A: 6, B: 3, C: 2}, {A: 5, B: 4, C: 2})
  = {A: max(6,5), B: max(3,4), C: max(2,2)}
  = {A: 6, B: 4, C: 2}

Value: 6 + 4 + 2 = 12
```

**Properties**:
- Can only increment (no decrement)
- All replicas converge to same value
- No conflicts possible (merge is element-wise max)

**PN-Counter (Positive-Negative Counter)**:
```
Structure: {P: {A:5, B:3}, N: {A:1, B:0}}  // Positive and Negative increments
Value: sum(P) - sum(N) = (5+3) - (1+0) = 7

Increment on A: P[A] += 1
Decrement on A: N[A] += 1

Merge: element-wise max for both P and N
```

**G-Set (Grow-only Set)**:
```
Structure: {a, b, c}

Add element:
  set.add(d)
  → {a, b, c, d}

Merge:
  merge({a, b, c, d}, {a, c, e})
  = {a, b, c, d, e}  (union)
```

**Properties**:
- Can only add elements (no remove)
- Merge is set union (commutative, associative, idempotent)

**OR-Set (Observed-Remove Set)**:
```
Structure: {(a, tag1), (b, tag2), (c, tag3)}  // Elements with unique tags

Add a:
  tag = unique_id()
  set.add((a, tag))

Remove a:
  set.remove_all_tags_for(a)

Merge:
  union of all (element, tag) pairs
  remove elements whose tags were observed as removed
```

**Properties**:
- Can add and remove
- Adds and removes commute (remove only affects observed adds)
- Resolves add-remove conflicts: adds win (element appears if any replica added it without seeing the remove)

**LWW-Register (Last-Write-Wins Register)**:
```
Structure: (value, timestamp)

Write(v):
  register = (v, now())

Merge:
  merge((v1, t1), (v2, t2)):
    if t1 > t2: return (v1, t1)
    else: return (v2, t2)
```

**Properties**:
- Merge picks value with higher timestamp
- Suffers from clock skew issues (like LWW strategy)
- But converges to single value (no siblings)

**MV-Register (Multi-Value Register)**:
```
Structure: {(value1, VC1), (value2, VC2), ...}

Write(v):
  VC = current_vector_clock
  VC[self] += 1
  register = {(v, VC)}

Merge:
  keep all values whose vector clocks are concurrent
  discard values that are dominated (happened-before another value)
```

**Properties**:
- Keeps concurrent writes as siblings (like vector clock approach)
- Application must resolve siblings

#### CRDT Use Cases

**Shopping Cart (OR-Set)**:
```
Add Book A: cart.add((BookA, tag1))
Add Book B: cart.add((BookB, tag2))
Remove Book A: cart.remove(BookA)  // removes tag1

Concurrent operations converge correctly.
```

**Like Counter (PN-Counter)**:
```
User likes post: counter.increment()
User unlikes post: counter.decrement()

All replicas eventually show same like count.
```

**Collaborative Editing (CRDT Text)**:
```
User A inserts "hello" at position 0
User B inserts "world" at position 0 (concurrent)

Both operations commute, final text deterministic.
```

**Evidence**:
- CRDT structure is evidence of convergence (mathematical proof)
- **Guarantee vector**: `⟨Object, EC, RA, EO, Idem, Merge⟩`
- Merge operation is evidence of conflict resolution

**When to use**:
- Need multi-master replication without coordination
- Conflicts are frequent (many concurrent writers)
- Data structure fits CRDT model (counters, sets, maps, text)

**Examples**:
- Riak (CRDT data types)
- Redis (CRDT modules)
- Apple Notes (collaborative editing)
- Figma (multiplayer design tool)

**Downsides**:
- Limited data types (not all data structures have CRDT formulation)
- Metadata overhead (tags, vector clocks)
- Semantic conflicts (CRDT resolves syntactic conflicts but not semantic ones—e.g., two users book the last seat)

### Quorum-Based Replication

**Idea**: Don't require all replicas to respond. Require quorum (majority or configurable).

#### The Quorum Principle

**Configuration**:
- **N**: Number of replicas
- **W**: Write quorum (how many replicas must acknowledge write)
- **R**: Read quorum (how many replicas must respond to read)

**Consistency condition**: **W + R > N**

**Why it works**:
- Write to W replicas
- Read from R replicas
- Since W + R > N, the read quorum overlaps with write quorum
- At least one replica in read quorum has the latest write

**Example**:
```
N = 3, W = 2, R = 2 (W + R = 4 > 3)

Write X=5:
  Send to all 3 replicas
  Wait for 2 acknowledgments (A, B)
  C might not have the write yet

Read X:
  Request from all 3 replicas
  Wait for 2 responses (B, C)
  B has X=5 (latest), C has X=4 (stale)
  Return X=5 (choose value with highest version)
```

**Evidence**:
- Write quorum certificate: W acknowledgments
- Read quorum certificate: R responses
- Overlap ensures at least one response has latest value
- **Guarantee vector**: `⟨Range, Causal, SI, BS(δ), Idem, Auth⟩`

#### Tuning W and R

**Strong consistency (linearizable)**:
- W = N, R = 1: Every write goes to all replicas (synchronous)
- W = 1, R = N: Every read goes to all replicas (expensive reads)
- W = quorum, R = quorum, W+R > N: Balanced

**Eventual consistency**:
- W = 1, R = 1: Fast but may read stale data (W+R = 2 ≤ N)
- Replicas sync in background (anti-entropy)

**Read-heavy workload**:
- W = N, R = 1: Expensive writes, cheap reads
- All replicas always up-to-date, single replica read is safe

**Write-heavy workload**:
- W = 1, R = N: Cheap writes, expensive reads
- Replicas may be stale, must read all to find latest

**Typical configuration**:
- N = 3, W = 2, R = 2 (quorum reads and writes)
- Balance of consistency, performance, availability

#### Sloppy Quorums and Hinted Handoff

**Problem**: What if quorum nodes are unavailable?

**Strict quorum**: Fail the write (CP choice).

**Sloppy quorum**: Accept write at non-designated replica (AP choice).

**Hinted handoff**:
```
Normal: Data X belongs to replicas {A, B, C}

Failure: Replica A is down

Sloppy quorum:
  Write X to replicas {B, C, D} (D is not normal replica for X)
  D stores X with hint: "This belongs to A"
  When A recovers, D hands off X to A, then deletes it

Result: Write succeeds (availability), eventually consistent
```

**Evidence**:
- Hint is evidence of temporary replica responsibility
- Handoff is evidence of recovery completion
- **Guarantee vector**: `⟨Range, EC, RA, EO, Idem, Auth⟩`

**Trade-offs**:
- Availability: Writes succeed even without quorum of designated replicas
- Consistency: Reads may miss data (hinted replica isn't in read quorum)
- Durability: Hint could be lost (hinted replica crashes before handoff)

**When to use**:
- Prefer availability over consistency (AP system)
- Temporary failures are common (network partitions, rolling restarts)
- Eventually consistent is acceptable

**Example: Amazon Dynamo**:
- Prefers availability (shopping carts must always be writable)
- Uses sloppy quorums with hinted handoff
- Eventual consistency with client-side conflict resolution

#### Read Repair

**Problem**: Replicas drift out of sync (missed writes, hinted handoff delays).

**Solution**: Repair during reads.

**Protocol**:
```
Read from R replicas:
  Replicas respond with (value, version)

Choose latest version to return to client

Background repair:
  Identify stale replicas (lower version)
  Send latest value to stale replicas
```

**Example**:
```
Read X from N=3 replicas:
  A: X=10 (version 5)
  B: X=10 (version 5)
  C: X=8  (version 3) [stale]

Return X=10 to client

Background: Send X=10 (version 5) to C to repair
```

**Properties**:
- **Passive repair**: Fixes inconsistencies as reads happen
- **Read amplification**: Every read triggers potential writes (repair)
- **Eventual consistency**: Frequently read data converges quickly, rarely read data stays stale longer

**Evidence**:
- Version numbers are evidence of currency
- Read repair is evidence generation (updating stale replicas)

#### Anti-Entropy

**Problem**: Read repair only fixes frequently read data. Rarely read data stays stale.

**Solution**: Background process compares replicas and repairs differences.

**Merkle Trees**:
```
Efficient way to detect differences:

Tree structure:
                Root hash
               /          \
        Hash(left)      Hash(right)
        /      \          /      \
    Hash(A)  Hash(B)  Hash(C)  Hash(D)
      |        |        |        |
    Data A   Data B   Data C   Data D

Comparison:
  If root hashes match: replicas identical (O(1) comparison)
  If root hashes differ: descend tree to find differences (O(log N) comparisons)
```

**Protocol**:
```
Periodically (e.g., every hour):
  Replica A and Replica B exchange root hashes
  If different:
    Exchange subtree hashes to identify divergent ranges
    Synchronize data in divergent ranges
```

**Example**:
```
Replica A Merkle tree root: 0x7a3b...
Replica B Merkle tree root: 0x8f1c...

Roots differ, descend:
  Left subtree: A=0x123, B=0x123 (match, skip)
  Right subtree: A=0xabc, B=0xdef (differ, descend further)

Identify: Keys [1000-1999] differ
Synchronize: Exchange and merge those keys
```

**Properties**:
- **Active repair**: Fixes inconsistencies proactively
- **Bandwidth efficient**: Only transfer differences
- **CPU intensive**: Computing hashes for all data

**Evidence**:
- Merkle tree is evidence of data state (cryptographic commitment)
- Hash mismatch is evidence of divergence
- **Guarantee vector**: Anti-entropy generates Fresh(φ) evidence from stale replicas

**When to use**:
- Eventually consistent systems with rare reads
- Replicas can diverge for extended periods
- Bandwidth and CPU available for background sync

**Examples**:
- Cassandra (Merkle tree-based repair)
- DynamoDB (background sync processes)
- Bitcoin (block synchronization)

### State Machine Replication

**Principle**: Replicate a deterministic state machine by replicating its input log.

**Key insight**: If all replicas apply the same operations in the same order to the same initial state, they reach the same final state.

**Determinism requirement**:
```
state_machine(state, input) → (new_state, output)

Must be deterministic:
  - Same state + same input → same new_state, same output
  - No randomness, no wall-clock time, no external I/O
```

**Non-deterministic operations must be eliminated**:
- Random number: Leader generates, includes in log entry
- Wall-clock time: Leader reads clock, includes in log entry
- External I/O: Leader performs, includes result in log entry

**Protocol**:
```
1. Client sends command to leader
2. Leader appends command to log
3. Leader replicates log entry to followers (using consensus: Raft, Paxos)
4. Once committed (replicated to quorum), leader applies to state machine
5. Followers apply committed entries in log order
6. All replicas reach same state
```

**Example: Key-Value Store**:
```
Initial state: {}

Log entry 1: SET(X, 5)
  All replicas apply: state[X] = 5
  All replicas now: {X: 5}

Log entry 2: SET(Y, 10)
  All replicas apply: state[Y] = 10
  All replicas now: {X: 5, Y: 10}

Log entry 3: DELETE(X)
  All replicas apply: delete state[X]
  All replicas now: {Y: 10}
```

**Properties**:
- **Strong consistency**: All replicas have identical state (deterministic application)
- **Fault tolerance**: F failures tolerated with 2F+1 replicas (consensus-based)
- **Recoverability**: Crashed replica replays log to catch up

**Evidence**:
- Log entry commit certificate (quorum agreement)
- Log sequence number is evidence of order
- **Guarantee vector**: `⟨Global, SS, SER, Fresh(φ), Idem, Auth⟩`

**Snapshot and Compaction**:
```
Problem: Log grows unbounded

Solution: Periodically snapshot state, discard old log entries

Log: [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
            ↑
        Snapshot at [5], state = S5

Compact: [Snapshot: S5] [6] [7] [8] [9] [10]

New replica recovery:
  1. Install snapshot S5
  2. Replay log entries [6-10]
  3. Caught up
```

**When to use**:
- Need strong consistency (linearizability)
- Operations are deterministic (or can be made so)
- Consensus overhead acceptable

**Examples**:
- etcd (Raft-based state machine replication)
- ZooKeeper (ZAB protocol, log-based replication)
- Kafka (log replication for topics, ISR model)
- Replicated state machines in Raft/Paxos papers

### Geo-Replication

**Challenge**: Replicate across continents (1000s of kilometers apart).

**Additional constraints**:
- **High latency**: 100-300ms cross-continent (speed of light)
- **Network partitions**: Intercontinental links fail (fiber cuts, BGP issues)
- **Regulatory requirements**: Data locality laws (GDPR, data residency)
- **Cost**: Cross-region bandwidth is expensive

#### Cross-Region Latency

**Speed of light limit**:
```
Distance NYC ↔ London: 5,585 km
Speed of light in fiber: ~200,000 km/s (2/3 of c due to refractive index)
Minimum latency: 5,585 / 200,000 = 28ms (one way)

Round trip: 56ms (theoretical minimum)
Actual: 70-80ms (routing overhead, queuing delays)
```

**Implication**: Synchronous replication across regions adds 70-80ms to every write.

**Example**:
```
Single-region write: 10ms
Cross-region synchronous: 10ms + 80ms = 90ms
P99: 200ms+ (network variance)

For 1M writes/day, 90ms latency = 25 hours of cumulative customer waiting time
```

#### Consistency Models for Geo-Replication

**Strong consistency (Google Spanner)**:
```
Protocol: Paxos across regions

Write X=5:
  1. Replicate to all 5 regions
  2. Wait for quorum (3 regions) to acknowledge
  3. Commit

Latency: 100-300ms (depends on regions)

Guarantee: Linearizable (external consistency)
Evidence: TrueTime intervals + Paxos commit certificate
Vector: ⟨Global, SS, SER, Fresh(TT), Idem, Auth⟩
```

**Trade-off**: Consistency over latency. Acceptable for financial transactions, not for social media.

**Regional consistency (AWS Aurora)**:
```
Protocol: Primary in one region, replicas in others

Write X=5:
  1. Write to primary region's quorum (3 of 6 copies within region)
  2. Acknowledge client (10-20ms)
  3. Asynchronously replicate to other regions (100-300ms lag)

Latency: 10-20ms (local quorum)
Consistency: Strong within region, eventual across regions
Evidence: Regional quorum certificate + async replication log
Vector: ⟨Regional, SS within region, EC across regions, BS(δ), Idem, Auth⟩
```

**Trade-off**: Low latency for local writes, eventual consistency globally.

**Eventual consistency (DynamoDB Global Tables)**:
```
Protocol: Multi-master, asynchronous replication

Write X=5 to US-East:
  1. Write to US-East local replicas
  2. Acknowledge client (10ms)
  3. Asynchronously replicate to other regions

Concurrent write Y=7 to EU-West:
  1. Write to EU-West local replicas
  2. Acknowledge client (10ms)
  3. Asynchronously replicate to other regions

Conflict resolution: Last-write-wins (based on timestamp)

Latency: 10ms (local write)
Consistency: Eventual (conflicts resolved via LWW)
Evidence: Timestamp + region priority
Vector: ⟨Range, EC, RA, EO, Idem(K), Auth⟩
```

**Trade-off**: Low latency, high availability, but conflicts possible.

**Causal consistency (Azure Cosmos DB)**:
```
Protocol: Session tokens track causality

Write X=5 from session S1:
  1. Write to local region
  2. Return session token T1 (encodes version)

Read from different region with session token T1:
  1. Request includes T1
  2. Region waits until it has version T1 (or later)
  3. Return data (guaranteed to include X=5)

Latency: Low for local writes, bounded wait for causally consistent reads
Consistency: Causal (reads see causally related writes)
Evidence: Session tokens encode vector clock
Vector: ⟨Global, Causal, SI, BS(δ), Idem, Auth⟩
```

**Trade-off**: Balance of consistency and performance. Causal consistency is weaker than linearizable but stronger than eventual.

#### Conflict Resolution in Geo-Replication

**Region priorities**:
```
US-East > EU-West > Asia-Pacific

During partition, both US-East and EU-West accept writes.

After partition heals:
  Conflicting writes resolved: US-East wins (higher priority)
```

**Custom resolution functions**:
```javascript
// Application-defined merge logic
function resolveConflict(valueA, valueB, metadataA, metadataB) {
  if (metadataA.priority > metadataB.priority) {
    return valueA;
  } else if (metadataA.timestamp > metadataB.timestamp) {
    return valueA;
  } else {
    return merge(valueA, valueB);  // Application logic
  }
}
```

**CRDTs for automatic convergence**:
```
Shopping cart (OR-Set CRDT):
  US-East: Add item A
  EU-West: Add item B (concurrent)

After replication: Both regions have {A, B}
No conflict, automatic merge.
```

**Evidence**:
- Region priority is evidence of tiebreaker authority
- Custom resolution function is evidence of application-level policy
- CRDT merge is evidence of mathematical convergence

---

## Part 3: MASTERY (Third Pass) — Composition and Operation

### Evidence-Based Replication

Replication is fundamentally about evidence: generating, propagating, and validating it.

#### Replication as Evidence Generation

Different strategies generate different evidence:

**Synchronous Primary-Backup**:
- **Evidence generated**: Write acknowledgments from all replicas
- **Scope**: All replicas
- **Lifetime**: Permanent (until next write)
- **Binding**: Write to specific log sequence number or version
- **Validation**: Client requires all acknowledgments before considering write committed

**Asynchronous Primary-Backup**:
- **Evidence generated**: Write acknowledgment from primary only
- **Scope**: Primary only
- **Lifetime**: Until replicas catch up (undefined)
- **Binding**: Write to primary's log position
- **Validation**: Client trusts primary, replicas validated asynchronously

**Quorum Replication**:
- **Evidence generated**: W acknowledgments from N replicas
- **Scope**: Write quorum (W replicas)
- **Lifetime**: Until next write (version-based)
- **Binding**: Write to specific version/timestamp
- **Validation**: Read quorum (R replicas) must overlap with write quorum

**CRDT**:
- **Evidence generated**: Local write plus merge function proof
- **Scope**: Single replica (no coordination)
- **Lifetime**: Permanent (commutative merge ensures convergence)
- **Binding**: CRDT operation with metadata (tags, vector clock)
- **Validation**: Merge operation validates consistency (mathematical proof)

#### Evidence Lifecycle in Replication

```
GENERATE (write operation)
  ↓
PROPAGATE (replication protocol)
  ↓
VALIDATE (version check, quorum verification)
  ↓
ACTIVE (serving reads from replica)
  ↓
EXPIRE (detect staleness, lag exceeds threshold)
  ↓
REFRESH (read repair, anti-entropy)
  ↓
(back to ACTIVE or GENERATE if conflict)
```

**Example: Quorum write lifecycle**:
```
T=0:     GENERATE: Client writes X=10 to leader
T=0:     Leader creates version 5, writes locally
T=0:     PROPAGATE: Send to replicas A, B, C
T=10ms:  VALIDATE: A acknowledges (1 of 3)
T=15ms:  VALIDATE: B acknowledges (2 of 3) → Quorum reached
T=15ms:  ACTIVE: Write committed, version 5 now readable
T=20ms:  C acknowledges (3 of 3, late but helpful for durability)
T=100ms: Read from replica C: ACTIVE (version 5)
T=200ms: C crashes, recovers with version 4
T=200ms: EXPIRE: C's evidence is stale (version 4 < current 5)
T=210ms: REFRESH: Read repair sends version 5 to C
T=210ms: ACTIVE: C back to version 5
```

**Evidence expiration**:
- **Synchronous**: Evidence never expires (all replicas always current)
- **Asynchronous**: Evidence expires after replication lag threshold (e.g., 10 seconds)
- **Quorum**: Evidence expires if quorum is lost (e.g., 2 of 3 replicas down)
- **CRDT**: Evidence never expires (eventual convergence guaranteed)

### Invariant Framework for Replication

#### Primary Invariant: AVAILABILITY

**Definition**: System remains operational and serves requests despite failures.

**Quantification**:
```
Availability = uptime / (uptime + downtime)

Target: 99.99% (52.6 minutes downtime/year)
Degraded: 99.9% (8.76 hours downtime/year)
Floor: 99% (87.6 hours downtime/year)
```

**Replication's contribution**:
- Single server: 99.9% (limited by hardware reliability)
- Three replicas: 99.99%+ (limited by common-mode failures)

**Protection mechanism**:
- Replicas provide redundancy
- Failover when primary fails
- Load balancing distributes load

#### Supporting Invariants

**DURABILITY: Data survives failures**

**Definition**: Once acknowledged, data is not lost.

**Quantification**:
```
Durability = 1 - P(data loss)

Target: 11 nines (99.999999999% - AWS S3 standard)
Degraded: 9 nines (99.9999999%)
Floor: 7 nines (99.99999%)
```

**Replication mechanism**:
- Synchronous replication: Data on F+1 replicas before acknowledgment
- F failures tolerated without data loss
- Asynchronous replication: Data on primary only (vulnerable)

**Evidence**:
- Write acknowledgment from quorum is evidence of durability
- Single acknowledgment (async) is weak evidence

**CONSISTENCY: Replicas converge**

**Definition**: All replicas eventually have the same data.

**Quantification**:
```
Consistency = 1 - divergence_time / total_time

Target: Strong consistency (divergence_time = 0)
Degraded: Bounded staleness (divergence_time < δ)
Floor: Eventual consistency (divergence_time → 0 eventually)
```

**Replication mechanism**:
- Synchronous: All replicas updated before acknowledgment (strong)
- Asynchronous: Replicas lag by replication lag δ (bounded staleness)
- Multi-master: Conflicts resolved via LWW, vector clocks, CRDTs (eventual)

**Evidence**:
- Version numbers, timestamps, vector clocks are evidence of consistency level
- Quorum overlaps ensure read-your-writes

**MONOTONICITY: No data regression**

**Definition**: Once a replica serves a value, it never serves an older value.

**Quantification**:
```
Monotonicity violations per million reads

Target: 0 violations
Degraded: < 1 violation per million
Floor: < 100 violations per million
```

**Threat**: Clock skew, out-of-order replication, failed anti-entropy.

**Replication mechanism**:
- Version numbers ensure monotonicity (reject writes with older versions)
- Read repair identifies and fixes regressions
- Anti-entropy prevents drift

**Evidence**:
- Monotonic reads guarantee: Read from same session token never goes backward
- Session tokens (Azure Cosmos DB) encode version, ensure monotonicity

**CAUSALITY: Order preserved**

**Definition**: If write B depends on write A, all replicas see A before B.

**Quantification**:
```
Causality violations per million operations

Target: 0 violations (causal consistency)
Degraded: < 10 violations per million (eventual consistency with tracking)
Floor: No guarantee (eventual consistency without tracking)
```

**Replication mechanism**:
- Vector clocks track causality (detect concurrent vs sequential writes)
- Causal consistency guarantees (Cosmos DB, Cassandra with causal consistency)
- Application-level tracking (session tokens, client-side versioning)

**Evidence**:
- Vector clock is evidence of happened-before relationship
- Session token is evidence of client's causal history

### Guarantee Vectors for Replication

Different replication strategies provide different guarantees.

**Synchronous Replication**:
```
⟨Global, Lx, SI, Fresh(φ), Idem, Auth⟩

Global: All replicas globally consistent
Lx: Linearizable (real-time order)
SI: Serializable isolation
Fresh(φ): All replicas immediately consistent
Idem: Writes are idempotent (safe to retry)
Auth: Writes authenticated
```

**Example**: PostgreSQL with synchronous_commit=on, synchronous_standby_names set.

**Asynchronous Replication**:
```
⟨Global, EC, RA, BS(δ), Idem, Auth⟩

Global: Eventually all replicas converge
EC: Eventual consistency
RA: Read atomic (single replica consistency)
BS(δ): Bounded staleness (replicas lag by δ)
Idem: Writes are idempotent
Auth: Writes authenticated
```

**Example**: MySQL with default asynchronous replication, typical lag δ=100ms.

**Quorum Replication (W+R>N)**:
```
⟨Range, EC, RA, BS(δ), Idem, Auth⟩

Range: Consistency over key range (not global)
EC: Eventual consistency
RA: Read atomic
BS(δ): Bounded staleness by replication lag
Idem(K): Idempotent per key
Auth: Authenticated
```

**Example**: Cassandra with QUORUM consistency level.

**CRDT Replication**:
```
⟨Object, EC, RA, EO, Idem, Merge⟩

Object: Consistency per CRDT object
EC: Eventual consistency
RA: Read atomic
EO: Eventually ordered (convergence via merge)
Idem: Operations idempotent
Merge: Automatic conflict resolution via merge function
```

**Example**: Riak with CRDT datatypes (counters, sets, maps).

**Geo-Replication with Strong Consistency**:
```
⟨Global, Lx, SER, Fresh(TT), Idem, Auth⟩

Global: All regions globally consistent
Lx: Linearizable
SER: Serializable
Fresh(TT): Fresh within TrueTime uncertainty
Idem: Idempotent
Auth: Authenticated
```

**Example**: Google Spanner with Paxos across regions.

**Geo-Replication with Eventual Consistency**:
```
⟨Regional, EC, RA, EO, Idem(K), Auth⟩

Regional: Consistent within region, eventual across regions
EC: Eventual consistency
RA: Read atomic
EO: Eventually ordered
Idem(K): Idempotent per key
Auth: Authenticated
```

**Example**: DynamoDB Global Tables with last-write-wins.

### Mode Matrix for Replication

Replication systems operate in multiple modes, transitioning based on replica health.

#### Target Mode (All Replicas Healthy)

**Conditions**:
- All replicas reachable and responsive
- Replication lag < threshold (e.g., <100ms)
- No failures detected

**Guarantees**:
- Full replication factor (e.g., 3 replicas)
- Synchronous replication possible (if configured)
- Strong consistency available
- Optimal performance (P99 latency within SLA)

**Operations**:
- Writes replicate to all replicas
- Reads can be served from any replica (if async) or majority (if quorum)
- Failover not needed

**Evidence**:
- All replicas have fresh evidence (recent heartbeats, up-to-date versions)
- Quorum reachable
- Replication lag metrics within bounds

**Example**: PostgreSQL cluster with 3 nodes, all healthy, synchronous_commit=on.
```
Primary: Writes committed to all 3 nodes
Standby 1: Lag <10ms
Standby 2: Lag <10ms
Failover: Not needed
Mode: Target
```

#### Degraded Mode (Some Replicas Failed)

**Conditions**:
- One or more replicas unreachable or slow
- Replication factor reduced (e.g., 3 → 2 replicas)
- Replication lag exceeds threshold (e.g., >1 second)

**Guarantees**:
- Reduced replication factor (higher risk)
- Synchronous replication may fall back to async (explicit degradation)
- Weaker consistency (if quorum lost)
- Increased latency (if waiting for slower replicas)

**Operations**:
- Writes succeed with fewer replicas
- Reads may be stale (if async and some replicas unavailable)
- Alerts triggered (ops team notified)

**Evidence**:
- Some replicas have stale evidence or no evidence (heartbeat timeout)
- Quorum may or may not be reachable (depends on configuration)
- Replication lag metrics elevated

**Example**: PostgreSQL with 3 nodes, 1 node failed.
```
Primary: Writes committed to 2 nodes (was 3)
Standby 1: Healthy, lag <10ms
Standby 2: Failed (network partition)
Failover: Not needed yet (primary healthy)
Mode: Degraded (alert: "Replication factor reduced to 2")
```

**Mode transition logic**:
```
if replica_healthy_count < replication_factor:
  mode = Degraded
  log_warning("Replica failure detected, replication factor reduced")
  if synchronous_commit == on:
    if replica_healthy_count >= min_sync_replicas:
      continue_synchronous()
    else:
      fallback_to_asynchronous()
      log_critical("Insufficient replicas for synchronous commit, falling back to async")
```

#### Floor Mode (Minimum Replicas)

**Conditions**:
- Only one replica available (primary only, or single surviving replica)
- No replication possible (no redundancy)
- High risk of data loss

**Guarantees**:
- No durability guarantee (single point of failure)
- No availability guarantee (if this replica fails, total outage)
- Strong consistency possible (only one copy, no divergence)
- Latency optimal (no replication overhead)

**Operations**:
- Writes committed locally only (no replication)
- Reads served from single replica
- System may switch to read-only mode (to preserve data until replicas recover)
- Critical alerts (ops team must restore replication immediately)

**Evidence**:
- Only one replica has evidence (single point of failure)
- No quorum reachable (other replicas dead)
- Replication lag meaningless (no replicas to lag)

**Example**: PostgreSQL with 3 nodes, 2 nodes failed, primary still running.
```
Primary: Writes committed locally (no replication)
Standby 1: Failed
Standby 2: Failed
Failover: Not possible (no standbys)
Mode: Floor (critical alert: "Single replica remaining, restore replication immediately")
```

**Floor mode policy**:
```
if replica_healthy_count == 1:
  mode = Floor
  log_critical("Only one replica remaining, no redundancy")
  if safety_policy == strict:
    switch_to_readonly()
    log_critical("Switched to read-only mode to prevent data loss")
  else:
    continue_accepting_writes()
    log_critical("Accepting writes at risk (no replication)")
```

**Read-only mode in Floor**:
- Refuse writes (preserve data consistency until replication restored)
- Serve reads (availability for read-heavy workloads)
- Ops team restores replicas (bring failed nodes back online)
- Once replicas healthy, resynchronize, return to Target mode

#### Recovery Mode (Rebuilding Replicas)

**Conditions**:
- Failed replicas are being restored
- Replicas catching up (replaying logs, copying snapshots)
- Replication lag high but decreasing

**Guarantees**:
- Durability improving (more replicas coming online)
- Availability improving (more replicas available for reads)
- Consistency eventually restored (replicas catching up)
- Latency may be impacted (catching-up replicas consume resources)

**Operations**:
- Replicas in catchup: replaying logs, installing snapshots
- Primary serves writes normally (to available replicas)
- Catching-up replicas not yet serving reads (stale data)
- Monitoring catchup progress (estimated time to Target mode)

**Evidence**:
- Recovering replicas have evidence generation in progress (log replay position)
- Replication lag decreasing (evidence of progress)
- Quorum may be reachable (if enough replicas caught up)

**Example**: PostgreSQL with 3 nodes, 1 node recovering from failure.
```
Primary: Writes committed to 2 healthy nodes
Standby 1: Healthy, lag <10ms
Standby 2: Recovering (replaying logs, lag 5 minutes, decreasing)
Failover: Not needed
Mode: Recovery (info: "Standby 2 catching up, ETA to Target mode: 10 minutes")
```

**Catchup strategies**:
- **Log replay**: Replay write-ahead log from last checkpoint (slow for large lag)
- **Snapshot transfer**: Copy full snapshot, then replay recent log (faster)
- **Incremental backup**: Copy only changed blocks since failure (fastest)

**Recovery completion**:
```
if recovering_replica.lag < threshold:
  mode = Target
  log_info("Replica recovered, full replication factor restored")
```

### Production Patterns

#### Monitoring Replication Health

**Key metrics**:

**Replication lag**:
- **Definition**: Time (or log offset) between primary and replica
- **Target**: <100ms (most systems)
- **Degraded**: 100ms - 10s (elevated but acceptable)
- **Floor**: >10s (critical, investigate immediately)

**Calculation**:
```
Lag (time) = replica.last_applied_timestamp - primary.last_committed_timestamp
Lag (offset) = primary.log_position - replica.log_position
```

**Alerts**:
- Warning: Lag > 1 second
- Critical: Lag > 10 seconds

**Replica availability**:
- **Definition**: Percentage of time replica is reachable
- **Target**: 99.99%
- **Degraded**: 99.9%
- **Floor**: <99%

**Calculation**:
```
Availability = (successful_heartbeats / total_heartbeats) over window
```

**Alerts**:
- Warning: Replica missed 3 consecutive heartbeats
- Critical: Replica missed 10 consecutive heartbeats (assume dead)

**Conflict rate (multi-master)**:
- **Definition**: Percentage of writes that conflict
- **Target**: <0.1% (rare conflicts)
- **Degraded**: 0.1% - 1%
- **Floor**: >1% (frequent conflicts, rethink data model)

**Calculation**:
```
Conflict rate = conflicts_detected / total_writes
```

**Alerts**:
- Warning: Conflict rate > 0.1%
- Critical: Conflict rate > 1%

**Resolution latency (multi-master)**:
- **Definition**: Time to resolve conflicts after detection
- **Target**: <100ms (automatic resolution)
- **Degraded**: 100ms - 1s
- **Floor**: >1s (manual intervention required)

**Alerts**:
- Warning: Resolution latency > 100ms
- Critical: Resolution latency > 1s or manual intervention needed

**Divergence detection**:
- **Definition**: Time to detect replicas have diverged
- **Target**: <1 second (via anti-entropy or read repair)
- **Degraded**: 1-10 seconds
- **Floor**: >10 seconds (unacceptable, increase anti-entropy frequency)

**Calculation**:
```
Compare checksums or Merkle tree roots periodically
Divergence detected when mismatch found
```

**Recovery time (RTO/RPO)**:
- **RTO (Recovery Time Objective)**: How long to restore service after failure
- **RPO (Recovery Point Objective)**: How much data loss is acceptable

**Target**:
- RTO: <1 minute (automatic failover)
- RPO: 0 (synchronous replication, no data loss)

**Degraded**:
- RTO: 1-10 minutes (manual intervention)
- RPO: <1 minute (asynchronous replication, small data loss)

**Floor**:
- RTO: >10 minutes (significant downtime)
- RPO: >1 minute (significant data loss)

#### Replication Topology Design

**Star Topology (Primary-Backup)**:
```
        [Primary]
       /    |    \
      /     |     \
  [Rep1] [Rep2] [Rep3]
```

**Advantages**:
- Simple (single source of truth)
- Easy to reason about (primary coordinates everything)

**Disadvantages**:
- Primary is bottleneck (all replication goes through it)
- Primary is single point of failure (failover required)

**Use case**: Most common, default for MySQL, PostgreSQL, MongoDB.

**Ring Topology (Circular Replication)**:
```
  [Node A] → [Node B] → [Node C] → [Node A]
```

**Advantages**:
- Load distribution (each node replicates to one downstream)
- Multi-master possible (each node accepts writes)

**Disadvantages**:
- Latency accumulation (writes propagate through entire ring)
- Failure recovery complex (ring breaks, must reconnect)

**Use case**: Rare in production (except specific DB setups like MySQL circular replication for multi-datacenter).

**Mesh Topology (All-to-All)**:
```
     [Node A] ←→ [Node B]
       ↕           ↕
     [Node C] ←→ [Node D]
```

**Advantages**:
- High redundancy (every node connected to every other)
- Fast propagation (direct connections)

**Disadvantages**:
- O(N²) connections (doesn't scale to large N)
- Complex conflict resolution (multi-master conflicts everywhere)

**Use case**: Small clusters (3-5 nodes), where all nodes are equals (DynamoDB-style multi-master).

**Tree Topology (Hierarchical)**:
```
        [Root]
       /      \
    [L1-A]   [L1-B]
    /    \
 [L2-A] [L2-B]
```

**Advantages**:
- Scalable (fanout replication)
- Tiered geo-replication (root in primary datacenter, branches in secondary)

**Disadvantages**:
- Root is bottleneck and single point of failure
- Latency to leaves (multiple hops)

**Use case**: Content distribution (CDN-like replication, Git replication).

**Hybrid Topology (Primary + Mesh)**:
```
   [Primary Region]
   [P] → [R1, R2]  (star within region)
    ↓
   [Secondary Region]
   [P] → [R1, R2]  (star within region)
```

**Advantages**:
- Strong consistency within region (synchronous star)
- Eventual consistency across regions (asynchronous cross-region)

**Disadvantages**:
- Complex configuration (multiple consistency levels)
- Cross-region conflicts possible (multi-master across regions)

**Use case**: Most geo-replicated systems (AWS Aurora, Azure Cosmos DB, Google Spanner).

### Common Problems and Solutions

#### Problem 1: Replication Lag

**Symptom**: Replicas lag behind primary by seconds or minutes.

**Causes**:
- Slow network (congestion, bandwidth limits)
- Overloaded replicas (CPU, disk I/O bottleneck)
- Large transactions (bulk writes, schema changes)
- Insufficient parallelism (single-threaded replay)

**Solutions**:

**Parallel apply** (multi-threaded replication):
```
Primary: Single write thread
Replica: Multiple apply threads (parallel replay)

Example: MySQL parallel replication
  slave_parallel_workers = 8
  slave_parallel_type = LOGICAL_CLOCK
```

**Better hardware** (upgrade replicas):
- Faster disks (SSD, NVMe)
- More CPU cores (parallel apply)
- More memory (larger buffer pool, less disk I/O)

**Network optimization**:
- Increase bandwidth (dedicated replication network)
- Reduce latency (co-locate replicas)
- Compression (reduce bytes transferred)

**Sharding** (reduce data per replica):
- Split large dataset into shards
- Each shard has independent replication
- Lag reduced proportionally

**Monitoring and alerting**:
```
if replication_lag > 1s:
  alert("Replication lag elevated")
  investigate_cause()

if replication_lag > 10s:
  critical_alert("Replication lag critical")
  trigger_degraded_mode()
```

#### Problem 2: Conflict Storms (Multi-Master)

**Symptom**: High conflict rate, resolution latency spikes, replicas diverge.

**Causes**:
- Clock skew (LWW resolution incorrect)
- Hot keys (many clients write same key)
- Network partition (replicas accept conflicting writes)
- Poor conflict resolution (siblings accumulate)

**Solutions**:

**Conflict-free designs** (use CRDTs):
```
Instead of:
  counter = 0
  replica_a: counter = counter + 1  (conflict with concurrent update)

Use CRDT:
  counter = PN-Counter()
  replica_a: counter.increment()  (commutative, no conflict)
```

**Sharding** (avoid hot keys):
```
Instead of:
  global_counter (all replicas update)

Shard:
  counter_shard_a, counter_shard_b, counter_shard_c
  aggregate = sum(counter_shard_*)
```

**Single-master per key range**:
```
Key range [0-1000]: Primary A
Key range [1001-2000]: Primary B
Key range [2001-3000]: Primary C

Each key has single master (no conflicts for that key)
```

**Clock synchronization** (NTP, PTP):
```
Ensure clocks synchronized within 10ms (for LWW correctness)
Monitor clock skew, alert if >10ms
```

**Conflict resolution policies**:
```
Priority-based: Region A > Region B (deterministic tiebreaker)
Application-defined: merge(valueA, valueB) (custom logic)
CRDT: automatic merge (mathematical convergence)
```

#### Problem 3: Chain Reaction Failures (Cascading Overload)

**Symptom**: One replica fails, others fail shortly after (cascading failure).

**Causes**:
- Failed replica's load redistributed to remaining replicas
- Remaining replicas overloaded (CPU, disk I/O)
- Overloaded replicas slow down or fail
- Cascade continues until all replicas fail

**Solutions**:

**Circuit breakers** (stop cascading load):
```
if replica_failure_rate > threshold:
  open_circuit()  # Stop sending traffic to failing replica
  route_to_healthy_replicas()

if all_replicas_failing:
  enter_degraded_mode()
  reduce_write_rate()  # Backpressure
```

**Backpressure** (slow down clients):
```
if replica_lag > threshold:
  slow_down_writes()
  return_503_service_unavailable()
  wait_for_lag_to_recover()
```

**Load shedding** (reject low-priority requests):
```
if system_overloaded():
  reject_low_priority_requests()
  serve_only_high_priority()
  preserve_critical_functionality()
```

**Capacity planning** (overprovisioning):
```
Provision for: peak_load × 2 (headroom for failures)
Ensure: N-1 replicas can handle full load (survive one failure)
```

**Graceful degradation**:
```
if replica_count < target:
  mode = Degraded
  reduce_consistency_guarantees()  # e.g., switch from sync to async
  increase_timeout_thresholds()
  alert_operators()
```

#### Problem 4: Data Divergence (Split-Brain)

**Symptom**: Replicas have conflicting data that cannot be reconciled automatically.

**Causes**:
- Network partition (replicas accept conflicting writes)
- Faulty conflict resolution (incorrect merge)
- Clock skew (LWW chooses wrong winner)
- Byzantine failures (malicious or buggy replicas)

**Solutions**:

**Checksums and validation**:
```
Periodically compute checksums of data ranges
Compare checksums across replicas
If mismatch: divergence detected

Example: Cassandra Merkle trees
```

**Reconciliation (anti-entropy)**:
```
if divergence_detected():
  identify_divergent_keys()
  apply_conflict_resolution()
  propagate_resolved_values()
  verify_convergence()
```

**Epoch fencing** (prevent stale writes):
```
Each write includes epoch number
If replica receives write with stale epoch:
  reject_write()
  log_warning("Stale epoch detected, preventing split-brain")
```

**Quorum consistency** (ensure overlap):
```
W + R > N (quorum overlap)
Ensure: Read quorum always overlaps write quorum
Result: Divergence detected during reads (version mismatch)
```

**Partition detection and response**:
```
if network_partition_detected():
  if CP_mode:
    minority_partition.reject_writes()
    majority_partition.continue_serving()
  elif AP_mode:
    all_partitions.continue_serving()
    mark_epoch_for_reconciliation()
```

### Case Studies

#### MySQL Replication Evolution

**Historical progression**:

**Statement-based replication (oldest)**:
```
Primary logs SQL statements: "UPDATE users SET balance = balance + 100 WHERE id = 5"
Replica replays statements: Execute same SQL

Problems:
- Non-deterministic functions (NOW(), RAND()) produce different results
- Statement order matters (concurrent updates)
- Complex to debug (what state led to divergence?)
```

**Row-based replication**:
```
Primary logs row changes: "users(id=5): balance 1000 → 1100"
Replica applies row changes: Direct update

Advantages:
- Deterministic (exact data changes logged)
- No non-deterministic functions issue
- Idempotent (can replay safely)

Disadvantages:
- Larger log size (entire rows, not SQL)
- Bulk updates expensive (log every row change)
```

**Mixed replication**:
```
Primary chooses: statement-based for simple queries, row-based for complex/non-deterministic

Balance: Size efficiency + determinism
```

**GTID (Global Transaction ID) introduction**:
```
Before GTID:
  Replicas tracked log file + position: mysql-bin.000042:1337
  Failover complex: Find position on new primary

With GTID:
  Each transaction has unique ID: 3e11fa47-71ca-11e1-9e33-c80aa9429562:23
  Replicas track GTID set: "all transactions up to GTID X"
  Failover simple: Connect to new primary, continue from GTID X
```

**Group Replication (multi-primary)**:
```
Group of servers with conflict detection
Writes propose to group via consensus (Paxos-like)
If conflict detected: abort transaction (first-committer-wins)

Result: Multi-master with strong consistency
```

**Semi-sync improvements**:
```
MySQL 5.7+: Semi-sync after commit (primary commits, then waits for replica)
MySQL 8.0+: Semi-sync after prepare (replica acknowledges before primary commits)

Result: No data loss even if primary crashes (replica already has data)
```

#### MongoDB Replica Sets

**Architecture**:
```
Primary: Accepts writes
Secondaries: Replicate from primary
Arbiter (optional): Participates in elections but doesn't replicate data
```

**Primary election**:
```
Trigger: Primary failure (heartbeat timeout), network partition
Process: Secondaries vote for new primary (Raft-like)
Quorum: Majority required (e.g., 2 of 3 nodes)

Election time: 7-12 seconds (default)
```

**Oplog replication**:
```
Primary writes to oplog (operations log)
Secondaries tail oplog, apply operations

Oplog format:
  { ts: Timestamp, op: "u", ns: "db.collection", o: {update} }

Idempotent operations: Safe to replay
```

**Read preferences**:
```
primary: Read from primary only (strong consistency)
primaryPreferred: Primary if available, else secondary
secondary: Read from secondary (eventual consistency, lower latency)
secondaryPreferred: Secondary if available, else primary
nearest: Read from lowest-latency node
```

**Write concerns**:
```
w=1: Acknowledge after primary write (default)
w=majority: Acknowledge after majority replication (durable)
w=N: Acknowledge after N replicas

j=true: Acknowledge after journal flush (durability)
```

**Arbiter nodes**:
```
Purpose: Provide quorum without data storage
Use case: 2-node replica set + arbiter = 3-node quorum (avoid split-brain)

Warning: Arbiters don't replicate data (no durability benefit)
```

#### Cassandra's Eventually Consistent Model

**Architecture**:
```
Peer-to-peer: No single primary, all nodes equal
Consistent hashing: Data partitioned across nodes
Replication factor: Each key replicated to N nodes
```

**Consistent hashing**:
```
Hash ring: [0, 2^127]
Nodes: Assigned positions on ring
Key: Hash to position, store on next N nodes clockwise

Example:
  Key "user123" hashes to position 42
  Stored on nodes at positions 42, 87, 135 (N=3)
```

**Gossip protocol**:
```
Every second:
  Each node gossips with 1-3 random nodes
  Exchange: node status, schema versions, token ranges

Result: Eventually all nodes learn about all other nodes
Convergence time: O(log N)
```

**Tunable consistency**:
```
Consistency levels (CL):
  ONE: Read/write from 1 replica (fast, weakest)
  QUORUM: Read/write from majority (balanced)
  ALL: Read/write from all replicas (slow, strongest)

Quorum: floor(replication_factor / 2) + 1
  Example: RF=3, quorum=2
```

**Read repair**:
```
Read from multiple replicas (based on CL)
Compare versions (using timestamps)
If mismatch: repair stale replicas in background
```

**Hinted handoff**:
```
Write to replicas A, B, C
Replica B is down
Write to temporary replica D with hint: "This belongs to B"
When B recovers, D hands off to B
```

**Conflict resolution (last-write-wins)**:
```
Each column has timestamp
Conflicting writes: highest timestamp wins
Clock skew issues: possible data loss
```

**Anti-entropy (Merkle trees)**:
```
Periodically:
  Nodes exchange Merkle tree roots for data ranges
  If mismatch: synchronize divergent ranges

Frequency: Configurable (default: weekly)
```

#### DynamoDB's Global Tables

**Architecture**:
```
Multi-region, multi-master
Each region: Independent DynamoDB table
Cross-region replication: Asynchronous, bi-directional
```

**Conflict resolution (last-write-wins)**:
```
Each item has version number and timestamp
Conflicting writes: highest timestamp wins (per attribute)

Clock synchronization: Relies on AWS NTP (high accuracy)
```

**Replication lag**:
```
Typical: <1 second
P99: <5 seconds
Max: Unbounded (during network partition)
```

**Global secondary indexes**:
```
Replicated across regions
Eventually consistent (replicated after base table)
```

**Auto-scaling**:
```
Each region independently scales
Replication bandwidth scales with write volume
```

**Guarantees**:
```
Within region: Read-after-write consistency (with consistent reads)
Across regions: Eventual consistency
Durability: 99.999999999% (11 nines) per region
```

#### Redis Replication

**Architecture**:
```
Master: Accepts writes
Replicas: Asynchronous replication from master
```

**Async replication protocol**:
```
Master: Buffers writes in replication backlog
Replicas: Connect, request backlog data
Master: Streams backlog to replicas
```

**PSYNC protocol (partial resync)**:
```
Replica disconnects, reconnects
Master: Checks replication offset
If offset within backlog: Partial resync (send missing data)
If offset expired: Full resync (send snapshot + subsequent writes)
```

**Diskless replication**:
```
Traditional: Master writes RDB snapshot to disk, sends to replica
Diskless: Master streams RDB directly to replica (no disk write)

Advantage: Faster, no disk I/O
Use case: Cloud instances with slow disks
```

**Redis Cluster (multi-master)**:
```
Cluster: 16,384 hash slots
Nodes: Each node owns subset of slots
Replication: Each master has replicas

Writes: Routed to master for relevant slot
Failover: Replica promoted if master fails
```

**Consistency guarantees**:
```
Async replication: Write acknowledged before replica confirmation
Result: Data loss possible (if master fails before replication)

Solution: WAIT command (semi-sync)
  WAIT N timeout: Wait for N replicas to acknowledge
```

#### Kafka's ISR Model

**Architecture**:
```
Topics: Divided into partitions
Partitions: Replicated across brokers
Leader: One leader per partition (accepts writes)
Followers: Replicate from leader
```

**ISR (In-Sync Replicas)**:
```
ISR: Set of replicas that are "caught up" with leader
Caught up: Replication lag < replica.lag.time.max.ms (default 10s)

Example:
  Partition 0: Leader=Broker1, ISR={Broker1, Broker2, Broker3}
  Broker3 lags 15s → ISR={Broker1, Broker2} (Broker3 removed)
```

**Min.insync.replicas**:
```
Configuration: Minimum ISR size for write to succeed

Example: min.insync.replicas=2, replication.factor=3
  Write succeeds if ISR size ≥ 2
  If ISR shrinks to 1: writes fail (insufficient replication)
```

**Unclean leader election**:
```
Scenario: All ISR replicas fail, only non-ISR replica available

unclean.leader.election.enable=false (default):
  Refuse to elect non-ISR replica (CP choice, prevent data loss)
  Partition unavailable until ISR replica recovers

unclean.leader.election.enable=true:
  Elect non-ISR replica (AP choice, accept data loss)
  Partition available, but messages may be lost
```

**Replication protocol**:
```
Leader: Appends message to log
Followers: Fetch from leader (pull-based)
Leader: Tracks follower fetch positions (high water mark)
High water mark: Offset up to which all ISR replicas have replicated
Consumers: Can only read up to high water mark (consistent reads)
```

**Evidence**:
- ISR membership is evidence of replica currency
- High water mark is evidence of committed messages
- **Guarantee vector**: `⟨Partition, SS for ISR, RA, Fresh(φ) for ISR, Idem, Auth⟩`

---

## Synthesis: The Replication Spectrum

### Mental Models for Replication

**1. Replication as Insurance**

Think of replicas as insurance policies:
- **Premiums**: Resources (storage, network, compute) paid continuously
- **Coverage**: Protection against failures (node crashes, disk failures, datacenter outages)
- **Deductible**: Latency overhead (synchronous replication = higher premium for better coverage)
- **Payout**: Data survives failures, system remains available

**Trade-offs**:
- More replicas = higher premiums (cost) but better coverage (durability/availability)
- Synchronous replication = higher premiums (latency) but immediate coverage (no data loss)
- Asynchronous replication = lower premiums (latency) but delayed coverage (potential data loss)

**2. Replication as Evidence Trail**

Each replica maintains evidence of data state:
- **Write acknowledgment**: Evidence that replica received the write
- **Version number**: Evidence of data currency
- **Vector clock**: Evidence of causality
- **Checksum/Merkle tree**: Evidence of data integrity

**Conflicts reveal evidence gaps**:
- Concurrent writes: No causal evidence linking them (vector clocks concurrent)
- Resolution: Create new evidence (merge, LWW, CRDT operation)

**Evidence propagation**:
- Synchronous: Evidence propagates before acknowledgment (fresh evidence)
- Asynchronous: Evidence propagates after acknowledgment (stale evidence possible)
- Quorum: Evidence propagates to majority (sufficient evidence for consistency)

**3. Replication as Distributed State Machine**

All replicas run the same deterministic state machine:
- **Same inputs**: Log entries (operations)
- **Same order**: Consensus ensures log order
- **Same outputs**: All replicas reach same state

**Determinism enables replication**:
- Non-deterministic operations must be externalized (timestamps, random numbers)
- State machine must be deterministic (same state + same input → same new state)

**Breaks determinism → breaks replication**:
- Clock-dependent logic: Different replicas see different times
- Random number generation: Different replicas see different values
- External I/O: Different replicas see different results

### Design Principles

**1. Design for failure from the start**

Don't treat replication as an afterthought. Design for:
- Replica failures (some replicas always down)
- Network partitions (replicas cannot communicate)
- Clock skew (timestamps unreliable)
- Conflicting writes (concurrent updates)

**Failure-aware design**:
```
Assume: At any time, F replicas may be failed
Ensure: System tolerates F failures (2F+1 replicas, quorum=F+1)
Test: Regularly inject failures (chaos engineering)
```

**2. Make consistency model explicit**

Don't leave consistency guarantees implicit. Document:
- **Consistency level**: Strong, bounded staleness, causal, eventual
- **Partition behavior**: CP or AP
- **Conflict resolution**: LWW, vector clocks, CRDTs, application-defined

**Example documentation**:
```
Shopping Cart Service:
  Consistency: Eventual (AP choice during partitions)
  Conflict resolution: OR-Set CRDT (add/remove commute)
  Guarantee vector: ⟨Object, EC, RA, EO, Idem, Merge⟩
  Mode matrix: Target (all regions), Degraded (some regions), Floor (single region)
```

**3. Monitor divergence constantly**

Track metrics that reveal replication health:
- **Replication lag**: Time/offset between primary and replicas
- **Conflict rate**: Percentage of writes that conflict
- **Divergence detection**: Checksum mismatches, Merkle tree differences
- **Resolution latency**: Time to resolve conflicts

**Alerting thresholds**:
```
Warning: Replication lag > 1s
Critical: Replication lag > 10s
Warning: Conflict rate > 0.1%
Critical: Conflict rate > 1%
Warning: Divergence detected
Critical: Divergence unresolved for >1 minute
```

**4. Automate recovery procedures**

Manual recovery is slow and error-prone. Automate:
- **Failover**: Automatic promotion of replica to primary
- **Catchup**: Automatic replication of missing data to recovering replicas
- **Anti-entropy**: Automatic background sync to fix divergence
- **Conflict resolution**: Automatic application of resolution policies

**Example: Automatic failover**:
```
if primary_unhealthy() for >30 seconds:
  elect_new_primary()
  reconfigure_replicas(new_primary)
  redirect_writes(new_primary)
  alert_operators("Failover completed")
```

**5. Test failure scenarios**

Don't wait for production failures to discover replication bugs. Test:
- **Chaos engineering**: Inject failures (kill replicas, partition network)
- **Fault injection**: Simulate slow replicas, packet loss, clock skew
- **Load testing**: High write volume, concurrent conflicts
- **Partition testing**: Split cluster, ensure CP/AP behavior correct

**Example test scenarios**:
```
Test: Kill primary during write
Expected: Replica promoted, write succeeds or fails cleanly (no data corruption)

Test: Partition cluster (2 nodes | 3 nodes)
Expected: Majority (3) continues, minority (2) rejects writes (CP mode)

Test: Concurrent writes to same key
Expected: Conflict detected, resolution applied, all replicas converge
```

### The Replication Decision Tree

```
Need strong consistency (linearizable, no stale reads)?
  Yes → Synchronous replication or chain replication
        Trade-off: High latency, lower availability
        Example: Financial transactions, inventory management
  No → Continue

Can tolerate conflicts (concurrent writes to same key)?
  No → Primary-backup or quorum with W=N (single writer)
       Trade-off: Write bottleneck (single primary)
       Example: User profiles, configuration data
  Yes → Continue

Need geographic distribution (low latency worldwide)?
  Yes → Multi-master with CRDTs or conflict resolution
        Trade-off: Eventual consistency, conflict handling
        Example: Shopping carts, social media posts
  No → Quorum-based replication (single datacenter)
       Trade-off: Balanced consistency/performance
       Example: Session storage, caches

Need high write throughput?
  Yes → Asynchronous replication or multi-master
        Trade-off: Potential data loss (async) or conflicts (multi-master)
        Example: Logs, metrics, analytics
  No → Synchronous or semi-synchronous replication
       Trade-off: Lower throughput, higher durability
       Example: Database transactions, audit logs
```

### Operational Wisdom

**Start simple**:
1. **Primary-backup**: Single leader, followers replicate asynchronously
2. **Add async replicas**: For read scaling, geo-distribution
3. **Tune quorums**: Configure W and R for desired consistency/performance balance
4. **Consider CRDTs**: If conflicts frequent and data model fits

**Don't**:
- Start with multi-master (complexity)
- Start with eventual consistency (hard to reason about)
- Start with custom conflict resolution (bugs)

**Grow incrementally**:
1. **Asynchronous** → **Semi-synchronous** (reduce data loss risk)
2. **Single datacenter** → **Multi-region** (add geo-replication)
3. **Primary-backup** → **Quorum** (tune consistency)
4. **LWW** → **CRDTs** (reduce conflicts)

**Monitor everything**:
- **Before production**: Establish baselines (lag, conflict rate)
- **In production**: Alert on deviations (lag spikes, divergence)
- **After incidents**: Post-mortem, improve monitoring

**Metrics dashboard**:
```
Replication Lag (P50, P99, P999)
Replica Availability (% uptime)
Conflict Rate (conflicts / writes)
Resolution Latency (P50, P99)
Divergence Detection (last detected, time to resolve)
Mode State (Target, Degraded, Floor, Recovery)
```

---

## Exercises

### Conceptual Exercises

**1. Prove W + R > N ensures read-your-writes**:
- Given N replicas, W write quorum, R read quorum
- Prove: If W + R > N, a read after write sees the write
- Hint: Consider quorum overlap

**2. Design replication for chat application**:
- Requirements: Low latency (<100ms), eventual consistency acceptable, messages never lost
- Choose: Replication strategy, conflict resolution, consistency level
- Justify: Trade-offs, failure modes

**3. Calculate replication lag bounds**:
- Given: Network latency 50ms, write rate 1000 writes/sec, replica apply rate 900 writes/sec
- Calculate: Steady-state replication lag, time to unbounded lag
- Hint: Lag accumulates when write rate > apply rate

**4. Analyze conflict resolution strategies**:
- Given: Last-write-wins (LWW), vector clocks, CRDTs
- Compare: Pros, cons, use cases
- Determine: Which to use for shopping cart, bank account, social media post

**5. Compare replication topologies**:
- Given: Star (primary-backup), ring, mesh, tree
- Analyze: Latency, fault tolerance, scalability, complexity
- Choose: Best topology for 3-node cluster, 100-node cluster, geo-distributed cluster

### Implementation Projects

**1. Build primary-backup replication**:
- Implement: Primary accepts writes, logs operations, sends to backup
- Implement: Backup applies operations, acknowledges
- Test: Primary failure (backup promotion), backup failure (degraded mode)

**2. Implement vector clocks**:
- Implement: Vector clock structure, increment, merge, compare
- Implement: Conflict detection (concurrent vector clocks)
- Test: Concurrent writes, causality tracking

**3. Create a simple CRDT**:
- Implement: G-Counter (grow-only counter) or OR-Set (observed-remove set)
- Test: Concurrent increments, convergence after replication

**4. Build anti-entropy with Merkle trees**:
- Implement: Merkle tree construction, root hash, subtree comparison
- Implement: Divergence detection (hash mismatch), synchronization (exchange differences)
- Test: Replicas diverge, anti-entropy repairs

**5. Implement read repair**:
- Implement: Read from multiple replicas, compare versions
- Implement: Detect stale replicas, repair in background
- Test: Replica misses write, read repair fixes it

### Production Analysis

**1. Measure replication lag in your system**:
- Instrument: Log primary commit time, replica apply time
- Calculate: Lag = apply_time - commit_time
- Analyze: P50, P99, P999, identify spikes

**2. Analyze conflict rates**:
- Instrument: Count conflicts detected (vector clock concurrent, LWW overwrite)
- Calculate: Conflict rate = conflicts / total writes
- Determine: Hot keys, conflict patterns, resolution effectiveness

**3. Design monitoring dashboard**:
- Metrics: Replication lag, replica availability, conflict rate, resolution latency
- Alerts: Lag > threshold, replica down, conflict rate > threshold
- Visualization: Time series graphs, mode state, topology diagram

**4. Test failover procedures**:
- Simulate: Primary failure (kill process, network partition)
- Measure: Failover time (detection → promotion → reconfiguration)
- Verify: No data loss, writes resume, clients reconnect

**5. Calculate availability improvement**:
- Single server: 99.9% availability (8.76 hours downtime/year)
- Three replicas: Calculate availability with failover
- Hint: Availability = 1 - P(all replicas down) = 1 - (1 - 0.999)^3

---

## Key Takeaways

**Replication is fundamental for availability**:
- Single replica: One failure → total outage
- Multiple replicas: F failures tolerated with F+1 replicas
- But: More replicas → more coordination → more complexity

**Every strategy has trade-offs**:
- Synchronous: Strong consistency, high latency, lower availability
- Asynchronous: Low latency, high availability, potential data loss
- Quorum: Tunable balance (W, R, N configuration)
- Multi-master: High availability, conflict resolution required
- CRDTs: Automatic conflict resolution, limited data types

**Conflicts are inevitable in multi-master**:
- Concurrent writes to same key → conflict
- Detection: Version numbers, vector clocks
- Resolution: LWW (data loss), vector clocks (siblings), CRDTs (automatic merge)

**CRDTs offer automatic resolution**:
- Commutative operations → no conflicts
- Examples: Counters, sets, registers, maps
- Trade-off: Limited data types, metadata overhead

**Monitoring is essential**:
- Track: Replication lag, replica availability, conflict rate
- Alert: Lag > threshold, divergence detected, failover triggered
- Dashboard: Real-time metrics, mode state, topology

**Recovery must be automated**:
- Failover: Automatic primary election
- Catchup: Automatic log replay, snapshot transfer
- Anti-entropy: Automatic background sync

**Test failure scenarios constantly**:
- Chaos engineering: Inject failures, verify recovery
- Partition testing: Verify CP/AP behavior
- Load testing: Verify performance under stress

---

## Further Reading

### Foundational Papers

**Replication Strategies**:
- Schneider, Fred. "Implementing Fault-Tolerant Services Using the State Machine Approach: A Tutorial" (ACM Computing Surveys, 1990) — State machine replication
- Gray et al. "The Dangers of Replication and a Solution" (SIGMOD 1996) — Two-phase commit, replication dangers
- Kemme, Alonso. "Database Replication: A Tale of Research across Communities" (VLDB 2010) — Survey of replication techniques

**Multi-Master and Conflict Resolution**:
- DeCandia et al. "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007) — Vector clocks, sloppy quorums, hinted handoff
- Lamport. "Time, Clocks, and the Ordering of Events in a Distributed System" (CACM 1978) — Logical clocks, causality (foundational)
- Shapiro et al. "Conflict-free Replicated Data Types" (SSS 2011) — CRDTs, convergence proofs

**Chain Replication**:
- van Renesse, Schneider. "Chain Replication for Supporting High Throughput and Availability" (OSDI 2004) — Chain replication protocol

**Geo-Replication**:
- Corbett et al. "Spanner: Google's Globally-Distributed Database" (OSDI 2012, TOCS 2013) — TrueTime, Paxos-based geo-replication
- Lloyd et al. "Don't Settle for Eventual: Scalable Causal Consistency for Wide-Area Storage with COPS" (SOSP 2011) — Causal consistency

### Modern Systems

**Case Studies**:
- Facebook. "TAO: Facebook's Distributed Data Store for the Social Graph" (ATC 2013) — Social graph replication
- LinkedIn. "Kafka: a Distributed Messaging System for Log Processing" (NetDB 2011) — ISR model
- Netflix. "Aegisthus: A Bulk Data Pipeline out of Cassandra" (blog post) — Cassandra replication at scale

### Books

- Kleppmann, Martin. "Designing Data-Intensive Applications" (2017) — Chapter 5 (Replication), practical focus
- Cachin, Guerraoui, Rodrigues. "Introduction to Reliable and Secure Distributed Programming" (2011) — Chapter 5 (Reliable Broadcast, Causal Broadcast)
- van Steen, Tanenbaum. "Distributed Systems" (3rd ed, 2017) — Chapter 7 (Consistency and Replication)

---

## Chapter Summary

### The Irreducible Truth

**"Replication is how distributed systems survive failures—by refusing to have a single point of failure. But every replica introduces a choice: consistency, availability, or performance. Pick two."**

This chapter explored replication strategies that enable distributed systems to survive failures while managing the fundamental trade-offs between consistency, availability, and performance.

### Key Mental Models

**1. Replication as Insurance**
More replicas = better coverage (durability, availability) but higher premiums (cost, latency, complexity). Synchronous = high premium for immediate coverage. Asynchronous = low premium for delayed coverage.

**2. Replication as Evidence Trail**
Each replica maintains evidence of data state. Conflicts reveal evidence gaps (concurrent vector clocks). Resolution creates new evidence (merge, LWW, CRDT operation).

**3. Replication as Distributed State Machine**
Deterministic state machines + same input order = same output. Non-determinism breaks replication (clock-dependent logic, random numbers).

**4. The Replication Spectrum**
- **Synchronous**: Strong consistency, high latency, lower availability
- **Asynchronous**: Eventual consistency, low latency, high availability
- **Semi-synchronous**: Bounded staleness, medium latency/availability
- **Quorum**: Tunable balance (W, R, N)
- **Multi-master**: High availability, conflict resolution required
- **CRDTs**: Automatic convergence, limited data types

### Practical Takeaways

**Design Principles**:
- Design for failure from the start (assume F replicas always failed)
- Make consistency model explicit (document CP/AP, conflict resolution)
- Monitor divergence constantly (replication lag, conflict rate)
- Automate recovery procedures (failover, catchup, anti-entropy)
- Test failure scenarios (chaos engineering, partition testing)

**Operational Guidelines**:
- Start simple (primary-backup, async replication)
- Add replicas incrementally (async → semi-sync → quorum)
- Choose topology wisely (star for small, hybrid for geo-distributed)
- Monitor metrics (lag, availability, conflicts, mode state)
- Alert on deviations (lag spikes, divergence, failover)

**Debugging Approaches**:
- When lag spikes: Check replica health (CPU, disk, network), increase parallelism
- When conflicts storm: Check clock skew, shard hot keys, use CRDTs
- When divergence detected: Run anti-entropy, verify checksums, reconcile
- When cascading failures: Use circuit breakers, backpressure, capacity planning

### What's Next

Replication ensures data survives and systems remain available despite failures. But replication alone isn't enough—we need to ensure data is stored durably on disk, recovered after crashes, and accessed efficiently.

Chapter 6 explores **Storage Systems**—the foundation beneath replication. We'll see how LSM trees, B-trees, write-ahead logs, and distributed storage systems (HDFS, S3, Ceph) provide the durability guarantees that replication depends on. The replication strategies from this chapter compose with storage engines to build complete, fault-tolerant systems.

---

## Sidebar: Cross-Chapter Connections

**To Chapter 1 (Impossibility Results)**:
- CAP theorem: Replication must choose CP or AP during partitions
- PACELC: Replication trades latency for consistency even without partitions
- FLP: Consensus required for consistent replication (leader election, log replication)

**To Chapter 2 (Time, Order, Causality)**:
- Vector clocks: Enable causality tracking in multi-master replication
- Hybrid clocks: Bounded staleness requires time bounds (HLC)
- Happened-before: Determines conflict vs sequential writes

**To Chapter 3 (Consensus)**:
- Consensus enables strong consistency replication (Paxos, Raft for log replication)
- Leader election: Primary-backup replication requires leader
- Quorum overlap: Replication quorums use consensus quorum principle

**To Chapter 6 (Storage)**:
- WAL (Write-Ahead Log): Replication replicates WAL entries
- LSM trees: Replication of LSM tree writes (Cassandra, RocksDB)
- Durability: Replication + storage durability = complete fault tolerance

**To Chapter 7 (Cloud-Native)**:
- Microservices: Replication within services (databases) and across services (caches)
- Service mesh: Replication patterns for service discovery, load balancing
- Kubernetes: StatefulSets provide replication for stateful services

---

*This chapter's guarantee vector: `⟨Global, Causal, RA, BS(proof), Idem, Auth⟩` — We've explored global replication patterns, established causal understanding of evidence propagation, provided read-atomic knowledge of strategies, bounded staleness with production examples and proofs, offered idempotent insights you can revisit, all authenticated by research and production case studies.*

*Context capsule for next chapter: `{invariant: DURABILITY, evidence: write-ahead-log, boundary: chapter transition, mode: Target, fallback: revisit replication as motivation for persistent storage}`*

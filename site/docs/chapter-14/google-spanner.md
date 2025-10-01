# Google Spanner: The Impossible Database

## Introduction: When Theory Said "No" But Google Said "Yes"

In 2012, Google published a paper that made database theorists do a double-take. They had built Spanner—a globally distributed database that provided:

- **Serializable transactions** across data centers
- **External consistency** (linearizability for transactions)
- **Global secondary indexes**
- **Schema changes without downtime**
- **Automatic failover across continents**

The CAP theorem says you can't have both consistency and availability during partitions. The conventional wisdom was that global transactions meant global latency—unacceptable for user-facing applications. Spanner threw away the rulebook and became the foundation for Google's most critical services: AdWords (billions in revenue), Google Play, and Gmail.

**This is the story of how Google built the impossible database by solving time.**

### The Impossibility They Overcame

Traditional distributed databases face a fundamental trade-off:

**Option 1: Strong consistency, poor availability**
- Wait for cross-datacenter coordination on every write
- Typical latency: 100-500ms for global writes
- Example: Traditional Paxos-based systems

**Option 2: High availability, weak consistency**
- Accept writes locally, replicate asynchronously
- Fast writes (<10ms) but eventual consistency
- Example: Cassandra, Dynamo

**Spanner's achievement**: Strong consistency with reasonable performance
- Cross-datacenter writes: 10-100ms (depending on distance)
- Local reads: 1-10ms with strong consistency
- Global transactions that preserve invariants

The secret ingredient: **TrueTime**, Google's distributed time API that turned a theoretical impossibility into a practical system.

### Why This Matters

Before Spanner, building globally distributed applications meant choosing between:

1. **Sharding with application logic**: Manually partition data, handle cross-shard transactions in application code, deal with inconsistencies
2. **Eventual consistency**: Accept that users might see stale or conflicting data, implement complex conflict resolution
3. **Single region**: Sacrifice global availability and latency for consistency

Spanner eliminated these trade-offs for Google's applications. AdWords could run transactions that touched multiple data centers. Play Store could update inventory atomically across continents. Gmail could provide consistent views of your mailbox regardless of which datacenter served you.

**The evidence-based lens**: Spanner generates **time evidence** with bounded uncertainty, uses it to establish global ordering of transactions, and preserves serializability invariants even during failures and partitions.

Let's see how they did it.

---

## Part 1: INTUITION (First Pass)—The TrueTime Insight

### The Core Problem: Ordering Without Coordination

Imagine you're building a banking application across three continents:

```
US datacenter:     Transfer $100 from Alice → Bob
Europe datacenter: Check Bob's balance
Asia datacenter:   Transfer $50 from Bob → Charlie
```

These operations must maintain invariants:

1. **Causality**: If Europe reads Bob's balance after the US transfer completes, it must see the +$100
2. **Serializability**: The final state must be equivalent to some serial execution order
3. **No overdrafts**: If Bob started with $0, Asia must see $100 before allowing the $50 transfer

In a single-datacenter database, these are easy—transactions execute in some total order. In a distributed system, you face:

**Problem 1: Network delays are variable**
- US → Europe message: 80ms ± 40ms
- Europe → Asia message: 150ms ± 60ms
- You can't know which transaction "happened first"

**Problem 2: Clocks are unreliable**
- NTP synchronization: ±100ms typical, ±1s worst case
- If US clock is 200ms fast, its timestamps lie about ordering

**Problem 3: Coordination is expensive**
- 2PC across continents: 100-500ms
- Synchronous replication: 2x round-trip time
- Global locks: serialization bottleneck

Traditional solution: Use **logical clocks** (Lamport timestamps, vector clocks) to track causality without physical time. But logical clocks have a fatal flaw for databases: **they require communication to establish ordering**. Every transaction must contact every other node to determine the global order.

### The TrueTime Breakthrough

Google's insight: **What if we had a clock with explicit uncertainty bounds?**

Instead of:
```python
timestamp = time.now()  # Returns 1633027200.0 (lies about precision)
```

What if:
```python
interval = TT.now()  # Returns (1633027200.0, 1633027200.014)
                      # Earliest and latest possible time
```

The API guarantees: **The absolute time is definitely somewhere in this interval.**

With this, you can establish ordering **without communication**:

```python
# Transaction 1 commits at TrueTime interval [10, 17]
# Transaction 2 starts at TrueTime interval [20, 27]

# If T2.start.earliest > T1.commit.latest:
#     We KNOW T2 happened after T1, guaranteed
#     No need to check with T1's node
```

This is the key insight: **Uncertainty bounds let you trade waiting time for coordination.**

If you wait long enough before committing, you can be certain that your commit timestamp is in the past for all observers. Other nodes can then order their transactions relative to yours using only local reasoning.

### How TrueTime Works

TrueTime isn't magic—it's engineering. Google deployed:

**Hardware**:
- GPS receivers in every datacenter (time from satellites, ±1μs accuracy)
- Atomic clocks in every datacenter (drift <0.2μs/sec, no dependency on external signals)

**Redundancy**:
- Multiple GPS receivers per datacenter (tolerate antenna failures)
- Multiple atomic clocks per datacenter (tolerate oscillator failures)
- Cross-check GPS vs atomic clocks (detect systematic errors)

**Time masters**:
- Dedicated servers that poll GPS and atomic clocks
- Compute uncertainty based on polling intervals, clock drift, network delays
- Provide TrueTime API to client machines

**Client uncertainty**:
- Track time since last sync with time master
- Increase uncertainty bound based on local clock drift
- Re-sync periodically to bound uncertainty

The result: **Typical TrueTime uncertainty is 1-7ms**, worst case <100ms.

### The Commit Wait: Trading Latency for Consistency

Here's how Spanner uses TrueTime to provide external consistency:

**Traditional approach (broken)**:
```python
def commit_transaction(txn):
    timestamp = time.now()
    replicate(txn, timestamp)
    return "committed"
```

Problem: If local clock is fast, another transaction with earlier wall-clock time might not have committed yet. You've created a causality violation.

**Spanner approach (correct)**:
```python
def commit_transaction(txn):
    tt_interval = TrueTime.now()
    commit_timestamp = tt_interval.latest

    # COMMIT WAIT: Sleep until commit_timestamp is definitely in the past
    while TrueTime.now().earliest < commit_timestamp:
        time.sleep(0.001)

    replicate(txn, commit_timestamp)
    return "committed"
```

The **commit wait** ensures: By the time we return to the client, the commit timestamp is in the past everywhere. Any subsequent transaction will get a later timestamp and thus a later position in the global order.

**The trade-off**:
- Added latency: 2× average TrueTime uncertainty (typically 2-14ms)
- Benefit: External consistency without global coordination

This is **evidence-based ordering**: The commit timestamp is evidence of when the transaction committed. The commit wait ensures this evidence is valid for all observers.

### Why This Works: The Mathematical Guarantee

TrueTime provides:

```
TT.now() returns [earliest, latest]

GUARANTEE: absolute_time ∈ [earliest, latest]
```

Spanner's commit protocol:

```
1. Transaction starts: s_start = TT.now().latest
2. Transaction executes (reads, writes to buffer)
3. Ready to commit: s_commit = TT.now().latest
4. COMMIT WAIT: sleep until TT.now().earliest > s_commit
5. Replicate with timestamp s_commit
6. Return to client
```

Why external consistency holds:

```
Transaction T1:
- Commits with timestamp s1
- Returns to client at absolute time t1

Transaction T2:
- Starts after T1 returns (absolute time t2 > t1)
- Gets timestamp s2 = TT.now().latest at start

We need to prove: s2 > s1

Proof:
- T1 did commit wait, so at absolute time t1:
  TT.now().earliest > s1
- At absolute time t2 > t1, TT.now().latest >= TT.now(t1).earliest
- Therefore: s2 = TT.now(t2).latest > s1
```

This is a **wait-free ordering algorithm**: No communication between transactions, just local waiting based on uncertainty bounds.

---

## Part 2: UNDERSTANDING (Second Pass)—Architecture Deep Dive

### Spanner's Data Model and Organization

Spanner organizes data in a hierarchy:

```
Universe
  ├─ Zone (datacenter)
  │   ├─ Zonemaster (manages zone)
  │   ├─ Location Proxy (client routing)
  │   └─ Spanservers (1000s per zone)
  │       └─ Tablets (shards of data)
  │           ├─ Paxos group (replication)
  │           ├─ Lock table (concurrency control)
  │           └─ Transaction manager (2PC)
  ├─ Placement driver (shard allocation)
  └─ Global configuration (schema)
```

**Key concepts**:

1. **Directory**: Unit of data placement, collection of rows with same key prefix
2. **Tablet**: Shard of data, typically holds one directory
3. **Paxos group**: 5-7 replicas of a tablet, one leader, uses Paxos for consensus
4. **Zone**: Deployment unit, typically one datacenter
5. **Spanserver**: Machine serving multiple tablets

### Read-Write Transaction Flow

Let's trace a transaction that updates a user's account balance across multiple rows:

```sql
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE user_id = 'alice';
UPDATE accounts SET balance = balance + 100 WHERE user_id = 'bob';
COMMIT;
```

**Phase 1: Client chooses coordinator**
```
Client → Coordinator (the Paxos leader for first key accessed)
```

**Phase 2: Read phase**
```
1. Coordinator assigns read timestamp: s_read = TT.now().latest
2. For each read, acquire read lock at Paxos leader for that tablet
3. Read from most recent committed version ≤ s_read
4. Buffer reads at coordinator
```

**Phase 3: Write phase**
```
1. Client sends COMMIT to coordinator
2. Coordinator chooses commit timestamp: s_commit = TT.now().latest
   (Must be > s_read and > any previous commit timestamp coordinator knows)
3. Coordinator becomes 2PC coordinator
4. Send PREPARE to Paxos leader of each participant tablet
```

**Phase 4: Two-Phase Commit**
```
Coordinator                  Participant 1           Participant 2
    |                              |                       |
    |------- PREPARE(txn) -------->|                       |
    |------- PREPARE(txn) --------------------------------->|
    |                              |                       |
    |                        Acquire locks            Acquire locks
    |                        Log PREPARE              Log PREPARE
    |                        (via Paxos)              (via Paxos)
    |                              |                       |
    |<-------- PREPARED ----------|                       |
    |<-------- PREPARED ------------------------------|
    |                              |                       |
  Choose s_commit                  |                       |
  (TT.now().latest)                |                       |
    |                              |                       |
  COMMIT WAIT                      |                       |
  (until TT.now().earliest > s_commit)                     |
    |                              |                       |
    |------- COMMIT(s) ----------->|                       |
    |------- COMMIT(s) ----------------------------------->|
    |                              |                       |
    |                         Apply writes            Apply writes
    |                         Release locks           Release locks
    |                         Log COMMIT              Log COMMIT
    |                         (via Paxos)             (via Paxos)
    |                              |                       |
    |<-------- ACK ----------------|                       |
    |<-------- ACK -----------------------------------|
    |                              |                       |
  Return to client                 |                       |
```

**Key details**:

- **Locks are held across 2PC**: Prevents conflicting transactions from committing with interleaved timestamps
- **Paxos for each step**: PREPARE and COMMIT are both replicated via Paxos, ensuring durability and consistency
- **Commit wait happens at coordinator**: After all participants PREPARED, before sending COMMIT
- **Timestamp chosen before commit**: Coordinator picks s_commit, does commit wait, then tells participants

### Read-Only Transactions: Lock-Free Reads

Spanner's killer feature: **Read-only transactions execute without locks and without blocking writes.**

```sql
BEGIN TRANSACTION READ ONLY;
SELECT * FROM accounts WHERE user_id = 'alice';
SELECT * FROM orders WHERE user_id = 'alice';
COMMIT;
```

**Protocol**:
```
1. Assign snapshot timestamp: s_read = TT.now().latest
2. For each read:
   a. Route to replica (ANY replica, not necessarily leader)
   b. Read most recent committed version with commit timestamp ≤ s_read
   c. If that version isn't available yet, WAIT until it's committed
3. Return results to client
```

**Why this is safe**:

Since all writes use commit wait, by the time absolute time reaches `s_read`, all transactions with commit timestamps ≤ `s_read` have completed their commit wait and are visible.

**Why this is fast**:

- No locks acquired (doesn't block writes)
- Can read from any replica (load balancing, geo-locality)
- No 2PC (local operation at each tablet)

**Typical latency**:
- Local datacenter read: 1-10ms
- Cross-continental read: 50-100ms (network latency, not coordination)

### Schema Changes: Online Without Downtime

Traditional databases require:
1. Take system offline
2. Run schema migration
3. Bring system back online

Spanner performs schema changes **while serving traffic**:

```sql
ALTER TABLE accounts ADD COLUMN email VARCHAR(255);
```

**Protocol**:

1. **Prepare phase**: Assign a future timestamp t_schema (far enough in the future that all in-flight transactions will finish)
2. **Propagate**: Send schema change to all Paxos groups
3. **Wait**: Transactions with t_commit < t_schema use old schema, t_commit ≥ t_schema use new schema
4. **Activate**: Once TrueTime passes t_schema, new schema is active

**Example timeline**:
```
t=0:    Schema change initiated, assign t_schema = 100 seconds from now
t=5:    Transaction T1 starts, reads old schema (will commit at t < 100)
t=10:   Schema change propagated to all nodes
t=95:   Transaction T2 starts, reads old schema (will commit at t < 100)
t=100:  Schema change becomes active
t=105:  Transaction T3 starts, reads new schema
```

**Key insight**: TrueTime gives us a global "switching point" where everyone agrees on which schema version to use, based purely on timestamps. No coordination required at activation time.

### Replication: Paxos Groups and Leader Leases

Each tablet is replicated across 5-7 replicas using Paxos:

```
Paxos Group for Tablet A:
  ├─ Leader (US-West-1) ← handles reads and coordinates writes
  ├─ Replica (US-West-2)
  ├─ Replica (US-East-1)
  ├─ Replica (Europe-1)
  └─ Replica (Asia-1)
```

**Leader leases**:

To provide low-latency reads, the leader maintains a **time-bounded lease**:

```python
class Leader:
    def __init__(self):
        self.lease_interval = None  # TrueTime interval [start, end]

    def acquire_lease(self):
        # Get votes from majority of replicas
        # Each replica grants lease for 10 seconds
        self.lease_interval = TrueTime.now().latest + 10

    def can_serve_read(self, timestamp):
        # Can serve if:
        # 1. Lease is valid
        # 2. Timestamp is within lease interval
        return TrueTime.now().earliest < self.lease_interval and \
               timestamp <= self.lease_interval
```

**Disjointness invariant**: At most one leader at any time.

**Enforcement**: Leaders must continuously renew leases. Before lease expires, must either:
- Renew (get votes from majority)
- Step down (stop serving reads/writes)

If a leader becomes partitioned and can't renew, it must abdicate after lease expires. Another replica can then become leader.

**External consistency for leader changes**:

When a new leader is elected, it must:
1. Wait for previous leader's lease to expire (based on TrueTime)
2. Acquire new lease
3. Determine the maximum committed timestamp (s_max)
4. Only accept new transactions with timestamps > s_max

This ensures no timestamp reordering across leader changes.

---

## Part 3: PRODUCTION NUMBERS AND REAL-WORLD USE

### Performance Characteristics

**From Google's published data (circa 2012)**:

**Latency (typical)**:
- Read-only transaction (single datacenter): 0.4-2ms
- Read-only transaction (cross-continental): 10-100ms (mostly network)
- Read-write transaction (single datacenter): 9-17ms
- Read-write transaction (cross-continental): 50-100ms

**Breakdown of read-write latency**:
```
Total: 14.4ms
  ├─ Network: 4.6ms (client ↔ server)
  ├─ Reads: 1.8ms
  ├─ Paxos (2PC PREPARE): 4.2ms
  ├─ Commit wait: 2.0ms (2× average TrueTime uncertainty)
  └─ Paxos (2PC COMMIT): 1.8ms
```

**Throughput**:
- Single Paxos group: ~10,000 writes/sec
- Read-only queries: Scales linearly with replicas (no locks)

**TrueTime uncertainty**:
- 50th percentile: 1-2ms
- 99th percentile: 3-7ms
- 99.9th percentile: <10ms
- Worst case (GPS outage): Falls back to atomic clocks, uncertainty grows ~1μs/sec

### Scaling AdWords: $200B+ Business on Spanner

Google AdWords generates over $200 billion in revenue annually. It runs on Spanner.

**The requirements**:

1. **Atomicity**: Advertiser updates budget, must propagate to all campaigns instantly
2. **Consistency**: Don't overspend budgets (even by a penny)
3. **Availability**: 99.999% uptime (downtime = lost revenue)
4. **Latency**: Bid evaluation <10ms (auction happens in real-time)
5. **Scale**: Billions of auctions per day

**The old system (2010)**:

- Sharded MySQL
- Manual shard management
- Application-level distributed transactions
- Eventual consistency for many operations
- Frequent budget overspending, required manual reconciliation

**The Spanner migration**:

Google migrated AdWords to Spanner over 2 years (2011-2013):

1. **Phase 1**: Shadow traffic (dual-write to old and new systems, compare results)
2. **Phase 2**: Read migration (serve reads from Spanner, writes still to MySQL)
3. **Phase 3**: Write migration (write to Spanner, async replicate to MySQL for rollback)
4. **Phase 4**: Full migration (MySQL decommissioned)

**The benefits**:

- **Eliminated shard management**: Spanner handles data placement automatically
- **Simplified code**: No more application-level transactions, use SQL
- **Exact budget enforcement**: Serializability prevents overspending
- **Lower latency**: Read-only transactions don't block, schema flexible indexing

**The numbers**:

- Data size: Petabytes of advertiser data
- Transaction rate: Millions per second
- Geographic span: 30+ datacenters globally
- Consistency: Full serializability, no budget violations
- Availability: 99.999% (5 minutes downtime per year)

### Lessons Learned

**Lesson 1: Time uncertainty is manageable**

Google's hardware investment (GPS + atomic clocks) was expensive upfront but:
- Cost amortizes over massive scale
- TrueTime became a platform feature for many services
- Uncertainty of 1-7ms is acceptable for most applications

**Other companies' response**: Cloud providers now offer time synchronization APIs:
- AWS Time Sync Service (microsecond accuracy)
- Azure Time Service (1ms accuracy)
- Google Cloud (uses Spanner's TrueTime)

**Lesson 2: Commit wait is cheaper than you think**

Adding 2-14ms to writes sounds expensive, but:
- It eliminates global coordination (which costs 50-500ms)
- Read-only transactions are lock-free (huge win)
- Most applications tolerate 10ms write latency

**Lesson 3: CAP theorem isn't violated—but nuanced**

Spanner chooses consistency over availability:
- During partitions, minority side can't commit (loses availability)
- But with 5+ replicas across continents, partitions are rare
- In practice: 99.999% availability despite strong consistency

**Lesson 4: External consistency is worth it**

Applications built on Spanner are simpler:
- No eventual consistency edge cases
- No conflict resolution logic
- Can use SQL and ACID guarantees

This is the **evidence principle**: Strong guarantees (external consistency) eliminate uncertainty in application logic. The cost (commit wait) is paid once in the database, not repeatedly in every application.

---

## Part 4: MASTERY (Third Pass)—Deep Technical Insights

### TrueTime Implementation Details

The TrueTime paper revealed the implementation:

**Time master architecture**:

Each datacenter has multiple time masters:
```
Datacenter
  ├─ GPS Time Masters (read GPS receivers)
  │   ├─ Master 1 (primary GPS)
  │   ├─ Master 2 (secondary GPS)
  │   └─ Master 3 (backup GPS)
  └─ Atomic Clock Time Masters (read atomic clocks)
      ├─ Master 4 (atomic clock 1)
      └─ Master 5 (atomic clock 2)
```

**Time master operation**:

```python
class TimeMaster:
    def __init__(self, source):
        self.source = source  # GPS or atomic clock
        self.last_sync = None
        self.drift_rate = None  # Measured drift from source

    def get_time(self):
        current_source_time = self.source.read()
        uncertainty = self.compute_uncertainty()
        return Interval(
            earliest=current_source_time - uncertainty,
            latest=current_source_time + uncertainty
        )

    def compute_uncertainty(self):
        # Uncertainty grows since last sync
        time_since_sync = local_clock() - self.last_sync
        uncertainty = time_since_sync * self.drift_rate

        # Add source-specific uncertainty
        if self.source.type == 'GPS':
            uncertainty += 1e-6  # GPS: ±1μs
        else:
            uncertainty += 1e-7  # Atomic: ±0.1μs base

        return uncertainty
```

**Client-side TrueTime**:

Machines running Spanner:
```python
class TrueTimeClient:
    def __init__(self):
        self.time_masters = [TM1, TM2, TM3, TM4, TM5]
        self.last_sync = None
        self.local_clock_when_synced = None
        self.synchronized_time = None

    def now(self):
        # Sync periodically (every 30 seconds)
        if time_since(self.last_sync) > 30:
            self.sync()

        # Compute current time based on last sync + local clock drift
        elapsed = local_clock() - self.local_clock_when_synced
        current_time = self.synchronized_time + elapsed

        # Compute uncertainty (grows since last sync)
        uncertainty = elapsed * LOCAL_CLOCK_DRIFT_RATE
        uncertainty += self.sync_uncertainty

        return Interval(
            earliest=current_time - uncertainty,
            latest=current_time + uncertainty
        )

    def sync(self):
        # Poll multiple time masters
        responses = []
        for tm in self.time_masters:
            try:
                interval = tm.get_time()
                responses.append(interval)
            except:
                continue  # Tolerate failures

        # Take intersection of intervals (conservative estimate)
        earliest = max(r.earliest for r in responses)
        latest = min(r.latest for r in responses)

        if earliest > latest:
            # Disagreement, use widest bound
            earliest = min(r.earliest for r in responses)
            latest = max(r.latest for r in responses)

        self.synchronized_time = (earliest + latest) / 2
        self.sync_uncertainty = (latest - earliest) / 2
        self.local_clock_when_synced = local_clock()
        self.last_sync = local_clock()
```

**Handling GPS outages**:

If GPS fails (e.g., antenna damaged), Spanner falls back to atomic clocks:
- Atomic clocks drift ~1μs/sec
- After 10 seconds: uncertainty ~10μs
- After 1 hour: uncertainty ~3.6ms
- After 10 hours: uncertainty ~36ms

Spanner increases commit wait proportionally. If uncertainty reaches ~50ms, it alerts operators to fix GPS.

### Concurrency Control: Wound-Wait Deadlock Prevention

Spanner uses **wound-wait** to prevent deadlocks:

**The problem**:
```
Transaction T1 (timestamp 100):
  - Holds lock on row A
  - Waiting for lock on row B

Transaction T2 (timestamp 200):
  - Holds lock on row B
  - Waiting for lock on row A

→ Deadlock!
```

**Wound-wait solution**:

When transaction T_new requests a lock held by T_old:
- If T_new.timestamp < T_old.timestamp: T_new "wounds" T_old (forces abort)
- If T_new.timestamp > T_old.timestamp: T_new waits

**Example**:
```
T1 (ts=100) holds lock on A
T2 (ts=200) holds lock on B

T1 requests lock on B:
  - T1.ts (100) < T2.ts (200)
  - T1 wounds T2 → T2 aborts, releases B
  - T1 acquires B, proceeds

T2 retries with new timestamp 250:
  - No conflicts (T1 completed)
  - Succeeds
```

**Why this works**:

- Older transactions (lower timestamps) have priority
- No cycles possible: If T1 waits for T2, then T1.ts > T2.ts
- Transactions form a DAG based on timestamps, DAGs can't have cycles

**Trade-off**: Younger transactions get aborted more often, but they retry quickly. Overall throughput increases due to no deadlock detection overhead.

### Snapshot Isolation for Read-Only Transactions

Spanner's read-only transactions use **multi-version concurrency control (MVCC)**:

**Versioned storage**:

Each row stores multiple versions:
```
row_id='alice' versions:
  (data='balance:100', commit_ts=50)
  (data='balance:150', commit_ts=75)
  (data='balance:200', commit_ts=120)
  (data='balance:180', commit_ts=145)
```

**Read protocol**:

```python
def read_only_transaction(queries):
    # Pick snapshot timestamp
    s_snapshot = TrueTime.now().latest

    results = []
    for query in queries:
        # For each row, find latest version ≤ s_snapshot
        for row in query.rows:
            version = row.get_version_at(s_snapshot)
            results.append(version)

    return results
```

**Safe time**: Each replica tracks "safe time" = the minimum timestamp at which it can serve reads:

```python
class Replica:
    def __init__(self):
        self.safe_time = 0  # Can serve reads up to this timestamp

    def update_safe_time(self):
        # Safe time = min of:
        # 1. Latest committed Paxos write
        # 2. Minimum prepared timestamp (from 2PC)
        self.safe_time = min(
            self.max_committed_timestamp,
            self.min_prepared_timestamp
        )

    def can_serve_read(self, timestamp):
        return timestamp <= self.safe_time
```

If a read-only transaction requests data at timestamp `t` but `safe_time < t`, the replica waits until safe time advances (i.e., until transactions with timestamps ≤ t have committed).

**Non-blocking invariant**: Read-only transactions never block writes. Writes advance safe time, allowing reads to proceed.

### Directory Movement: Load Balancing and Placement

Spanner automatically migrates directories (groups of rows) between tablets:

**Triggers for movement**:
1. **Load balancing**: Tablet too hot, split and move
2. **Data growth**: Tablet too large, split
3. **Geo-locality**: Move data closer to users
4. **Failure recovery**: Replica failure, move to healthy zone

**Movement protocol (using Paxos)**:

```
Source Paxos group → Destination Paxos group

1. Source: Take snapshot of directory at timestamp t_move
2. Source: Continue serving traffic while copying
3. Copy data to destination (incremental, in background)
4. When caught up, do atomic switch:
   a. Source stops accepting writes
   b. Destination applies final delta
   c. Metadata updated (directory now owned by destination)
   d. Clients redirected to destination
5. Source deletes directory data
```

**Timestamp assignment**: Directory movement preserves timestamp ordering:
- All transactions on source before movement: timestamps < t_move
- All transactions on destination after movement: timestamps > t_move

This maintains external consistency across movements.

---

## Key Takeaways

### What Made Spanner Possible

1. **TrueTime**: Explicit uncertainty bounds transform time from a liability into an asset
2. **Commit wait**: Trading latency for consistency—2-14ms wait eliminates global coordination
3. **Paxos everywhere**: Every tablet replicated, every write durable, consensus on all state changes
4. **MVCC**: Multi-version storage enables lock-free reads at any timestamp
5. **Distributed transactions with 2PC**: Coordinated by Paxos leaders, made atomic and durable

### When to Use Spanner-Style Architecture

**Good fit**:
- Global applications requiring strong consistency
- Complex transactions across many rows/tables
- Need for SQL and schema flexibility
- Can tolerate 10-100ms write latency
- Have resources for time synchronization infrastructure

**Poor fit**:
- Ultra-low latency writes required (<5ms)
- Eventual consistency acceptable
- Simple key-value access patterns
- Single-region deployment
- Budget-constrained (Spanner-level infrastructure is expensive)

### Implementing TrueTime Without Google's Hardware

Modern alternatives:

1. **AWS Time Sync Service**: Microsecond accuracy using GPS and atomic clocks in AWS datacenters
2. **Azure Time**: 1ms accuracy with PTP (Precision Time Protocol)
3. **NTP with bounded uncertainty**: Configure NTP conservatively, measure worst-case drift, use bounded intervals

**DIY TrueTime**:
```python
class SimpleTrueTime:
    def __init__(self, max_drift_ms=10):
        self.max_drift = max_drift_ms / 1000.0  # Convert to seconds
        self.last_ntp_sync = None

    def now(self):
        current_time = time.time()
        time_since_sync = current_time - self.last_ntp_sync
        uncertainty = time_since_sync * 50e-6  # Assume 50ppm drift
        uncertainty = max(uncertainty, self.max_drift)

        return Interval(
            earliest=current_time - uncertainty,
            latest=current_time + uncertainty
        )
```

Won't match Google's 1-7ms uncertainty, but 10-50ms is still useful for many applications.

### The Evidence Lens on Spanner

Spanner is a masterclass in **evidence-based system design**:

- **Time evidence**: TrueTime generates timestamp intervals with proven bounds
- **Commit evidence**: Paxos replication proves majority accepted the write
- **Ordering evidence**: Commit wait proves timestamp is in the past everywhere
- **Consistency evidence**: 2PC proves all participants agreed on outcome
- **Liveness evidence**: Leader leases prove at most one leader at a time

Each piece of evidence has a **lifetime** (TrueTime uncertainty, lease duration), **scope** (which tablet, which datacenter), and **verifiability** (can be checked by any node).

When evidence expires or is unavailable, the system **degrades gracefully**:
- If TrueTime uncertainty exceeds threshold: Increase commit wait
- If leader lease expires: Abdicate, elect new leader
- If replica fails: Paxos continues with remaining majority

This is the pattern: **Generate evidence, bound its uncertainty, verify at boundaries, degrade when evidence is weak.**

---

## Next Steps

We've seen how Google solved global consistency by solving time. Next, we'll explore a different approach to the same problem: **Amazon Dynamo**, which chose availability over consistency and pioneered the modern "AP" database design.

**Continue to**: [Amazon Dynamo: Shopping Cart That Scaled](./amazon-dynamo.md)

**Related chapters**:
- [Chapter 2: Time and Order](../chapter-02/index.md) - Logical clocks and causality
- [Chapter 3: Consensus](../chapter-03/index.md) - Paxos and Raft algorithms
- [Chapter 6: Replication](../chapter-06/index.md) - Multi-version concurrency control

---

**References**:
- Corbett et al., "Spanner: Google's Globally-Distributed Database" (OSDI 2012)
- Shute et al., "F1: A Distributed SQL Database That Scales" (VLDB 2013)
- Bacon et al., "Spanner: Becoming a SQL System" (SIGMOD 2017)

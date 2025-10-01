# NewSQL: Having Your ACID and Scaling Too

## The Impossible Made Real

> "For decades, we believed horizontal scalability and ACID guarantees were mutually exclusive. Then Google published the Spanner paper."

The year was 2012. The distributed systems community had accepted the NoSQL trade-offs: to scale horizontally, you must abandon ACID. CAP theorem proved it mathematically. Production systems confirmed it empirically. Then Google quietly announced they'd been running a globally distributed, strongly consistent, ACID-compliant database at scale for years.

Spanner wasn't supposed to be possible.

## The NewSQL Revolution

### What Makes NewSQL Different

NewSQL systems provide:
- **Full ACID guarantees** - Not just "mostly consistent"
- **Horizontal scalability** - Add nodes for more capacity
- **SQL interface** - Familiar programming model
- **Distributed by design** - Not bolted on later

### The Key Innovation: Consensus at the Storage Layer

Traditional databases use two-phase commit (2PC) for distributed transactions:

```
Coordinator → Prepare → All Participants
            ← Vote →
Coordinator → Commit/Abort → All Participants
            ← Acknowledgment →
```

**Problem**: If coordinator fails after prepare, participants block indefinitely.

NewSQL uses consensus (Paxos/Raft) instead:

```
Transaction → Paxos/Raft → Majority Agreement → Commit
           No single point of failure
           Minority can fail without blocking
```

## Spanner: The Impossible Database

### The TrueTime Innovation

Spanner's secret weapon: **synchronized atomic clocks with bounded uncertainty**.

```
TrueTime API:
- TT.now() returns [earliest, latest] interval
- TT.before(t) - true if t definitely passed
- TT.after(t) - true if t definitely future

Uncertainty typically 4ms (1-7ms range)
```

### External Consistency via Commit-Wait

**The Genius**: Wait out clock uncertainty before making commits visible.

```python
def commit_transaction(txn):
    # Get commit timestamp
    commit_ts = TT.now().latest

    # Write to Paxos groups
    for group in affected_groups:
        group.paxos_write(txn, commit_ts)

    # CRITICAL: Wait until timestamp definitely passed
    while not TT.after(commit_ts):
        sleep(0.001)  # Wait out uncertainty

    # Now safe to make visible
    txn.mark_visible()
```

**Result**: If transaction T1 completes before T2 starts, T1's timestamp < T2's timestamp. **Guaranteed**.

### Global Scale Architecture

```
┌─────────────────────────────────────────────┐
│            Universe (Deployment)            │
├─────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Zone 1  │  │  Zone 2  │  │  Zone 3  │ │
│  │  (US-E)  │  │  (US-W)  │  │  (EU-W)  │ │
│  └──────────┘  └──────────┘  └──────────┘ │
│       ↓             ↓             ↓         │
│  ┌──────────────────────────────────────┐  │
│  │         Placement Driver              │  │
│  │   (Decides replica placement)         │  │
│  └──────────────────────────────────────┘  │
│       ↓             ↓             ↓         │
│  ╔═══════════╗ ╔═══════════╗ ╔═══════════╗│
│  ║ Paxos     ║ ║ Paxos     ║ ║ Paxos     ║│
│  ║ Group 1   ║ ║ Group 2   ║ ║ Group 3   ║│
│  ║ [A-M data]║ ║ [N-S data]║ ║ [T-Z data]║│
│  ╚═══════════╝ ╚═══════════╝ ╚═══════════╝│
└─────────────────────────────────────────────┘
```

### Production Numbers (from Google)

- **Availability**: 99.999% (5 nines) multi-region
- **Latency**: 8.7ms median read, 22.5ms median write (global)
- **Scale**: Trillions of requests/day, exabytes of data
- **Consistency**: Zero consistency violations in production

## CockroachDB: Spanner for Mortals

### The Problem with TrueTime

TrueTime requires:
- Atomic clocks (expensive)
- GPS receivers (datacenter modifications)
- Custom hardware (not cloud-friendly)

Most companies can't replicate Google's infrastructure.

### Hybrid Logical Clocks (HLC)

CockroachDB's solution: Combine physical time with logical counters.

```python
class HybridLogicalClock:
    def __init__(self):
        self.physical = 0
        self.logical = 0

    def update(self, msg_time=None):
        now = time.time()

        if msg_time:
            # Receive: max of local and message time
            if msg_time.physical > now:
                # Message from future, use it
                self.physical = msg_time.physical
                self.logical = msg_time.logical + 1
            elif msg_time.physical == self.physical:
                # Same physical time, increment logical
                self.logical = max(self.logical, msg_time.logical) + 1
            else:
                # Our time is ahead
                self.physical = now
                self.logical = 0
        else:
            # Local event
            if now > self.physical:
                self.physical = now
                self.logical = 0
            else:
                self.logical += 1

        return (self.physical, self.logical)
```

**Trade-off**: Weaker than external consistency (can't guarantee global ordering), but provides **causal consistency** without special hardware.

### Multi-Version Concurrency Control (MVCC)

Every write creates a new version with HLC timestamp:

```
Key: "balance"
Versions:
  - (10:00:00.000, 0): $1000
  - (10:00:05.123, 0): $900
  - (10:00:10.456, 1): $1100
```

Reads at any timestamp see consistent snapshot:
- Read at 10:00:03 → sees $1000
- Read at 10:00:07 → sees $900
- Read at 10:00:12 → sees $1100

### Production Architecture

```python
class CockroachRange:
    """64MB of contiguous keyspace"""

    def __init__(self, start_key, end_key):
        self.raft_group = RaftGroup(
            replicas=self.select_replicas(num=3)
        )
        self.leaseholder = self.elect_leaseholder()

    def read(self, key, timestamp):
        if self.leaseholder.is_local():
            # Fast path: read from leaseholder
            return self.local_read(key, timestamp)
        else:
            # Forward to leaseholder
            return self.forward_to_leaseholder(key, timestamp)

    def write(self, key, value):
        # All writes go through Raft
        proposal = WriteProposal(key, value, hlc.now())
        return self.raft_group.propose(proposal)
```

## FoundationDB: The Database Database

### Record Layer Architecture

FoundationDB takes a different approach: **minimal kernel + layers**.

```
┌─────────────────────────────────┐
│     SQL Layer (Optional)        │
├─────────────────────────────────┤
│    Document Layer (Optional)    │
├─────────────────────────────────┤
│     Record Layer (Indexes)      │
├─────────────────────────────────┤
│  FoundationDB Core (K/V Store)  │
│   - ACID transactions           │
│   - Strict serializability      │
│   - Automatic sharding          │
└─────────────────────────────────┘
```

### Deterministic Simulation Testing

FoundationDB's secret: **test everything deterministically**.

```python
class DeterministicSimulator:
    """Reproduce any bug deterministically"""

    def run_test(self, seed):
        random.seed(seed)

        # Control all non-determinism
        self.control_time()
        self.control_network()
        self.control_disk_io()
        self.control_cpu_scheduling()

        # Run millions of failure scenarios
        for scenario in self.generate_failures():
            cluster = self.create_cluster()

            # Inject failures
            scenario.apply(cluster)

            # Verify invariants still hold
            assert cluster.check_consistency()
            assert cluster.check_durability()
            assert cluster.check_availability()
```

**Result**: Bugs found in simulation reproduce exactly in production.

## NewSQL in Production

### When to Use NewSQL

**Perfect for:**
- Global applications needing consistency
- Financial systems (payments, trading)
- Inventory management across regions
- User authentication and sessions
- Configuration management

**Avoid for:**
- Analytics workloads (use columnar stores)
- Time-series data (use specialized TSDB)
- Blob storage (use object stores)
- Cache layers (use Redis/Memcached)

### Migration Patterns

```python
def migrate_to_newsql():
    """Progressive migration strategy"""

    # Phase 1: Shadow reads
    def read_with_shadow(key):
        old_value = legacy_db.read(key)
        new_value = newsql_db.read(key)
        if old_value != new_value:
            log_discrepancy(key, old_value, new_value)
        return old_value  # Still trust legacy

    # Phase 2: Shadow writes
    def write_with_shadow(key, value):
        legacy_db.write(key, value)
        newsql_db.write(key, value)  # Async, best-effort

    # Phase 3: Gradual cutover
    def read_with_cutover(key):
        if should_use_newsql(key):  # Percentage/allowlist
            return newsql_db.read(key)
        return legacy_db.read(key)

    # Phase 4: Full migration
    def read(key):
        return newsql_db.read(key)  # Legacy retired
```

### Operational Challenges

**Challenge 1: Cross-Region Latency**
- Physics: Light takes 70ms across US
- Reality: Add protocol overhead → 100ms+ RTT
- Solution: Read replicas, follower reads, regional partitioning

**Challenge 2: Hot Spots**
```python
# Problem: Sequential IDs create hot ranges
user_id = increment_counter()  # 1, 2, 3, 4...
# All writes hit same range!

# Solution: Hash prefix distribution
user_id = f"{hash(timestamp) % 100:02d}{increment_counter()}"
# Writes spread across 100 ranges
```

**Challenge 3: Transaction Contention**
```python
# Problem: Popular rows cause serialization
UPDATE inventory SET count = count - 1 WHERE product_id = 'hot_item'
# All transactions serialize on this row

# Solution: Commutative operations
INSERT INTO inventory_deltas (product_id, delta) VALUES ('hot_item', -1)
# Periodic aggregation, no contention
```

## The Cost of Consistency

### Latency Breakdown

Global transaction in Spanner:
```
Client request arrives        : 0ms
Acquire locks (local)        : 2ms
Prepare at participants      : 50ms (cross-region)
Paxos consensus              : 20ms
Commit wait (TrueTime)       : 7ms
Release locks                : 2ms
-----------------------------------
Total                        : 81ms
```

Compare with eventually consistent:
```
Client request arrives        : 0ms
Write to local replica       : 2ms
Async replication (hidden)   : 50ms (not blocking)
-----------------------------------
Total (visible latency)      : 2ms
```

**40x difference** - This is the price of consistency.

### The Jepsen Reports

Kyle Kingsbury's Jepsen tests revealed:
- **CockroachDB**: Passed (after fixing early bugs)
- **TiDB**: Passed (with caveats on isolation)
- **YugabyteDB**: Failed initially, fixed issues, passed retest
- **FaunaDB**: Passed with strong isolation

Key finding: **NewSQL systems generally deliver on ACID promises**, unlike many NoSQL systems that failed consistency tests.

## Evolution and Future

### The Serverless Push

Next generation NewSQL goes serverless:
- **Aurora Serverless v2**: MySQL/PostgreSQL compatible, auto-scaling
- **CockroachDB Serverless**: Pay per request, no capacity planning
- **PlanetScale**: Serverless MySQL with Vitess sharding

### Multi-Region by Default

Modern NewSQL assumes global deployment:
```python
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email STRING UNIQUE,
    region STRING AS (CASE
        WHEN ip_location IN ('US', 'CA', 'MX') THEN 'americas'
        WHEN ip_location IN ('GB', 'FR', 'DE') THEN 'europe'
        ELSE 'asia-pacific'
    END) STORED,
    -- Partition by region for data sovereignty
    PARTITION BY LIST (region) (
        PARTITION americas VALUES IN ('americas'),
        PARTITION europe VALUES IN ('europe'),
        PARTITION asia VALUES IN ('asia-pacific')
    )
);
```

### Hardware Acceleration

- **RDMA networking**: Bypass kernel, microsecond latency
- **Persistent memory**: DRAM speed with SSD persistence
- **GPU acceleration**: Parallel query execution
- **Computational storage**: Push computation to SSDs

## Summary: The NewSQL Promise

NewSQL proved the impossible: **ACID at scale is achievable**.

### Key Innovations

1. **Consensus instead of 2PC** - No blocking on coordinator failure
2. **Time as a weapon** - TrueTime or HLC for consistency
3. **MVCC everywhere** - Lock-free reads, time travel queries
4. **Horizontal scaling** - Add nodes for capacity
5. **Geographic distribution** - Data follows users

### The Evidence Trail

- **Consistency evidence**: Consensus certificates, HLC timestamps, MVCC versions
- **Durability evidence**: Raft logs, majority acknowledgments
- **Availability evidence**: Leaseholder leases, replica health
- **Freshness evidence**: TrueTime bounds, HLC guarantees

### When to Choose NewSQL

Choose when you need:
- ACID guarantees
- Horizontal scalability
- Geographic distribution
- SQL familiarity

Avoid when you have:
- Analytics workloads (use OLAP)
- Simple K/V needs (use Redis)
- Document flexibility (debatable)
- Extreme write throughput (use Cassandra)

The future is hybrid: NewSQL for transactions, specialized systems for specific workloads, unified by application logic.

---

**Mental Model**: NewSQL systems maintain ACID invariants through consensus evidence (Paxos/Raft certificates) and temporal evidence (TrueTime/HLC), accepting coordination latency to provide consistency at scale.

Continue to [Storage Engines →](storage-engines.md)
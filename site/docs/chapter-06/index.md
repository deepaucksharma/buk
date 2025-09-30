# Chapter 6: The Storage Revolution

## Introduction: The Database Wars and What They Taught Us

"In 20 years, we went from 'ACID or die' to 'eventual consistency is fine' back to 'we need ACID at scale.'"

This isn't technological whiplash—it's the distributed systems community learning, the hard way, that storage is the hardest problem in distributed computing. Every other challenge we've explored—impossibility results, time and causality, consensus, replication—converges in storage systems. A database must preserve data across crashes (durability), serve it consistently across replicas (consistency), remain available during failures (availability), and do all this at scale (performance).

The laws of physics say you can't have everything. The CAP theorem proved it mathematically. But businesses need their data. So for 50 years, database designers have fought these impossibilities, inventing increasingly sophisticated mechanisms to preserve what matters most while gracefully degrading what doesn't.

### The Pendulum Swings

**1970s-1990s: The ACID Era**
Relational databases dominated. ACID guarantees were sacred. Transactions were serializable. Every write was durable. Two-phase commit coordinated distributed transactions. Scaling meant bigger machines (vertical scaling). Oracle, DB2, SQL Server ruled the enterprise.

**Problem**: The web era arrived. Google needed to index billions of pages. Amazon needed to serve millions of customers. Facebook needed to store billions of social connections. ACID didn't scale horizontally. Two-phase commit was too slow across datacenters. Vertical scaling hit physical limits.

**2000s-2010s: The NoSQL Revolution**
"The relational model is too rigid. ACID is too expensive. Eventual consistency is fine for most applications." Dynamo (2007) and Bigtable (2006) papers launched a thousand NoSQL databases. Cassandra, MongoDB, Redis, Riak, CouchDB proliferated. BASE (Basically Available, Soft state, Eventual consistency) replaced ACID. Horizontal scaling became easy. Consistency became hard.

**Problem**: Eventual consistency is harder than it looks. Developers don't reason well about conflict resolution. Business logic requires transactions. Compensating for inconsistency is expensive. "We traded away consistency for scalability and regret it every day."

**2010s-2020s: The NewSQL Renaissance**
"We can have ACID *and* scalability." Google Spanner (2012) proved it with TrueTime and global transactions. CockroachDB brought Spanner's ideas to open source. VoltDB, FoundationDB, TiDB emerged. Transactions returned. Serializability at scale became real.

**Problem**: Operational complexity. Global coordination is expensive. Cross-region latency is physics. CAP theorem still applies—NewSQL chooses consistency over availability during partitions.

**2020s-Present: The Convergence**
"Different data needs different guarantees. Let's support multiple consistency levels, multiple data models, and let applications choose." Azure Cosmos DB offers five consistency levels. PostgreSQL added JSON support. MongoDB added transactions. DynamoDB added ACID. The line between SQL and NoSQL blurs. **Polyglot persistence** gives way to **multi-model databases**.

### Why Storage Is the Hardest Problem

Storage uniquely combines every challenge:

**Durability**: Data must survive crashes, disk failures, datacenter fires, regional outages. Evidence of durability: replication, write-ahead logs, checksums, backups. But replication is expensive, logs grow unbounded, checksums add overhead, backups are stale.

**Consistency**: Multiple replicas must agree on state. Evidence of consistency: quorum certificates, version vectors, Merkle trees, timestamps. But quorums require majority, vectors grow large, Merkle trees add space, timestamps rely on clocks.

**Performance**: Reads and writes must be fast. Millisecond latencies, millions of operations per second. But coordination is slow, replication adds latency, consensus requires rounds, strong consistency requires synchronization.

**Scalability**: Must handle terabytes, petabytes, exabytes. Thousands of nodes, millions of clients. But large clusters partition more often, coordination overhead grows as O(n) or O(n²), failure rates increase linearly with cluster size.

Every storage system is a negotiation with these impossibilities. The art is in choosing which guarantees to provide, which to weaken, and how to degrade predictably when reality intrudes.

### What This Chapter Reveals

By the end, you'll understand:

1. **The ACID Era**: Why relational databases emerged, what ACID really means, and why it didn't scale
2. **The NoSQL Revolution**: How Dynamo and Bigtable changed everything, what BASE trade-offs actually mean
3. **The NewSQL Renaissance**: How Spanner achieved the impossible, why CockroachDB made different choices
4. **Multi-Model Databases**: Why Cosmos DB and modern PostgreSQL represent convergence
5. **Storage Engine Deep Dive**: How LSM trees and B-trees embody fundamental trade-offs
6. **Production Patterns**: How to choose, migrate, and operate storage systems in reality

More importantly, you'll internalize the **evidence-based mental model** for storage:

**Storage systems preserve invariants (durability, consistency, availability) by generating and verifying evidence (commits, quorums, checksums), with explicit modes that degrade predictably when evidence cannot be maintained.**

Every storage decision becomes comprehensible through this lens: "Spanner uses TrueTime intervals as freshness evidence, enabling external consistency at the cost of waiting out uncertainty" or "Cassandra uses vector clocks as causality evidence, accepting eventual consistency to avoid coordination costs."

### The Conservation Principle

Throughout this chapter, observe the **conservation of guarantees**: you cannot strengthen guarantees without adding coordination, and you cannot remove coordination without weakening guarantees. Every storage system exists somewhere on this spectrum:

**Strong Coordination (CP Systems)**:
- Evidence: Quorum commits, Paxos certificates, TrueTime intervals
- Guarantees: Linearizability, serializability, external consistency
- Cost: High latency, reduced availability during partitions

**Weak Coordination (AP Systems)**:
- Evidence: Vector clocks, version numbers, last-write-wins timestamps
- Guarantees: Eventual consistency, causal consistency at best
- Cost: Conflict resolution complexity, potential data loss

**Hybrid (Tunable Systems)**:
- Evidence: Application chooses (strong reads need quorum, weak reads use local)
- Guarantees: Per-operation choice
- Cost: Complexity, coordination budget management

The revolution in storage wasn't about discovering new physics—it was about learning to make these trade-offs explicit, principled, and comprehensible.

Let's begin with the problem that started it all: the bank account.

---

## Part 1: INTUITION (First Pass) — The Felt Need

### The Bank Account Problem

You have $1,000 in your checking account. You make two withdrawals simultaneously:

- **ATM in New York**: Withdraw $600 at 12:00:00.000
- **Online banking**: Withdraw $600 at 12:00:00.100 (100ms later)

Both systems check your balance: $1,000. Both see sufficient funds. Both approve the withdrawal. Your balance becomes $1,000 - $600 - $600 = **-$200**.

**This is unacceptable.** Banks cannot allow negative balances (ignoring overdraft protection). More fundamentally, this violates **conservation**: money cannot be created or destroyed except through authorized transactions.

#### The ACID Solution

Relational databases solved this with **transactions** and **ACID guarantees**:

**Atomicity**: Both withdrawals are atomic—either complete entirely or abort entirely. No partial withdrawals.

**Consistency**: Balance constraints are enforced. If both transactions commit, at least one must fail the balance check.

**Isolation**: Transactions execute as if they're alone. When ATM checks balance, it sees either $1,000 (before online withdrawal) or $400 (after). Never an intermediate state.

**Durability**: Once committed, withdrawals survive crashes, disk failures, power outages.

**How it works**:
```
Transaction 1 (ATM):
  BEGIN TRANSACTION
  SELECT balance FROM accounts WHERE id=123 FOR UPDATE  -- Lock the row
  -- balance = $1,000
  UPDATE accounts SET balance = balance - 600 WHERE id=123
  COMMIT  -- Release lock

Transaction 2 (Online):
  BEGIN TRANSACTION
  SELECT balance FROM accounts WHERE id=123 FOR UPDATE  -- Waits for lock...
  -- (Transaction 1 commits, balance now $400)
  -- balance = $400
  -- Withdrawal would overdraw! Abort.
  ROLLBACK
```

**Evidence**: The `FOR UPDATE` clause acquires a **lock**, which is evidence of exclusive access. Transaction 2 cannot proceed until Transaction 1 releases the lock. Locks prevent concurrent modifications, ensuring isolation.

**Guarantee vector**: `⟨Object, SS, SER, Fresh(lock), Idem(txn_id), Auth(user)⟩`
- Scope: Single object (account row)
- Order: Strict serializable (transactions have global order)
- Visibility: Serializable (see all previous committed transactions)
- Recency: Fresh (lock ensures latest committed value)
- Idempotence: Transaction ID prevents duplicate execution
- Auth: User credentials authorize action

**Mode**: Always Target—ACID systems don't degrade. They block or abort.

#### Why ACID Didn't Scale

This works beautifully on a single database server. But when you try to scale:

**Problem 1: Vertical Scaling Limits**
Bigger machines have physical limits: maximum CPU cores, RAM, disk throughput. Eventually you hit a ceiling. For high-traffic applications (Google search, Amazon checkout, Facebook feeds), one server isn't enough.

**Problem 2: Geographic Distribution**
Users in Tokyo shouldn't wait 200ms to talk to a database in Virginia. Low latency requires local replicas. But replicating ACID across datacenters requires distributed transactions.

**Problem 3: Two-Phase Commit (2PC) Is Slow**
To commit a transaction across multiple databases:

```
Phase 1 (Prepare):
  Coordinator: "Can you all commit?"
  Replica 1: "Yes" (after acquiring locks, writing to log)
  Replica 2: "Yes"
  Replica 3: "Yes"

Phase 2 (Commit):
  Coordinator: "Commit!"
  All replicas: Apply changes, release locks
```

**Problems**:
- Blocks on slowest replica (tail latency amplification)
- Coordinator failure stalls transaction (no progress without coordinator)
- Locks held for 2 network round-trips (cross-region: 200ms+ of blocking)
- Availability: Any replica unavailable = whole transaction blocks

**Real-world impact**: Amazon measured that 100ms of added latency decreased sales by 1%. Two-phase commit across US-East and US-West adds 60-100ms. Across continents: 200-300ms. Unacceptable for user-facing services.

**The realization**: ACID is perfect for correctness, terrible for scalability and latency. "We need a different approach."

### The Shopping Cart Revolution

Amazon faced a problem in the early 2000s: their shopping cart service kept going down during peak traffic. The relational database couldn't handle the load. ACID transactions were overkill—shopping carts don't need the same consistency as bank accounts.

**Insight**: It's okay if two datacenters briefly disagree about what's in your cart. Eventual consistency is acceptable. If you add an item in one datacenter and the replica lags 100ms, no big deal. When you check out, we'll resolve conflicts.

This led to **Dynamo** (2007), Amazon's distributed key-value store, and a radical idea: **give up consistency for availability**.

#### The Dynamo Design

**Architecture**:
- Data partitioned across nodes using consistent hashing
- Each partition replicated N times (N=3 typically)
- No master, no leader—every node can handle reads and writes
- **Sloppy quorum**: R + W > N (e.g., R=2, W=2, N=3)
  - Write succeeds when W nodes acknowledge
  - Read queries R nodes, returns latest value

**What happens during conflicts**:

User adds "Laptop" to cart in datacenter A.
User adds "Mouse" to cart in datacenter B (before replication).
Both writes propagate. Now replicas disagree: cart = {Laptop} vs cart = {Mouse}.

**Conflict resolution**:
- **Vector clocks**: Track causality. If neither write causally follows the other, it's a conflict.
- **Application-level merge**: Shopping cart merge is a union: {Laptop, Mouse}. Application decides.
- **Last-write-wins** (LWW): Use timestamps. Risky—clocks lie—but simple.

**Evidence**: Vector clocks provide **causality evidence**: if event A happened-before event B, vector clock proves it. If vector clocks are concurrent, there's a conflict requiring resolution.

**Guarantee vector**: `⟨Range, Causal, RA, EO, Idem(K), Auth⟩`
- Scope: Range (partition)
- Order: Causal (vector clocks preserve causality)
- Visibility: Read-atomic (read from single snapshot)
- Recency: Eventual order (replicas converge eventually)
- Idempotence: Keyed by operation ID
- Auth: Request signature

**Mode matrix**:
- **Target**: All N replicas reachable, R+W>N satisfied, conflicts rare
- **Degraded**: Some replicas down, sloppy quorum uses "hinted handoff" (write to temporary replica)
- **Floor**: Quorum unavailable—serve stale reads or reject writes (configuration-dependent)

#### The Trade-Off

**What Dynamo gained**:
- Availability: Always writable (even during partitions, sloppy quorum accepts writes)
- Scalability: No master bottleneck, linear scalability by adding nodes
- Low latency: Local writes (no cross-datacenter coordination)

**What Dynamo sacrificed**:
- Consistency: Concurrent writes conflict, application must resolve
- Complexity: Vector clocks grow, conflict resolution is application burden
- No transactions: Can't atomically update multiple keys

**When it's acceptable**: Shopping carts, session storage, user preferences—data where conflicts are rare and merge is obvious.

**When it's not**: Bank accounts, inventory counts, seat reservations—data where conflicts are unacceptable and money is at stake.

**The lesson**: Consistency is a spectrum, not a binary. Choose based on business requirements, not technical purity.

### The Global Database Dream

Google faced a different problem: services like Gmail, Google Ads, Google Play needed **global** storage with **strong consistency**. Eventual consistency doesn't work for ad budgets (can't overspend) or inventory (can't oversell).

But Google operates globally: datacenters on every continent. Users expect local latency. ACID across continents requires distributed transactions, which are slow. Can we have both?

#### The Spanner Impossibility

**Requirement**: External consistency (stronger than linearizability)
- If transaction T1 completes before T2 starts (in real-world wall-clock time), T1's effects must be visible to T2
- Essentially: respect causality based on real time, not just logical time

**Problem**: This requires global time synchronization. But clocks skew. NTP has ±10-100ms uncertainty. If clocks disagree by 100ms, you can't tell if T1 finished before T2 started.

**Standard impossibility argument**:
1. External consistency requires real-time ordering
2. Real-time ordering requires synchronized clocks
3. Synchronized clocks are impossible (bounded uncertainty at best)
4. Therefore, external consistency is impossible

**Google's answer**: "What if we make uncertainty explicit and wait it out?"

#### TrueTime: Making Uncertainty First-Class

Instead of a timestamp, TrueTime returns an **interval**: `[earliest, latest]`. "The true time is somewhere in this interval, guaranteed."

**How**:
- GPS receivers in every datacenter (GPS provides time within ±1ms)
- Atomic clocks in every datacenter (drift ≈ 1ms/year)
- Combine GPS and atomic clocks, compute uncertainty bound
- Typical interval: ±7ms (99.9th percentile)

**Transaction protocol**:
```
Write transaction:
1. Assign commit timestamp t
2. Wait until t.earliest > now.latest (uncertainty wait)
3. Then commit

Read transaction:
1. Assign snapshot timestamp s
2. Wait until s.earliest > now.latest
3. Read at snapshot s
```

**The magic**: By waiting out uncertainty, Spanner ensures that if commit completes before read starts (wall-clock time), the wait guarantees non-overlapping intervals. Real-time order is preserved.

**Cost**:
- Average commit latency: +7ms (wait time)
- 99.9th percentile: +10ms
- Infrastructure: GPS receivers + atomic clocks in every datacenter = $$$

**Evidence**: TrueTime intervals are **freshness evidence** with explicit uncertainty bounds. The commit wait converts uncertain time into certain order.

**Guarantee vector**: `⟨Global, SS, SER, Fresh(TT), Idem, Auth⟩`
- Scope: Global (transactions span the world)
- Order: Strict serializable
- Visibility: Serializable
- Recency: Fresh (TrueTime-proven)
- Idempotence: Transaction ID
- Auth: Strong (Google's internal auth)

**Mode matrix**:
- **Target**: TrueTime uncertainty < 10ms, all Paxos quorums healthy
- **Degraded**: Minority partitions become unavailable for writes (CP choice)
- **Floor**: TrueTime uncertainty exceeds threshold—commit waits longer or aborts
- **Recovery**: Paxos re-election, replay log

#### The Lesson

**Spanner proved**: You can have ACID at global scale. External consistency is possible.

**The catch**: You need specialized hardware (GPS + atomic clocks) and accept latency penalties (wait out uncertainty). Most companies can't or won't pay that cost.

**The broader insight**: Impossibility results have loopholes. CAP says "consistency or availability during partitions." Spanner chooses consistency (minority unavailable). FLP says "no deterministic consensus in async systems." Spanner assumes partial synchrony (TrueTime bounds). Every impossibility has assumptions; question the assumptions.

### What We've Learned (Intuition Pass)

**From bank accounts**: ACID is essential for some data. Transactions, isolation, durability matter. But coordination is expensive—doesn't scale horizontally, high latency across distance.

**From shopping carts**: Eventual consistency is acceptable for some data. Availability and low latency are worth occasional conflicts. But conflict resolution is complex—requires application logic, vector clocks, careful design.

**From Spanner**: Strong consistency at scale is possible—with enough money and clever engineering. But physics still constrains: must choose CP (unavailable during partitions), must wait out uncertainty (latency cost), must pay for hardware (GPS + atomic clocks).

**The unifying theme**: Storage is about choosing which invariants to protect (durability always, consistency sometimes, availability when possible) and using the right evidence (locks for isolation, vector clocks for causality, TrueTime for freshness) to enforce them.

Now let's formalize these insights with the full taxonomy of storage systems.

---

## Part 2: UNDERSTANDING (Second Pass) — The Limits and Solutions

### The ACID Era (1970-2000)

#### ACID Properties: A Deeper Look

**Atomicity**: All-or-nothing execution
- **Invariant protected**: Conservation (partial updates create/destroy data inconsistently)
- **Mechanism**: Write-ahead logging (WAL)
  - Before modifying data, write change to log
  - Log entry format: `<TxnID, Before, After, LSN>`
  - On crash: replay log to redo committed transactions, undo uncommitted
- **Evidence**: Log sequence number (LSN) proves transaction committed
- **Failure mode**: Torn writes (crash mid-transaction) → abort via undo log

**Consistency**: Valid state transitions
- **Invariant protected**: Application-defined constraints (balance ≥ 0, foreign key integrity, uniqueness)
- **Mechanism**: Constraint checking before commit
  - Check constraints in transaction context
  - Abort if violated
- **Evidence**: Constraint validation is proof of integrity
- **Failure mode**: Constraint violation → abort transaction

**Isolation**: Concurrent = sequential
- **Invariant protected**: Visibility (transactions see consistent snapshots)
- **Mechanism**: Locking or MVCC (multi-version concurrency control)
  - **Locking**: Acquire locks before access, block others
  - **MVCC**: Each transaction sees snapshot, writes create new version
- **Evidence**:
  - Locks: Lock grant is evidence of exclusive access
  - MVCC: Timestamp/LSN is evidence of snapshot consistency
- **Failure mode**: Deadlock (circular lock wait) → abort victim transaction

**Durability**: Survive failures
- **Invariant protected**: Persistence (committed data survives crashes)
- **Mechanism**: fsync to disk before acknowledging commit
  - WAL must hit stable storage (disk, SSD)
  - Data pages can be cached (will replay from log on recovery)
- **Evidence**: fsync completion is evidence of durability
- **Failure mode**: Disk failure → need replication or backup

#### Isolation Levels: The Hierarchy

Isolation is a spectrum, not a binary. SQL defines levels:

**Read Uncommitted**: No isolation
- See uncommitted changes from other transactions
- **Dirty reads**: Read data that might be aborted
- **Use case**: Almost never (analytics on approximate data)

**Read Committed**: See only committed data
- No dirty reads
- But **non-repeatable reads**: read same row twice, get different values (another transaction committed between reads)
- **Mechanism**: Short locks (release after read) or MVCC
- **Use case**: Default in many databases (PostgreSQL default)

**Repeatable Read**: Consistent snapshot
- Same reads return same values within transaction
- But **phantom reads**: range queries might see new rows (another transaction inserted)
- **Mechanism**: MVCC with snapshot isolation
- **Use case**: Most OLTP applications

**Serializable**: Full isolation
- Transactions execute as if serial (one at a time)
- No anomalies
- **Mechanism**: Strict two-phase locking (S2PL) or serializable snapshot isolation (SSI)
- **Cost**: High contention, many aborts
- **Use case**: Financial transactions, critical invariants

**Evidence hierarchy**:
- Read Uncommitted: No evidence (trust nothing)
- Read Committed: Commit evidence (LSN)
- Repeatable Read: Snapshot evidence (transaction start timestamp)
- Serializable: Serialization evidence (lock graph or dependency tracking)

#### Traditional RDBMS Architecture

**Storage layer**: B-tree indexes
- **Structure**: Balanced tree, sorted keys, O(log n) access
- **Invariant**: Order (keys sorted), balance (height ≤ log n)
- **Mechanism**: Copy-on-write or write-ahead logging
- **Trade-off**: Read-optimized (O(log n) lookup), write-heavy (random I/O, page splits)

**Transaction layer**: ARIES recovery algorithm
- **Write-ahead logging**: Log before data
- **Undo log**: Abort uncommitted transactions
- **Redo log**: Replay committed transactions
- **Checkpointing**: Periodically flush pages, truncate log

**Concurrency control**: Two-phase locking (2PL)
- **Growing phase**: Acquire locks
- **Shrinking phase**: Release locks (after commit/abort)
- **Guarantee**: Serializability
- **Cost**: Deadlocks possible (detect via cycle in wait-for graph, abort victim)

**Replication**: Primary-backup
- Primary handles writes
- Backups replay WAL (asynchronous or synchronous)
- Failover: Promote backup to primary
- **CP choice**: Synchronous replication = consistent but slow, Asynchronous = fast but potential data loss on failover

#### The Scaling Wall

**Problem 1**: Vertical scaling ceiling
- CPUs: Limited cores, limited frequency
- Memory: Limited capacity (terabytes expensive)
- Disk: Limited IOPS (SSDs help, but expensive)

**Problem 2**: Locking contention
- Hotspot key: Many transactions want same row
- All block on lock
- Throughput = 1 / lock hold time
- **Example**: Inventory count for popular item → serialized updates, low throughput

**Problem 3**: Replication bottleneck
- Primary serializes all writes
- Backups replay serially (WAL is sequential)
- Write throughput limited by primary, not total cluster capacity

**Problem 4**: Geographic latency
- Cross-region replication: 50-200ms
- Synchronous replication: Commit waits for slowest region
- Asynchronous replication: Failover loses recent writes

**The realization**: ACID is fundamentally hard to scale horizontally. Coordination (locks, 2PC) creates bottlenecks. Serialization (single primary, ordered log) prevents parallelism.

### The NoSQL Revolution (2000-2010)

The web era brought new workloads: read-heavy, write-heavy, key-value access, flexible schemas, massive scale. NoSQL systems said: "Let's rethink everything."

#### BASE Properties: The Anti-ACID

**Basically Available**: System remains operational (AP choice)
- **Invariant**: Availability promise (respond within SLA)
- **Mechanism**: Partition data, replicate widely, accept stale reads
- **Evidence**: Any replica can serve request (no quorum required)

**Soft state**: State may change without input (due to eventual consistency)
- **Invariant**: Convergence (replicas eventually agree)
- **Mechanism**: Anti-entropy, gossip protocols, read repair
- **Evidence**: Version vectors, Merkle trees (detect divergence)

**Eventual consistency**: If updates stop, replicas converge
- **Invariant**: Eventual order (all replicas apply same updates)
- **Mechanism**: Conflict resolution (LWW, CRDT, application logic)
- **Evidence**: Happens-before relation (vector clocks, causal order)

**Trade-off vs ACID**:
- ACID: Strong guarantees, low availability, low scale
- BASE: Weak guarantees, high availability, high scale

#### Key-Value Stores: Dynamo and Successors

**Amazon Dynamo (2007)**: The blueprint for AP systems

**Architecture**:
- **Consistent hashing**: Keys mapped to ring, nodes own ranges
  - Add/remove nodes: only adjacent ranges affected (incremental rebalancing)
  - Virtual nodes: Each physical node owns multiple ring positions (load balancing)
- **Replication**: Each key stored on N consecutive nodes (N=3 typical)
- **Sloppy quorum**: W + R > N (e.g., W=2, R=2, N=3)
  - Write to any W nodes (might not be the "primary" N due to failures)
  - Read from any R nodes, return all versions
- **Hinted handoff**: If primary node down, write to temporary node with hint "deliver to primary when available"
- **Anti-entropy**: Background Merkle tree sync to repair divergence

**Evidence types**:
- **Vector clocks**: Causality evidence
  - Each write increments writer's clock
  - Read sees multiple versions, vector clocks indicate causality
  - Concurrent versions = conflict (application resolves)
- **Merkle trees**: Divergence evidence
  - Hash tree of key ranges
  - Compare tree roots to detect differences
  - Traverse subtrees to find specific keys needing repair

**Guarantee vector**: `⟨Range, Causal, RA, EO, Idem(K), Auth⟩`
- Tunable: Increase W or R for stronger consistency (W=N, R=1 = read-after-write)

**Mode matrix**:
- **Target**: N replicas healthy, quorum satisfied
- **Degraded**: Sloppy quorum + hinted handoff (temporary replicas)
- **Floor**: Fewer than R replicas → stale reads or unavailable
- **Recovery**: Anti-entropy repairs divergence

**Successors**:
- **Apache Cassandra**: Dynamo + Bigtable (column families, CQL)
- **Riak**: Dynamo clone with pluggable backends
- **Voldemort**: LinkedIn's Dynamo implementation

**Redis Evolution**: Different philosophy
- In-memory key-value store (disk for persistence)
- Single-threaded (no locking, deterministic)
- Rich data structures (lists, sets, sorted sets, hashes)
- **Replication**: Primary-replica (asynchronous)
- **Persistence**: RDB snapshots + AOF (append-only file)
- **Guarantee vector**: `⟨Object, Lx(primary), RA, BS(δ), Idem(K), Auth⟩`
  - Linearizable on primary (single-threaded = serialized)
  - Replicas lag (bounded staleness δ = replication delay)

#### Document Stores: MongoDB's Journey

**MongoDB (2009)**: JSON-like documents, flexible schema

**Early architecture** (pre-3.0):
- **Primary-replica replication**: Single primary, multiple secondaries
- **Replica set**: Automatic failover (Raft-like election)
- **Sharding**: Horizontal partitioning (shard key determines placement)
- **Consistency**: Read from primary (consistent) or secondaries (eventually consistent)

**Problem**: No transactions (even single-document updates not isolated in early versions), eventual consistency confusing, sharding manual and error-prone

**Evolution**:
- **v3.0**: WiredTiger storage engine (MVCC, compression)
- **v4.0**: Multi-document transactions (within single replica set)
- **v4.2**: Distributed transactions (across shards)
- **v5.0**: Versioned API, time-series collections

**Modern guarantee vector**: `⟨Transaction, SS(writeConcern=majority), SER(readConcern=linearizable), Fresh(φ), Idem(txn), Auth⟩`
- Strong consistency now available (by choosing appropriate read/write concerns)
- But default is still eventual consistency (secondaries lag)

**Mode matrix**:
- **Target**: Primary + majority secondaries healthy
- **Degraded**: Primary election in progress (writes unavailable for ~10s)
- **Floor**: Majority unavailable → read-only or unavailable (depends on `writeConcern`)
- **Recovery**: Sync from primary, replay oplog

**The lesson**: NoSQL systems evolved toward ACID as users demanded transactions. Eventual consistency alone wasn't enough.

#### Column Families: Bigtable and Cassandra

**Google Bigtable (2006)**: Sparse, distributed, sorted map

**Data model**: `(row, column family:column, timestamp) → value`
- Rows sorted by key
- Columns grouped into families (co-located for locality)
- Each cell versioned by timestamp (MVCC)

**Architecture**:
- **Tablet**: Contiguous row range (analogous to shard)
- **Tablet server**: Serves tablets (stateless, can move tablets between servers)
- **Master**: Assigns tablets to servers, monitors server health
- **GFS (Google File System)**: Underlying storage (replicated, durable)
- **Chubby**: Distributed lock service (for master election, metadata)

**Storage engine**: LSM tree (Log-Structured Merge tree)
- **Write path**: Append to in-memory memtable + commit log (WAL)
- **Compaction**: Periodically flush memtable to sorted SSTable (immutable file)
- **Read path**: Check memtable, then SSTables (newest to oldest)
- **Optimization**: Bloom filters (skip SSTables that don't contain key)

**Why LSM trees?**
- Write-optimized: Sequential writes (append-only)
- Compaction amortizes cost (batch sort and merge)
- Read amplification: Must check multiple SSTables (mitigated by Bloom filters)
- Space amplification: Old versions not immediately reclaimed (compaction lags)

**Guarantee vector**: `⟨Range, Lx(tablet), RA, BS(δ), Idem(K), Auth⟩`
- Linearizable within tablet (single server)
- Bounded staleness across tablets (replication lag)

**Apache Cassandra**: Dynamo + Bigtable hybrid
- Dynamo's decentralized architecture (no master, consistent hashing)
- Bigtable's data model (column families)
- Tunable consistency (quorum reads/writes)
- CQL (Cassandra Query Language) resembles SQL

**Guarantee vector**: Tunable based on consistency level
- `⟨Range, Lx, RA, Fresh(quorum), Idem(K), Auth⟩` with `QUORUM` reads/writes
- `⟨Range, Causal, RA, EO, Idem(K), Auth⟩` with `ONE` reads/writes

#### Graph Databases: Neo4j and Challenges

**Neo4j**: Property graph model (nodes, relationships, properties)

**Why graphs?**
- Social networks: "Friends of friends who like X"
- Recommendation: "Users who bought A also bought B"
- Fraud detection: "Money flows through suspicious accounts"

**Advantage over SQL**: Traversals vs joins
- SQL join: Hash or merge join (O(n log n) or O(n))
- Graph traversal: Follow pointers (O(degree))
- For deep traversals (6 degrees of separation), graph >> SQL

**Distributed graph challenges**:
- **Graph partitioning**: Minimizing edge cuts is NP-hard
- **Traversals cross partitions**: High network overhead
- **Transactions**: Multi-partition traversals need distributed transactions

**Most graph DBs**: Single-node ACID (Neo4j) or eventual consistency (TigerGraph distributed)

**Guarantee vector** (Neo4j single-node): `⟨Global(in-node), SS, SER, Fresh(lock), Idem(txn), Auth⟩`

### The NewSQL Renaissance (2010-2020)

"We can have our ACID cake and eat our scalability too."

#### The Best of Both Worlds

**NewSQL goals**:
- ACID guarantees (transactions, serializability)
- Horizontal scalability (add nodes, increase throughput)
- Geographic distribution (low latency globally)
- SQL compatibility (familiar interface)

**Key insight**: Partition data, use consensus (Paxos/Raft) for coordination, careful protocol design to minimize coordination.

#### Google Spanner (2012)

**Architecture**:
- **Spanserver**: Serves data partitions (called "splits")
- **Paxos group per split**: 3-5 replicas, one leader
- **TrueTime**: GPS + atomic clocks, returns time interval
- **Directories**: Movable unit of data (co-locate related data)

**Transaction protocol**:

**Read-only transactions**:
- Assign snapshot timestamp (TrueTime interval start)
- Read from any replica at that snapshot (no locks, no coordination)
- Wait rule: Ensure snapshot time has passed (wait out TrueTime uncertainty)

**Read-write transactions**:
- Acquire locks (two-phase locking)
- Assign commit timestamp t (TrueTime.now)
- **Commit wait**: Wait until t.earliest > TrueTime.now.latest
  - Ensures no concurrent transaction can have earlier timestamp
  - Preserves external consistency (real-time order)
- Write to Paxos groups (may span multiple splits)
- Release locks

**External consistency**: If T1 commits before T2 starts (wall-clock time), T1's timestamp < T2's timestamp. Achieved via commit wait.

**Evidence**:
- **TrueTime interval**: Freshness evidence with explicit uncertainty
- **Commit wait**: Converts uncertainty into ordering guarantee
- **Paxos commit certificate**: Durability and consistency evidence

**Guarantee vector**: `⟨Global, SS, SER, Fresh(TT), Idem(txn), Auth⟩`
- Strongest guarantees possible in distributed setting

**Mode matrix**:
- **Target**: TrueTime uncertainty < 10ms, all Paxos groups healthy
- **Degraded**: Minority replicas down (Paxos continues with majority)
- **Floor**: Majority unavailable or TrueTime uncertainty spikes → unavailable
- **Recovery**: Paxos leader election, replay Paxos log

**Cost**:
- Commit latency: +7-10ms (TrueTime wait)
- Infrastructure: GPS + atomic clocks (~$200M initial investment)
- Operational complexity: Spanner is not open-source, Google-only

#### CockroachDB: Open-Source Spanner

**Goal**: Bring Spanner's ideas to everyone, without requiring specialized hardware.

**Architecture**:
- **Range**: Contiguous key range (like Spanner split)
- **Raft per range**: 3-5 replicas, one leader (Raft instead of Paxos—simpler)
- **Hybrid Logical Clocks (HLC)**: Physical time + logical counter
  - No GPS/atomic clocks (use NTP)
  - HLC tolerates clock skew up to max offset (500ms default)
- **SQL layer**: PostgreSQL wire protocol compatible

**Transaction protocol**:

**Optimistic transactions** (read-write):
- Read without locks (optimistic = assume no conflicts)
- Buffer writes
- Commit phase:
  - Check for conflicts (another transaction modified same keys)
  - If conflict: Abort and retry
  - Else: Write to Raft groups, commit

**Pessimistic transactions** (`SELECT FOR UPDATE`):
- Acquire locks
- Two-phase commit if spanning multiple ranges

**Serializable isolation**:
- Serializable Snapshot Isolation (SSI)
- Track read/write dependencies
- Abort transactions that would create cycles (serialization violation)

**Clock synchronization**:
- NTP + max clock offset bound (default 500ms)
- If clock skew exceeds bound: Node removed from cluster (safety over availability)
- HLC ensures happened-before even with skew

**Evidence**:
- **HLC timestamp**: Causality + approximate real-time evidence
- **Max offset bound**: Uncertainty evidence (explicit)
- **Raft commit certificate**: Durability evidence

**Guarantee vector**: `⟨Global, SS, SER, Fresh(HLC+bound), Idem(txn), Auth⟩`
- Nearly Spanner-level guarantees, without specialized hardware

**Mode matrix**:
- **Target**: Clock skew < max offset, Raft quorums healthy
- **Degraded**: Minority replicas down (Raft continues)
- **Floor**: Majority unavailable or clock skew exceeds max offset → range unavailable
- **Recovery**: Raft leader election, replay log

**Trade-off vs Spanner**:
- No TrueTime → larger uncertainty → more clock-wait → higher latency
- But no specialized hardware → deployable anywhere

#### VoltDB: In-Memory Determinism

**Different approach**: Eliminate coordination by eliminating non-determinism.

**Architecture**:
- **In-memory**: All data in RAM (disk for durability via command log)
- **Single-threaded per partition**: No locking needed (deterministic execution)
- **Partitioned**: Data sharded by partition key
- **Stored procedures**: Transactions are pre-declared procedures (deterministic)

**Transaction protocol**:
- Submit procedure call to relevant partition(s)
- Execute serially (single thread = no races)
- If multi-partition: Two-phase commit
- Command log: Append procedure call + inputs (not outputs)
- Replicas: Execute same commands deterministically (same inputs → same outputs)

**Why it works**:
- Determinism → no coordination needed (replicas converge by executing same commands)
- In-memory → no disk I/O latency
- Pre-compiled procedures → no parsing overhead

**Limitation**:
- Data must fit in RAM (expensive for terabytes)
- Single-threaded = limited per-partition throughput
- Hotspots = bottlenecks (popular partition serializes)

**Guarantee vector**: `⟨Global(partitioned), SS, SER, Fresh(command_log), Idem(txn), Auth⟩`

**Use case**: High-throughput OLTP with predictable access patterns (telecom billing, financial trading)

#### FoundationDB: Layered Architecture

**Radical idea**: Separate storage from data model.

**Architecture**:
- **Core**: Distributed, ordered key-value store with ACID transactions
- **Layers**: SQL, document, graph, etc. built on top
- **Transaction protocol**: Optimistic MVCC (similar to Spanner's read-write)
- **Storage**: Custom storage engine (ssd, memory)

**Why layers?**
- Core does one thing well: Transactional key-value storage
- Layers provide flexibility: SQL, MongoDB-compatible API, graph queries
- Operational simplicity: Single core system to manage

**Evidence**:
- Version stamps (MVCC)
- Transaction conflict detection
- Commit evidence from distributed commit protocol

**Guarantee vector**: `⟨Global, SS, SER, Fresh(version), Idem(txn), Auth⟩`

**Adoption**: Apple uses FoundationDB for CloudKit (iCloud backend)

### Multi-Model Databases (2020+)

The latest evolution: "Why choose SQL vs NoSQL? Support both."

#### Azure Cosmos DB: Five Consistency Levels

**Architecture**:
- **Global distribution**: Replicas in multiple regions
- **Multi-model**: SQL API, MongoDB API, Cassandra API, Gremlin (graph), Table (key-value)
- **Tunable consistency**: Application chooses per-request

**Five consistency levels** (strongest to weakest):

**1. Strong**: Linearizability
- Reads see latest committed write
- **Evidence**: Quorum reads with commit LSN
- **Guarantee vector**: `⟨Global, Lx, SI, Fresh(quorum), Idem, Auth⟩`
- **Cost**: High latency (cross-region quorum)

**2. Bounded Staleness**: Reads lag by at most K versions or T seconds
- **Evidence**: Version staleness bound
- **Guarantee vector**: `⟨Global, —, SI, BS(K|T), Idem, Auth⟩`
- **Cost**: Medium latency

**3. Session**: Read-your-writes within session
- **Evidence**: Session token (tracks writes)
- **Guarantee vector**: `⟨Session, Causal, RA, BS(session), Idem, Auth⟩`
- **Cost**: Low latency, session overhead

**4. Consistent Prefix**: Reads see writes in order (no gaps)
- **Evidence**: Ordered commit log
- **Guarantee vector**: `⟨Range, Causal, RA, EO(prefix), Idem, Auth⟩`
- **Cost**: Low latency

**5. Eventual**: Replicas converge eventually
- **Evidence**: Anti-entropy, version vectors
- **Guarantee vector**: `⟨Range, —, —, EO, Idem, Auth⟩`
- **Cost**: Minimal latency

**The innovation**: Application declares desired consistency, Cosmos provides it or degrades explicitly. Per-request choice (not cluster-wide).

**Mode matrix**:
- **Target**: All regions healthy, chosen consistency level available
- **Degraded**: Some regions partitioned, consistency downgrades (Strong → Bounded Staleness → Session → Eventual)
- **Floor**: Session or Eventual (always available)
- **Recovery**: Regions rejoin, anti-entropy, upgrade consistency

**Evidence flow**: Application passes session token across requests (context capsule for consistency).

#### Amazon DynamoDB: Evolution from Simple to Sophisticated

**Original Dynamo (2007)**: Eventual consistency only

**Modern DynamoDB (2020s)**:
- **Transactions**: ACID transactions (read-write, all-or-nothing)
- **Global tables**: Multi-region active-active
- **Streams**: Change data capture (CDC)
- **Consistency options**: Eventual (default) or Strongly consistent reads

**Global tables**:
- Multi-master (write to any region)
- Last-write-wins (LWW) conflict resolution (based on timestamps)
- Cross-region replication (asynchronous)

**Transactions**:
- Two-phase commit
- Serializable isolation
- Limited to single region (not global)

**Guarantee vector**:
- Transactional: `⟨Region, SS, SER, Fresh(commit), Idem(txn), Auth⟩`
- Eventual: `⟨Global, —, —, EO, Idem(K), Auth⟩`

**Trade-off**: Global tables = eventual consistency (LWW conflicts). Transactions = single-region only.

#### Modern PostgreSQL: From SQL to Multi-Model

**Evolution**:
- **JSON/JSONB**: Store and query JSON documents
- **Foreign data wrappers (FDW)**: Query external data (MongoDB, Redis, etc.)
- **Logical replication**: Publish/subscribe model (selective replication)
- **Extensions**: PostGIS (spatial), TimescaleDB (time-series), Citus (sharding)

**Why it works**: Relational core + extensibility = multi-model without sacrificing ACID.

**Guarantee vector**: `⟨Transaction, SS, SER, Fresh(lock), Idem(txn), Auth⟩` (unchanged, but data model flexible)

**The lesson**: SQL vs NoSQL is a false dichotomy. Modern databases support multiple models with appropriate guarantees for each.

### Storage Engines Deep Dive

Storage engines embody fundamental trade-offs. Let's see how.

#### LSM Trees (Log-Structured Merge Trees)

**Structure**:
- **Memtable**: In-memory sorted map (red-black tree or skip list)
- **Immutable SSTables**: On-disk sorted files
- **Levels**: L0, L1, L2, … (exponentially larger)

**Write path**:
1. Append to write-ahead log (WAL) for durability
2. Insert into memtable (in-memory, fast)
3. When memtable full: Flush to L0 SSTable
4. Background compaction: Merge SSTables across levels

**Read path**:
1. Check memtable
2. Check L0 SSTables (newest to oldest)
3. Check L1, L2, … (binary search within SSTable)
4. Optimization: Bloom filters skip SSTables that don't contain key

**Compaction strategies**:
- **Size-tiered**: Merge SSTables of similar size (write-amplification lower, space-amplification higher)
- **Leveled**: Each level contains non-overlapping SSTables (read-amplification lower, write-amplification higher)

**Trade-offs**:
- **Write amplification**: Each write eventually compacted multiple times (10× typical)
- **Read amplification**: Must check multiple SSTables (bloom filters help)
- **Space amplification**: Old versions not immediately deleted (compaction lags)

**Why use LSM?**
- Write-heavy workloads (logs, metrics, time-series)
- Sequential writes >> random writes on HDDs (less important on SSDs)
- Compression effective (sorted data compresses well)

**Evidence in LSM**:
- **LSN in WAL**: Durability evidence
- **Sequence numbers in SSTables**: Ordering evidence (newer values override older)
- **Bloom filters**: Negative evidence (key definitely not present)

**Databases using LSM**: Cassandra, RocksDB, LevelDB, HBase, ScyllaDB

#### B-Trees and B+Trees

**Structure**:
- **Internal nodes**: Keys + pointers to children
- **Leaf nodes**: Keys + values (B+tree) or keys + pointers to values (B-tree)
- **Balanced**: All leaves at same depth

**Properties**:
- **Height**: O(log n)
- **Fanout**: Typically 100-1000 (cache line / page size optimized)
- **Ordered**: In-order traversal gives sorted keys

**Write path**:
1. Traverse tree to find leaf
2. Insert key-value in leaf
3. If leaf full: Split leaf, propagate split upward
4. WAL for durability

**Read path**:
1. Traverse tree (O(log n))
2. Read leaf node

**Trade-offs**:
- **Read-optimized**: O(log n) random reads (vs O(log n) SSTables in LSM)
- **Write-amplification**: Random I/O (page updates), splits
- **Space overhead**: Internal nodes (pointers)

**Why use B-trees?**
- Read-heavy workloads
- Range scans (sorted order in leaf nodes)
- In-place updates (no compaction lag)

**Optimizations**:
- **Copy-on-write (COW)**: Immutable nodes (easier recovery, snapshots)
- **Fractal trees**: Buffer writes in internal nodes (batch to leaves)

**Evidence in B-trees**:
- **Lock coupling**: Lock parent before child (tree structure integrity)
- **WAL**: Durability evidence

**Databases using B-trees**: PostgreSQL, MySQL (InnoDB), SQLite, Oracle

#### Hybrid Approaches: RocksDB and Adaptive Engines

**RocksDB**: LSM tree with heavy tuning
- Column families (separate LSM trees for different data)
- Tunable compaction (size-tiered, leveled, universal)
- Block cache (cache hot SSTables)
- Bloom filters, prefix bloom filters
- Merge operators (delta compression)

**Adaptive engines** (research area):
- Monitor workload (read-heavy vs write-heavy)
- Switch storage engine dynamically (LSM for write-heavy, B-tree for read-heavy)
- Example: MyRocks (MySQL with RocksDB), WiredTiger (MongoDB's engine, supports both LSM and B-tree)

**The lesson**: No single storage engine is optimal. Workload matters. Adaptive systems detect and respond.

---

## Part 3: MASTERY (Third Pass) — Composition and Operation

### Evidence in Storage Systems

Storage systems are evidence-generating machines. Every operation produces or consumes evidence.

#### Storage Evidence Types

**Write Evidence**: Proof that data was written durably
- **WAL entry**: Append-only log, LSN proves ordering and durability
- **Quorum acknowledgment**: Majority replicas confirmed write
- **Commit certificate**: Consensus protocol (Paxos/Raft) generated commit evidence
- **Properties**:
  - Scope: Single write operation or transaction
  - Lifetime: Until checkpointed or log truncated
  - Binding: Transaction ID or LSN
  - Transitivity: Replicas can verify commit certificate

**Read Evidence**: Proof that data is fresh or within staleness bound
- **Version vector**: Tracks causal dependencies (which writes happened-before)
- **Timestamp/LSN**: MVCC snapshot, proves read consistency
- **Quorum read**: Read from majority, guarantees seeing latest quorum write
- **TrueTime interval**: Explicit uncertainty bound
- **Properties**:
  - Scope: Snapshot (set of reads)
  - Lifetime: Duration of transaction or session
  - Binding: Transaction ID or session token
  - Transitivity: Depends on consistency level (linearizable = transitive, session = non-transitive)

**Consistency Evidence**: Proof that replicas agree
- **Merkle tree hash**: Hierarchical hash, detects divergence efficiently
- **Vector clocks**: Causality tracking, detects conflicts
- **Consensus commit**: Raft/Paxos log entry, proves agreement
- **Properties**:
  - Scope: Range or partition
  - Lifetime: Until next anti-entropy cycle
  - Binding: Replica set
  - Transitivity: No (local to replica set)

**Durability Evidence**: Proof that data survives failures
- **Replication confirmation**: N replicas acknowledged write
- **Checksum**: Detects corruption (bit flips, disk errors)
- **Backup confirmation**: Data replicated to separate failure domain
- **Properties**:
  - Scope: Object, partition, or full database
  - Lifetime: Indefinite (until explicitly deleted)
  - Binding: Data identifier (key, row ID)
  - Transitivity: Yes (downstream can trust checksums)

#### Evidence Lifecycle in Storage

Every piece of evidence has a lifecycle:

```
Generate (write/commit) →
Replicate (distribute to replicas) →
Validate (verify on read) →
Serve (use for read/write decision) →
Compact (garbage collect old evidence) →
Archive (move to cold storage)
```

**Example: Write transaction in Spanner**

1. **Generate**: Client issues write, Spanner assigns commit timestamp t (TrueTime.now)
2. **Replicate**: Write sent to Paxos group (3-5 replicas)
3. **Validate**: Majority acknowledges, commit certificate generated
4. **Serve**: Later reads at timestamp ≥ t see this write
5. **Compact**: After checkpoint, Paxos log truncated (evidence no longer needed)
6. **Archive**: Old snapshots moved to cold storage (Colossus, Google's successor to GFS)

**Evidence expiration and renewal**:
- **Leases**: Leader leases expire, must be renewed (typically 10s)
- **Timestamps**: Clock skew accumulates, must resynchronize (NTP every 10-100s)
- **Checksums**: Bit rot accumulates, must be recomputed (scrubbing)
- **Merkle trees**: Recomputed on write, stale after compaction

**Degradation on expiry**:
- Lease expires → leader steps down, election begins (degraded mode)
- Clock skew exceeds bound → node removed or commit waits longer (floor mode)
- Checksum mismatch → read fails or returns alternate replica (recovery mode)
- Merkle tree stale → anti-entropy triggered (repair)

### Storage Invariants

Every storage system protects a core set of invariants. Let's make them explicit.

#### Primary Invariant: DURABILITY

**Definition**: Once acknowledged, data survives failures.

**Threat model**:
- Single-node crash: Disk failure, process crash, power loss
- Multi-node failure: Rack failure, datacenter outage
- Correlated failure: Software bug, configuration error affects all replicas
- Byzantine failure: Corruption, bit rot, malicious tampering

**Protection mechanisms**:
- **Replication**: N replicas across failure domains (N=3 typical)
- **Write-ahead logging (WAL)**: Append-only, fsync before ack
- **Checksums**: Detect corruption (CRC32, SHA256)
- **Backups**: Periodic snapshots to separate storage (daily, weekly)

**Evidence**:
- Quorum acknowledgment (W replicas confirmed)
- Checksum validation (data integrity)
- Backup confirmation (archival proof)

**Guarantee vector component**: Durability is implicit in all storage systems (not part of typed G vector, but foundational)

**Mode matrix**:
- **Target**: N replicas healthy, checksum valid, backups current
- **Degraded**: N-1 replicas healthy (still durable if N≥3)
- **Floor**: < quorum replicas (data at risk, read-only or unavailable)
- **Recovery**: Restore from backup or rebuild replica

#### Supporting Invariant: CONSISTENCY

**Definition**: Replicas agree on state (to some bound).

**Spectrum**:
- **Strong (Linearizability)**: Every read sees latest write, real-time order
- **Sequential**: Operations ordered, but not real-time
- **Causal**: Causally related operations ordered
- **Eventual**: Replicas converge if updates stop

**Protection mechanisms**:
- **Consensus (Paxos/Raft)**: Ensures all replicas apply operations in same order
- **Quorum reads (R+W>N)**: Guarantees overlap with latest write
- **Vector clocks**: Track causality, detect conflicts
- **Merkle trees**: Detect divergence, trigger repair

**Evidence**:
- Consensus commit certificate (total order)
- Quorum read (freshness)
- Vector clock (happens-before)
- Merkle tree hash (convergence)

**Guarantee vector component**: Order and Recency fields

**Mode matrix**:
- **Target**: Consensus quorum available, clocks synchronized
- **Degraded**: Eventual consistency (anti-entropy active)
- **Floor**: Partitioned minority (stale reads or unavailable)
- **Recovery**: Merkle tree sync, conflict resolution

#### Supporting Invariant: AVAILABILITY

**Definition**: System responds to requests within SLA.

**Threat model**:
- Network partition (CAP)
- Node failure
- Overload (request rate > capacity)
- Cascading failure

**Protection mechanisms**:
- **Replication**: Multiple nodes can serve requests
- **Load balancing**: Distribute requests
- **Caching**: Reduce load on primary storage
- **Backpressure**: Reject requests before queues overflow

**Evidence**:
- Health checks (node liveness)
- SLA metrics (latency, success rate)

**Guarantee vector component**: Implicit (affects Recency and Order during degradation)

**Mode matrix**:
- **Target**: All nodes healthy, SLA met
- **Degraded**: Some nodes down, SLA degraded (higher latency or weaker consistency)
- **Floor**: Minimal availability (serve cached/stale data)
- **Recovery**: Failed nodes rejoin, load rebalanced

#### Supporting Invariant: PARTITION-TOLERANCE

**Definition**: System continues operating despite network partitions.

**CAP choice**:
- **CP (Consistency)**: Majority partition available, minority unavailable
- **AP (Availability)**: All partitions available, eventual consistency

**Protection mechanisms**:
- **Quorum**: Majority partition continues (CP)
- **Sloppy quorum + hinted handoff**: All partitions continue (AP)
- **Partition detection**: Gossip protocols, heartbeats

**Evidence**:
- Quorum status (do we have majority?)
- Partition detection (which nodes are reachable?)

**Mode matrix**:
- **Target**: No partition
- **Degraded**: Partition detected, majority continues (CP) or all continue (AP)
- **Floor**: Quorum lost (CP = unavailable, AP = stale reads)
- **Recovery**: Partition heals, anti-entropy repairs divergence

### Storage Mode Matrix

Let's formalize the modes for a typical storage system (CP choice, like Spanner or CockroachDB).

#### Target Mode

**Invariants preserved**: Durability, Strong Consistency, High Availability
**Evidence available**: Quorum commits, fresh timestamps, healthy replicas
**Operations**:
- Reads: Linearizable (see latest write)
- Writes: ACID transactions, serializable isolation
- Latency: P50 < 10ms, P99 < 50ms

**Guarantee vector**: `⟨Global, SS, SER, Fresh(quorum), Idem(txn), Auth⟩`

**Entry condition**: All nodes healthy, network stable, clock skew < bound
**Exit trigger**: Node failure, partition detected, clock skew exceeds bound

#### Degraded Mode

**Invariants preserved**: Durability, Eventual Consistency, Reduced Availability
**Evidence available**: Some quorum commits, stale timestamps, partial replicas
**Operations**:
- Reads: Bounded staleness (lag ≤ δ)
- Writes: Accepted if quorum available, queued otherwise
- Latency: P50 < 50ms, P99 < 200ms

**Guarantee vector**: `⟨Range, Causal, SI, BS(δ), Idem(txn), Auth⟩`

**Entry condition**: Minor partition or node failure (majority still available)
**Exit trigger**: Partition heals or quorum lost

#### Floor Mode

**Invariants preserved**: Durability (reads only), No consistency guarantees
**Evidence available**: Stale evidence only
**Operations**:
- Reads: Stale reads from available replicas (explicit staleness bound)
- Writes: Rejected (no quorum)
- Latency: P50 < 100ms (local replica), P99 < 500ms

**Guarantee vector**: `⟨Local, —, —, BS(unbounded), —, Auth⟩`

**Entry condition**: Quorum lost (majority partition unreachable)
**Exit trigger**: Quorum restored or manual intervention

#### Recovery Mode

**Invariants preserved**: Durability, Convergence (in progress)
**Evidence available**: Rebuilding (replaying logs, syncing Merkle trees)
**Operations**:
- Reads: Limited (may serve stale while catching up)
- Writes: Queued or rejected (until sync complete)
- Latency: Variable (depends on lag)

**Guarantee vector**: `⟨Range, Causal, RA, BS(sync_lag), Idem(txn), Auth⟩`

**Entry condition**: Partition healed or node rejoining
**Exit trigger**: Sync complete (Merkle trees match, log replayed)

### Production Patterns

Now let's apply this to real-world decision-making.

#### Choosing Storage Systems

**Decision Framework**:

**1. Consistency requirements**
- Transactions needed? (yes = SQL/NewSQL, no = NoSQL)
- Serializability required? (yes = Spanner/CockroachDB/VoltDB, no = eventual consistency okay)
- Conflict tolerance? (conflicts rare = AP acceptable, conflicts unacceptable = CP required)

**2. Availability requirements**
- SLA? (99.9% = can tolerate partitions, 99.99% = need multi-region)
- Partition handling? (CP = minority unavailable, AP = always available but stale)

**3. Latency requirements**
- P99 latency? (<10ms = single-region, <50ms = regional, <200ms = global acceptable)
- Geographic distribution? (users global = need local replicas)

**4. Scale requirements**
- Data size? (GB = single node, TB = sharded, PB = distributed)
- Throughput? (1K qps = single node, 100K qps = replicated, 1M+ qps = sharded)
- Growth rate? (doubling annually = need horizontal scalability)

**5. Query complexity**
- SQL queries? (joins, aggregations = relational DB)
- Key-value? (simple lookups = NoSQL)
- Graph traversals? (social network = graph DB)
- Time-series? (metrics, logs = specialized time-series DB)

**6. Operational complexity**
- Team expertise? (SQL familiar = PostgreSQL/MySQL, distributed systems experts = Cassandra/Spanner)
- Managed service? (cloud-native = DynamoDB/Cosmos, self-hosted = Cassandra/CockroachDB)
- Operational burden? (simple = managed, complex = self-hosted with full control)

**Example decision tree**:

**Scenario**: E-commerce platform
- Consistency: Inventory and payments need strong consistency (can't oversell, double-charge). User sessions and carts tolerate eventual consistency.
- Availability: 99.95% SLA. Partitions rare but must handle.
- Latency: P99 < 100ms for checkout, P99 < 500ms for browsing.
- Scale: 10M users, 100K concurrent, 1TB data, growing 50%/year.
- Query: Product catalog (complex queries, joins), orders (transactional), sessions (key-value).
- Operational: Team knows SQL, prefer managed service.

**Choice**:
- **Inventory/Payments**: Cloud Spanner or CockroachDB (strong consistency, ACID, SQL)
- **Product catalog**: PostgreSQL with read replicas (complex queries, read-heavy)
- **User sessions**: Redis (key-value, in-memory, low latency)
- **Shopping carts**: DynamoDB (eventual consistency acceptable, high availability)

**Polyglot persistence**: Different storage for different needs. Unified by application logic and APIs.

#### Migration Strategies

**Scenario**: Migrating from monolithic PostgreSQL to distributed Cassandra (scalability bottleneck).

**Challenges**:
- **Consistency model change**: PostgreSQL = ACID, Cassandra = eventual consistency
- **Schema change**: Relational → column-family (denormalization required)
- **Zero-downtime**: Can't take system offline
- **Rollback**: Must be able to abort migration

**Strategy: Dual Writes**

**Phase 1: Shadow writes**
- Application writes to PostgreSQL (primary)
- Asynchronously replicate to Cassandra (shadow)
- All reads from PostgreSQL
- **Goal**: Populate Cassandra, test performance

**Phase 2: Dual reads (validation)**
- Application reads from both PostgreSQL and Cassandra
- Compare results, log discrepancies
- Serve PostgreSQL result (canonical)
- Fix bugs in Cassandra schema/logic
- **Goal**: Validate consistency, build confidence

**Phase 3: Gradual cutover**
- Read from Cassandra for 1% of traffic (canary)
- Monitor metrics: latency, error rate, consistency
- Increase to 10%, 50%, 100% over weeks
- **Goal**: Risk mitigation, gradual rollout

**Phase 4: Dual writes (reverse)**
- Cassandra is primary
- Writes to PostgreSQL for rollback capability
- **Goal**: Safety net

**Phase 5: Decommission PostgreSQL**
- Stop writes to PostgreSQL
- Archive data for compliance
- **Goal**: Complete migration

**Evidence and context capsules**:
- Each write tagged with source (PG or Cassandra)
- Reads include staleness bound (Cassandra lag)
- Context capsule: `{invariant: Consistency, evidence: dual-read-validation, boundary: application-layer, mode: Migration, fallback: PostgreSQL}`

**Rollback**:
- Any phase: Revert reads to PostgreSQL
- Phase 1-3: Stop Cassandra writes, continue PostgreSQL
- Phase 4: Restore from PostgreSQL backup

**Timeline**: 3-6 months (depends on data size, traffic, team size)

#### Multi-Region Patterns

**Pattern 1: Primary Region + Read Replicas**

**Architecture**:
- One region is primary (handles all writes)
- Other regions have read replicas (asynchronous replication)
- Reads served locally, writes forwarded to primary

**Guarantee vector**:
- Writes: `⟨Region(primary), SS, SER, Fresh(quorum), Idem, Auth⟩`
- Reads (replica): `⟨Region(local), —, SI, BS(replication_lag), Idem, Auth⟩`

**Mode matrix**:
- Target: Primary healthy, replicas lag < 100ms
- Degraded: Replication lag > 100ms (serve stale reads, label staleness)
- Floor: Primary unavailable (promote replica to primary, accept downtime during promotion)

**Use case**: Read-heavy, global users, can tolerate stale reads (news sites, social media feeds)

**Pattern 2: Multi-Master (Active-Active)**

**Architecture**:
- All regions accept writes
- Asynchronous replication between regions
- Conflict resolution (LWW, CRDTs, application logic)

**Guarantee vector**:
- Writes: `⟨Region(local), Causal, RA, BS(propagation), Idem(K), Auth⟩`
- Reads: `⟨Region(local), Causal, RA, BS(δ), Idem(K), Auth⟩`

**Mode matrix**:
- Target: All regions healthy, conflicts rare
- Degraded: Some regions partitioned (continue locally, resolve conflicts on heal)
- Floor: Isolated region (serve locally, large staleness bound)

**Use case**: Write-heavy, global users, conflict resolution acceptable (collaborative editing, shopping carts)

**Example**: DynamoDB Global Tables

**Pattern 3: Geo-Partitioning (Data Locality)**

**Architecture**:
- Data partitioned by region (EU users → EU region, US users → US region)
- Strong consistency within region
- Cross-region queries slow or unavailable

**Guarantee vector**:
- Within region: `⟨Region, SS, SER, Fresh(quorum), Idem, Auth⟩`
- Cross-region: `⟨Global, —, SI, BS(cross-region), Idem, Auth⟩` (rare)

**Mode matrix**:
- Target: All regions healthy, partitioning by location
- Degraded: Region failure (users in that region degraded)
- Floor: Region unavailable (users fail over to another region, higher latency)

**Use case**: Data residency requirements (GDPR), latency-sensitive (gaming, financial trading)

**Example**: CockroachDB with geo-partitioning, Spanner with regional replication

### Case Studies

Let's see how real companies navigated storage challenges.

#### Netflix's Cassandra Journey

**Background**: Netflix started with Oracle (monolithic, ACID). Scaling bottleneck as streaming grew.

**Migration**:
- **2011**: Started Cassandra migration (open-source, AP, horizontal scaling)
- **Goal**: Multi-region active-active, 99.99% availability

**Architecture**:
- 3 regions (US-East, US-West, EU)
- 3 replicas per region (RF=3)
- Quorum reads/writes within region (LOCAL_QUORUM)
- Asynchronous replication across regions

**Challenges**:
- **Consistency**: Eventual consistency caused bugs (user sees different data in different requests)
- **Hotspots**: Popular titles → hot partitions → slow queries
- **Operations**: Cassandra is complex (tuning, compaction, repair)

**Solutions**:
- **Idempotent writes**: Designed application logic to tolerate duplicate writes
- **Sharding by user**: User data co-located (single partition queries)
- **Chaos engineering**: Simian Army randomly kills nodes (test failure handling)
- **Tooling**: Built extensive tooling for monitoring, repair, backup

**Outcome**: Handles billions of requests/day, 99.99% availability, sub-100ms P99 latency. But operational complexity high.

**Lessons**:
- AP choice fits Netflix (availability > consistency for user data)
- Eventual consistency requires application changes (idempotence, conflict tolerance)
- Operational investment essential (monitoring, automation, chaos)

#### Uber's Storage Evolution

**Background**: Uber started with PostgreSQL (single instance). Growth → sharding → complexity.

**Phase 1: Sharding PostgreSQL**
- Horizontal sharding by city (New York data on one shard, SF on another)
- Application-layer routing
- **Problem**: Cross-city queries slow, rebalancing manual

**Phase 2: Migration to Schemaless (Cassandra-based)**
- Built custom layer on top of Cassandra ("Schemaless")
- JSON documents, versioned
- Eventually consistent
- **Problem**: Lost PostgreSQL features (joins, transactions)

**Phase 3: Docstore (Hybrid)**
- Retained Schemaless for some data
- Rebuilt transactional layer on top ("Docstore")
- MySQL for metadata (strongly consistent)
- **Goal**: Best of both worlds (scalability + transactions)

**Phase 4: Multi-Region MySQL (Current)**
- Returning to MySQL for critical data
- Multi-region replication (primary + replicas)
- Vitess for sharding
- **Reason**: Team expertise (SQL), transactional needs

**Lessons**:
- No one-size-fits-all (different data → different storage)
- Operational complexity matters (Schemaless required large team)
- Sometimes simple + sharded > complex distributed system

#### Stripe's Database Stack

**Background**: Payment processing = strong consistency required (can't double-charge or lose money).

**Architecture**:
- **MongoDB (early)**: Fast development, flexible schema
- **Problem**: Eventual consistency caused payment bugs (double charges, lost transactions)

**Migration to custom solution**:
- MySQL for transactional data (payments, charges)
- Custom sharding layer
- **Guarantees**: Serializable isolation, exactly-once semantics

**Key patterns**:
- **Idempotency keys**: Clients provide unique key, server deduplicates
- **State machines**: Payment states (pending → succeeded/failed), transitions enforced
- **Audit logs**: Immutable log of all state changes (forensics, compliance)

**Evidence**:
- Idempotency key = deduplication evidence
- Audit log = compliance evidence
- Transaction ID = atomicity evidence

**Lessons**:
- Financial data = strong consistency non-negotiable
- Idempotency essential (network retries inevitable)
- Audit trails = accountability + debugging

#### Discord's Storage Scaling

**Background**: Chat platform, billions of messages, read-heavy.

**Phase 1: MongoDB**
- Single replica set
- **Problem**: Scaling bottleneck, high P99 latencies (slow queries block others)

**Phase 2: Migration to Cassandra**
- Horizontal scaling
- Partitioned by channel ID
- **Problem**: Tombstone accumulation (deletes create tombstones, slow reads)

**Phase 3: Hot Partition Problem**
- Popular channels = hot partitions
- Cassandra struggles with hot partitions (single partition = single node)
- **Solution**: Caching (Redis), read replicas

**Phase 4: ScyllaDB (Cassandra-compatible, C++ rewrite)**
- 10× better P99 latencies
- Better hot partition handling
- **Reason**: GC pauses in Java Cassandra caused tail latencies

**Lessons**:
- Workload matters (read-heavy, hot partitions)
- Implementation matters (ScyllaDB vs Cassandra = same model, different performance)
- Caching essential for hot data

---

## Synthesis: The Storage Continuum

### It's Not OR, It's AND

The evolution from ACID → BASE → NewSQL → Multi-Model isn't a rejection of previous ideas—it's an expansion of the toolkit.

**ACID (1970s)**: Strong guarantees, vertical scaling
- Still essential for financial transactions, inventory, critical data
- Modern implementations: Spanner, CockroachDB, VoltDB

**BASE (2000s)**: Weak guarantees, horizontal scaling
- Essential for high-availability, high-scale, eventual consistency workloads
- Modern implementations: Cassandra, DynamoDB, Riak

**NewSQL (2010s)**: Strong guarantees at scale
- Combines ACID + horizontal scaling
- Requires careful engineering (consensus, distributed transactions)
- Modern implementations: Spanner, CockroachDB, FoundationDB

**Multi-Model (2020s)**: Different guarantees for different data
- Application chooses consistency level per operation
- Polyglot persistence within single system
- Modern implementations: Cosmos DB, PostgreSQL + extensions, DynamoDB + transactions

**The realization**: Different data has different needs. One size doesn't fit all. Choose based on requirements, not dogma.

### The Invariant Lens on Storage

Every storage system makes the same fundamental choices:

**Which invariants to protect?**
- Durability: Always (core purpose of storage)
- Consistency: Strong (CP) or eventual (AP)?
- Availability: During partitions (AP) or sacrifice minority (CP)?

**What evidence to generate?**
- Durability: Replication confirmations, checksums, WAL
- Consistency: Quorum certificates, vector clocks, Merkle trees
- Freshness: Timestamps, TrueTime intervals, version numbers

**How to degrade under stress?**
- CP systems: Minority unavailable, majority continues
- AP systems: All partitions available, conflicts resolved eventually
- Hybrid: Application chooses per-operation

**The invariant lens clarifies**:
- Spanner: Protects strong consistency (linearizability) via TrueTime evidence, degrades by making minority unavailable (CP)
- Cassandra: Protects availability via quorum tuning, degrades consistency to eventual via vector clock conflict resolution (AP)
- Cosmos DB: Lets application choose invariants (strong → eventual spectrum) via session tokens, degrades explicitly with labeled staleness

### Design Principles

**1. Start with requirements, not technology**
- What consistency does business logic require? (inventory = strong, shopping cart = eventual)
- What availability SLA? (99.9% vs 99.99% = different architectures)
- What scale? (GB vs TB vs PB = different systems)

**2. Understand the CAP trade-offs**
- CP: Consistent but unavailable during partitions (Spanner, HBase, MongoDB)
- AP: Available but eventually consistent (Cassandra, DynamoDB, Riak)
- Hybrid: Choose per-operation (Cosmos DB)

**3. Plan for operations, not just development**
- Monitoring: What evidence to track? (quorum status, replication lag, clock skew)
- Failures: How to detect? (heartbeats, health checks) How to recover? (re-election, anti-entropy)
- Scaling: How to add capacity? (sharding, replication)

**4. Consider total cost of ownership**
- Infrastructure: Spanner's GPS/atomic clocks, Cassandra's large clusters
- Operational: Team size, expertise, on-call burden
- Opportunity cost: Engineering time on storage vs product features

**5. Design for evolution**
- Data outlives systems (will migrate eventually)
- Polyglot persistence: Different storage for different needs
- Migration strategy: Dual writes, gradual cutover, rollback plan

### Future Directions

**Disaggregated storage**: Separate compute and storage (AWS Aurora, Snowflake)
- Compute nodes (query processing) ephemeral
- Storage layer (persistent) scales independently
- Advantage: Scale compute and storage separately, faster failover
- Challenge: Network latency (compute ↔ storage), cache coherence

**Computational storage**: Push computation to storage (SmartSSDs, FPGA-accelerated databases)
- Idea: Filter, aggregate at storage layer (reduce data movement)
- Advantage: Lower latency, higher bandwidth utilization
- Challenge: Limited programmability, specialized hardware

**Persistent memory (PMem)**: Byte-addressable, persistent (Intel Optane)
- Blurs line between memory and storage
- PMDK (Persistent Memory Development Kit) provides ACID primitives
- Challenge: New programming models, limited adoption (Optane discontinued)

**Quantum storage**: Long-term vision
- Quantum error correction for ultra-durable storage
- Quantum entanglement for instant replication (theoretical)
- Challenge: Decades away, if ever practical

---

## Exercises

### Conceptual

**1. Compare ACID vs BASE trade-offs**

Design a social media "like" feature (users like posts). Analyze:
- ACID approach: Transaction increments like count, ensures accuracy
  - Pros: Accurate count, no lost likes
  - Cons: High contention (popular post = hotspot), low throughput
- BASE approach: Eventually consistent counter (increment without lock)
  - Pros: High throughput, scales horizontally
  - Cons: Temporary inaccuracy (count might lag), conflict resolution needed
- Which approach for which scenario?
  - ACID: Financial donations (every like = $1 donation)
  - BASE: Social likes (approximate count acceptable)

**2. Design storage for social media platform**

Requirements:
- 1B users, 10B posts, 100B likes
- Read-heavy (100:1 read:write ratio)
- Global users (low latency worldwide)

Design:
- **User profiles**: PostgreSQL (relational, moderate scale, joins for friend graphs)
- **Posts**: Cassandra (timeline queries = partition by user_id, write-heavy)
- **Likes**: Redis counters (in-memory, eventual consistency acceptable)
- **Media (images/videos)**: S3 + CDN (blob storage, globally distributed)

Justify each choice via invariant lens:
- User profiles: Consistency (strong, avoid duplicate accounts), moderate scale
- Posts: Availability (partitions shouldn't block posts), scale (10B records)
- Likes: Low latency (in-memory), eventual consistency acceptable

**3. Analyze consistency levels**

For each scenario, choose consistency level and justify:

a) **Bank account balance check before withdrawal**
- Strong consistency (linearizable read)
- Evidence: Quorum read or read-after-write on primary
- Reason: Cannot allow overdraft due to stale read

b) **Social media feed (see posts from friends)**
- Eventual consistency
- Evidence: Read from local replica
- Reason: Seeing post 100ms late is acceptable, latency more important

c) **E-commerce inventory (remaining stock count)**
- Bounded staleness (δ = 1 second) or strong consistency
- Evidence: Quorum read with staleness bound or linearizable read
- Reason: Overselling is unacceptable, but 1s lag tolerable (batch updates)

d) **Collaborative document editing (Google Docs)**
- Causal consistency + CRDTs
- Evidence: Vector clocks for causality, CRDT merge for conflict-free convergence
- Reason: See your own edits immediately (causal), others' edits eventually

**4. Evaluate storage engines**

Given workload: 80% reads, 20% writes, 1TB data, SSD storage

**LSM tree** (e.g., RocksDB):
- Write path: Memtable + periodic flush (sequential writes to SSTable)
- Read path: Check memtable + multiple SSTables (read amplification = 5-10×)
- Analysis: Write-optimized but read amplification high
- Verdict: Suboptimal for 80% read workload

**B-tree** (e.g., InnoDB):
- Write path: Random I/O to leaf pages (slower writes)
- Read path: O(log n) tree traversal (predictable, low amplification)
- Analysis: Read-optimized, writes acceptable with SSD
- Verdict: Better fit for read-heavy workload

**Recommendation**: B-tree or hybrid (RocksDB with large block cache for hot data)

**5. Plan multi-region deployment**

Requirements:
- Users in US, EU, Asia
- Writes must be durable globally (survive regional outage)
- Reads must be fast locally (<50ms P99)

**Pattern**: Primary region + read replicas + geo-partitioning

Architecture:
- **Primary region**: US-East (handles all writes, 3 replicas for durability)
- **Read replicas**: EU, Asia (asynchronous replication, serve local reads)
- **Geo-partitioning**: EU users' data primarily in EU region (GDPR compliance)

Guarantee vectors:
- Writes (US-East): `⟨Global, SS, SER, Fresh(quorum), Idem, Auth⟩`
- Reads (EU replica): `⟨Region, —, SI, BS(100ms), Idem, Auth⟩`
- Reads (geo-partitioned EU data in EU): `⟨Region, SS, SER, Fresh(quorum), Idem, Auth⟩`

Mode matrix:
- Target: All regions healthy, replication lag < 100ms
- Degraded: Region partitioned (serve local reads, queue writes or forward to primary)
- Floor: Primary region down (promote replica to primary, accept downtime)

### Implementation

**1. Build LSM tree**

Implement basic LSM tree:
- Memtable (in-memory sorted map)
- Flush to SSTable (sorted file)
- Compaction (merge SSTables)
- Read path (check memtable + SSTables)

Measure:
- Write throughput (keys/sec)
- Read latency (P50, P99)
- Write amplification (bytes written to disk / bytes written by user)

**2. Implement vector clocks**

Data structure:
```
VectorClock = Map<NodeID, int>
```

Operations:
- `increment(node_id)`: Increment local clock
- `merge(other)`: Element-wise max (for reads)
- `compare(other)`: Returns `BEFORE | AFTER | CONCURRENT`

Test cases:
- Sequential updates (A → B → C) = BEFORE
- Concurrent updates (A || B) = CONCURRENT
- Merge (A + B = max(A, B))

**3. Create consistent hashing**

Implement:
- Hash ring (sorted list of positions)
- Virtual nodes (each physical node at multiple positions)
- Add/remove nodes (rehash only adjacent ranges)
- Key lookup (find successor node)

Measure:
- Load distribution (standard deviation of keys per node)
- Rebalancing cost (keys moved when adding node)

**4. Build simple KV store**

Features:
- GET, PUT, DELETE operations
- In-memory storage (HashMap)
- WAL for durability (append-only file)
- Recovery (replay WAL on startup)

Extensions:
- Replication (primary-replica)
- Compaction (truncate WAL after checkpoint)

**5. Add transactions to KV store**

Implement:
- BEGIN, COMMIT, ABORT
- Isolation (snapshot isolation via MVCC)
- Atomicity (undo log for rollback)
- Durability (fsync WAL before commit)

Test:
- Concurrent transactions (ensure isolation)
- Crash recovery (abort uncommitted transactions)

### Production Analysis

**1. Analyze your storage choices**

For each service in your production system:
- What storage system? (PostgreSQL, Cassandra, Redis, etc.)
- What consistency level? (strong, eventual, tunable)
- What scale? (data size, throughput)
- CAP choice? (CP or AP)
- Why chosen? (justify via invariants, evidence, requirements)

Document:
- Guarantee vectors for each operation
- Mode matrix (target, degraded, floor, recovery)
- Evidence types generated and verified

**2. Measure consistency in practice**

Experiment:
- Multi-region deployment (or simulate with network delay)
- Write to primary
- Measure replication lag to replicas
- Read from replica, check staleness

Metrics:
- Replication lag (P50, P99, max)
- Staleness observed (timestamp difference)
- Consistency violations (read stale data)

Graph:
- Latency vs consistency (strong reads vs eventual reads)
- Availability vs consistency (during partition)

**3. Calculate storage costs**

For your workload (or hypothetical):
- Data size: 10TB
- Throughput: 100K ops/sec
- Replication: 3 replicas
- Retention: 90 days

Cost comparison:
- **AWS DynamoDB**: On-demand pricing (~$3/GB/month for storage, ~$1.25/million writes)
  - 10TB × 3 × $3 = $90K/month storage
  - 100K writes/sec × 86400 × 30 × $1.25/million = $324K/month writes
  - Total: ~$414K/month
- **Self-hosted Cassandra on EC2**: i3.4xlarge instances ($1.25/hr, 1.9TB SSD)
  - 30TB / 1.9TB = 16 instances
  - 16 × $1.25/hr × 730 hrs/month = $14.6K/month
  - Total: ~$15K/month + operational overhead

Analysis:
- DynamoDB: 28× more expensive, but fully managed (no ops)
- Cassandra: Cheaper, but requires ops team (salaries, on-call)

Decision: Depends on team size and expertise (small team = DynamoDB, large team = Cassandra)

**4. Plan migration strategy**

Current: PostgreSQL (single instance, vertical scaling limit)
Target: CockroachDB (horizontal scaling, ACID)

Plan:
1. **Pilot** (1 month): Deploy CockroachDB, load test, benchmark
2. **Schema migration** (1 month): Convert schema, test application
3. **Dual writes** (2 months): Write to both, read from PostgreSQL, validate consistency
4. **Gradual cutover** (2 months): Read from CockroachDB (1% → 100% traffic)
5. **Decommission PostgreSQL** (1 month): Stop dual writes, archive data

Risks and mitigations:
- Incompatibility: Test application thoroughly (stage 2)
- Performance regression: Benchmark and optimize (stage 1)
- Data loss: Dual writes provide safety net (stage 3-4)
- Rollback: Revert to PostgreSQL at any stage

**5. Design backup/recovery**

Strategy:
- **Full backup**: Weekly (dump entire database)
- **Incremental backup**: Daily (WAL shipping or change data capture)
- **Retention**: 90 days
- **Storage**: S3 (durability: 11 9's)

Recovery scenarios:
- **Accidental DELETE**: Restore from most recent backup (RPO = 24 hours, RTO = 2 hours)
- **Corruption**: Restore from backup, replay WAL (RPO = 0, RTO = 4 hours)
- **Region failure**: Failover to replica region (RPO = replication lag, RTO = 10 minutes)

Evidence:
- Backup completion confirmation
- Checksum validation (integrity)
- Restore test (monthly drill)

---

## Key Takeaways

**1. Storage evolution follows business needs**
- ACID emerged for correctness (financial transactions)
- BASE emerged for scale (web-scale applications)
- NewSQL emerged to combine both (global applications)
- Multi-model emerged to support both in one system

**2. ACID and BASE both have their place**
- ACID: Financial transactions, inventory, critical data
- BASE: User sessions, shopping carts, social feeds
- Choice based on business requirements, not technology preference

**3. NewSQL proves we can have both**
- Spanner: ACID at global scale (with TrueTime and $$$)
- CockroachDB: ACID at scale without specialized hardware
- FoundationDB: Layered architecture for flexibility

**4. Multi-model is the future**
- Cosmos DB: Five consistency levels, application chooses
- PostgreSQL: JSON, FDW, extensions = multi-model
- DynamoDB: Eventual + transactions = hybrid

**5. Operations matter more than features**
- Cassandra: Feature-rich but operationally complex
- VoltDB: Fast but limited use case (in-memory only)
- DynamoDB: Less flexible but fully managed

**6. Evidence-based thinking clarifies trade-offs**
- Storage systems protect invariants (durability, consistency) with evidence (commits, quorums, checksums)
- Trade-offs are evidence trade-offs: Strong consistency = expensive evidence (quorum), eventual = cheap evidence (async)
- Degradation is evidence expiration: Quorum lost = downgrade to stale reads or unavailable

**The irreducible truth**: Storage is about preserving data durably, consistently, and accessibly across failures, partitions, and scale. Every system chooses which guarantees to prioritize, what evidence to generate, and how to degrade when reality intrudes. The art is in making those choices explicit, principled, and comprehensible.

---

## Further Reading

### Foundational Papers

**ACID and Relational**:
- Codd, E.F. "A Relational Model of Data for Large Shared Data Banks" (CACM 1970) — The relational model
- Gray, Jim. "The Transaction Concept" (VLDB 1981) — ACID formalization
- Härder, Theo and Reuter, Andreas. "Principles of Transaction-Oriented Database Recovery" (ACM Computing Surveys 1983) — ARIES recovery algorithm

**NoSQL**:
- DeCandia et al. "Dynamo: Amazon's Highly Available Key-value Store" (SOSP 2007) — AP systems blueprint
- Chang et al. "Bigtable: A Distributed Storage System for Structured Data" (OSDI 2006) — Column-family model, LSM trees
- Lakshman, Avinash and Malik, Prashant. "Cassandra: A Decentralized Structured Storage System" (ACM SIGOPS 2010) — Dynamo + Bigtable

**NewSQL**:
- Corbett et al. "Spanner: Google's Globally Distributed Database" (OSDI 2012) — TrueTime, external consistency
- Taft et al. "CockroachDB: The Resilient Geo-Distributed SQL Database" (SIGMOD 2020) — Open-source Spanner
- Thomson et al. "Calvin: Fast Distributed Transactions for Partitioned Database Systems" (SIGMOD 2012) — Deterministic databases

**Storage Engines**:
- O'Neil et al. "The Log-Structured Merge-Tree (LSM-Tree)" (Acta Informatica 1996) — LSM trees formalized
- Bayer, Rudolf and McCreight, Edward. "Organization and Maintenance of Large Ordered Indices" (Acta Informatica 1972) — B-trees

### Consistency Models

- Herlihy, Maurice and Wing, Jeannette. "Linearizability: A Correctness Condition for Concurrent Objects" (TOPLAS 1990) — Linearizability definition
- Adya, Atul. "Weak Consistency: A Generalized Theory and Optimistic Implementations for Distributed Transactions" (PhD Thesis, MIT 1999) — Taxonomy of isolation levels
- Terry et al. "Session Guarantees for Weakly Consistent Replicated Data" (PDIS 1994) — Session consistency

### Multi-Model

- Karim et al. "Cosmos DB: Microsoft's Cloud-Born Globally Distributed Database" (SIGMOD 2018) — Five consistency levels
- Shapiro et al. "Conflict-Free Replicated Data Types" (SSS 2011) — CRDTs for eventual consistency

### Industry Experience

- "How We Scaled Dropbox" (blog series) — Metadata storage evolution
- "Uber Engineering Blog: Schemaless to Docstore" — Migration challenges
- "Netflix Tech Blog: Cassandra at Scale" — Multi-region AP system
- "Discord Blog: How Discord Stores Billions of Messages" — MongoDB → Cassandra → ScyllaDB

### Books

- Kleppmann, Martin. "Designing Data-Intensive Applications" (2017) — Comprehensive storage systems survey
- Pavlo, Andy and Aslett, Matthew. "What's Really New with NewSQL?" (SIGMOD Record 2016) — NewSQL taxonomy
- Redmond, Eric and Wilson, Jim. "Seven Databases in Seven Weeks" (2012) — Hands-on exploration

---

## Chapter Summary

### The Irreducible Truth

**"Storage systems preserve data durably, consistently, and accessibly by generating evidence of commits, quorums, and freshness, degrading predictably when evidence cannot be maintained due to failures, partitions, or scale."**

This chapter traced the 50-year evolution of storage systems, from ACID's strong guarantees to BASE's high availability, NewSQL's global consistency, and multi-model's flexibility. The pendulum swung from correctness to scale and back, ultimately settling on "it depends"—different data needs different guarantees.

### Key Mental Models

**1. Storage as Evidence-Generating Machine**
- Durability evidence: Replication confirmations, WAL, checksums
- Consistency evidence: Quorum commits, vector clocks, Merkle trees
- Freshness evidence: Timestamps, TrueTime intervals, version numbers
- Every operation generates or consumes evidence

**2. Invariants Define Storage**
- Durability: Always protected (core purpose)
- Consistency: Strong (CP) or eventual (AP)—choose based on requirements
- Availability: During partitions, CP = minority unavailable, AP = always available
- Trade-offs are explicit: More consistency = more coordination = higher latency

**3. Storage Engines Embody Trade-Offs**
- LSM trees: Write-optimized (sequential I/O), read amplification (multiple SSTables)
- B-trees: Read-optimized (O(log n)), write amplification (random I/O)
- No universal best—choose based on workload (read-heavy vs write-heavy)

**4. Polyglot Persistence**
- Different data has different needs
- Financial transactions: Strong consistency (Spanner, CockroachDB)
- User sessions: Eventual consistency (Redis, DynamoDB)
- One application, multiple storage systems, unified by business logic

**5. Operations Matter More Than Features**
- Feature-rich but operationally complex (Cassandra) vs simple but managed (DynamoDB)
- Team expertise, on-call burden, total cost of ownership
- Success = not just technical correctness, but operational sustainability

### The Evidence-Based View

Reframe storage decisions through evidence:

- **ACID systems** generate strong evidence (locks, quorum commits, WAL) to protect strong invariants (serializability, durability), accepting coordination cost (latency, reduced availability)
- **BASE systems** generate weak evidence (vector clocks, async replication) to protect weak invariants (eventual consistency), accepting conflict resolution complexity
- **NewSQL systems** generate global evidence (TrueTime intervals, distributed consensus) to protect strong invariants at scale, accepting infrastructure cost and operational complexity
- **Multi-model systems** let applications choose evidence strength (quorum vs local), providing flexibility at the cost of complexity

### Practical Takeaways

**Design Principles**:
- Choose storage based on requirements (consistency, availability, latency, scale), not dogma
- Use polyglot persistence (different storage for different needs)
- Make CAP choice explicit (CP or AP per service)
- Design for operations (monitoring, failure handling, scaling)
- Plan for migration (systems evolve, data outlives code)

**Operational Guidelines**:
- Monitor evidence: Quorum status, replication lag, clock skew, Merkle tree divergence
- Alert on degradation: Quorum lost, evidence stale, mode transition (target → degraded)
- Test failures: Chaos engineering (partition regions, kill nodes, skew clocks)
- Document modes: Target, degraded, floor, recovery—what changes, what doesn't

**Debugging Approaches**:
- Data loss: Check durability evidence (replication confirmations, WAL, backups)
- Inconsistency: Check consistency evidence (quorum status, vector clocks, Merkle trees)
- High latency: Check coordination cost (cross-region quorum, lock contention, compaction)
- Unavailability: Check CAP choice (CP minority unavailable, AP degraded consistency)

### What's Next

Storage systems are where the rubber meets the road—where impossibility results (CAP), time challenges (clock skew), and consensus protocols (Paxos/Raft) manifest in production. But modern applications aren't monolithic databases. They're **distributed microservices** with complex interactions, cascading failures, and emergent behavior.

Chapter 7 will explore **Cloud-Native Architectures**—how modern applications compose storage, compute, and networking into resilient, scalable systems. We'll see how evidence-based thinking scales from individual storage systems to entire application architectures, and how the invariant-evidence-mode framework provides a unified mental model for reasoning about complexity at any scale.

---

## Sidebar: Cross-Chapter Connections

**To Chapter 1 (Impossibility Results)**:
- CAP theorem manifests: Storage systems choose CP (Spanner, MongoDB) or AP (Cassandra, DynamoDB)
- FLP circumvented: Consensus protocols (Paxos in Spanner, Raft in CockroachDB) use partial synchrony
- PACELC embodied: Strong consistency = high latency (quorum), eventual = low latency (local reads)

**To Chapter 2 (Time, Order, Causality)**:
- Physical time: TrueTime in Spanner, NTP + HLC in CockroachDB
- Logical time: Vector clocks in Dynamo/Cassandra, version numbers in MVCC
- Causality: Happens-before in conflict resolution, causal consistency in Cosmos DB

**To Chapter 3 (Consensus)**:
- Paxos in Spanner: Per-split Paxos groups, majority quorum
- Raft in CockroachDB: Per-range Raft groups, leader election, log replication
- Consensus evidence: Commit certificates prove durability and ordering

**To Chapter 4 (Replication)**:
- Primary-replica: PostgreSQL, MySQL, Redis (asynchronous or synchronous)
- Multi-master: DynamoDB Global Tables, Cassandra (conflict resolution required)
- Chain replication: Used in Azure Storage (CORFU protocol variant)

**To Chapter 5 (Consistency Models)**:
- Linearizability: Spanner (external consistency), strong reads in Cosmos DB
- Serializability: All ACID databases (PostgreSQL, Spanner, CockroachDB)
- Causal consistency: Session consistency in Cosmos DB, vector clocks in Cassandra
- Eventual consistency: Default in Dynamo, Cassandra, DynamoDB

**To Chapter 7 (Cloud-Native)**:
- Microservices storage: Polyglot persistence (each service owns its storage)
- Service mesh: Distributed tracing across storage boundaries
- Kubernetes operators: Automated storage provisioning, scaling, backup

---

**This chapter's guarantee vector**: `⟨Global, Causal, RA, BS(examples), Idem, Auth(research)⟩`
- Explored global storage landscape (ACID → BASE → NewSQL → Multi-Model)
- Preserved causal understanding (evolution driven by business needs)
- Provided read-atomic knowledge (comprehensive examples)
- Bounded staleness via concrete case studies and papers
- Idempotent insights (revisit anytime)
- Authenticated by foundational papers and production experience

**Context capsule for next chapter**: `{invariant: COMPOSITION, evidence: polyglot-persistence, boundary: service-boundaries, mode: Target, fallback: revisit storage choices per service}`

# ACID to BASE: The Great Paradigm Shift

## Introduction

For decades, database developers operated in a world of comforting certainties. Transactions were atomic, consistency was guaranteed, isolation was perfect, and durability was absolute. These ACID properties weren't just features—they were the foundation of how we reasoned about data correctness. They made programming easier, debugging simpler, and operations more predictable.

Then the web happened.

Not the web of the 1990s, with its millions of users and gigabytes of data. The web of the 2000s and beyond—with billions of users, petabytes of data, global distribution, and the expectation of always-on availability. Suddenly, the ACID guarantees that had served us so well became an anchor holding us back.

This chapter tells the story of one of computing's most fundamental transitions: the shift from ACID to BASE. It's a story of scaling limits, paradigm shifts, practical compromises, and the gradual realization that consistency isn't binary—it exists on a spectrum, and the right choice depends on context.

### The Comfort of ACID Guarantees

ACID databases provided a beautiful abstraction. Within a transaction boundary, you could pretend the rest of the world didn't exist. You could read data, modify it, and write it back with the guarantee that:

- Either all your changes would succeed or none would (Atomicity)
- Your changes would never violate database constraints (Consistency)
- Other transactions wouldn't interfere with yours (Isolation)
- Once committed, your changes would survive any failure (Durability)

This meant you could write business logic without worrying about concurrent access, partial failures, or data corruption. The database handled all that complexity for you. It was like having a perfect secretary who ensured all your paperwork was always in order.

### Why ACID Hit Scaling Limits

The problem emerged when databases needed to scale beyond a single machine. ACID properties rely on coordination—the ability for different parts of the system to communicate and reach agreement. On a single machine, this coordination happens through shared memory and is relatively cheap. Across multiple machines, especially across geographic regions, coordination becomes expensive and sometimes impossible.

Consider a simple transfer between two bank accounts. In an ACID system on a single machine, this is straightforward:

```sql
BEGIN TRANSACTION;
UPDATE accounts SET balance = balance - 100 WHERE id = 'A';
UPDATE accounts SET balance = balance + 100 WHERE id = 'B';
COMMIT;
```

But what if account A is in a database in New York and account B is in a database in London? Now that transaction requires:

- Network communication across the Atlantic (100ms+ latency)
- Distributed locking to prevent conflicts
- Two-phase commit to ensure atomicity
- Synchronous replication for durability

The transaction that took microseconds on a single machine now takes hundreds of milliseconds and can fail in dozens of new ways.

### The BASE Alternative

BASE—Basically Available, Soft state, Eventual consistency—emerged as an alternative approach. Instead of providing perfect guarantees at all times, BASE systems provide weaker guarantees that are easier to maintain at scale:

- **Basically Available**: The system remains operational even during partial failures
- **Soft state**: System state may change over time, even without new input
- **Eventual consistency**: If we stop updating the system, it will eventually reach a consistent state

This might sound like a step backward—and in some ways it is—but it enables scaling that's simply impossible with ACID. It's a trade-off, and like all trade-offs in distributed systems, the right choice depends on your specific requirements.

### Not a Replacement but a Complement

Here's the crucial insight that took the industry years to fully grasp: BASE isn't a replacement for ACID. It's a complement. Modern systems use both, applying ACID where strong consistency is critical and BASE where availability and scale are more important.

The art of distributed system design is knowing where to draw those boundaries.

## The ACID Foundation

Before we explore the transition to BASE, we need to deeply understand what we're transitioning from. ACID isn't just four letters—it's a carefully constructed system of guarantees, each with its own implementation mechanisms, costs, and trade-offs.

### Atomicity: All or Nothing

#### What It Means

Atomicity is the guarantee that a transaction is indivisible. Either all operations in the transaction succeed and are committed, or they all fail and the database remains unchanged. There is no middle ground, no partial completion, no "mostly worked."

Consider a travel booking system:

```python
def book_trip(user_id, flight_id, hotel_id):
    with transaction():
        reserve_flight(user_id, flight_id)
        reserve_hotel(user_id, hotel_id)
        charge_credit_card(user_id, total_cost)
        commit()
```

With atomicity, if the credit card charge fails, the flight and hotel reservations are automatically rolled back. The user won't end up with reservations they can't pay for, and the business won't provide services without payment.

#### Implementation Mechanisms

Atomicity doesn't happen by magic. Databases use several sophisticated mechanisms to provide this guarantee:

**Write-Ahead Logging (WAL)**

The most common approach. Before making any change to the database, the system writes a log entry describing what it's about to do. This log serves two purposes:

1. **Redo**: If a transaction commits but the system crashes before changes reach disk, the log can replay the changes
2. **Undo**: If a transaction needs to abort, the log contains information needed to reverse the changes

The log is written sequentially, making it much faster than random writes to the main database files.

**Undo/Redo Logs**

A more sophisticated version of WAL that maintains both:

- **Undo records**: Old values, used to roll back transactions
- **Redo records**: New values, used to replay committed transactions

This allows the database to recover from crashes at any point in transaction processing.

**Shadow Paging**

Instead of modifying data in place, the database makes a copy, modifies the copy, and atomically switches to the new version. The original version serves as a backup if rollback is needed.

```
Before:
Root -> Page A -> Page B (contains "old value")

During Transaction:
Root -> Page A -> Page B (contains "old value")
Shadow Root -> Page A -> Page B' (contains "new value")

After Commit:
Root -> Page A -> Page B' (contains "new value")
```

**Multi-Version Concurrency Control (MVCC)**

Maintains multiple versions of data items. Each transaction sees a consistent snapshot of the database at a particular point in time. Old versions are kept until no transaction needs them.

#### The Cost

Atomicity isn't free. Every transaction pays these costs:

**Locking Overhead**

To ensure atomicity, the database must prevent conflicting concurrent access. This means:

- Acquiring locks (CPU cost)
- Waiting for locks held by other transactions (latency cost)
- Deadlock detection and resolution (CPU + latency cost)

**Log Writes**

Every transaction generates log entries that must be written to durable storage before commit:

- Log write I/O (latency cost)
- Log space consumption (storage cost)
- Log archival and cleanup (operational cost)

**Rollback Space**

The database must maintain enough information to undo any active transaction:

- Undo log space (memory/storage cost)
- Longer transactions = more undo space required
- Limits on transaction size or duration

**Coordination Cost**

In distributed databases, atomicity requires coordination between nodes:

- Two-phase commit protocol (multiple network round-trips)
- Holding locks across network calls (increased lock contention)
- Failure handling complexity (timeouts, uncertainty)

For a single-node database handling small transactions, these costs are manageable. For a globally distributed database handling large transactions, they become prohibitive.

### Consistency: Valid States Only

#### Database Invariants

Consistency means the database remains in a valid state. But what does "valid" mean? It means all database invariants hold—rules that must always be true about your data.

**Referential Integrity**

The most common invariant. Foreign keys must reference existing rows:

```sql
CREATE TABLE orders (
    id INT PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    product_id INT REFERENCES products(id)
);
```

This ensures you can't create an order for a non-existent customer or product.

**Check Constraints**

Arbitrary rules about data values:

```sql
CREATE TABLE accounts (
    id INT PRIMARY KEY,
    balance DECIMAL CHECK (balance >= 0),
    account_type VARCHAR(20) CHECK (account_type IN ('checking', 'savings'))
);
```

**Triggers and Rules**

Complex invariants enforced by database code:

```sql
CREATE TRIGGER maintain_total
AFTER INSERT OR UPDATE OR DELETE ON line_items
FOR EACH ROW
EXECUTE FUNCTION update_order_total();
```

**Application Invariants**

Higher-level rules that span multiple tables:

- "A user cannot have more than 3 active subscriptions"
- "Total allocated inventory cannot exceed total available inventory"
- "An appointment cannot be double-booked"

#### Enforcement Points

Consistency is enforced at several points in transaction processing:

**Pre-Commit Validation**

Before a transaction commits, the database checks all constraints:

```
1. Transaction modifies data
2. Transaction calls COMMIT
3. Database checks all constraints
4. If any constraint violated: ROLLBACK
5. If all constraints satisfied: COMMIT proceeds
```

**Constraint Checking**

Can happen at different times:

- **Immediate**: Checked after each statement
- **Deferred**: Checked at commit time (allows temporary violations)

**Trigger Execution**

Triggers fire at defined points and can enforce complex invariants:

```sql
CREATE TRIGGER check_inventory
BEFORE INSERT ON order_items
FOR EACH ROW
EXECUTE FUNCTION verify_inventory_available();
```

**Transaction Boundaries**

Consistency is only guaranteed at transaction boundaries. Within a transaction, the database might temporarily violate invariants, but they must be restored before commit.

#### Scaling Challenge

Consistency becomes difficult in distributed systems because invariants often span data that's stored on different nodes.

**Cross-Shard Constraints**

If customers are on one shard and orders on another, enforcing referential integrity requires cross-shard coordination:

```
Shard A (Customers):     Shard B (Orders):
customer_id=123          order wants customer_id=123
                         Must verify 123 exists
                         Requires communication
```

**Distributed Validation**

Checking a constraint like "total inventory across all warehouses" requires:

1. Querying all warehouses (network calls)
2. Computing the total (coordination)
3. Holding locks until commit (blocking)
4. Two-phase commit (more coordination)

**Global Invariants**

Some invariants are inherently global:

- "No two users can have the same email address"
- "The sum of all account balances must equal zero" (for double-entry bookkeeping)
- "Only one admin per organization"

Enforcing these across a distributed system requires either:

- Putting all related data on the same node (limits scalability)
- Global coordination (limits performance)
- Weakening the guarantee (breaks consistency)

**Coordination Overhead**

Every constraint check that spans nodes adds latency:

- Same datacenter: ~1ms
- Cross-datacenter (same region): ~5-10ms
- Cross-region (e.g., US to Europe): ~100ms+

For a transaction that checks 10 cross-shard constraints, you've added a second of latency just for consistency checking.

### Isolation: Alone Together

Isolation is perhaps the most complex of the ACID properties. It defines how concurrent transactions interact with each other. Perfect isolation means each transaction executes as if it's the only transaction in the system, but perfect isolation is also the most expensive to provide.

#### Isolation Levels

SQL defines four standard isolation levels, each trading consistency for performance:

**Read Uncommitted**

The weakest isolation level. Transactions can see uncommitted changes from other transactions.

```
Transaction A:              Transaction B:
UPDATE accounts
SET balance = 100
WHERE id = 1
                           SELECT balance FROM accounts WHERE id = 1
                           -- Sees 100 (uncommitted!)
ROLLBACK
                           -- Value is now wrong
```

This allows **dirty reads**—reading data that might be rolled back. Almost never used in practice because it's too dangerous.

**Advantages:**
- Highest concurrency (no read locks)
- Lowest latency
- Simplest implementation

**Disadvantages:**
- Can read data that never "officially" existed
- Complex error handling in application code
- Debugging nightmares

**Read Committed**

Transactions can only see committed changes. This is the default level for many databases.

```
Transaction A:              Transaction B:
                           SELECT balance FROM accounts WHERE id = 1
                           -- Sees 50
UPDATE accounts
SET balance = 100
WHERE id = 1
COMMIT
                           SELECT balance FROM accounts WHERE id = 1
                           -- Now sees 100
```

This prevents dirty reads but allows **non-repeatable reads**—reading the same data twice in a transaction can return different values.

**Advantages:**
- No dirty reads
- Good performance
- Reasonable for many workloads

**Disadvantages:**
- Same query can return different results in one transaction
- Complex application logic if consistency within transaction is needed

**Repeatable Read**

A transaction sees a consistent snapshot of the database. If you read a value, you'll get the same value if you read it again.

```
Transaction A:              Transaction B:
                           BEGIN TRANSACTION
                           SELECT balance FROM accounts WHERE id = 1
                           -- Sees 50
UPDATE accounts
SET balance = 100
WHERE id = 1
COMMIT
                           SELECT balance FROM accounts WHERE id = 1
                           -- Still sees 50 (repeatable read)
                           COMMIT
```

This prevents non-repeatable reads but allows **phantom reads**—new rows can appear in query results.

```
Transaction A:              Transaction B:
                           BEGIN TRANSACTION
                           SELECT COUNT(*) FROM accounts
                           -- Sees 10 accounts
INSERT INTO accounts
VALUES (11, 100)
COMMIT
                           SELECT COUNT(*) FROM accounts
                           -- Sees 11 accounts (phantom!)
                           COMMIT
```

**Advantages:**
- Consistent reads within transaction
- Good for reports and analytics
- Better reasoning about data

**Disadvantages:**
- Higher lock contention
- Phantoms still possible
- More memory for versioning

**Serializable**

The strongest isolation level. Transactions execute as if they ran serially, one after another.

```
Transaction A:              Transaction B:
BEGIN TRANSACTION          BEGIN TRANSACTION
SELECT balance FROM accounts WHERE id = 1
-- Sees 50
                           SELECT balance FROM accounts WHERE id = 1
                           -- Also sees 50
UPDATE accounts
SET balance = 60
WHERE id = 1
                           UPDATE accounts
                           SET balance = 70
                           WHERE id = 1
COMMIT                     -- Transaction B must wait or abort
                           -- (depending on implementation)
```

No anomalies are possible, but at significant cost.

**Advantages:**
- Perfect isolation
- Simplest application logic
- Easiest to reason about

**Disadvantages:**
- Lowest concurrency
- Highest lock contention
- Frequent aborts/retries
- Worst performance

#### Implementation Approaches

Different databases implement isolation using different techniques:

**Pessimistic Locking**

Acquire locks before accessing data. Hold locks until transaction completes.

```
Transaction wants to read row:
1. Acquire shared (read) lock
2. Read the row
3. Hold lock until COMMIT/ROLLBACK

Transaction wants to write row:
1. Acquire exclusive (write) lock
2. Write the row
3. Hold lock until COMMIT/ROLLBACK
```

**Pros:**
- Prevents conflicts before they happen
- Straightforward to understand
- Works well for high-contention workloads

**Cons:**
- Deadlocks possible (two transactions waiting for each other's locks)
- Reduced concurrency (locks block other transactions)
- Lock management overhead

**Optimistic Concurrency**

Assume conflicts are rare. Don't lock, but check for conflicts before commit.

```
Transaction execution:
1. Read data without locks (note version/timestamp)
2. Make changes in private workspace
3. At commit time, verify no one else modified the data
4. If modified: abort and retry
5. If unchanged: commit changes
```

**Pros:**
- High concurrency (no locks held during execution)
- No deadlocks
- Good for low-contention workloads

**Cons:**
- Wasted work if transaction aborts
- High contention causes retry storms
- Application must handle aborts

**Multi-Version Concurrency Control (MVCC)**

Maintain multiple versions of each data item. Each transaction sees a consistent snapshot.

```
Version Chain for row with id=1:
[v1: balance=50, xmin=100, xmax=∞] -> current version
[v2: balance=60, xmin=150, xmax=∞] -> newer version

Transaction with snapshot_id=120:
- Sees version v1 (created by xmin=100, before snapshot)

Transaction with snapshot_id=160:
- Sees version v2 (created by xmin=150, before snapshot)
```

**Pros:**
- Readers don't block writers
- Writers don't block readers
- Good performance for read-heavy workloads
- Can provide different isolation levels

**Cons:**
- Space overhead (old versions)
- Cleanup complexity (vacuum/garbage collection)
- Write-write conflicts still need resolution

**Timestamp Ordering**

Assign each transaction a unique timestamp. Ensure reads/writes happen in timestamp order.

```
Transaction T1 (timestamp=100):
- Wants to read row X
- Check: has any T > 100 written X? (no)
- Proceed with read

Transaction T2 (timestamp=150):
- Wants to write row X
- Check: has any T > 150 read X? (no)
- Check: has any T > 150 written X? (no)
- Proceed with write
```

**Pros:**
- Deadlock-free
- No waiting for locks
- Distributed-friendly (can use synchronized clocks)

**Cons:**
- Transaction aborts if timestamp order violated
- Synchronized clocks difficult in distributed systems
- Overhead of timestamp tracking

### Durability: Surviving Failure

Durability guarantees that once a transaction commits, its changes persist even if the system crashes immediately afterward. This seems simple but has profound implications for performance and system design.

#### Mechanisms

**Write-Ahead Logging (WAL)**

The primary mechanism for durability. Log changes before applying them:

```
Transaction commits:
1. Write log record to log buffer
2. Flush log buffer to disk (fsync)
3. Return success to client
4. Later: Apply changes to actual database files
```

The log is the source of truth. As long as the log persists, changes can be recovered.

**Checkpointing**

Periodically apply logged changes to the main database files and mark a "checkpoint":

```
Checkpoint process:
1. Flush all dirty pages to disk
2. Write checkpoint record to log
3. Now recovery can start from checkpoint (not from beginning of log)
```

This keeps recovery time bounded and allows old log files to be archived.

**Replication**

Maintain multiple copies of data:

- **Synchronous replication**: Wait for replicas to acknowledge before commit
- **Asynchronous replication**: Commit immediately, replicate in background

**Backup Strategies**

Periodic backups provide disaster recovery:

- **Full backup**: Copy entire database
- **Incremental backup**: Copy only changes since last backup
- **Point-in-time recovery**: Replay logs to specific time

#### Trade-offs

Durability has a cost, and different applications make different trade-offs:

**Synchronous vs Async**

```python
# Synchronous (durable, slow)
def commit_sync():
    write_to_log()
    fsync()  # Wait for disk
    return "committed"

# Asynchronous (fast, risky)
def commit_async():
    write_to_log()
    # OS will write to disk eventually
    return "committed"
```

Synchronous is safer but adds ~10ms per transaction (SSD seek time). Asynchronous is faster but can lose the last few transactions if power fails.

**Performance Impact**

Every commit requires a disk sync, which is slow:

- HDD: ~10ms seek time
- SSD: ~0.1ms seek time
- RAM: ~0.0001ms

This means a single-threaded synchronous system can do:

- HDD: ~100 commits/second
- SSD: ~10,000 commits/second
- RAM: ~10,000,000 commits/second

Group commit helps: batch multiple transactions into one fsync.

**Recovery Time**

More durable systems often have longer recovery times:

```
Recovery process:
1. Read checkpoint
2. Replay all logs since checkpoint
3. Undo uncommitted transactions
4. System ready for use

Time = log_size * processing_rate
```

Long-running transactions or delayed checkpoints increase recovery time.

**Data Loss Potential**

Different configurations lose different amounts of data on failure:

- **Synchronous replication**: Zero data loss
- **Asynchronous replication (1s lag)**: Up to 1 second of transactions
- **No replication**: Everything since last backup

## Why ACID Hit the Wall

ACID served the industry well for decades, but three forces converged to make ACID databases insufficient for modern web-scale applications: hardware limits, geographic distribution, and economic pressures.

### The Vertical Scaling Limit

For most of computing history, databases scaled by buying bigger machines. Need more performance? Add more RAM, faster CPUs, more disks. This **vertical scaling** worked wonderfully because:

1. Hardware got exponentially better (Moore's Law)
2. Software didn't need to change
3. ACID guarantees were preserved

Then the free lunch ended.

**Moore's Law Slowdown**

CPU clock speeds stopped increasing around 2005:

```
Year    Clock Speed
1990    25 MHz
2000    1.5 GHz     (60x improvement)
2005    3.5 GHz     (2.3x improvement)
2010    3.5 GHz     (no improvement)
2020    4.0 GHz     (1.1x improvement)
```

We got more cores, but that doesn't help single-threaded workloads (like transaction processing with strict serialization).

**RAM Limitations**

Physical limits on RAM per machine:

- Commodity servers: ~1TB RAM
- High-end servers: ~12TB RAM
- Cost: $10-$100 per GB at scale

Facebook has ~3 billion users. Just storing user IDs (4 bytes each) requires 12GB. Add any actual data and you've exceeded a single machine's capacity.

**I/O Bottlenecks**

Disk I/O improvements slowed:

```
Technology     Random IOPS    Latency
HDD (2000)     ~100           ~10ms
HDD (2020)     ~100           ~10ms    (no improvement)
SSD (2020)     ~100,000       ~0.1ms   (1000x better)
RAM (2020)     ~10,000,000    ~0.0001ms
```

SSDs helped, but they're expensive and still slower than RAM. Meanwhile, data sizes grew exponentially.

**Cost Explosion**

Bigger machines cost exponentially more:

```
RAM             Machine Cost    Cost per GB
64 GB          $5,000          $78
256 GB         $15,000         $59
1 TB           $80,000         $80
4 TB           $400,000        $100
```

At some point, buying a machine twice as big costs more than twice as much. Vertical scaling hits economic limits.

### The Geographic Challenge

Modern applications serve global users. Users in Tokyo shouldn't experience terrible latency because your database is in Virginia. But spreading data globally is incompatible with ACID.

**Cross-Region Latency**

Physics imposes limits:

```
Connection              Latency (speed of light)    Observed
Same rack              ~0.1ms                      ~1ms
Same datacenter        ~1ms                        ~2ms
Cross-coast US         ~20ms                       ~50ms
US to Europe           ~40ms                       ~100ms
US to Asia             ~80ms                       ~200ms
```

Every cross-region transaction coordination adds at least one round-trip. A transaction that touches data in 3 regions takes 200-300ms minimum—an eternity for web requests.

**Network Partitions**

Networks fail, especially across regions. When that happens, ACID systems face an impossible choice:

```
Datacenter A (US)      <--X-->      Datacenter B (Europe)
Has user data                       Has order data

Network partition occurs!

Option 1: Block all transactions (preserve ACID, lose availability)
Option 2: Allow transactions (preserve availability, lose consistency)
```

The CAP theorem proves you can't have both consistency and availability during a partition. ACID chooses consistency, which means unavailability during network failures.

**Consistency Delays**

To maintain consistency across regions, every transaction must:

1. Acquire locks in all regions
2. Validate constraints in all regions
3. Two-phase commit across all regions
4. Wait for all regions to acknowledge

This means every write takes as long as the slowest region's round-trip time.

**Availability Issues**

ACID requires all replicas to be available:

```
3-replica system with ACID:
- All 3 available: System works
- 1 fails: System blocks (can't guarantee consistency)
- 2 fail: System definitely blocks
```

With replicas in different regions, the probability of at least one being unreachable increases dramatically.

### The Web Scale Problem

"Web scale" isn't just marketing—it's a qualitatively different problem than traditional database applications.

**Billions of Users**

Facebook: 3 billion users
Google: 4 billion users
WeChat: 1.3 billion users

Traditional databases were designed for thousands of concurrent users. Web scale means millions of concurrent users, all making requests simultaneously.

**Petabytes of Data**

Facebook: ~300 petabytes
Google: ~15,000 petabytes
Amazon: ~100 petabytes

No single machine can store this much data. Even if one could, the backup and recovery times would be measured in months.

**24/7 Availability**

Traditional systems had maintenance windows:

```
"The database will be down Saturday 2am-6am for upgrades"
```

Web scale means always-on:

- Users in every timezone
- Global markets never close
- Downtime costs millions per minute
- Competition is one click away

**Global Distribution**

Users everywhere expect local performance:

- US user: database in Virginia (50ms)
- Europe user: database in Virginia (150ms) ❌
- Asia user: database in Virginia (250ms) ❌❌

The only solution is data in multiple regions. But that's incompatible with single-machine ACID.

### The Economics

Ultimately, ACID hit the wall because of money.

**Hardware Costs**

Vertical scaling costs grow exponentially:

```
Scenario: 1 million transactions/second

Option A: One giant machine
- Cost: $2 million
- Risk: Single point of failure
- Scaling: Hit ceiling at ~2 million TPS

Option B: 100 commodity machines
- Cost: $500,000
- Risk: Redundancy built in
- Scaling: Add more machines
```

The cost difference compounds over time as the system grows.

**Operational Complexity**

Large ACID databases are operationally complex:

- Long backup/recovery times
- Careful upgrade planning
- Expensive DBAs
- Risky migrations

**Development Velocity**

ACID systems often become bottlenecks:

- Schema changes require downtime
- Migrations are risky
- Scaling requires DBA involvement
- Joins across shards are impossible

This slows down product development.

**Business Agility**

Markets move fast. The cost of ACID isn't just money—it's opportunity:

- Competitor launches feature while you're migrating database
- Can't enter new market due to scaling limits
- Can't handle traffic spike during event
- Can't process data fast enough for real-time decisions

Companies that solved the scaling problem gained competitive advantage.

## Enter BASE

Faced with ACID's scaling limits, a new approach emerged: BASE (Basically Available, Soft state, Eventual consistency). Rather than providing perfect guarantees at all times, BASE systems provide weaker guarantees that are much easier to maintain at scale.

### Basically Available

The system stays operational even during partial failures. Instead of blocking all requests when something fails, the system continues serving requests with possibly degraded functionality.

#### What It Means

Traditional ACID systems follow an "all or nothing" approach to availability:

```
Database cluster:
- All nodes healthy: System available ✓
- One node fails: System unavailable ✗ (can't guarantee consistency)
```

BASE systems follow a "best effort" approach:

```
Database cluster:
- All nodes healthy: System fully available ✓
- One node fails: System partially available ✓ (serve from other nodes)
- Two nodes fail: System still partially available ✓
- All nodes fail: System unavailable ✗
```

This is a probabilistic guarantee: the system is probably available, and the probability increases with the number of replicas.

**Degraded Mode is Acceptable**

When failures occur, the system doesn't shut down—it degrades gracefully:

```
Normal mode:
- All features available
- All data accessible
- Full consistency guarantees

Degraded mode:
- Core features available
- Some data might be stale
- Reduced consistency guarantees
- Slower responses
```

Example: Amazon's shopping cart continues working even if recommendation system fails. You lose personalized recommendations, but you can still check out.

**Partial Failures OK**

In ACID systems, any failure can halt the entire system. In BASE systems, failures are isolated:

```
E-commerce system:
- User service fails: Auth affected, but browsing works
- Inventory service fails: Can't order, but can browse
- Payment service fails: Can't checkout, but can add to cart
- Recommendation service fails: No recommendations, but shopping works
```

Each subsystem can fail independently without taking down the entire application.

**Best Effort Service**

The system tries to serve every request but doesn't guarantee success:

```python
def read_user_profile(user_id):
    # Try primary datacenter
    try:
        return primary_dc.read(user_id)
    except Exception:
        # Fall back to secondary datacenter
        try:
            return secondary_dc.read(user_id)
        except Exception:
            # Fall back to cache
            try:
                return cache.read(user_id)
            except Exception:
                # Give up gracefully
                return default_profile()
```

This approach maximizes availability at the cost of consistency—you might get stale data from cache, but you get something.

#### Implementation

Achieving basic availability requires several strategies:

**Redundancy**

Multiple copies of everything:

```
3-replica system:
Node A: Full copy of data
Node B: Full copy of data
Node C: Full copy of data

Any 1 node can serve requests
System survives 2 node failures
```

More replicas = higher availability but higher cost.

**Failover**

Automatic detection and recovery from failures:

```
1. Health check detects node failure
2. Remove failed node from rotation
3. Route traffic to healthy nodes
4. Alert operators
5. When node recovers, add back to rotation
```

Fast failover (< 1 second) is critical for availability.

**Load Balancing**

Distribute requests across healthy nodes:

```
Load Balancer
    ├─> Node A (healthy, 30% capacity)
    ├─> Node B (healthy, 40% capacity)
    ├─> Node C (degraded, 10% capacity)
    └─X─ Node D (failed, removed)
```

Load balancers continuously monitor node health and adjust routing.

**Circuit Breakers**

Stop calling failing services:

```python
class CircuitBreaker:
    def call_service(self):
        if self.state == OPEN:
            # Circuit open, fail fast
            raise ServiceUnavailable()

        try:
            result = service.call()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            if self.failure_rate > threshold:
                self.state = OPEN  # Stop calling
            raise

States:
CLOSED (normal): Calls go through
OPEN (failing): Calls fail immediately
HALF-OPEN (testing): Try occasional calls
```

This prevents cascading failures—a failing service doesn't bring down callers.

### Soft State

The state of the system may change over time without external input. This is a radical departure from ACID databases, where state only changes due to transactions.

#### The Concept

In ACID systems, data is hard state:

```
Write: balance = 100
Read:  balance = 100 (always, until another write)
```

In BASE systems, data is soft state:

```
Write: balance = 100
Read:  balance = 100 (probably)
Read:  balance = 95  (maybe, if stale replica)
Wait:  balance = 100 (eventually converges)
```

State can change due to:

- Background synchronization
- Conflict resolution
- Cache expiration
- Lease expiration
- Anti-entropy repairs

**No External Input Needed**

The system evolves toward consistency on its own:

```
Time 0: Write "value=100" to Node A
Time 1: Node A = 100, Node B = old, Node C = old (inconsistent)
Time 2: Node A = 100, Node B = 100, Node C = old (converging)
Time 3: Node A = 100, Node B = 100, Node C = 100 (consistent)
```

No additional writes happened, but state changed.

**Eventual Convergence**

Given enough time without new writes, all replicas converge to the same value:

```python
def anti_entropy_repair():
    """Background process that repairs inconsistencies"""
    while True:
        for key in all_keys():
            versions = [node.get(key) for node in nodes]
            if versions_differ(versions):
                latest = resolve_conflict(versions)
                for node in nodes:
                    node.put(key, latest)
        sleep(repair_interval)
```

**Time-Bounded Inconsistency**

While state is soft, inconsistency doesn't last forever:

```
Typical convergence times:
Same datacenter: milliseconds
Cross-datacenter: seconds
With failures: minutes
```

Systems aim to minimize this window.

#### Examples

**Cache Expiration**

Caches hold soft state with explicit TTLs:

```python
cache.set("user:123", user_data, ttl=300)  # 5 minutes

# Read immediately: gets cached value (fast)
cache.get("user:123")  # Returns user_data

# After 5 minutes: cache expired
cache.get("user:123")  # Returns None

# Next read fetches from database and repopulates cache
```

State changed (cached data disappeared) without external write.

**Session Timeouts**

User sessions are soft state:

```python
# User logs in
session_id = create_session(user_id, expires=now() + hours(24))

# 24 hours later, session expires automatically
# User must log in again
# State changed without explicit "logout" action
```

**Lease Expiration**

Distributed locks with automatic expiration:

```python
# Acquire lock
lock = acquire_lock("resource", lease_time=10)

# Do work
process_resource()

# If process crashes, lock auto-releases after 10 seconds
# Other processes can proceed
```

Leases prevent deadlocks from failures—if a lock holder crashes, the lock eventually expires.

**TTL Values**

DNS, CDNs, and many distributed systems use TTL:

```
DNS record:
example.com -> 1.2.3.4 (TTL: 300 seconds)

After 300 seconds, clients re-query DNS
If IP changed, clients get new IP
Old IP still cached some places
Eventually all clients see new IP
```

### Eventual Consistency

The system guarantees that if no new updates are made, all replicas will eventually converge to the same value. This is the heart of BASE: trading immediate consistency for eventual consistency.

#### The Promise

**Convergence Guaranteed**

No matter what sequence of operations occurs, given enough time without new writes, all nodes will agree:

```
Scenario:
Time 0: Write X=1 to Node A
Time 1: Write X=2 to Node B
Time 2: Write X=3 to Node C

Inconsistent state:
Node A: X=1
Node B: X=2
Node C: X=3

Eventually (exact time unbounded):
Node A: X=3
Node B: X=3
Node C: X=3
```

**Time Unbounded**

"Eventually" has no specific deadline:

- Might be milliseconds
- Might be seconds
- Might be minutes (during failures)
- Might be hours (if network partition)

The system makes no promises about how long it takes.

**No Ordering Guarantees**

Different replicas might see operations in different orders:

```
Client 1 writes A=1
Client 2 writes A=2

Node X sees: A=1, then A=2 (final: A=2)
Node Y sees: A=2, then A=1 (final: A=1)

Conflict! Needs resolution.
```

**Conflict Resolution**

When replicas disagree, the system needs a strategy:

- Last write wins (based on timestamp)
- Application-defined merge (e.g., shopping cart union)
- Version vectors (track causality)
- User choice (prompt user to resolve)

#### Mechanisms

**Anti-Entropy**

Background process that compares replicas and repairs differences:

```python
def anti_entropy():
    """Compare local data with peers and sync differences"""
    for peer in peers:
        # Exchange Merkle trees to find differences efficiently
        their_tree = peer.get_merkle_tree()
        my_tree = self.get_merkle_tree()

        differences = compare_trees(my_tree, their_tree)

        for key in differences:
            my_version = self.get(key)
            their_version = peer.get(key)

            # Reconcile versions
            latest = reconcile(my_version, their_version)

            # Push latest to both nodes
            self.put(key, latest)
            peer.put(key, latest)
```

Runs periodically to ensure convergence.

**Read Repair**

Fix inconsistencies detected during reads:

```python
def read(key):
    # Read from multiple replicas
    responses = [replica.get(key) for replica in replicas]

    # Find most recent version
    latest = max(responses, key=lambda r: r.timestamp)

    # If any replica has old version, repair it
    for replica, response in zip(replicas, responses):
        if response.timestamp < latest.timestamp:
            replica.put(key, latest)  # Asynchronously repair

    return latest.value
```

Every read helps maintain consistency.

**Hinted Handoff**

When a node is temporarily unavailable, other nodes hold writes for it:

```
Normal write:
Client -> Node A (primary for key)

Node A unavailable:
Client -> Node B (not primary, but available)
Node B stores: "key=value, intended for Node A"

Node A returns:
Node B hands off to Node A: "here's a write for you"
Node A now has the data
```

Helps with temporary failures.

**Vector Clocks**

Track causality to detect conflicts:

```
Vector clock: [Node A: 0, Node B: 0, Node C: 0]

Node A writes: [Node A: 1, Node B: 0, Node C: 0]
Node B writes: [Node A: 0, Node B: 1, Node C: 0]

Later, Node C sees both writes:
[Node A: 1, Node B: 0, Node C: 0] vs [Node A: 0, Node B: 1, Node C: 0]

Neither dominates the other -> concurrent writes -> conflict!
Must resolve using business logic
```

Vector clocks allow detecting true conflicts vs. causally related updates.

## The Transition Journey

Moving from ACID to BASE isn't just a technical change—it's a paradigm shift. Teams go through predictable stages, remarkably similar to the Kübler-Ross five stages of grief.

### Stage 1: Denial

**"We need ACID for everything"**

Fresh from traditional database backgrounds, teams initially try to maintain ACID properties even as they scale. This leads to:

**Over-Engineering**

```python
# Trying to maintain ACID across microservices
def create_order(user_id, items):
    with distributed_transaction():  # Doesn't scale!
        user_service.validate_user(user_id)
        inventory_service.reserve_items(items)
        payment_service.charge_card(user_id, total)
        shipping_service.create_shipment(user_id, items)
        commit_all_or_nothing()
```

The code looks clean, but the distributed transaction implementation is a nightmare:

- Two-phase commit across services
- Locks held across network calls
- Timeouts and uncertainty
- Deadlocks across services

**Performance Problems**

Every operation requires coordination:

```
Normal response time: 50ms
With distributed transaction:
- Prepare phase: +50ms (network round-trip)
- Lock acquisition: +20ms (contention)
- Commit phase: +50ms (another round-trip)
Total: 170ms (3.4x slower)

Under load:
- Lock contention increases
- Timeouts become common
- Retries make it worse
Total: 500ms+ (10x slower)
```

**Scaling Issues**

The system hits scaling limits early:

```
1,000 TPS: System OK
5,000 TPS: Latency increases (lock contention)
10,000 TPS: Timeouts common (coordination overhead)
20,000 TPS: System unusable (deadlocks everywhere)
```

**Cost Explosion**

Maintaining ACID at scale requires expensive hardware:

```
Year 1: $100K/month (single large database)
Year 2: $250K/month (bigger database, starting to max out)
Year 3: $500K/month (largest available, still struggling)
```

Eventually, the team realizes this isn't sustainable.

### Stage 2: Anger

**"This distributed stuff is impossible"**

The team starts adopting eventual consistency but without proper understanding. Chaos ensues.

**Consistency Bugs**

```python
# Shopping cart in eventually consistent database
def add_to_cart(user_id, item):
    cart = read_cart(user_id)
    cart.items.append(item)
    write_cart(user_id, cart)

# Problem: concurrent adds from multiple devices
Device 1: read cart (3 items), add item A, write (4 items)
Device 2: read cart (3 items), add item B, write (4 items)

# Result: cart has 4 items instead of 5
# One item disappeared!
```

**Data Corruption**

```python
# Updating counter without proper coordination
def increment_view_count(article_id):
    count = read_count(article_id)
    write_count(article_id, count + 1)

# Multiple concurrent increments
Thread 1: read 100, write 101
Thread 2: read 100, write 101
Thread 3: read 100, write 101

# Result: count is 101 instead of 103
# Lost updates!
```

**Debugging Nightmares**

```
Customer: "My order shows different items in app vs website"
Developer: "Let me check... they're reading different replicas"

Customer: "Sometimes my new address shows up, sometimes the old one"
Developer: "That's eventual consistency, it'll fix itself eventually"

Customer: "I added an item but it disappeared"
Developer: "Concurrent update conflict with resolution logic that chose wrong version"

Customer: "This is unacceptable"
Developer: "I know... I know..."
```

**Customer Complaints**

Users don't understand or care about eventual consistency:

- "The app is buggy"
- "My data keeps disappearing"
- "Different devices show different information"
- "I can't trust this service"

The team feels like they've made things worse, not better.

### Stage 3: Bargaining

**"Maybe some eventual consistency"**

The team realizes they need a more nuanced approach. Not everything needs to be eventually consistent, and not everything needs to be ACID.

**Identify Boundaries**

Start analyzing which data needs strong consistency:

```
Strong consistency needed:
- User authentication (can't be eventually logged in)
- Financial transactions (money must be exact)
- Inventory reservation (can't oversell)
- Unique constraints (email, username)

Eventual consistency acceptable:
- Social media timeline (stale OK)
- Product recommendations (stale OK)
- Analytics/metrics (approximate OK)
- Search indexes (lag tolerable)
```

**Separate Concerns**

Break the system into bounded contexts:

```
Identity Service (ACID):
- User accounts
- Authentication
- Permissions

Shopping Service (Mixed):
- Product catalog (eventual)
- Shopping cart (eventual with conflict resolution)
- Checkout (ACID within order)

Analytics Service (Eventual):
- Page views
- User behavior
- A/B test results
```

**Hybrid Approaches**

Use different consistency models for different operations:

```python
class UserProfile:
    # Strong consistency
    email: str          # Unique, must be consistent
    password: str       # Security-critical

    # Eventual consistency
    display_name: str   # Can be stale
    avatar_url: str     # Can be stale
    preferences: dict   # Can be stale
```

**Gradual Migration**

Move to eventual consistency incrementally:

```
Phase 1: Move read-only data (catalogs, static content)
Phase 2: Move append-only data (logs, events)
Phase 3: Move user-generated content (comments, posts)
Phase 4: Move transactional data (orders, payments) - carefully!
```

### Stage 4: Depression

**"We've lost all guarantees"**

The system now has parts that are ACID and parts that are BASE. The cognitive load is overwhelming.

**Complexity Explosion**

```python
# Every operation now has caveats
def get_user_profile(user_id):
    # Strongly consistent read from primary
    account = account_db.read_consistent(user_id)

    # Eventually consistent read from replica
    preferences = prefs_db.read_eventual(user_id)

    # Might be stale from cache
    avatar = cdn.get_cached(user_id)

    # Three different consistency models in one function!
    return merge_profile(account, preferences, avatar)
```

**Operational Burden**

The operations team struggles with:

```
Monitoring:
- Replication lag (how far behind are replicas?)
- Conflict rate (how often do conflicts occur?)
- Convergence time (how long until consistency?)

Debugging:
- "Is this a bug or eventual consistency?"
- "Which replica did the user read from?"
- "When did this value propagate to which nodes?"

Incidents:
- Partial failures (some data consistent, some not)
- Split-brain scenarios (network partition)
- Conflict resolution bugs
```

**Mental Model Confusion**

Engineers struggle to reason about correctness:

```
Engineer 1: "If I write then read, do I see my write?"
Engineer 2: "Depends if you hit the same replica"

Engineer 1: "If two users write simultaneously, what happens?"
Engineer 2: "They both succeed, then conflict resolves based on..."

Engineer 1: "How do I test this?"
Engineer 2: "Good question..."
```

**Team Frustration**

```
"This is way more complex than ACID"
"We spend more time debugging consistency issues than building features"
"Our customers are confused about the behavior"
"I'm not sure we made the right choice"
```

The team questions whether the benefits are worth the costs.

### Stage 5: Acceptance

**"Right tool for the job"**

After pain and learning, the team reaches maturity. They understand when to use ACID, when to use BASE, and how to combine them effectively.

**Clear Boundaries**

The team has clear guidelines:

```
Use ACID when:
- Correctness is critical (money, inventory)
- Uniqueness required (usernames, emails)
- Within a bounded context
- Scale is manageable

Use BASE when:
- Availability is critical
- Scale is massive
- Staleness is acceptable
- Conflicts are rare or resolvable
```

**Proper Abstractions**

Build abstractions that hide complexity:

```python
class EventuallyConsistentCache:
    """Cache that handles staleness gracefully"""

    def get(self, key, max_staleness=None):
        value, timestamp = self._read(key)
        if max_staleness and (now() - timestamp) > max_staleness:
            # Too stale, read from source
            value = self._read_source(key)
            self._write(key, value)
        return value

class ConsistentRegion:
    """Strongly consistent operations within a region"""

    def transaction(self):
        # Provides ACID within single region
        return self.db.transaction()

class CrossRegionSync:
    """Eventual consistency across regions"""

    def replicate_async(self, data):
        # Asynchronously replicate, handle conflicts
        self._queue_for_replication(data)
```

**Team Expertise**

The team understands distributed systems:

- CAP theorem implications
- Consistency models (linearizability, causal, eventual)
- Conflict resolution strategies
- Failure modes and recovery

**Operational Maturity**

Operations have the tools and processes:

```
Monitoring:
- Dashboards for replication lag
- Alerts for anomalies
- Automatic remediation for common issues

Debugging:
- Distributed tracing
- Version tracking
- Replay capabilities

Incident Response:
- Runbooks for consistency issues
- Tools for manual intervention
- Post-mortem processes
```

The team has reached a sustainable equilibrium.

## ACID + BASE: The Hybrid Reality

Modern systems don't choose between ACID and BASE—they use both. The key is knowing where to draw the boundaries.

### Transactional Boundaries

Use ACID within natural boundaries and BASE across them.

**ACID Within Bounds**

Identify bounded contexts where ACID makes sense:

```python
# Order Service - ACID within an order
class Order:
    def checkout(self, cart, payment_info):
        with transaction():  # ACID transaction
            # All these must succeed or fail together
            order = self.create_order(cart)
            self.reserve_inventory(cart.items)
            self.charge_payment(payment_info)
            self.create_shipment(order)
            commit()
```

Within a single order, atomicity is critical. Either the entire checkout succeeds or it fails.

**BASE Across Bounds**

Between bounded contexts, use eventual consistency:

```python
# Cross-service interaction - BASE
def checkout(user_id, cart, payment_info):
    # Create order (ACID within order service)
    order = order_service.create_order(cart)

    # Notify other services (eventual consistency)
    event_bus.publish(OrderCreated(order.id))

    # These happen asynchronously, eventually
    # - Inventory service deducts stock
    # - Shipping service creates shipment
    # - Email service sends confirmation
    # - Analytics service records sale
```

**Saga Patterns**

For distributed transactions, use sagas with compensation:

```python
class CheckoutSaga:
    """Multi-step process with compensation"""

    def execute(self, user_id, cart, payment):
        try:
            # Step 1: Reserve inventory
            reservation = inventory_service.reserve(cart.items)

            # Step 2: Charge payment
            charge = payment_service.charge(payment)

            # Step 3: Create order
            order = order_service.create(user_id, cart, charge)

            return order

        except InventoryError:
            # Nothing to compensate
            raise

        except PaymentError:
            # Compensate: Release inventory
            inventory_service.release(reservation)
            raise

        except OrderError:
            # Compensate: Refund payment and release inventory
            payment_service.refund(charge)
            inventory_service.release(reservation)
            raise
```

Each step can succeed or fail independently, with compensation logic to undo previous steps.

**Compensation Logic**

Business operations that can be undone:

```python
# Forward operations
def reserve_inventory(items): ...
def charge_payment(amount): ...
def create_shipment(order): ...

# Compensation operations
def release_inventory(reservation): ...
def refund_payment(charge): ...
def cancel_shipment(shipment): ...

# Saga executes forward operations
# On failure, executes compensation operations in reverse order
```

### Consistency Zones

Structure your system in concentric circles of consistency:

**Strong Consistency Core**

Critical data that must be consistent:

```
Core (ACID):
└─ User accounts
└─ Authentication tokens
└─ Permissions
└─ Financial transactions
└─ Unique identifiers
```

This data lives in traditional ACID databases with strong consistency guarantees.

**Eventually Consistent Edge**

Less critical data that can tolerate staleness:

```
Edge (BASE):
├─ User profiles (display names, avatars)
├─ Social graphs (followers, friends)
├─ Content feeds
├─ Search indexes
├─ Recommendations
└─ Analytics
```

This data uses eventually consistent stores for scale and availability.

**Read Replicas**

Separate read and write paths:

```python
class UserService:
    def update_email(self, user_id, new_email):
        # Write to primary (ACID)
        self.primary_db.update(user_id, email=new_email)
        # Asynchronously replicates to replicas

    def get_profile(self, user_id):
        # Read from replica (eventual consistency)
        # Might be slightly stale, but fast and scalable
        return self.replica_db.get(user_id)

    def get_email_for_auth(self, user_id):
        # Critical operation, read from primary
        return self.primary_db.get(user_id).email
```

**Cache Layers**

Accept staleness for performance:

```python
class ProductCatalog:
    def get_product(self, product_id):
        # Try cache first (fastest, might be stale)
        cached = self.cache.get(product_id)
        if cached and not self._too_stale(cached):
            return cached

        # Fall back to replica (eventual consistency)
        product = self.replica_db.get(product_id)
        self.cache.set(product_id, product, ttl=300)
        return product

    def update_product(self, product_id, changes):
        # Write to primary (ACID)
        self.primary_db.update(product_id, changes)

        # Invalidate cache (eventual consistency)
        self.cache.delete(product_id)
```

### Business Logic Adaptation

The biggest change is in how you write business logic:

**ACID Approach**

```python
# Traditional ACID approach
def transfer_money(from_account, to_account, amount):
    with transaction():
        # Read balances
        from_balance = accounts.read(from_account).balance
        to_balance = accounts.read(to_account).balance

        # Validate
        if from_balance < amount:
            raise InsufficientFunds()

        # Update both
        accounts.update(from_account, balance=from_balance - amount)
        accounts.update(to_account, balance=to_balance + amount)

        # Commit atomically
        commit()
```

Simple, straightforward, but doesn't scale across distributed systems.

**BASE Approach**

```python
# BASE approach with eventual consistency
def transfer_money(from_account, to_account, amount):
    # Create transfer record (intent)
    transfer = Transfer(
        id=generate_id(),
        from_account=from_account,
        to_account=to_account,
        amount=amount,
        status='pending',
        created_at=now()
    )
    transfer_db.create(transfer)

    # Debit source (eventually consistent)
    eventually(debit_account, from_account, amount, transfer.id)

    # Credit destination (eventually consistent)
    eventually(credit_account, to_account, amount, transfer.id)

    # Monitor and handle failures
    eventually(monitor_transfer, transfer.id)

    return transfer

def debit_account(account_id, amount, transfer_id):
    """Idempotent operation"""
    account = accounts.read(account_id)

    # Check if already processed
    if transfer_id in account.processed_transfers:
        return  # Idempotent

    # Debit account
    account.balance -= amount
    account.processed_transfers.add(transfer_id)
    accounts.write(account_id, account)

    # Update transfer status
    transfers.update(transfer_id, debited=True)

def credit_account(account_id, amount, transfer_id):
    """Idempotent operation"""
    account = accounts.read(account_id)

    # Check if already processed
    if transfer_id in account.processed_transfers:
        return  # Idempotent

    # Credit account
    account.balance += amount
    account.processed_transfers.add(transfer_id)
    accounts.write(account_id, account)

    # Update transfer status
    transfers.update(transfer_id, credited=True)

def monitor_transfer(transfer_id):
    """Check if transfer completed, compensate if needed"""
    transfer = transfers.read(transfer_id)

    if transfer.debited and transfer.credited:
        # Success!
        transfers.update(transfer_id, status='completed')
    elif transfer.age > timeout:
        # Timed out, compensate
        if transfer.debited:
            # Refund the debit
            credit_account(transfer.from_account, transfer.amount,
                         f"refund-{transfer_id}")
        transfers.update(transfer_id, status='failed')
```

More complex, but scales across distributed systems. Key principles:

1. **Idempotency**: Operations can be retried safely
2. **Observability**: Transfer status tracked explicitly
3. **Compensation**: Failures handled with business logic
4. **Eventual**: Operations complete eventually, not immediately

## Real-World Transitions

Let's look at how major companies made this transition.

### Amazon: From Oracle to Dynamo

Amazon's journey from Oracle to Dynamo is one of the most influential BASE transitions.

#### The Problem

Early Amazon ran on Oracle databases:

```
Year 2000:
- All data in Oracle
- Vertical scaling
- Regular downtime for maintenance
- Scaling limits approaching
```

As Amazon grew, problems emerged:

**Oracle Couldn't Scale**

```
Black Friday 2004:
- Traffic spike 10x normal
- Database overwhelmed
- Site slow/unavailable
- Lost sales
- Angry customers
```

No amount of hardware could handle the spikes.

**Cost Prohibitive**

```
Oracle licensing:
- Per-core licensing
- Expensive support contracts
- Consulting fees
- Hardware requirements

Annual cost: $50M+ and growing
```

**Availability Issues**

```
Planned downtime:
- Schema changes: 4 hours
- Upgrades: 8 hours
- Backups: performance impact

Unplanned downtime:
- Hardware failures
- Software bugs
- Human errors

Total downtime: ~99.9% availability (43 minutes/month)
Target: 99.99% (4 minutes/month)
```

**Geographic Distribution**

```
All data in US datacenter:
- US customers: 50ms latency
- European customers: 150ms latency
- Asian customers: 300ms latency

Need: local latency everywhere
```

#### The Solution

Amazon built Dynamo, a key-value store designed for BASE:

**Dynamo for Cart**

Shopping cart was the first use case:

```python
# Shopping cart requirements
class ShoppingCart:
    # Doesn't need strong consistency
    # - Multiple adds can be merged
    # - Stale cart is OK
    # - Deletion can be eventual

    # Needs high availability
    # - Always writable (even during failures)
    # - Fast reads (customer experience)
    # - Never lose items
```

**Eventually Consistent**

Dynamo provides eventual consistency:

```
User adds item from laptop:
- Write goes to nearest Dynamo node
- Asynchronously replicates to other nodes
- User immediately sees item in cart

User opens phone 1 second later:
- Might not see new item yet (replication lag)
- Sees it a few seconds later (eventual consistency)
```

**Always Writable**

Key design principle: never refuse a write:

```
Normal operation:
- Write to 3 replicas
- Acknowledge after 2 succeed
- 3rd catches up eventually

During network partition:
- Some replicas unreachable
- Write to available replicas
- Use hinted handoff for unreachable ones
- Reconcile later
```

This means the cart is always writable, even during partial failures.

**Business Logic Adaptation**

Amazon adapted their business logic:

```python
# Conflict resolution: union of carts
def merge_carts(cart1, cart2):
    """If two versions exist, merge them"""
    merged = Cart()

    # Union of items
    for item in cart1.items + cart2.items:
        merged.add_item(item)

    # If item added from multiple devices, keep higher quantity
    # Better to show more items than lose items
    return merged
```

The business rule: when in doubt, show more items. Better to let the customer remove items than to lose items they added.

#### Lessons Learned

**Eventual Consistency Works for Carts**

```
Analysis after 1 year:
- 99.9% of cart reads see all items immediately
- 0.1% see slightly stale cart
- Stale carts converge within seconds
- Customer complaints about cart: decreased
- Customer satisfaction: increased
```

**Customers Tolerate Inconsistency**

Customers didn't notice or care about eventual consistency:

```
User survey:
Q: "Did you notice your cart sometimes missing items temporarily?"
A: 95% said "no"

Q: "Would you prefer a slower cart that's always consistent?"
A: 80% said "no, keep it fast"
```

**Availability > Consistency for Shopping**

```
Holiday season results:
- Zero cart downtime
- 100% of adds succeeded
- Site remained fast under load
- No lost sales due to cart issues

Business impact:
- Revenue increased
- Customer satisfaction increased
- Operational costs decreased
```

**Cost Savings Massive**

```
Before Dynamo (Oracle):
- $50M/year license and hardware
- Regular downtime
- Scaling limitations

After Dynamo:
- $5M/year commodity hardware
- No downtime
- Scales infinitely

Savings: $45M/year
```

Amazon's success with Dynamo influenced the entire industry. The Dynamo paper spawned Cassandra, Riak, and countless other eventually consistent systems.

### eBay: From Oracle to Custom

eBay's transition was more gradual, focusing on vertical partitioning and functional segmentation.

#### The Journey

**Vertical Partitioning**

Split the monolithic database:

```
Before (single Oracle DB):
┌─────────────────────┐
│ Everything:         │
│ - Users             │
│ - Items             │
│ - Bids              │
│ - Search            │
│ - Messages          │
│ - Feedback          │
└─────────────────────┘

After (partitioned):
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Users DB │ │ Items DB │ │ Bids DB  │
└──────────┘ └──────────┘ └──────────┘
┌──────────┐ ┌──────────┐ ┌──────────┐
│Search DB │ │Msg DB    │ │ Fback DB │
└──────────┘ └──────────┘ └──────────┘
```

Each partition can scale independently.

**Functional Segmentation**

Group related data:

```
User Service:
- User accounts (ACID)
- Authentication (ACID)
- Profile (eventual)

Listing Service:
- Item details (eventual)
- Images (eventual)
- Search index (eventual)

Bidding Service:
- Active bids (ACID)
- Bid history (eventual)
```

**Custom Caching**

Heavy caching layer:

```python
class ItemCache:
    def get_item(self, item_id):
        # Try L1 cache (local process)
        item = self.l1_cache.get(item_id)
        if item:
            return item

        # Try L2 cache (shared memcached)
        item = self.l2_cache.get(item_id)
        if item:
            self.l1_cache.set(item_id, item)
            return item

        # Fall back to database
        item = self.db.get(item_id)
        self.l1_cache.set(item_id, item)
        self.l2_cache.set(item_id, item)
        return item
```

**BASE Adoption**

Gradually weakened consistency:

```
Phase 1: Read replicas (lag acceptable)
Phase 2: Cache with staleness (seconds old OK)
Phase 3: Eventual consistency (minutes old OK for some data)
```

#### The Results

**100x Scale Increase**

```
Year 2000:
- 10M users
- 1M listings
- 10K concurrent users

Year 2010:
- 1B users (100x)
- 100M listings (100x)
- 1M concurrent users (100x)
```

**10x Cost Reduction**

```
Cost per transaction:
Year 2000: $0.50 (Oracle + expensive hardware)
Year 2010: $0.05 (commodity hardware + custom software)

Total savings: $100M+/year
```

**Better Availability**

```
Availability:
Year 2000: 99.5% (43 hours downtime/year)
Year 2010: 99.95% (4.3 hours downtime/year)

Revenue impact:
Each 9 of availability = $100M additional revenue
```

**Faster Development**

```
Time to deploy changes:
Year 2000: Weeks (schema changes risky)
Year 2010: Days (loosely coupled services)

Features per year:
Year 2000: 50
Year 2010: 500 (10x increase)
```

### Twitter: From MySQL to Mixed

Twitter's evolution shows a hybrid approach.

#### The Evolution

**MySQL for Users**

User data remained in MySQL with strong consistency:

```sql
-- User accounts need ACID
CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(15) UNIQUE,  -- Must be unique
    email VARCHAR(255) UNIQUE,     -- Must be unique
    password_hash VARCHAR(128),    -- Security critical
    created_at TIMESTAMP
);

-- Strong consistency required because:
-- - Usernames must be unique
-- - Authentication must be secure
-- - Profile updates must be immediate
```

**Cassandra for Tweets**

Tweets moved to Cassandra for scale:

```python
# Tweet requirements
class Tweet:
    # Eventual consistency OK
    # - Retweets can be slightly delayed
    # - Like counts can be approximate
    # - Old tweets rarely change

    # Needs massive scale
    # - 500M tweets/day
    # - Must be always available
    # - Global distribution
```

**Redis for Timeline**

Timeline generation used Redis:

```python
class Timeline:
    def get_home_timeline(self, user_id):
        # Redis stores pre-computed timelines
        # - Updated in near real-time
        # - Some lag acceptable
        # - Scales to millions of reads/second

        timeline_key = f"timeline:{user_id}"
        tweet_ids = redis.lrange(timeline_key, 0, 100)

        # Fetch full tweets (might be slightly stale)
        tweets = cassandra.get_tweets(tweet_ids)
        return tweets
```

**Mixed Consistency**

Different data, different consistency:

```
Strong consistency (MySQL):
- User accounts
- Direct messages
- Account settings

Eventual consistency (Cassandra):
- Tweets
- Retweets
- Likes
- Follower counts

Cache (Redis):
- Timelines
- Trending topics
- Rate limits
```

#### The Trade-offs

**Timeline Eventual**

```
User A tweets:
Time 0: Tweet posted
Time 1: Appears in User A's timeline
Time 2: Appears in some followers' timelines
Time 3: Appears in more followers' timelines
Time 5: Appears in all followers' timelines

Eventual consistency acceptable because:
- Users understand tweets aren't instant everywhere
- 5-second delay is acceptable
- Alternative (ACID) would make tweeting slow
```

**Users Consistent**

```
User changes username:
- Must update immediately (ACID transaction)
- All future requests see new username
- No eventual consistency acceptable

Why:
- Username is identity
- Inconsistency would be confusing
- Uniqueness constraint must be enforced
```

**Tweets Available**

```
Network partition between datacenters:
- Tweets remain writable (always available)
- Different users might see different recent tweets
- Eventually converges when partition heals

Alternative (ACID):
- Tweets would be unavailable during partition
- Users couldn't tweet
- Unacceptable for social media
```

**Hybrid Success**

```
Results:
- 500M tweets/day (massive scale)
- 99.9% availability (reliable)
- Sub-second latency (fast)
- $0.001 per tweet (economical)

With pure ACID:
- 1M tweets/day maximum (didn't scale)
- 95% availability (failed during load)
- Multi-second latency (slow)
- $1 per tweet (too expensive)
```

## Patterns for ACID to BASE

Several design patterns help manage the transition:

### Event Sourcing

Store events, not state. Rebuild state from events.

**Concept**

Instead of storing current state:

```sql
-- Traditional approach: store current state
CREATE TABLE accounts (
    id INT PRIMARY KEY,
    balance DECIMAL
);

UPDATE accounts SET balance = 100 WHERE id = 1;
-- Balance is now 100, but we don't know why or how
```

Store sequence of events:

```sql
-- Event sourcing: store events
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    aggregate_id INT,
    event_type VARCHAR(50),
    event_data JSON,
    timestamp TIMESTAMP
);

INSERT INTO events (aggregate_id, event_type, event_data)
VALUES (1, 'AccountCreated', '{"initial_balance": 0}');

INSERT INTO events (aggregate_id, event_type, event_data)
VALUES (1, 'MoneyDeposited', '{"amount": 100}');

-- Rebuild state by replaying events:
-- AccountCreated: balance = 0
-- MoneyDeposited: balance = 0 + 100 = 100
```

**Natural Audit Log**

All changes are recorded:

```python
# Query event history
def get_account_history(account_id):
    events = db.query(
        "SELECT * FROM events WHERE aggregate_id = ? ORDER BY timestamp",
        account_id
    )

    for event in events:
        print(f"{event.timestamp}: {event.event_type} {event.event_data}")

# Output:
# 2024-01-01 10:00:00: AccountCreated {"initial_balance": 0}
# 2024-01-01 10:05:00: MoneyDeposited {"amount": 100}
# 2024-01-01 10:10:00: MoneyWithdrawn {"amount": 20}
# 2024-01-01 10:15:00: MoneyDeposited {"amount": 50}
```

**Time Travel Capability**

Reconstruct state at any point in time:

```python
def get_balance_at_time(account_id, timestamp):
    events = db.query(
        "SELECT * FROM events WHERE aggregate_id = ? AND timestamp <= ? ORDER BY timestamp",
        account_id, timestamp
    )

    balance = 0
    for event in events:
        if event.event_type == 'MoneyDeposited':
            balance += event.event_data['amount']
        elif event.event_type == 'MoneyWithdrawn':
            balance -= event.event_data['amount']

    return balance

# What was the balance on January 1st?
balance = get_balance_at_time(account_id, '2024-01-01')
```

**Eventual Consistency Friendly**

Events can be replayed to different datastores:

```python
# Event handler
def on_money_deposited(event):
    # Update multiple stores eventually

    # Update transactional store (ACID)
    transactional_db.update_balance(event.account_id, event.amount)

    # Update analytics store (eventual)
    analytics_db.record_deposit(event.account_id, event.amount)

    # Update search index (eventual)
    search.index_transaction(event)

    # Send notification (eventual)
    notification_service.send(event.account_id, "Deposit received")
```

### CQRS

Command Query Responsibility Segregation: separate read and write models.

**Concept**

Traditional approach: same model for reads and writes:

```python
class Account:
    def deposit(self, amount):
        # Write operation
        self.balance += amount
        db.save(self)

    def get_balance(self):
        # Read operation
        return self.balance

    def get_transaction_history(self):
        # Read operation
        return self.transactions
```

CQRS approach: different models:

```python
# Write model (commands)
class AccountCommands:
    def deposit(self, account_id, amount):
        # Optimized for writes
        # Strong consistency
        # Normalized data
        event = DepositEvent(account_id, amount)
        event_store.append(event)
        event_bus.publish(event)

# Read model (queries)
class AccountQueries:
    def get_balance(self, account_id):
        # Optimized for reads
        # Eventual consistency OK
        # Denormalized data
        # Cached/indexed
        return balance_cache.get(account_id)

    def get_transaction_history(self, account_id):
        # Optimized specifically for this query
        # Pre-joined, pre-sorted
        return history_view.get(account_id)
```

**Optimize Independently**

Write model optimized for correctness:

```python
# Write model uses normalized tables
class WriteModel:
    accounts_table = """
        CREATE TABLE accounts (
            id INT PRIMARY KEY,
            user_id INT REFERENCES users(id),
            account_type VARCHAR(20)
        )
    """

    transactions_table = """
        CREATE TABLE transactions (
            id BIGINT PRIMARY KEY,
            account_id INT REFERENCES accounts(id),
            amount DECIMAL,
            type VARCHAR(20),
            timestamp TIMESTAMP
        )
    """
```

Read model optimized for performance:

```python
# Read model uses denormalized views
class ReadModel:
    account_summary_view = """
        CREATE MATERIALIZED VIEW account_summary AS
        SELECT
            a.id,
            a.user_id,
            u.username,
            a.account_type,
            SUM(t.amount) as balance,
            COUNT(t.id) as transaction_count,
            MAX(t.timestamp) as last_transaction
        FROM accounts a
        JOIN users u ON a.user_id = u.id
        LEFT JOIN transactions t ON a.id = t.account_id
        GROUP BY a.id, a.user_id, u.username, a.account_type
    """
```

**Different Consistency**

Writes use strong consistency:

```python
def deposit(account_id, amount):
    with transaction():  # ACID
        account = accounts.get(account_id)
        if account.is_frozen:
            raise AccountFrozenError()

        transactions.insert({
            'account_id': account_id,
            'amount': amount,
            'type': 'deposit',
            'timestamp': now()
        })

        commit()
```

Reads accept eventual consistency:

```python
def get_balance(account_id):
    # Read from eventually consistent view
    # Might be slightly stale
    # But much faster
    summary = account_summary_view.get(account_id)
    return summary.balance
```

**Scale Separately**

```
Write side:
- 3 database nodes
- Strong consistency
- Lower throughput
- 10,000 writes/second

Read side:
- 20 read replicas
- Eventual consistency
- Higher throughput
- 1,000,000 reads/second
```

### Saga Pattern

Distributed transactions using compensation logic.

**Concept**

Traditional distributed transaction (doesn't scale):

```python
def book_trip(user_id, flight, hotel):
    with distributed_transaction():  # Expensive!
        flight_service.book(user_id, flight)
        hotel_service.book(user_id, hotel)
        payment_service.charge(user_id, total)
        commit_all()
```

Saga pattern (scalable):

```python
class BookTripSaga:
    def execute(self, user_id, flight, hotel):
        try:
            # Step 1
            flight_booking = flight_service.book(user_id, flight)

            # Step 2
            hotel_booking = hotel_service.book(user_id, hotel)

            # Step 3
            payment = payment_service.charge(user_id, total)

            return TripBooking(flight_booking, hotel_booking, payment)

        except FlightError as e:
            # Nothing to compensate
            raise

        except HotelError as e:
            # Compensate: Cancel flight
            flight_service.cancel(flight_booking)
            raise

        except PaymentError as e:
            # Compensate: Cancel flight and hotel
            flight_service.cancel(flight_booking)
            hotel_service.cancel(hotel_booking)
            raise
```

**Eventually Consistent**

Each step can complete independently:

```
Time 0: Start saga
Time 1: Flight booked (committed)
Time 2: Hotel booked (committed)
Time 3: Payment charged (committed)
Time 4: Saga complete (eventually)

If step fails:
Time 2: Hotel booking fails
Time 3: Cancel flight (compensate)
Time 4: Saga failed (eventually consistent)
```

**Business Process**

Saga captures business process:

```python
class OrderFulfillmentSaga:
    def execute(self, order):
        # Business process with compensation

        try:
            # Reserve inventory
            reservation = inventory.reserve(order.items)

            # Charge payment
            payment = billing.charge(order.customer, order.total)

            # Create shipment
            shipment = shipping.create(order, reservation)

            # Send confirmation
            notification.send(order.customer, "Order confirmed")

            return FulfilledOrder(order, reservation, payment, shipment)

        except InventoryError:
            # No compensation needed
            raise OrderFailed("Out of stock")

        except BillingError:
            # Compensate: Release inventory
            inventory.release(reservation)
            raise OrderFailed("Payment failed")

        except ShippingError:
            # Compensate: Refund payment and release inventory
            billing.refund(payment)
            inventory.release(reservation)
            raise OrderFailed("Shipping unavailable")
```

### Outbox Pattern

Guarantee message delivery with transactional outbox.

**Problem**

Naive approach has atomicity issues:

```python
def create_order(order):
    # Write to database
    db.insert_order(order)

    # Send event (might fail!)
    event_bus.publish(OrderCreated(order.id))

    # Problem: If publish fails, event is lost
    # Database has order, but other services don't know
```

**Solution**

Use transactional outbox:

```python
def create_order(order):
    with transaction():
        # Write order
        db.insert_order(order)

        # Write event to outbox (same transaction!)
        db.insert_outbox({
            'event_type': 'OrderCreated',
            'event_data': order.to_json(),
            'status': 'pending'
        })

        commit()

# Separate process publishes from outbox
def outbox_publisher():
    while True:
        # Find pending events
        events = db.query("SELECT * FROM outbox WHERE status = 'pending'")

        for event in events:
            try:
                # Publish event
                event_bus.publish(event)

                # Mark as published
                db.update_outbox(event.id, status='published')
            except Exception:
                # Will retry later
                pass

        sleep(1)
```

**Guaranteed Delivery**

Events are never lost:

```
Scenario 1: Database write succeeds, event_bus succeeds
- Order created ✓
- Event in outbox ✓
- Event published ✓
- Everything consistent ✓

Scenario 2: Database write succeeds, event_bus fails
- Order created ✓
- Event in outbox ✓
- Event not published yet ✗
- Outbox publisher retries
- Event eventually published ✓

Scenario 3: Database write fails
- Order not created ✗
- Event not in outbox ✗
- Nothing published ✗
- Everything consistent ✓
```

**At-Least-Once Semantics**

Events might be published multiple times:

```python
# Event might be published twice if:
# 1. Publisher publishes event
# 2. Publisher crashes before marking as published
# 3. Publisher restarts and publishes again

# Solution: Idempotent processing
def handle_order_created(event):
    # Check if already processed
    if db.exists_order(event.order_id):
        return  # Already processed, ignore

    # Process event
    process_order(event)
```

**Idempotent Processing**

Event handlers must be idempotent:

```python
class OrderEventHandler:
    def handle_order_created(self, event):
        # Idempotent: safe to call multiple times

        # Check if already processed
        if self.already_processed(event.id):
            return

        # Process event
        self.create_shipment(event.order_id)

        # Mark as processed
        self.mark_processed(event.id)

    def already_processed(self, event_id):
        return db.exists("processed_events", event_id)

    def mark_processed(self, event_id):
        db.insert("processed_events", event_id)
```

## Monitoring the Transition

You can't manage what you don't measure. Moving to BASE requires new metrics.

### Consistency Metrics

**Convergence Time**

How long until replicas agree:

```python
def measure_convergence_time():
    # Write value with timestamp
    timestamp = now()
    value = {"data": "test", "timestamp": timestamp}
    primary.write("key", value)

    # Poll replicas until they all see the value
    start = now()
    while True:
        replica_values = [r.read("key") for r in replicas]

        if all(v.timestamp == timestamp for v in replica_values):
            convergence_time = now() - start
            metrics.record("convergence_time", convergence_time)
            break

        sleep(0.01)

# Typical results:
# p50: 10ms
# p95: 50ms
# p99: 200ms
# p99.9: 1000ms (during failures)
```

**Conflict Rate**

How often do conflicts occur:

```python
def measure_conflict_rate():
    total_writes = metrics.get("total_writes")
    conflicts = metrics.get("conflicts_detected")
    conflict_rate = conflicts / total_writes

    metrics.record("conflict_rate", conflict_rate)

# Typical results:
# Normal operation: 0.01% (1 in 10,000)
# High contention: 1% (1 in 100)
# During partition: 10% (1 in 10)
```

**Divergence Detection**

Detect when replicas disagree:

```python
def check_divergence():
    # Sample random keys
    sample_keys = random.sample(all_keys, 1000)

    divergent = 0
    for key in sample_keys:
        values = [r.read(key) for r in replicas]
        if not all_equal(values):
            divergent += 1
            log.warning(f"Divergence detected for {key}: {values}")

    divergence_rate = divergent / len(sample_keys)
    metrics.record("divergence_rate", divergence_rate)

    if divergence_rate > 0.01:  # 1%
        alert("High divergence rate!")

# Typical results:
# Normal: 0.001% (1 in 100,000)
# Degraded: 0.1% (1 in 1,000)
# Critical: 1% (1 in 100)
```

**Resolution Success**

How often conflict resolution works:

```python
def track_conflict_resolution():
    # When conflict detected
    def on_conflict(key, versions):
        try:
            resolved = resolve_conflict(versions)
            metrics.increment("conflicts_resolved_success")
            return resolved
        except Exception as e:
            metrics.increment("conflicts_resolved_failure")
            alert(f"Conflict resolution failed for {key}: {e}")
            raise

# Typical results:
# Resolution success: 99.9%
# Resolution failure: 0.1% (requires manual intervention)
```

### Availability Metrics

**Request Success Rate**

Percentage of requests that succeed:

```python
def track_requests():
    @app.route("/api/data")
    def get_data():
        start = time.time()
        try:
            data = service.get_data()
            metrics.increment("requests_success")
            metrics.record("request_latency", time.time() - start)
            return data
        except Exception as e:
            metrics.increment("requests_failure")
            metrics.record("request_latency", time.time() - start)
            raise

# Monitor:
success_rate = metrics.get("requests_success") / (
    metrics.get("requests_success") + metrics.get("requests_failure")
)

# Typical targets:
# Normal: 99.99% (1 failure in 10,000)
# Degraded: 99.9% (1 failure in 1,000)
# Critical: < 99% (alert!)
```

**Partial Failure Rate**

How often system operates in degraded mode:

```python
def check_service_health():
    services = ["database", "cache", "search", "recommendation"]

    healthy = []
    unhealthy = []

    for service in services:
        if health_check(service):
            healthy.append(service)
        else:
            unhealthy.append(service)

    if unhealthy:
        mode = "degraded"
        metrics.increment("partial_failure")
        log.warning(f"Degraded mode: {unhealthy} unhealthy")
    else:
        mode = "normal"

    metrics.record("service_mode", mode)

# Typical results:
# Full availability: 99% of time
# Partial degradation: 0.9% of time
# Complete outage: 0.1% of time
```

**Degraded Mode Time**

How long system operates degraded:

```python
def track_degraded_mode():
    global degraded_mode_start

    if is_degraded() and not degraded_mode_start:
        # Entering degraded mode
        degraded_mode_start = time.time()
        log.warning("Entering degraded mode")

    elif not is_degraded() and degraded_mode_start:
        # Exiting degraded mode
        duration = time.time() - degraded_mode_start
        metrics.record("degraded_mode_duration", duration)
        log.info(f"Exited degraded mode after {duration}s")
        degraded_mode_start = None

# Typical results:
# Mean duration: 30 seconds
# p95: 5 minutes
# p99: 30 minutes
```

**Recovery Time**

How quickly system recovers from failures:

```python
def track_recovery():
    global failure_start

    if service_failed() and not failure_start:
        failure_start = time.time()
        log.error("Service failure detected")

    elif service_healthy() and failure_start:
        recovery_time = time.time() - failure_start
        metrics.record("recovery_time", recovery_time)
        log.info(f"Service recovered in {recovery_time}s")
        failure_start = None

# Typical targets:
# Node failure: < 10 seconds
# Datacenter failure: < 60 seconds
# Network partition: < 300 seconds
```

### Business Metrics

Technical metrics aren't enough—measure business impact.

**User Experience Impact**

How do technical issues affect users:

```python
def measure_user_impact():
    # Correlate technical and user metrics

    # Technical metric
    divergence_rate = metrics.get("divergence_rate")

    # User metric
    user_complaints = metrics.get("support_tickets")

    # Correlation
    if divergence_rate > 0.01 and user_complaints > threshold:
        alert("High divergence causing user complaints")

# Track:
# - Support tickets mentioning data inconsistency
# - User-reported bugs related to stale data
# - Customer churn correlated with outages
```

**Revenue Impact**

How do technical issues affect revenue:

```python
def measure_revenue_impact():
    # Revenue during normal operation
    normal_revenue_per_hour = metrics.get("revenue_per_hour_baseline")

    # Revenue during current hour
    current_revenue = metrics.get("revenue_current_hour")

    # Impact
    if is_degraded():
        revenue_loss = normal_revenue_per_hour - current_revenue
        metrics.record("revenue_loss_degraded", revenue_loss)

        if revenue_loss > threshold:
            alert(f"Degraded mode costing ${revenue_loss}/hour")

# Typical findings:
# 100ms latency increase -> 1% revenue drop
# 99.9% -> 99% availability -> 5% revenue drop
# Stale recommendations -> 2% revenue drop
```

**Support Tickets**

User-reported issues:

```python
def analyze_support_tickets():
    tickets = support_system.get_tickets(last_24_hours)

    # Categorize
    consistency_issues = [
        t for t in tickets
        if "wrong data" in t.description or "disappeared" in t.description
    ]

    availability_issues = [
        t for t in tickets
        if "error" in t.description or "timeout" in t.description
    ]

    # Alert if spike
    if len(consistency_issues) > baseline * 2:
        alert("Spike in consistency-related support tickets")

# Track over time:
# Before BASE: 10 tickets/day about data issues
# After BASE (poor): 100 tickets/day about data issues
# After BASE (good): 5 tickets/day about data issues
```

**Customer Satisfaction**

Overall happiness:

```python
def measure_satisfaction():
    # NPS score
    nps = survey_system.get_nps()

    # Correlate with technical metrics
    if nps < threshold and metrics.get("divergence_rate") > 0.01:
        investigate("Low NPS may be due to data consistency")

# Track:
# - Net Promoter Score (NPS)
# - Customer Satisfaction (CSAT)
# - App store ratings
# - Social media sentiment
```

## Common Pitfalls

### Over-BASEification

Making everything eventually consistent is as bad as making everything ACID.

**Making Everything Eventual**

```python
# Bad: Even critical data is eventually consistent
class UserAuth:
    def login(self, username, password):
        # Reading from eventually consistent replica
        user = eventual_db.get_user(username)  # Might be stale!

        if user and check_password(password, user.password_hash):
            return create_session(user)
        return None

# Problem: User changes password
# Old replica still has old password
# Attacker can use old password!
```

**Losing Critical Invariants**

```python
# Bad: Allowing double-spending
class PaymentService:
    def charge(self, account_id, amount):
        # Eventually consistent balance check
        balance = eventual_db.get_balance(account_id)

        if balance >= amount:
            # Two concurrent charges might both see sufficient balance
            eventual_db.update_balance(account_id, balance - amount)
            return True
        return False

# Problem: Race condition allows spending more than balance
```

**Business Logic Complexity**

```python
# Bad: Too much conflict resolution logic
def merge_user_profiles(profile1, profile2):
    merged = Profile()

    # Complex merge logic for every field
    merged.name = most_recent(profile1.name, profile2.name)
    merged.email = least_likely_typo(profile1.email, profile2.email)
    merged.age = highest_value(profile1.age, profile2.age)
    merged.address = longest_address(profile1.address, profile2.address)
    # ... 50 more fields ...

    # This is maintainability nightmare!
    return merged
```

**Debugging Impossibility**

```
Support ticket: "User says their order disappeared"

Developer: "Let me check... I see 3 different versions of their order across replicas"
Developer: "One has item A, one has item B, one has both"
Developer: "They were written at almost the same time"
Developer: "Conflict resolution chose the version with just item A"
Developer: "So from user's perspective, item B disappeared"
Developer: "Is this a bug or working as designed? I honestly don't know"
```

### Under-BASEification

Keeping ACID where it's not needed prevents scaling.

**Keeping Unnecessary ACID**

```python
# Bad: Using ACID transaction for analytics
class AnalyticsService:
    def record_page_view(self, user_id, page):
        with transaction():  # Unnecessary!
            # Analytics don't need ACID
            # Approximate counts are fine
            # This creates contention
            db.execute("""
                UPDATE page_stats
                SET view_count = view_count + 1
                WHERE page = ?
            """, page)
            commit()
```

**Scaling Problems Persist**

```
Using ACID for data that could be eventually consistent:

Result:
- Database doesn't scale
- High latency
- Lock contention
- Expensive hardware still required
```

**Cost Remains High**

```
Keeping ACID where BASE would work:

Year 1: $500K database costs
Year 2: $1M database costs (oops, still scaling vertically)
Year 3: $2M database costs
Year 4: Hit scaling wall, forced migration anyway

Better: Migrate to BASE earlier
Year 1: $500K (same)
Year 2: $600K (gradual migration)
Year 3: $400K (BASE is cheaper)
Year 4: $300K (continues to scale)
```

**Availability Suffers**

```
ACID system during failure:
- Node fails
- All writes block (must maintain consistency)
- System unavailable

BASE system during failure:
- Node fails
- Writes continue to other nodes
- System remains available
```

### Poor Boundaries

**Wrong Transaction Boundaries**

```python
# Bad: Transaction too large (crosses service boundaries)
def process_order(order):
    with transaction():
        # Each of these is a different service!
        inventory.reserve(order.items)
        payment.charge(order.customer, order.total)
        shipping.create_shipment(order)
        email.send_confirmation(order.customer)
        analytics.record_sale(order)
        commit_all()  # This won't scale

# Better: Separate transactions with eventual consistency
def process_order(order):
    # ACID within order service
    with transaction():
        order_db.create_order(order)
        commit()

    # Eventually consistent across services
    event_bus.publish(OrderCreated(order))
    # Other services react to event asynchronously
```

**Inconsistent Models**

```python
# Bad: Same data, different consistency models
class User:
    # Email is strongly consistent
    def update_email(self, new_email):
        acid_db.update(self.id, email=new_email)

    # Email is also eventually consistent (inconsistent!)
    def get_email(self):
        return eventual_cache.get(f"email:{self.id}")

# Problem: Just updated email, but get_email returns old value
# Which consistency model applies?
```

**Leaky Abstractions**

```python
# Bad: Exposing consistency model to callers
class DataService:
    def get_data(self, key, consistency_level):
        # Caller must know about consistency!
        if consistency_level == "strong":
            return self.primary_db.get(key)
        elif consistency_level == "eventual":
            return self.replica_db.get(key)

# Better: Hide consistency model
class DataService:
    def get_critical_data(self, key):
        # Strong consistency (implementation detail)
        return self.primary_db.get(key)

    def get_display_data(self, key):
        # Eventual consistency (implementation detail)
        return self.replica_db.get(key)
```

**Mental Model Confusion**

```
Team member 1: "This data is eventually consistent, right?"
Team member 2: "No, it's ACID within the service"
Team member 1: "But it's replicated across regions?"
Team member 2: "Yes, eventual across regions, ACID within region"
Team member 1: "So... is it ACID or BASE?"
Team member 3: "Yes"
Team member 1: "I'm so confused"
```

## Best Practices

### Start Small

**One Use Case**

Don't migrate everything at once:

```
Phase 1 (Month 1-3):
- Migrate product catalog to BASE
- Low risk (read-mostly data)
- Learn lessons
- Build expertise

Phase 2 (Month 4-6):
- Migrate user profiles (non-critical fields)
- Medium risk (some writes)
- Apply lessons learned

Phase 3 (Month 7-12):
- Migrate shopping cart
- Higher risk (frequent writes)
- Team is now experienced
```

**Non-Critical Data**

Start with data where mistakes won't hurt:

```
Good first candidates:
✓ Product descriptions (stale OK)
✓ User avatars (stale OK)
✓ Analytics data (approximate OK)
✓ Cache data (stale by definition)

Bad first candidates:
✗ Payment processing (must be correct)
✗ User authentication (security critical)
✗ Inventory counts (can't oversell)
✗ Unique constraints (must be enforced)
```

**Learn and Iterate**

```
Iteration 1:
- Migrate read-only product catalog
- Learn: Replication lag is 50ms average
- Learn: Cache invalidation is tricky
- Improve: Add monitoring for lag

Iteration 2:
- Migrate user-generated content
- Learn: Conflicts happen 0.1% of the time
- Learn: Users notice stale data sometimes
- Improve: Add conflict resolution

Iteration 3:
- Migrate more critical data
- Apply lessons from previous iterations
- Faster, smoother migration
```

**Build Expertise**

```
Team skill progression:

Month 1:
- Understanding eventual consistency
- Reading about CAP theorem
- Experimenting with tools

Month 3:
- First production deployment
- Learning from incidents
- Developing intuition

Month 6:
- Confident with BASE
- Can design new systems
- Can debug issues

Month 12:
- Expert-level understanding
- Teaching others
- Contributing to patterns
```

### Measure Everything

**Before Metrics**

Establish baseline before migration:

```python
# Collect baseline metrics
baseline = {
    "p50_latency": measure_latency(p=50),
    "p99_latency": measure_latency(p=99),
    "availability": measure_availability(),
    "consistency": 1.0,  # ACID is 100% consistent
    "cost_per_request": measure_cost(),
    "requests_per_second": measure_throughput(),
    "support_tickets_per_day": count_tickets(),
    "customer_satisfaction": measure_nps(),
}

save_baseline(baseline)
```

**After Metrics**

Compare after migration:

```python
# Measure after migration
after = {
    "p50_latency": measure_latency(p=50),
    "p99_latency": measure_latency(p=99),
    "availability": measure_availability(),
    "consistency": measure_consistency(),  # < 1.0 (eventually consistent)
    "cost_per_request": measure_cost(),
    "requests_per_second": measure_throughput(),
    "support_tickets_per_day": count_tickets(),
    "customer_satisfaction": measure_nps(),
}

# Compare
comparison = compare(baseline, after)
print(f"Latency: {comparison.latency_change}")
print(f"Availability: {comparison.availability_change}")
print(f"Cost: {comparison.cost_change}")
```

**Business Impact**

Most important: business metrics:

```python
# Business impact analysis
impact = {
    # Revenue
    "revenue_change": after.revenue - before.revenue,
    "revenue_per_request": after.revenue / after.requests,

    # User experience
    "user_complaints": after.support_tickets,
    "nps_change": after.nps - before.nps,
    "churn_rate": after.churn_rate,

    # Operational
    "incident_count": count_incidents(after_migration),
    "time_to_resolve": mean_time_to_resolve(),
    "developer_velocity": features_shipped_per_month(),
}

# Decision
if impact["revenue_change"] > 0 and impact["nps_change"] > -5:
    print("Migration successful!")
else:
    print("Consider rolling back")
```

**Technical Debt**

Track complexity cost:

```python
# Code complexity metrics
complexity = {
    "lines_of_code": count_lines(),
    "cyclomatic_complexity": measure_complexity(),
    "test_coverage": measure_coverage(),
    "bug_rate": bugs_per_kloc(),
    "time_to_onboard": time_for_new_dev_productivity(),
}
```

### Educate the Team

**Mental Models**

Teach thinking frameworks:

```
Workshop 1: Consistency Models
- What is eventual consistency?
- Why does it exist?
- When is it acceptable?
- How do we reason about it?

Workshop 2: CAP Theorem
- Consistency vs Availability vs Partition tolerance
- Real-world examples
- Making informed trade-offs

Workshop 3: Failure Modes
- What can go wrong?
- How do we detect issues?
- How do we recover?

Workshop 4: Design Patterns
- Saga pattern
- Event sourcing
- CQRS
- Outbox pattern
```

**Trade-offs**

Help team make decisions:

```
Decision framework:

Question 1: Is strong consistency required?
- If yes -> Use ACID
- If no -> Continue

Question 2: Is high availability required?
- If yes -> Use BASE
- If no -> ACID is simpler

Question 3: Is scale important?
- If yes -> Use BASE
- If no -> ACID is simpler

Question 4: Can business logic handle conflicts?
- If yes -> Use BASE
- If no -> Use ACID or redesign logic
```

**Patterns**

Provide reusable solutions:

```python
# Pattern library
from patterns import EventSourcing, CQRS, Saga, Outbox

# Use pattern
class OrderService:
    def __init__(self):
        # Use outbox pattern for reliable messaging
        self.outbox = Outbox(db=self.db, event_bus=self.event_bus)

    def create_order(self, order):
        with transaction():
            self.db.insert_order(order)
            # Guaranteed delivery via outbox
            self.outbox.publish(OrderCreated(order))
            commit()
```

**Operations**

Train operations team:

```
Ops training:

1. Monitoring
   - What metrics to watch
   - What alerts to set
   - How to interpret dashboards

2. Debugging
   - How to trace request across replicas
   - How to identify consistency issues
   - Tools for investigating problems

3. Incident Response
   - Common failure modes
   - Runbooks for each scenario
   - When to escalate

4. Capacity Planning
   - How to scale BASE systems
   - Different from ACID systems
   - Cost optimization
```

### Plan for Failure

**Compensation Logic**

Every operation needs compensation:

```python
# Every forward operation has compensation
class BookingService:
    def reserve_hotel(self, booking):
        # Forward operation
        reservation = hotel_api.reserve(booking)
        return reservation

    def cancel_hotel(self, reservation):
        # Compensation operation
        hotel_api.cancel(reservation)

# Use in saga
def book_trip(user, flight, hotel):
    reservations = []
    try:
        # Forward operations
        flight_res = flight_service.reserve(flight)
        reservations.append(('flight', flight_res))

        hotel_res = hotel_service.reserve(hotel)
        reservations.append(('hotel', hotel_res))

        payment = payment_service.charge(user, total)

        return Trip(flight_res, hotel_res, payment)

    except Exception:
        # Compensate in reverse order
        for type, res in reversed(reservations):
            if type == 'flight':
                flight_service.cancel(res)
            elif type == 'hotel':
                hotel_service.cancel(res)
        raise
```

**Monitoring**

Know when things go wrong:

```python
# Comprehensive monitoring
class MonitoringService:
    def check_health(self):
        # Technical health
        replication_lag = measure_replication_lag()
        if replication_lag > threshold:
            alert("High replication lag")

        # Business health
        order_success_rate = measure_order_success()
        if order_success_rate < threshold:
            alert("Low order success rate")

        # User impact
        support_tickets = count_tickets()
        if support_tickets > threshold:
            alert("High support ticket volume")
```

**Rollback Plans**

Be able to revert:

```python
# Feature flag for gradual rollout
def get_user_profile(user_id):
    if feature_flags.is_enabled("eventual_consistent_profiles", user_id):
        # New BASE approach
        return eventual_db.get_profile(user_id)
    else:
        # Old ACID approach
        return acid_db.get_profile(user_id)

# Rollback plan:
# 1. Disable feature flag (instant rollback)
# 2. Monitor metrics
# 3. If issues persist, fully revert code
```

**Communication**

Keep stakeholders informed:

```
Communication plan:

Before migration:
- Explain why we're doing this
- Set expectations about behavior changes
- Provide timeline

During migration:
- Daily status updates
- Immediate notification of issues
- Metrics dashboard accessible to all

After migration:
- Results summary
- Lessons learned
- Next steps
```

## The Modern Synthesis

The future of database systems isn't ACID or BASE—it's both.

### It's Not ACID vs BASE

Modern systems use both:

```
E-commerce application architecture:

ACID components:
├─ User authentication (PostgreSQL)
├─ Payment processing (PostgreSQL with 2PC)
├─ Inventory reservations (PostgreSQL)
└─ Order creation (PostgreSQL)

BASE components:
├─ Product catalog (MongoDB)
├─ Search index (Elasticsearch)
├─ Shopping cart (Redis)
├─ Recommendations (Cassandra)
├─ User activity (Cassandra)
└─ Analytics (BigQuery)

Hybrid components:
├─ User profiles (PostgreSQL primary, cache layer)
├─ Order history (PostgreSQL with read replicas)
└─ Product reviews (PostgreSQL with eventual indexing)
```

**Both Have Their Place**

```
Use ACID when:
✓ Financial transactions (banking, payments)
✓ Inventory management (can't oversell)
✓ User authentication (security critical)
✓ Unique constraints (usernames, emails)
✓ Audit trails (must be correct)
✓ Regulatory compliance (legally required)

Use BASE when:
✓ Social media feeds (stale OK)
✓ Product catalogs (stale OK)
✓ Recommendations (approximate OK)
✓ Analytics (approximate OK)
✓ Search indexes (lag tolerable)
✓ Activity streams (stale OK)
```

**Context Determines Choice**

```python
# Same application, different choices
class EcommerceApp:
    # ACID: Money must be exact
    def process_payment(self, order):
        with transaction():  # ACID
            self.charge_card(order.payment)
            self.create_order(order)
            commit()

    # BASE: Recommendations can be stale
    def get_recommendations(self, user):
        return self.recommendation_cache.get(user)  # Eventual

    # Hybrid: Order history is ACID, but cached
    def get_order_history(self, user):
        cached = self.cache.get(f"orders:{user}")
        if cached:
            return cached  # Eventual (cache)

        orders = self.db.get_orders(user)  # ACID (primary)
        self.cache.set(f"orders:{user}", orders)
        return orders
```

**Evolution Continues**

The industry continues evolving:

```
Timeline:

1970s-2000s: ACID dominates
- All databases are ACID
- Vertical scaling
- Single datacenter

2000s-2010s: BASE emerges
- NoSQL movement
- Eventual consistency
- Horizontal scaling
- Multiple datacenters

2010s-2020s: Hybrid approaches
- Right tool for job
- Mixed consistency
- Distributed ACID (NewSQL)
- Global distribution

2020s-future: Unified systems
- Single system, multiple consistency levels
- Application chooses per operation
- Automatic optimization
- Global, consistent, available (pick three?)
```

### NewSQL: Having Your Cake

NewSQL systems attempt to provide both ACID and scale.

**Spanner's Approach**

Google Spanner: ACID transactions at global scale:

```
How Spanner works:

1. TrueTime API
   - Synchronized clocks across datacenters
   - GPS + atomic clocks
   - Tight bounds on clock uncertainty

2. Commit timestamps
   - Each transaction gets globally unique timestamp
   - Timestamp reflects true time
   - Total ordering of transactions

3. Distributed transactions
   - Two-phase commit across datacenters
   - Paxos for consistency
   - Reads see most recent committed data

Result:
- ACID transactions
- Global scale
- High latency (for writes)
```

**CockroachDB's Method**

CockroachDB: Open source Spanner alternative:

```
How CockroachDB works:

1. Hybrid Logical Clocks (HLC)
   - Doesn't require atomic clocks
   - Maintains causality
   - Good enough for most applications

2. Distributed SQL
   - PostgreSQL wire compatible
   - Distributes data automatically
   - Transparent sharding

3. Multi-region
   - Place data near users
   - Configurable consistency/latency trade-offs
   - Survive datacenter failures

Result:
- ACID transactions
- Horizontal scale
- No special hardware
- Open source
```

**FoundationDB's Layers**

FoundationDB: ACID key-value store with layers:

```
FoundationDB architecture:

Core (ACID key-value store):
├─ Strict serializability
├─ ACID transactions
└─ Distributed consensus

Layers (different data models):
├─ Document layer (MongoDB-compatible)
├─ SQL layer (SQL database)
├─ Blob layer (S3-compatible)
└─ Custom layers (your data model)

Approach:
- Core provides ACID guarantees
- Layers provide familiar interfaces
- Choose layer for your needs
```

**Future Directions**

Where the industry is headed:

```
Trends:

1. Consistency as a spectrum
   - Not binary (ACID vs BASE)
   - Choose per operation
   - Application-specified

2. Automatic optimization
   - System chooses best consistency level
   - Based on access patterns
   - Transparent to application

3. Global distribution
   - Data everywhere
   - Local latency
   - Strong consistency

4. Intelligent caching
   - AI-driven cache placement
   - Predictive prefetching
   - Automatic invalidation

5. Unified interfaces
   - Single API for multiple models
   - Polyglot persistence simplified
   - Consistency guarantees clear
```

### The Invariant View

The most profound insight: it's all about invariants.

**ACID Protects Invariants Synchronously**

```python
# ACID approach: enforce invariant synchronously
def transfer_money(from_account, to_account, amount):
    with transaction():
        # Invariant: total money stays constant
        from_balance = accounts.get(from_account).balance
        to_balance = accounts.get(to_account).balance

        accounts.update(from_account, balance=from_balance - amount)
        accounts.update(to_account, balance=to_balance + amount)

        # At commit time:
        # - Invariant checked (implicitly)
        # - Either all changes apply or none
        # - Invariant never violated (externally visible)
        commit()
```

**BASE Protects Invariants Eventually**

```python
# BASE approach: enforce invariant eventually
def transfer_money(from_account, to_account, amount):
    # Invariant might be temporarily violated
    # But guaranteed to be restored eventually

    transfer_id = create_transfer_intent(from_account, to_account, amount)

    # These might complete at different times
    debit(from_account, amount, transfer_id)
    credit(to_account, amount, transfer_id)

    # Background process ensures invariant:
    def reconciliation_process():
        while True:
            incomplete_transfers = find_incomplete_transfers()
            for transfer in incomplete_transfers:
                if transfer.debited and not transfer.credited:
                    # Complete the transfer
                    credit(transfer.to_account, transfer.amount, transfer.id)
                elif transfer.credited and not transfer.debited:
                    # Compensate
                    debit_reversal(transfer.to_account, transfer.amount, transfer.id)

            # Eventually, invariant is restored:
            # - All transfers complete, OR
            # - Failed transfers compensated
```

**Choose Based on Invariant Criticality**

```
Critical invariants (ACID):
- Money must balance (financial)
- Inventory can't go negative (physical)
- Unique constraints (logical)
- Security constraints (safety)

Non-critical invariants (BASE):
- Recommendation relevance (approximate)
- Cache consistency (temporary)
- Analytics accuracy (aggregate)
- Search index freshness (lag tolerable)

Decision framework:
1. What invariants exist?
2. How critical is each invariant?
3. Can invariant be violated temporarily?
4. What's the recovery process?
5. Choose consistency model accordingly
```

**Evidence Determines Possibility**

Some invariants can't be eventually consistent:

```python
# Example: Unique username
# Cannot be eventually consistent!

# Why? Consider:
User A registers username "john"
User B registers username "john" (concurrent)

Both succeed (BASE approach)

Eventually consistent resolution:
- One user gets username
- Other user... gets what?
- Can't just remove their account
- Can't silently change their username
- User experience is terrible

Conclusion:
- Unique constraints need ACID
- No way around it
- Some invariants require synchronous enforcement
```

## Summary

The transition from ACID to BASE represents a fundamental shift in how we think about data:

**From: Perfect consistency always**
**To: Appropriate consistency where needed**

ACID gave us perfect consistency but couldn't scale. BASE gave us scale but lost perfect consistency. The future is using both intelligently.

**From: Synchronous coordination**
**To: Asynchronous convergence**

ACID required all nodes to agree before committing. BASE allows nodes to disagree temporarily and converge eventually. The trade-off is between latency (how long operations take) and consistency (whether all nodes agree).

**From: Preventing all failures**
**To: Handling failures gracefully**

ACID systems tried to prevent failures by blocking operations during uncertainty. BASE systems accept failures and handle them with compensation logic. The trade-off is between availability (system stays up) and correctness (operations succeed atomically).

**From: One-size-fits-all**
**To: Right tool for the job**

Early systems used ACID for everything. Then NoSQL systems used BASE for everything. Modern systems use both, choosing based on requirements. The art is knowing where to draw the boundaries.

**Key Lessons:**

1. **ACID and BASE are complementary**, not competing approaches
2. **Context matters**: financial transactions need ACID, product catalogs can use BASE
3. **Invariants are the key**: what must always be true vs. what can be eventually true?
4. **Start small**: migrate gradually, learn from each step
5. **Measure everything**: technical metrics and business impact
6. **Team education**: everyone needs to understand trade-offs
7. **Plan for failure**: compensation logic, monitoring, rollback plans

**The Future:**

The industry is converging on systems that provide:

- **Multiple consistency levels** in a single system
- **Automatic optimization** based on access patterns
- **Global distribution** with local latency
- **Clear semantics** so developers know what they're getting

The question isn't "ACID or BASE?" but rather "Which consistency model for this invariant?"

The great paradigm shift from ACID to BASE isn't about abandoning correctness—it's about understanding that correctness exists on a spectrum, and choosing the appropriate point on that spectrum for each part of your system.

---

Continue to [NoSQL Movement →](nosql.md)

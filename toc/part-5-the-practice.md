# Part V: The Practice

## Chapter 14: Building a Global Database

### 14.1 Storage Architecture

#### 14.1.1 Storage Engine Selection

**LSM Tree Deep Dive**

Write path anatomy:
```
Client Write
  → MemTable (skip list, 64-256MB)
    → WAL append (sequential, fsync group commit)
      → MemTable flush to L0 SST
        → Compaction cascade (L0→L1→...→Ln)
```

Write amplification calculation:
```
WA = (L0_writes + ∑(Li_writes × fanout^i)) / user_writes
   = 1 + (4 × 10) + (40 × 10) + (400 × 10)
   = 4441 / 100 = 44x for worst case
```

Optimization strategies:
- Tiered compaction: 10-15x WA, better for time-series
- Leveled compaction: 25-40x WA, better for point reads
- Hybrid: L0-L2 tiered, L3+ leveled
- Partitioned compaction: reduce long-tail stalls

**B-Tree Deep Dive**

Update-in-place challenges:
```
Single row update:
  1. Read page (8-16KB) from disk
  2. Modify row in memory
  3. Write entire page back
  4. Update parent if split
  5. Cascade updates up tree
```

Copy-on-write B-tree (e.g., LMDB):
```
Root pointer atomic swap
  → New root page
    → Modified branch pages
      → Modified leaf pages
        → Old pages become garbage
```

**Hybrid Approaches**

Bw-tree (used in SQL Server Hekaton):
- Lock-free via CAS operations
- Log-structured delta chains
- Page consolidation in background
- Eliminates latch contention

WiscKey (LSM with value separation):
```
Key: [user_key, seq] → SST files (sorted)
Value: → vLog (append-only, unsorted)
Reduces compaction I/O by 90%
```

#### 14.1.2 Durability and Write Path

**fsync and Write Barriers**

The durability stack:
```
Application buffer
  → Kernel page cache (write() returns)
    → Device write cache (volatile!)
      → Persistent media

fsync() forces: cache → device cache
FUA (Force Unit Access): cache → media, bypassing device cache
```

Device write cache behavior:
```c
// ext4 with barrier=1 (default)
write(fd, buf, size);           // Returns immediately
fsync(fd);                      // Kernel issues:
                                // 1. FLUSH CACHE command
                                // 2. Writes metadata
                                // 3. Another FLUSH CACHE

// With write cache disabled (dangerous!)
hdparm -W0 /dev/sda             // All writes wait for platter
```

**Filesystem Behaviors**

ext4 ordered mode (default):
```
Transaction commit:
  1. Write data blocks
  2. Wait for data I/O completion
  3. Write journal (metadata + commit block)
  4. Checkpoint to main filesystem

Durability: Good
Performance: ~5K fsync/sec (7200 RPM)
```

ext4 journal mode:
```
Transaction commit:
  1. Write data + metadata to journal
  2. Checkpoint both to main filesystem

Durability: Excellent
Performance: ~2.5K fsync/sec (double write)
```

XFS delayed logging:
```
In-memory log buffer (32MB default)
  → Group commit every 30 seconds OR buffer full
  → Single large sequential write
  → Then issue FLUSH CACHE

Performance: 50K+ async writes/sec
Risk: 30-second window data loss on crash
```

**NVMe Flush Semantics**

NVMe command queue model:
```
Host issues commands:
  - WRITE commands → volatile buffer
  - FLUSH command → persist all prior writes

Device guarantees:
  - Completion = data in non-volatile media
  - Flush completion = all prior writes durable
```

Optimizations:
```bash
# Check NVMe volatile write cache status
nvme id-ctrl /dev/nvme0 | grep "Volatile Write Cache"
# VWC Present: 1 = has volatile cache

# Query namespace flush support
nvme id-ns /dev/nvme0n1 | grep "FUA"
# NSFEAT bit 0 = FUA support
```

Configuration example:
```bash
# Enable FUA for database workloads
mount -o barrier=1,noatime /dev/nvme0n1 /var/lib/db

# Verify settings
tune2fs -l /dev/nvme0n1 | grep features
# Should show: has_journal, needs_recovery
```

**Power-Loss Protection**

Enterprise SSD vs consumer:
```
Consumer SSD crash:
  - Loses 32-256MB in DRAM buffer
  - Possible metadata corruption
  - Firmware state inconsistent

Enterprise SSD (PLP):
  - Supercapacitor holds power 5-30 seconds
  - Firmware flushes DRAM → NAND
  - Completes in-flight operations
  - Total durability guarantee
```

Testing power-loss protection:
```bash
#!/bin/bash
# Power-loss test harness
while true; do
  dd if=/dev/urandom of=/mnt/test bs=4k count=1000 oflag=direct
  sync
  # Simulate power loss
  echo b > /proc/sysrq-trigger  # Emergency reboot
done

# Recovery verification
fsck -n /dev/sda1                # Check filesystem
db verify --corruption-check     # Check DB integrity
```

**Group Commit Optimization**

Traditional approach:
```
Thread 1: write → fsync (10ms)
Thread 2: write → fsync (10ms) ← waits for disk
Total: 20ms for 2 transactions
```

Group commit:
```
Threads 1-100: write to WAL buffer
Leader thread: fsync (10ms) ← syncs all 100
Followers: wake up, return success
Total: 10ms for 100 transactions

Throughput: 100 TPS → 10,000 TPS
```

Implementation:
```c
// PostgreSQL-style group commit
typedef struct {
    int leader_pid;
    int num_waiters;
    sem_t commit_sem;
} GroupCommitState;

void wal_commit(WALRecord *rec) {
    append_to_buffer(rec);

    if (try_become_leader()) {
        // I'm the leader
        wait_for_batch(5ms);      // Accumulate more writes
        fsync(wal_fd);
        wake_all_waiters();
    } else {
        // I'm a follower
        wait_on_semaphore();
    }
}
```

Tuning parameters:
```sql
-- PostgreSQL
wal_writer_delay = 200ms              -- Group commit window
commit_delay = 10                     -- Microseconds to wait
commit_siblings = 5                   -- Min concurrent commits to wait

-- MySQL InnoDB
innodb_flush_log_at_trx_commit = 1    -- Fsync every commit
innodb_flush_log_at_timeout = 1       -- Seconds
innodb_log_buffer_size = 16M          -- Group commit buffer
```

**WAL Preallocation**

Avoiding fallocate() latency:
```c
// RocksDB approach
void PreallocateWAL() {
    for (int i = 0; i < 3; i++) {
        int fd = open("wal.preallocate", O_CREAT|O_EXCL);
        fallocate(fd, 0, 0, 64*1024*1024);  // 64MB
        close(fd);
        // Keep file around for fast rename
    }
}

// When creating new WAL segment:
rename("wal.preallocate.0", "wal.000123");  // Instant!
```

Benefits:
- Eliminates fallocate() stalls (50-200ms)
- No filesystem fragmentation
- Predictable write performance

**Torn Write Protection**

Problem:
```
Database page: 16KB
Disk sector: 512 bytes or 4KB
Power loss during write → partial page on disk
```

Solutions:

1. Double-write buffer (InnoDB):
```
Write flow:
  1. Write page to doublewrite buffer (sequential)
  2. fsync doublewrite buffer
  3. Write page to actual location
  4. If crash: recover from doublewrite buffer
```

2. Checksum verification (PostgreSQL):
```c
typedef struct {
    uint32_t checksum;
    uint16_t page_id;
    uint8_t data[8192 - 6];
} Page;

// On read:
if (compute_checksum(page) != page.checksum) {
    // Torn write detected
    recover_from_wal();
}
```

3. Log-structured approach (RocksDB):
```
Never update in place → no torn writes possible
WAL itself protected by CRC32C per record
```

#### 14.1.3 MVCC Implementation

**Version Storage Strategies**

Append-only (PostgreSQL):
```sql
CREATE TABLE accounts (id INT, balance INT);
INSERT INTO accounts VALUES (1, 100);

-- Time T1: UPDATE accounts SET balance = 200 WHERE id = 1;
-- Physical layout:
[id=1, balance=100, xmin=1000, xmax=2000] ← old version
[id=1, balance=200, xmin=2000, xmax=∞]    ← new version

-- Bloat: table grows indefinitely until VACUUM
```

Time-travel delta (SQL Server):
```
Base row: [id=1, balance=200]
Version store: [id=1, old_balance=100, undo_ptr=...]

-- Older transactions read from version store
-- Newer transactions read from base table
```

Separate version chain (MySQL InnoDB):
```
Clustered index: [id=1, balance=200, roll_ptr]
                           ↓
Undo log: [balance=150] → [balance=100] → NULL

-- Traverse chain to reconstruct old versions
```

**Garbage Collection with Time-Travel**

Requirements:
```
1. Support time-travel queries: AS OF SYSTEM TIME '-1h'
2. GC versions older than TTL (e.g., 24 hours)
3. Don't GC versions needed by active transactions
4. Don't GC versions in snapshot exports
```

GC watermark calculation:
```python
def compute_gc_watermark():
    watermarks = []

    # Active transaction low-water mark
    watermarks.append(min(txn.start_ts for txn in active_txns))

    # Time-travel query limit
    watermarks.append(now() - time_travel_ttl)

    # Long-running export snapshots
    watermarks.append(min(snap.ts for snap in exports))

    # Replica lag (can't GC if replicas need data)
    watermarks.append(min(replica.applied_ts for replica in replicas))

    return min(watermarks)
```

CockroachDB-style GC:
```sql
-- Configure per-table TTL
ALTER TABLE events CONFIGURE ZONE USING gc.ttlseconds = 86400;

-- GC process:
-- 1. Scan range for versions older than watermark
-- 2. Delete old versions (RocksDB DeleteRange)
-- 3. Update intent resolution
-- 4. Report GC metrics

SELECT range_id, gc_bytes_age, live_bytes
FROM crdb_internal.ranges
WHERE gc_bytes_age > 1000000000;  -- 1GB-seconds of garbage
```

Compaction with MVCC:
```c
// RocksDB compaction with MVCC awareness
bool ShouldDropVersion(Key key, Sequence seq, Timestamp ts) {
    if (ts > gc_watermark) return false;           // Too new
    if (key in protected_timestamps) return false; // Export needs it
    if (seq >= earliest_snapshot) return false;    // Transaction needs it

    return true;
}

// Compaction output:
for (key, value_list in sst) {
    for (seq, ts, value in value_list) {
        if (!ShouldDropVersion(key, seq, ts)) {
            emit(key, seq, ts, value);
        }
    }
}
```

**Compaction Debt Management**

Measuring compaction debt:
```python
# RocksDB metrics
compaction_pending_bytes = sum(
    level.num_files * level.avg_file_size
    for level in levels
    if level.score > 1.0  # Score > 1 = needs compaction
)

# Debt grows when: write_rate > compaction_rate
debt_rate = write_rate - compaction_rate

# Time to clear debt:
time_to_clear = compaction_pending_bytes / compaction_rate

# Alert if: time_to_clear > 1 hour
```

Backlog controls:
```c
// Tiered approach based on debt level
enum BackpressureLevel {
    GREEN,   // debt < 1GB   : No limits
    YELLOW,  // debt < 10GB  : Delay writes 1-10ms
    ORANGE,  // debt < 50GB  : Delay writes 10-100ms
    RED      // debt > 50GB  : Stall writes until debt < 40GB
};

void apply_backpressure() {
    uint64_t debt = get_compaction_pending_bytes();

    if (debt > 50*GB) {
        // STALL: block all writes
        while (get_compaction_pending_bytes() > 40*GB) {
            sleep_ms(100);
        }
    } else if (debt > 10*GB) {
        // DELAY: slow down writes
        int delay_ms = (debt - 10*GB) / (50*MB);
        sleep_ms(min(delay_ms, 100));
    }
}
```

Tuning compaction:
```python
# RocksDB options
options = {
    # Concurrent compactions
    'max_background_compactions': 8,

    # Compaction priority
    'compaction_pri': 'kMinOverlappingRatio',  # or kOldestSmallestSeqFirst

    # Level sizes
    'level0_file_num_compaction_trigger': 4,
    'max_bytes_for_level_base': 256*MB,
    'max_bytes_for_level_multiplier': 10,

    # Rate limiting
    'rate_limiter': RateLimiter(
        rate_bytes_per_sec=100*MB,
        refill_period_us=100*1000,
    ),

    # Subcompactions for parallelism
    'max_subcompactions': 4,
}
```

Monitoring query:
```promql
# Compaction debt growth rate
rate(rocksdb_compaction_pending_bytes[5m]) > 0

# Estimated time to clear debt
rocksdb_compaction_pending_bytes /
  rate(rocksdb_compact_write_bytes[5m])

# Write stall events
increase(rocksdb_stall_micros[5m]) > 0
```

#### 14.1.4 Compression and Encoding

**Block Compression Trade-offs**

Compression algorithms:
```python
# Benchmark on real data:
algorithm     ratio    compress    decompress   CPU
-----------------------------------------------
none         1.0x     -           -            0%
snappy       2.5x     500 MB/s    1500 MB/s    5%
lz4          2.3x     600 MB/s    3000 MB/s    3%
zstd:1       2.8x     400 MB/s    1000 MB/s    8%
zstd:3       3.2x     200 MB/s    900 MB/s     15%
zlib:6       3.5x     100 MB/s    400 MB/s     25%
```

RocksDB configuration:
```cpp
// Tiered compression: fast for L0-L2, high ratio for L3+
options.compression_per_level = {
    kNoCompression,    // L0: hot data, fast access
    kNoCompression,    // L1
    kSnappyCompression,// L2
    kZSTD,             // L3+: cold data, high compression
};

options.bottommost_compression = kZSTD;
options.bottommost_compression_opts.level = 3;
```

**Column Encoding**

Delta encoding for sorted columns:
```
Sorted integers: [1000, 1001, 1003, 1005, 1010]
Delta encoded:   [1000, +1, +2, +2, +5]
Bit-packed:      12 bits for base, 3 bits per delta
Savings:         40 bytes → 9 bytes (77% reduction)
```

Dictionary compression:
```
String column: ["USA", "USA", "UK", "USA", "France", "UK"]
Dictionary:    {0: "USA", 1: "UK", 2: "France"}
Encoded:       [0, 0, 1, 0, 2, 1]
Savings:       30 bytes → 11 bytes (63% reduction)
```

Run-length encoding:
```
Boolean column: [true, true, true, false, false, true]
RLE encoded:    [(true, 3), (false, 2), (true, 1)]
Savings:       6 bytes → 12 bytes (RLE not beneficial here)
```

Parquet-style encoding:
```python
# Column statistics for encoding selection
class ColumnStats:
    distinct_ratio: float  # unique/total
    null_ratio: float
    sorted_ratio: float    # how sorted is it?
    avg_value_length: int

def choose_encoding(stats):
    if stats.null_ratio > 0.9:
        return RLE_NULL
    elif stats.distinct_ratio < 0.01:
        return DICTIONARY
    elif stats.sorted_ratio > 0.8:
        return DELTA_BINARY_PACKED
    else:
        return PLAIN
```

### 14.2 Transaction Processing
* 14.2.1 Isolation Implementation
  - SI anomaly prevention
  - SSI conflict detection
  - Phantom prevention
  - Predicate locks
* 14.2.2 Concurrency Control
  - Pessimistic locking
  - Optimistic validation
  - Hybrid approaches
  - Hot key mitigation
    - Hash-to-range splitting
    - Key space redistribution
* 14.2.3 Distributed Transactions
  - 2PC optimizations
  - Parallel commit
  - Deterministic execution
  - Clock-based ordering

### 14.3 Query Processing
* 14.3.1 Distributed Planning
  - Cost models
  - Statistics management
  - Plan caching
  - Adaptive execution
* 14.3.2 Execution Strategies
  - Predicate pushdown
  - Join strategies
  - Aggregation pushdown
  - Result streaming
* 14.3.3 Optimization Challenges
  - Network round trips
  - Data skew
  - Stragglers
  - Memory management

---

## Chapter 14B: Schema Evolution and Migrations

### 14B.1 Online Schema Changes

#### 14B.1.1 Expand/Contract Pattern

The safest online migration strategy:

**Phase 1: Expand** (add new without removing old)
```sql
-- Week 1: Add new nullable column
ALTER TABLE users ADD COLUMN email_verified BOOLEAN NULL;

-- Deploy code that writes to both columns
UPDATE users SET
  email_verified = (email_status = 'verified')
WHERE email_verified IS NULL;

-- Create index in background
CREATE INDEX CONCURRENTLY idx_email_verified ON users(email_verified);
```

**Phase 2: Migrate** (backfill data)
```python
# Backfill script with rate limiting
def backfill_email_verified():
    batch_size = 1000
    rate_limit = 100  # batches per second

    cursor = get_last_checkpoint()

    while True:
        batch = db.query("""
            SELECT id, email_status
            FROM users
            WHERE id > %s AND email_verified IS NULL
            ORDER BY id
            LIMIT %s
        """, cursor, batch_size)

        if not batch:
            break

        db.execute("""
            UPDATE users
            SET email_verified = (email_status = 'verified')
            WHERE id = ANY(%s)
        """, [row.id for row in batch])

        cursor = batch[-1].id
        save_checkpoint(cursor)

        time.sleep(1.0 / rate_limit)  # Rate limiting
```

**Phase 3: Contract** (remove old)
```sql
-- Week 4: After backfill complete, make NOT NULL
ALTER TABLE users ALTER COLUMN email_verified SET NOT NULL;

-- Week 5: Deploy code that only uses new column
-- Week 6: Drop old column
ALTER TABLE users DROP COLUMN email_status;
```

#### 14B.1.2 Dual Writes with Reconciliation

For breaking changes that need transactional consistency:

```python
class UserService:
    def update_email_status(self, user_id, verified):
        # Dual write: old and new representations
        with db.transaction():
            # Write to old column (for old code)
            db.execute("""
                UPDATE users
                SET email_status = %s
                WHERE id = %s
            """, 'verified' if verified else 'unverified', user_id)

            # Write to new column (for new code)
            db.execute("""
                UPDATE users
                SET email_verified = %s
                WHERE id = %s
            """, verified, user_id)

            # Audit log for reconciliation
            db.execute("""
                INSERT INTO schema_migration_audit
                (table_name, row_id, old_value, new_value, timestamp)
                VALUES ('users', %s, %s, %s, NOW())
            """, user_id, 'email_status', 'email_verified')

# Reconciliation checker (runs async)
def check_consistency():
    inconsistent = db.query("""
        SELECT id, email_status, email_verified
        FROM users
        WHERE (email_status = 'verified') != email_verified
        LIMIT 1000
    """)

    for row in inconsistent:
        alert(f"Inconsistency: user {row.id}")
        # Auto-repair or manual intervention
        repair_user(row.id)
```

#### 14B.1.3 Shadow Reads/Writes

Testing new schema before full cutover:

```python
class UserRepository:
    def __init__(self):
        self.shadow_mode = get_feature_flag("shadow_new_schema")
        self.shadow_write_percent = 5  # 5% of traffic
        self.shadow_compare = True

    def get_user(self, user_id):
        # Primary read: old schema
        old_result = self._read_old_schema(user_id)

        if self.shadow_mode:
            # Shadow read: new schema
            new_result = self._read_new_schema(user_id)

            if self.shadow_compare:
                # Compare results async
                asyncio.create_task(
                    self._compare_results(old_result, new_result)
                )

        return old_result  # Always return old result

    def update_user(self, user_id, data):
        # Primary write: old schema
        self._write_old_schema(user_id, data)

        if self.shadow_mode and random.random() < self.shadow_write_percent:
            try:
                # Shadow write: new schema
                self._write_new_schema(user_id, data)
            except Exception as e:
                # Log but don't fail primary write
                log.error(f"Shadow write failed: {e}")

    async def _compare_results(self, old, new):
        if old != new:
            metrics.increment("schema_migration.mismatch")
            log.warning(f"Schema mismatch: {old} != {new}")
```

#### 14B.1.4 Idempotent Migrations

Making migrations safe to retry:

```python
class Migration:
    def __init__(self, name, version):
        self.name = name
        self.version = version

    def run(self):
        # Check if already applied
        if self._is_applied():
            log.info(f"Migration {self.name} already applied")
            return

        # Acquire lock to prevent concurrent runs
        with self._acquire_lock():
            # Double-check after acquiring lock
            if self._is_applied():
                return

            try:
                self._execute()
                self._mark_applied()
            except Exception as e:
                self._mark_failed(str(e))
                raise

    def _is_applied(self):
        result = db.query("""
            SELECT status FROM schema_migrations
            WHERE name = %s AND version = %s
        """, self.name, self.version)
        return result and result[0].status == 'applied'

    def _acquire_lock(self):
        # PostgreSQL advisory lock
        return db.execute("""
            SELECT pg_advisory_lock(%s)
        """, hash(f"{self.name}:{self.version}"))

    def _execute(self):
        # Migration logic (must be idempotent!)
        db.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email_verified BOOLEAN
        """)

    def _mark_applied(self):
        db.execute("""
            INSERT INTO schema_migrations (name, version, status, applied_at)
            VALUES (%s, %s, 'applied', NOW())
            ON CONFLICT (name, version) DO UPDATE
            SET status = 'applied', applied_at = NOW()
        """, self.name, self.version)

### 14B.2 Large-Scale Backfills

#### 14B.2.1 Backfill Strategies

**Chunked backfill with checkpointing:**

```python
class BackfillJob:
    def __init__(self, table, column, compute_fn):
        self.table = table
        self.column = column
        self.compute_fn = compute_fn
        self.checkpoint_table = "backfill_checkpoints"

    def run(self):
        job_id = self._get_job_id()
        start_key = self._load_checkpoint(job_id)

        while True:
            batch = self._fetch_batch(start_key, batch_size=1000)
            if not batch:
                break

            # Process batch
            updates = []
            for row in batch:
                new_value = self.compute_fn(row)
                updates.append((row.id, new_value))

            # Apply updates
            self._apply_batch(updates)

            # Checkpoint progress
            start_key = batch[-1].id
            self._save_checkpoint(job_id, start_key)

            # Rate limit
            time.sleep(0.01)  # 100 batches/sec

    def _fetch_batch(self, start_key, batch_size):
        return db.query(f"""
            SELECT * FROM {self.table}
            WHERE id > %s
            ORDER BY id
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """, start_key, batch_size)

    def _apply_batch(self, updates):
        db.execute(f"""
            UPDATE {self.table}
            SET {self.column} = data.value
            FROM (SELECT unnest(%s::bigint[]) as id,
                         unnest(%s::text[]) as value) data
            WHERE {self.table}.id = data.id
        """, [u[0] for u in updates], [u[1] for u in updates])

# Example usage:
def compute_email_verified(row):
    return row.email_status == 'verified'

job = BackfillJob('users', 'email_verified', compute_email_verified)
job.run()
```

**Parallel backfill with range partitioning:**

```python
def parallel_backfill(table, column, compute_fn, num_workers=10):
    # Partition key space
    min_id, max_id = db.query(f"SELECT MIN(id), MAX(id) FROM {table}")[0]
    range_size = (max_id - min_id) // num_workers

    ranges = [
        (min_id + i * range_size, min_id + (i+1) * range_size)
        for i in range(num_workers)
    ]
    ranges[-1] = (ranges[-1][0], max_id)  # Last range goes to max

    # Launch workers
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(backfill_range, table, column, compute_fn, start, end)
            for start, end in ranges
        ]

        # Wait for completion
        for future in futures:
            future.result()

def backfill_range(table, column, compute_fn, start_id, end_id):
    cursor = start_id
    while cursor < end_id:
        batch = db.query(f"""
            SELECT * FROM {table}
            WHERE id >= %s AND id < %s
            ORDER BY id
            LIMIT 1000
        """, cursor, end_id)

        if not batch:
            break

        # Process and update
        updates = [(row.id, compute_fn(row)) for row in batch]
        apply_batch(table, column, updates)

        cursor = batch[-1].id + 1
```

#### 14B.2.2 Keyspace Reshaping

Changing primary key or sharding scheme:

**Scenario: Migrate from auto-increment ID to UUID**

```python
# Phase 1: Add UUID column
db.execute("""
    ALTER TABLE orders ADD COLUMN uuid UUID DEFAULT gen_random_uuid()
""")

# Phase 2: Backfill UUIDs
db.execute("""
    UPDATE orders SET uuid = gen_random_uuid() WHERE uuid IS NULL
""")

# Phase 3: Create mapping table for dual-key period
db.execute("""
    CREATE TABLE order_id_mapping (
        legacy_id BIGINT PRIMARY KEY,
        uuid UUID NOT NULL UNIQUE
    );

    INSERT INTO order_id_mapping (legacy_id, uuid)
    SELECT id, uuid FROM orders;

    CREATE INDEX idx_uuid_lookup ON order_id_mapping(uuid);
""")

# Phase 4: Application dual-read layer
class OrderRepository:
    def get_order(self, identifier):
        if isinstance(identifier, int):
            # Legacy ID lookup
            uuid = self._legacy_id_to_uuid(identifier)
            return self._get_by_uuid(uuid)
        else:
            # Direct UUID lookup
            return self._get_by_uuid(identifier)

    def _legacy_id_to_uuid(self, legacy_id):
        result = db.query("""
            SELECT uuid FROM order_id_mapping WHERE legacy_id = %s
        """, legacy_id)
        return result[0].uuid if result else None

# Phase 5: Switch primary key (requires table rewrite)
db.execute("""
    ALTER TABLE orders DROP CONSTRAINT orders_pkey;
    ALTER TABLE orders ADD PRIMARY KEY (uuid);
    CREATE INDEX idx_orders_legacy_id ON orders(id);  -- Keep for lookups
""")

# Phase 6: Update foreign keys (gradual)
db.execute("""
    ALTER TABLE order_items ADD COLUMN order_uuid UUID;

    UPDATE order_items oi
    SET order_uuid = o.uuid
    FROM orders o
    WHERE oi.order_id = o.id;

    ALTER TABLE order_items ALTER COLUMN order_uuid SET NOT NULL;
    ALTER TABLE order_items ADD FOREIGN KEY (order_uuid) REFERENCES orders(uuid);
""")
```

**Resharding strategy:**

```python
# Old sharding: hash(user_id) % 16
# New sharding: hash(user_id) % 64

def migrate_shard_scheme():
    old_shards = 16
    new_shards = 64

    for old_shard in range(old_shards):
        # Each old shard splits into multiple new shards
        new_shard_targets = [
            new_shard for new_shard in range(new_shards)
            if (new_shard % old_shards) == old_shard
        ]

        # Read from old shard
        rows = db.query(f"""
            SELECT * FROM users_{old_shard}
        """)

        # Route to new shards
        for row in rows:
            new_shard = hash(row.user_id) % new_shards
            db.execute(f"""
                INSERT INTO users_{new_shard}_new VALUES (...)
            """, row)

        # Verify counts match
        old_count = db.query(f"SELECT COUNT(*) FROM users_{old_shard}")[0]
        new_count = sum(
            db.query(f"SELECT COUNT(*) FROM users_{s}_new")[0]
            for s in new_shard_targets
        )
        assert old_count == new_count

    # Atomic cutover: rename tables
    for shard in range(new_shards):
        db.execute(f"""
            ALTER TABLE users_{shard} RENAME TO users_{shard}_old;
            ALTER TABLE users_{shard}_new RENAME TO users_{shard};
        """)
```

#### 14B.2.3 TTL and Lifecycle Backfills

**Add TTL to existing data:**

```python
# Phase 1: Add TTL column
db.execute("""
    ALTER TABLE events ADD COLUMN expires_at TIMESTAMP;
    CREATE INDEX idx_events_expires ON events(expires_at)
    WHERE expires_at IS NOT NULL;
""")

# Phase 2: Backfill TTL based on creation time
def backfill_ttl(retention_days=90):
    db.execute("""
        UPDATE events
        SET expires_at = created_at + INTERVAL '%s days'
        WHERE expires_at IS NULL
    """, retention_days)

# Phase 3: TTL enforcement (scheduled job)
def run_ttl_cleanup():
    while True:
        deleted = db.execute("""
            DELETE FROM events
            WHERE expires_at < NOW()
            RETURNING id
        """)

        metrics.increment('ttl_cleanup.deleted', len(deleted))

        if len(deleted) < 1000:
            time.sleep(60)  # Sleep if nothing to do
        else:
            time.sleep(1)   # Continue if backlog exists

# Phase 4: Partition by time for efficient cleanup
db.execute("""
    CREATE TABLE events_partitioned (
        id BIGINT,
        created_at TIMESTAMP,
        expires_at TIMESTAMP,
        data JSONB
    ) PARTITION BY RANGE (created_at);

    -- Create monthly partitions
    CREATE TABLE events_2025_01 PARTITION OF events_partitioned
        FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

    CREATE TABLE events_2025_02 PARTITION OF events_partitioned
        FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

    -- Drop entire partition for TTL (instant!)
    DROP TABLE events_2024_01;  -- Drop Jan 2024 data
""")
```

**Lifecycle state transitions:**

```python
# Add lifecycle state to objects
db.execute("""
    CREATE TYPE object_lifecycle AS ENUM (
        'active', 'archived', 'deleted', 'purged'
    );

    ALTER TABLE objects ADD COLUMN lifecycle object_lifecycle DEFAULT 'active';
""")

# Backfill lifecycle based on rules
def backfill_lifecycle():
    # Archive objects inactive for 6 months
    db.execute("""
        UPDATE objects
        SET lifecycle = 'archived'
        WHERE lifecycle = 'active'
          AND last_accessed_at < NOW() - INTERVAL '6 months'
    """)

    # Soft delete after 12 months
    db.execute("""
        UPDATE objects
        SET lifecycle = 'deleted',
            deleted_at = NOW()
        WHERE lifecycle = 'archived'
          AND last_accessed_at < NOW() - INTERVAL '12 months'
    """)

    # Hard delete (purge) after 24 months
    db.execute("""
        UPDATE objects
        SET lifecycle = 'purged',
            data = NULL,  -- Clear actual data
            purged_at = NOW()
        WHERE lifecycle = 'deleted'
          AND deleted_at < NOW() - INTERVAL '12 months'
    """)

# Scheduled lifecycle manager
class LifecycleManager:
    def __init__(self):
        self.rules = [
            LifecycleRule('archive', 'active', timedelta(days=180)),
            LifecycleRule('delete', 'archived', timedelta(days=180)),
            LifecycleRule('purge', 'deleted', timedelta(days=365)),
        ]

    def run(self):
        for rule in self.rules:
            count = self.apply_rule(rule)
            metrics.gauge(f'lifecycle.{rule.action}', count)

    def apply_rule(self, rule):
        return db.execute(f"""
            UPDATE objects
            SET lifecycle = %s,
                {rule.action}_at = NOW()
            WHERE lifecycle = %s
              AND last_accessed_at < NOW() - %s
        """, rule.target_state, rule.source_state, rule.age_threshold)
```

---

## Chapter 15: Cross-Cloud Transactions

### 15.1 Multi-Cloud Economics
* 15.1.1 Cost Analysis
  - Egress pricing models
  - Compute vs network trade-offs
  - Storage tiering
  - Reserved vs on-demand
* 15.1.2 Placement Optimization
  - Data locality strategies
  - Consistent hashing
  - Compute-near-data patterns
  - Caching economics
* 15.1.3 Vendor Management
  - API abstractions
  - Portability layers
  - Lock-in mitigation
  - Multi-cloud governance

### 15.2 Technical Implementation
* 15.2.1 Network Architecture
  - VPN setup
  - Direct peering
  - Transit gateways
  - Latency optimization
* 15.2.2 Consensus Across Clouds
  - WAN-optimized protocols
  - Witness node placement
  - Quorum configuration
  - Leader placement
* 15.2.3 Transaction Patterns
  - Cross-cloud 2PC
  - Saga orchestration
  - Compensation logic
  - Idempotency strategies

### 15.3 Production Examples
* 15.3.1 Multi-Cloud Spanner
  - Architecture details
  - Performance metrics
  - Operational challenges
  - Cost analysis
* 15.3.2 Cross-Cloud Streaming
  - Kafka MirrorMaker 2
  - Exactly-once guarantees
  - Cluster federation
  - Offset management
* 15.3.3 Hybrid Patterns
  - On-premise integration
  - Edge computing
  - Cloud bursting
  - Disaster recovery

---

## Chapter 16: Operating at Scale

### 16.1 Incident Management

#### 16.1.1 Detection Infrastructure

**SLO-based alerting:**

```yaml
# slo-config.yaml
slos:
  - name: api_availability
    target: 0.999  # 99.9%
    window: 30d
    error_budget: 43m  # 0.1% of 30 days

    indicators:
      - type: availability
        success_criteria: "status_code < 500"
        data_source: "prometheus"
        query: |
          sum(rate(http_requests_total{status!~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))

    alerts:
      - name: BurnRate6x
        condition: "burn_rate > 6 for 10m"
        severity: page
        message: "Burning error budget 6x faster than target"

      - name: BurnRate3x
        condition: "burn_rate > 3 for 1h"
        severity: page

      - name: BurnRate1x
        condition: "burn_rate > 1 for 24h"
        severity: warning
```

Implementation:
```python
class SLOMonitor:
    def __init__(self, slo_config):
        self.target = slo_config.target
        self.window = slo_config.window
        self.error_budget = (1 - self.target) * self.window

    def compute_burn_rate(self, current_error_rate):
        # Burn rate = (actual error rate) / (target error rate)
        target_error_rate = 1 - self.target
        return current_error_rate / target_error_rate

    def check_alerts(self):
        # Short window (1 hour) for fast burn
        error_rate_1h = self.measure_error_rate(window="1h")
        burn_rate_1h = self.compute_burn_rate(error_rate_1h)

        if burn_rate_1h > 14.4:  # 2% error budget in 1h
            self.page("Critical: burning 2% budget/hour")

        # Medium window (6 hour) for sustained issues
        error_rate_6h = self.measure_error_rate(window="6h")
        burn_rate_6h = self.compute_burn_rate(error_rate_6h)

        if burn_rate_6h > 6:  # 5% error budget in 6h
            self.page("High: burning 5% budget in 6h")

        # Long window (3 days) for slow leaks
        error_rate_3d = self.measure_error_rate(window="3d")
        burn_rate_3d = self.compute_burn_rate(error_rate_3d)

        if burn_rate_3d > 1:
            self.warn("Sustained degradation over 3 days")
```

**Anomaly detection:**

```python
# Time-series anomaly detection
class AnomalyDetector:
    def __init__(self):
        self.history = deque(maxlen=1440)  # 24h at 1min resolution

    def is_anomalous(self, value, metric_name):
        if len(self.history) < 60:
            return False  # Need baseline

        # Statistical approach: modified Z-score
        median = np.median(self.history)
        mad = np.median(np.abs(self.history - median))
        z_score = 0.6745 * (value - median) / mad

        if abs(z_score) > 3.5:
            return True

        # Trend-based: sudden slope change
        recent_trend = np.polyfit(range(10), list(self.history)[-10:], 1)[0]
        if abs(recent_trend) > 2 * np.std(self.history):
            return True

        return False

    def update(self, value):
        self.history.append(value)

# Usage
latency_detector = AnomalyDetector()
while True:
    p99 = get_metric("api.latency.p99")
    if latency_detector.is_anomalous(p99, "latency"):
        alert("Latency anomaly detected", value=p99)
    latency_detector.update(p99)
    time.sleep(60)
```

#### 16.1.2 Operational Reality Patterns

**Retry Budgets**

Prevent retry storms:

```python
class RetryBudget:
    def __init__(self, ttl=10, ratio=0.1, min_requests=200):
        self.ttl = ttl  # seconds
        self.ratio = ratio  # 10% of requests can be retries
        self.min_requests = min_requests

        self.request_count = 0
        self.retry_count = 0
        self.last_reset = time.time()

    def can_retry(self):
        self._maybe_reset()

        # Need minimum traffic for meaningful ratio
        if self.request_count < self.min_requests:
            return True

        retry_percentage = self.retry_count / self.request_count
        return retry_percentage < self.ratio

    def record_request(self, is_retry=False):
        self._maybe_reset()
        self.request_count += 1
        if is_retry:
            self.retry_count += 1

    def _maybe_reset(self):
        now = time.time()
        if now - self.last_reset > self.ttl:
            self.request_count = 0
            self.retry_count = 0
            self.last_reset = now

# Usage in HTTP client
class RetryableClient:
    def __init__(self):
        self.budget = RetryBudget()

    def request(self, url, max_retries=3):
        self.budget.record_request(is_retry=False)

        for attempt in range(max_retries):
            try:
                return self._do_request(url)
            except RetriableError as e:
                if attempt == max_retries - 1:
                    raise

                if not self.budget.can_retry():
                    raise BudgetExhausted("Retry budget depleted")

                self.budget.record_request(is_retry=True)
                time.sleep(2 ** attempt)  # Exponential backoff
```

**Brownout Mode**

Graceful degradation under load:

```python
class BrownoutController:
    def __init__(self):
        self.mode = "normal"  # normal, brownout, emergency
        self.cpu_threshold = 0.80
        self.latency_threshold_p99 = 1000  # ms

    def check_and_adjust(self):
        cpu = get_cpu_utilization()
        p99_latency = get_p99_latency()

        if cpu > 0.95 or p99_latency > 2000:
            self.enter_emergency_mode()
        elif cpu > self.cpu_threshold or p99_latency > self.latency_threshold_p99:
            self.enter_brownout_mode()
        elif cpu < 0.60 and p99_latency < 500:
            self.enter_normal_mode()

    def enter_brownout_mode(self):
        if self.mode == "brownout":
            return

        log.warning("Entering brownout mode")
        self.mode = "brownout"

        # Disable expensive features
        feature_flags.disable("recommendations")
        feature_flags.disable("real_time_notifications")

        # Reduce cache TTL (fresher = more cache hits)
        cache.set_default_ttl(300)  # 5 minutes instead of 1

        # Enable request coalescing
        request_coalescer.enable()

        metrics.increment("brownout.entered")

    def enter_emergency_mode(self):
        if self.mode == "emergency":
            return

        log.error("Entering emergency mode")
        self.mode = "emergency"

        # Aggressive load shedding
        load_shedder.enable(drop_rate=0.3)  # Drop 30% of requests

        # Disable all non-critical endpoints
        endpoint_limiter.disable_non_critical()

        # Stop all background jobs
        background_jobs.pause_all()

        metrics.increment("emergency.entered")
        page_oncall("Emergency mode activated")

# Integrated with request handler
@app.middleware
def brownout_middleware(request):
    controller = get_brownout_controller()

    if controller.mode == "emergency":
        if not request.is_critical():
            return Response("Service temporarily unavailable", 503)

    if controller.mode == "brownout":
        if request.is_expensive():
            return Response("Feature temporarily disabled", 503)

    return next(request)
```

**Shadow/Mirrored Traffic Pitfalls**

Common issues and solutions:

```python
class TrafficMirror:
    def __init__(self, primary_host, shadow_host):
        self.primary = primary_host
        self.shadow = shadow_host
        self.mirror_percent = 5  # Start small!

    async def handle_request(self, request):
        # ALWAYS return primary response
        primary_response = await self._call_primary(request)

        # Mirror async (don't block)
        if random.random() < self.mirror_percent / 100:
            asyncio.create_task(self._mirror_request(request))

        return primary_response

    async def _mirror_request(self, request):
        # Clone request (careful with ID generation!)
        shadow_request = self._sanitize_request(request)

        try:
            shadow_response = await self._call_shadow(shadow_request)
            self._compare_responses(request, shadow_response)
        except Exception as e:
            # NEVER let shadow errors affect primary
            log.error(f"Shadow request failed: {e}")
            metrics.increment("shadow.errors")

    def _sanitize_request(self, request):
        # CRITICAL: prevent side effects
        cloned = request.copy()

        # Change idempotency keys
        if 'Idempotency-Key' in cloned.headers:
            cloned.headers['Idempotency-Key'] += '-SHADOW'

        # Flag as shadow traffic
        cloned.headers['X-Shadow-Traffic'] = 'true'

        # Sanitize IDs (prevent duplicate key violations)
        if 'id' in cloned.body:
            cloned.body['id'] = self._generate_shadow_id(cloned.body['id'])

        return cloned

    def _compare_responses(self, request, shadow_response):
        # Compare semantically, not byte-for-byte
        if shadow_response.status != 200:
            metrics.increment("shadow.error_rate")

        # Compare critical fields only
        if not self._responses_equivalent(request, shadow_response):
            log.warning("Shadow divergence", request_id=request.id)
            metrics.increment("shadow.divergence")
```

**Time-Travel Debugging via Replay**

Reproduce production issues:

```python
class EventRecorder:
    """Record all events for later replay"""

    def __init__(self):
        self.storage = S3Storage("event-recordings")

    def record_request(self, request_id, request_data):
        event = {
            'type': 'request',
            'timestamp': time.time_ns(),
            'request_id': request_id,
            'data': request_data,
            'clock': get_hybrid_logical_clock(),
        }
        self.storage.append(f"recording-{date.today()}.jsonl", event)

    def record_db_query(self, request_id, query, result):
        event = {
            'type': 'db_query',
            'timestamp': time.time_ns(),
            'request_id': request_id,
            'query': query,
            'result': result,
            'clock': get_hybrid_logical_clock(),
        }
        self.storage.append(f"recording-{date.today()}.jsonl", event)

class EventReplayer:
    """Replay recorded events"""

    def __init__(self, recording_file):
        self.events = self._load_events(recording_file)
        self.mock_db = MockDatabase()

    def replay(self, request_id):
        # Filter events for this request
        request_events = [
            e for e in self.events
            if e.get('request_id') == request_id
        ]

        # Sort by causal order (HLC)
        request_events.sort(key=lambda e: e['clock'])

        # Set up mocks
        for event in request_events:
            if event['type'] == 'db_query':
                self.mock_db.add_response(event['query'], event['result'])

        # Replay request
        with mock.patch('db', self.mock_db):
            request = request_events[0]['data']
            response = handle_request(request)
            return response

# Usage: debug production issue
replayer = EventReplayer("recording-2025-09-30.jsonl")
response = replayer.replay(request_id="abc-123")
# Now you can step through with debugger!
```

**Cache Stampede Prevention**

```python
class CacheWithStampedeProtection:
    def __init__(self):
        self.cache = {}
        self.locks = {}  # Per-key locks
        self.inflight = {}  # Track in-flight requests

    async def get_or_compute(self, key, compute_fn, ttl=60):
        # Fast path: cache hit
        if key in self.cache and not self._is_expired(key):
            return self.cache[key]

        # Acquire per-key lock
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()

        async with self.locks[key]:
            # Double-check after acquiring lock
            if key in self.cache and not self._is_expired(key):
                return self.cache[key]

            # Check if another request is already computing
            if key in self.inflight:
                # Wait for in-flight request
                return await self.inflight[key]

            # Start computation
            future = asyncio.create_task(compute_fn())
            self.inflight[key] = future

            try:
                result = await future
                self.cache[key] = {
                    'value': result,
                    'expires_at': time.time() + ttl
                }
                return result
            finally:
                del self.inflight[key]

    def _is_expired(self, key):
        return time.time() > self.cache[key]['expires_at']

# Probabilistic early expiration (jittered)
class JitteredCache:
    def get_or_compute(self, key, compute_fn, ttl=60):
        cached = self.cache.get(key)
        if not cached:
            return self._compute_and_cache(key, compute_fn, ttl)

        # Compute "effective TTL" with jitter
        age = time.time() - cached['created_at']
        effective_ttl = ttl * (1 - random.uniform(0, 0.1))  # 0-10% jitter

        # Probabilistic early refresh
        refresh_probability = age / effective_ttl
        if random.random() < refresh_probability:
            # Refresh async, return stale data
            asyncio.create_task(self._refresh(key, compute_fn, ttl))

        return cached['value']
```

**Admission Control at Edges**

```python
class AdmissionController:
    """Adaptive admission control based on system health"""

    def __init__(self):
        self.accept_rate = 1.0  # 100% = accept all
        self.recent_latencies = deque(maxlen=1000)
        self.concurrency = 0
        self.max_concurrency = 1000

    def try_admit(self, request):
        # Check concurrency limit
        if self.concurrency >= self.max_concurrency:
            metrics.increment("admission.rejected.concurrency")
            return False

        # Probabilistic rejection based on load
        if random.random() > self.accept_rate:
            metrics.increment("admission.rejected.rate")
            return False

        self.concurrency += 1
        return True

    def request_completed(self, latency_ms):
        self.concurrency -= 1
        self.recent_latencies.append(latency_ms)
        self._adjust_rate()

    def _adjust_rate(self):
        if len(self.recent_latencies) < 100:
            return

        p50 = np.percentile(self.recent_latencies, 50)
        p99 = np.percentile(self.recent_latencies, 99)

        # Use Little's Law to estimate healthy concurrency
        # L = λ * W
        # Healthy concurrency = arrival_rate * target_latency
        target_latency = 100  # ms
        current_throughput = self.concurrency / (p50 / 1000)
        healthy_concurrency = current_throughput * (target_latency / 1000)

        # Adjust acceptance rate
        if p99 > 1000 or self.concurrency > healthy_concurrency:
            # System overloaded, reduce rate
            self.accept_rate = max(0.5, self.accept_rate * 0.9)
        elif p99 < 500 and self.concurrency < healthy_concurrency * 0.8:
            # System has headroom, increase rate
            self.accept_rate = min(1.0, self.accept_rate * 1.1)

# Middleware integration
@app.middleware
async def admission_control(request):
    controller = get_admission_controller()

    if not controller.try_admit(request):
        return Response("Service at capacity", 503,
                       headers={"Retry-After": "5"})

    start = time.time()
    try:
        response = await next(request)
        return response
    finally:
        latency = (time.time() - start) * 1000
        controller.request_completed(latency)
```

#### 16.1.3 Diagnosis Tools

**HLC-Stamped Distributed Tracing**

```python
class HybridLogicalClock:
    def __init__(self, node_id):
        self.node_id = node_id
        self.physical = 0
        self.logical = 0

    def now(self):
        physical_now = time.time_ns()

        if physical_now > self.physical:
            self.physical = physical_now
            self.logical = 0
        else:
            self.logical += 1

        return HLCTimestamp(self.physical, self.logical, self.node_id)

    def update(self, remote_ts):
        """Update clock based on received timestamp"""
        physical_now = time.time_ns()
        max_physical = max(physical_now, self.physical, remote_ts.physical)

        if max_physical == self.physical == remote_ts.physical:
            self.logical = max(self.logical, remote_ts.logical) + 1
        elif max_physical == self.physical:
            self.logical += 1
        elif max_physical == remote_ts.physical:
            self.logical = remote_ts.logical + 1
        else:
            self.logical = 0

        self.physical = max_physical
        return self.now()

# Tracing with causality
class DistributedTrace:
    def __init__(self, trace_id, hlc):
        self.trace_id = trace_id
        self.spans = []
        self.hlc = hlc

    def start_span(self, operation):
        span = Span(
            trace_id=self.trace_id,
            span_id=generate_span_id(),
            operation=operation,
            start_hlc=self.hlc.now(),
        )
        self.spans.append(span)
        return span

    def propagate_headers(self):
        """Headers to send in RPC calls"""
        return {
            'X-Trace-ID': self.trace_id,
            'X-HLC-Timestamp': str(self.hlc.now()),
        }

    @staticmethod
    def from_headers(headers, hlc):
        """Reconstruct trace from incoming headers"""
        trace_id = headers['X-Trace-ID']
        remote_ts = HLCTimestamp.parse(headers['X-HLC-Timestamp'])

        # Update local clock with remote timestamp
        hlc.update(remote_ts)

        return DistributedTrace(trace_id, hlc)

# Causality reconstruction for debugging
def reconstruct_causality(traces):
    """Build causal DAG from HLC timestamps"""
    events = []
    for trace in traces:
        for span in trace.spans:
            events.append({
                'span_id': span.span_id,
                'operation': span.operation,
                'hlc': span.start_hlc,
            })

    # Sort by HLC (respects causality)
    events.sort(key=lambda e: e['hlc'])

    # Build happens-before graph
    graph = nx.DiGraph()
    for i, event in enumerate(events):
        graph.add_node(event['span_id'], **event)
        # Add edge if this event could have caused next event
        if i < len(events) - 1:
            next_event = events[i + 1]
            if event['hlc'] < next_event['hlc']:
                graph.add_edge(event['span_id'], next_event['span_id'])

    return graph
```

### 16.2 Capacity Planning
* 16.2.1 Load Testing
  - Production traffic replay
  - Synthetic workloads
  - Shadow testing
  - Chaos experiments
* 16.2.2 Scaling Mechanisms
  - Auto-scaling policies
  - Pre-warming strategies
  - Capacity reservations
  - Burst handling
* 16.2.3 Queueing Analysis
  - Little's Law application
  - Kingman's formula
  - Tail amplification
  - Series queue effects

### 16.3 Human Systems
* 16.3.1 On-Call Excellence
  - Error budget policies
  - Escalation paths
  - Runbook automation
  - Post-mortem culture
* 16.3.2 Knowledge Transfer
  - Documentation standards
  - Architecture reviews
  - Game days
  - Training programs
* 16.3.3 Team Scaling
  - Conway's Law alignment
  - Service ownership
  - Platform teams
  - SRE practices
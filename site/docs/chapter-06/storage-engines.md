# Storage Engines: The Physics of Persistence

## The Fundamental Trade-off

> "Show me your storage engine, and I'll tell you your database's personality."

Every database, regardless of its interface or consistency model, ultimately stores bytes on disk. How it organizes those bytes—its storage engine—determines everything: performance characteristics, failure modes, operational complexity. Two dominant designs have emerged, each optimizing for opposite ends of a fundamental trade-off.

**Write-optimized vs Read-optimized**. You cannot have both.

## LSM Trees: Born to Write

### The Log-Structured Merge Tree

In 1996, Patrick O'Neil introduced the LSM tree to solve a simple problem: **disk seeks are slow, sequential writes are fast**.

```
Memory (MemTable):
┌─────────────────────┐
│ key1 → value1 (new) │  ← All writes go here (fast)
│ key3 → value3       │
│ key7 → value7       │
└─────────────────────┘
         ↓ (flush when full)

Disk (Sorted String Tables - SSTables):
Level 0:  ┌──────┐ ┌──────┐ ┌──────┐
          │SST-9 │ │SST-8 │ │SST-7 │  ← Recent flushes
          └──────┘ └──────┘ └──────┘

Level 1:  ┌──────────┐ ┌──────────┐
          │  SST-6    │ │  SST-5    │  ← Compacted, no overlap
          └──────────┘ └──────────┘

Level 2:  ┌──────────────────────┐
          │       SST-4          │  ← Older, larger
          └──────────────────────┘
```

### Write Path: Blindingly Fast

```python
def write(key, value):
    # 1. Append to Write-Ahead Log (sequential)
    wal.append(f"{key},{value}")  # Durability

    # 2. Insert into MemTable (in-memory)
    memtable.insert(key, value)   # Fast writes

    # 3. Return immediately
    return "SUCCESS"

    # Background: Flush MemTable when full
    if memtable.size() > threshold:
        sstable = memtable.flush_to_disk()  # Sequential write
        level0.add(sstable)
        memtable.clear()
```

**Performance**:
- Write latency: ~100 microseconds (just memory + WAL)
- Write throughput: 1M+ ops/sec on NVMe SSD

### Read Path: The Amplification Problem

```python
def read(key):
    # 1. Check MemTable (fast)
    if key in memtable:
        return memtable[key]

    # 2. Check each level (slow - "read amplification")
    for level in [0, 1, 2, 3, ...]:
        for sstable in level.sstables:
            if key in sstable.bloom_filter:  # Probabilistic
                value = sstable.binary_search(key)
                if value:
                    return value

    return None  # Key not found
```

**Problem**: Might check dozens of SSTables!

### Compaction: The Hidden Cost

```python
def compact():
    """Merge SSTables to reduce read amplification"""

    # Leveled Compaction (RocksDB/LevelDB style)
    for level in range(max_level):
        if level_size[level] > level_capacity[level]:
            # Pick overlapping SSTables from level and level+1
            victims = pick_victims(level)

            # Merge sort (expensive!)
            merged = merge_sort(victims)

            # Write new SSTable to level+1
            write_new_sstable(merged, level + 1)

            # Delete old SSTables
            delete(victims)
```

### LSM Optimizations

**Bloom Filters**: Probabilistic existence check
```python
class BloomFilter:
    def __init__(self, expected_items, false_positive_rate=0.01):
        self.size = self.optimal_size(expected_items, false_positive_rate)
        self.bits = BitArray(self.size)
        self.num_hashes = self.optimal_hashes(expected_items)

    def add(self, key):
        for i in range(self.num_hashes):
            pos = hash(key, i) % self.size
            self.bits[pos] = 1

    def might_contain(self, key):
        for i in range(self.num_hashes):
            pos = hash(key, i) % self.size
            if not self.bits[pos]:
                return False  # Definitely not present
        return True  # Might be present (or false positive)
```

**Block Cache**: Keep hot blocks in memory
```python
class BlockCache:
    def __init__(self, capacity_mb):
        self.cache = LRUCache(capacity_mb * 1024 * 1024)

    def read_block(self, sstable, block_offset):
        cache_key = f"{sstable.id}:{block_offset}"

        if cache_key in self.cache:
            return self.cache[cache_key]  # Cache hit

        # Cache miss - read from disk
        block = sstable.read_block_from_disk(block_offset)
        self.cache[cache_key] = block
        return block
```

### Production LSM: RocksDB

Facebook's RocksDB powers:
- **MySQL (MyRocks)**: 50% storage reduction vs InnoDB
- **Kafka Streams**: State stores for stream processing
- **CockroachDB**: Underlying storage engine
- **TiKV**: Distributed key-value store

Configuration example:
```python
options = {
    'write_buffer_size': 64 * 1024 * 1024,  # 64MB MemTable
    'max_write_buffer_number': 3,  # 3 MemTables
    'level0_file_num_compaction_trigger': 4,
    'max_bytes_for_level_base': 256 * 1024 * 1024,  # 256MB
    'max_bytes_for_level_multiplier': 10,  # Each level 10x larger
    'compression': 'lz4',  # Fast compression
    'bottommost_compression': 'zstd',  # Better compression for cold data
}
```

## B-Trees: Born to Read

### The Balanced Tree Structure

B-trees, invented in 1970, optimize for the opposite: **minimize disk seeks during reads**.

```
                    Root Node (in memory)
                    ┌──────────────────┐
                    │ 17 | 35 | 60     │
                    └──────────────────┘
                    /    |      |       \
                   /     |      |        \
    Internal    ┌────┐ ┌────┐ ┌────┐  ┌────┐
    Nodes       │5,12│ │23,30│ │42,55│ │70,90│
                └────┘ └────┘ └────┘  └────┘
                /  |    /  |    /  |     / |
               /   |   /   |   /   |    /  |
    Leaf    ┌──┐┌──┐ ┌──┐┌──┐ ┌──┐┌──┐ ┌──┐┌──┐
    Pages   │1-4││5-11│...│60-69││70-89││90-99│
            └──┘└──┘ └──┘└──┘ └──┘└──┘ └──┘└──┘
            (Contains actual key-value pairs)
```

### Read Path: Logarithmically Bounded

```python
def read(key):
    """Read is always O(log n) disk seeks"""
    node = root

    while not node.is_leaf():
        # Binary search within node (in memory if cached)
        child_index = node.binary_search(key)
        # One disk seek (unless cached)
        node = load_node(node.children[child_index])

    # Final binary search in leaf
    return node.get(key)
```

**Performance**:
- Read latency: 3-4 disk seeks for billion keys
- With SSD: ~300 microseconds per read
- With page cache: ~1 microsecond if hot

### Write Path: The Amplification Problem

```python
def write(key, value):
    # 1. Find leaf page (same as read)
    leaf = find_leaf(key)

    # 2. Write to WAL (sequential)
    wal.append(f"{key},{value}")

    # 3. Update leaf page (random write!)
    if leaf.has_space():
        leaf.insert(key, value)
        disk.write_page(leaf)  # Random I/O
    else:
        # Page split (expensive!)
        split_page(leaf, key, value)
```

**Problem**: Every write potentially updates multiple pages (write amplification).

### B-Tree Optimizations

**Copy-on-Write (CoW)**:
```python
def cow_write(key, value):
    """Never modify pages in place - used by LMDB, BtrFS"""

    # Clone path from root to leaf
    new_root = root.clone()
    node = new_root

    while not node.is_leaf():
        child_index = node.binary_search(key)
        # Clone child (never modify original)
        node.children[child_index] = node.children[child_index].clone()
        node = node.children[child_index]

    # Insert in cloned leaf
    node.insert(key, value)

    # Atomic pointer swap
    atomic_swap(root_pointer, new_root)
```

**B+Tree with Sequential Insert Optimization**:
```python
class BPlusTreeWithSIO:
    def __init__(self):
        self.last_leaf = None
        self.insert_buffer = []

    def insert(self, key, value):
        # Detect sequential insert pattern
        if self.last_leaf and key > self.last_leaf.max_key():
            # Fast path: append to rightmost leaf
            if self.last_leaf.has_space():
                self.last_leaf.append(key, value)
            else:
                # Bulk insert buffered items
                self.bulk_insert(self.insert_buffer)
                self.insert_buffer = [(key, value)]
        else:
            # Regular B-tree insert
            super().insert(key, value)
```

### Production B-Trees: InnoDB

MySQL's InnoDB storage engine:

```sql
-- Primary key physically clusters data
CREATE TABLE orders (
    order_id BIGINT PRIMARY KEY,  -- B-tree sorted by this
    customer_id BIGINT,
    order_date DATETIME,
    amount DECIMAL(10,2)
) ENGINE=InnoDB;

-- Secondary indexes are separate B-trees
CREATE INDEX idx_customer ON orders(customer_id);
CREATE INDEX idx_date ON orders(order_date);
```

Physical layout:
```
Primary Index (Clustered):
order_id → (entire row data)

Secondary Index:
customer_id → order_id (primary key reference)
order_date → order_id
```

## Head-to-Head Comparison

### Write Performance

| Metric | LSM Tree | B-Tree |
|--------|----------|--------|
| Write Latency | 100μs (MemTable) | 1-10ms (disk seek) |
| Write Throughput | 1M+ ops/sec | 10-100K ops/sec |
| Sequential Insert | Optimal | Good with SIO |
| Random Insert | Optimal | Poor (random I/O) |
| Space Amplification | 1.1x (compressed) | 1.5x (fragmentation) |

### Read Performance

| Metric | LSM Tree | B-Tree |
|--------|----------|--------|
| Point Read | 1-100ms (worst) | 0.3-1ms (consistent) |
| Range Scan | Good (sorted) | Excellent (sequential) |
| Read Amplification | 10-100x | 3-4x |
| Cache Efficiency | Poor (many SSTables) | Excellent (hot pages) |

### Operational Characteristics

| Aspect | LSM Tree | B-Tree |
|--------|----------|--------|
| Compaction | Background CPU/IO spikes | None needed |
| Fragmentation | Self-healing via compaction | Requires OPTIMIZE TABLE |
| Backup | Complex (multiple files) | Simple (single file) |
| Recovery | Fast (sequential replay) | Slower (random reads) |
| Tuning | Many knobs | Fewer knobs |

## Hybrid Approaches

### LSM with Tiering

RocksDB's hybrid approach:
```python
class TieredStorage:
    def __init__(self):
        self.hot_tier = LSMTree(ssd_path)    # Recent data on SSD
        self.cold_tier = LSMTree(hdd_path)   # Old data on HDD

    def compact(self):
        # Move old data to cold tier
        for sstable in self.hot_tier.old_sstables():
            if sstable.age > 30_days:
                self.cold_tier.add(sstable)
                self.hot_tier.remove(sstable)
```

### B-Trees with LSM Write Buffer

MongoDB's WiredTiger:
```python
class WiredTiger:
    def __init__(self):
        self.lsm_buffer = LSMTree(max_size=1GB)  # Write buffer
        self.btree = BTree()  # Main storage

    def write(self, key, value):
        # Write to LSM buffer (fast)
        self.lsm_buffer.write(key, value)

        # Periodic merge to B-tree
        if self.lsm_buffer.size > threshold:
            self.merge_to_btree()

    def read(self, key):
        # Check LSM buffer first
        value = self.lsm_buffer.read(key)
        if value:
            return value
        # Then check B-tree
        return self.btree.read(key)
```

## Choosing the Right Engine

### Use LSM Trees When:

- **Write-heavy workload** (logging, metrics, events)
- **Sequential keys** (time-series, append-only)
- **Storage cost matters** (better compression)
- **Can tolerate read latency variance**

Examples:
- Time-series databases (InfluxDB)
- Log aggregation (Elasticsearch)
- Message queues (Kafka)
- Blockchain (LevelDB in Bitcoin)

### Use B-Trees When:

- **Read-heavy workload** (OLTP, web applications)
- **Predictable latency required**
- **Many secondary indexes** (complex queries)
- **Operational simplicity preferred**

Examples:
- Relational databases (PostgreSQL, MySQL)
- Document stores (MongoDB default)
- Graph databases (Neo4j)

## Future Directions

### Learned Indexes

Using machine learning instead of trees:
```python
class LearnedIndex:
    def __init__(self, data):
        # Train model to predict position from key
        self.model = train_regression_model(
            keys=data.keys,
            positions=range(len(data))
        )

    def lookup(self, key):
        # Model predicts position
        predicted_pos = self.model.predict(key)

        # Local search around prediction
        for offset in [-10, -9, ..., 10]:
            if data[predicted_pos + offset].key == key:
                return data[predicted_pos + offset].value
```

Early results: 1.5-3x faster than B-trees for some workloads!

### Persistent Memory

Intel Optane changes the game:
- Byte-addressable like RAM
- Persistent like SSD
- Latency: 300ns (between DRAM and SSD)

New storage engines for PM:
```python
class PMEMStorage:
    def __init__(self, pmem_device):
        self.pmem = mmap(pmem_device, MAP_SYNC)

    def write(self, key, value):
        offset = hash(key) % self.pmem.size

        # Direct write to persistent memory
        self.pmem[offset:offset+len(value)] = value

        # Ensure persistence (like a fence)
        pmem_persist(self.pmem, offset, len(value))
```

### Computational Storage

SSDs with built-in processors:
```python
class SmartSSD:
    def query(self, sql):
        # Push computation to SSD
        # Never transfer unnecessary data
        return self.ssd_processor.execute(sql)
```

## Summary: The Eternal Trade-off

Storage engines embody a fundamental truth: **optimizing for writes pessimizes reads, and vice versa**.

### The Evidence Model

- **Write evidence**: WAL entries, MemTable inserts
- **Read evidence**: Index lookups, bloom filter checks
- **Durability evidence**: Flush confirmations, checkpoints
- **Consistency evidence**: Version numbers, timestamps

### Key Insights

1. **No free lunch**: Every optimization has a cost
2. **Workload determines choice**: Know your read/write ratio
3. **Hybrid approaches emerging**: Best of both worlds
4. **Hardware drives innovation**: NVMe, Optane, computational storage

The physics of storage—seek time, sequential vs random I/O, memory hierarchy—creates immutable constraints. Storage engines are our negotiation with these constraints.

---

**Mental Model**: Storage engines convert between write-optimized (sequential) and read-optimized (indexed) representations, with LSM trees favoring writes through sequential operations and B-trees favoring reads through hierarchical indexing.

Continue to [Polyglot Persistence →](polyglot.md)